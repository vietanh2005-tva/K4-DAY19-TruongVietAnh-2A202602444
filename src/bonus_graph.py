"""Source-scoped assertions, canonical substances and mass thresholds.

No benchmark answers are used here. Legal rules come from the supplied law
documents, and news assertions must include verbatim source evidence.
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata

from .graph import NEWS_EXTRACTION_PROMPT, find_substances, link_entity, parse_law_article


def canonical_text(value: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", value).casefold()).strip().strip('"\'“”‘’')


SUBSTANCE_ALIASES = {
    "Heroine": ["heroine", "heroin"],
    "Cocaine": ["cocaine", "cocain"],
    "Methamphetamine": ["methamphetamine", "methamphetamin", "ma túy đá"],
    "Amphetamine": ["amphetamine", "amphetamin"],
    "MDMA": ["mdma", "thuốc lắc"],
    "XLR-11": ["xlr-11"],
    "Ketamine": ["ketamine", "ketamin"],
    "Etomidate": ["etomidate"],
    "cần sa": ["cần sa", "cannabis"],
    "thuốc phiện": ["thuốc phiện"],
    "côca": ["côca", "coca"],
}


def canonical_substance(value: str) -> str:
    key = canonical_text(value)
    for name, aliases in SUBSTANCE_ALIASES.items():
        if key == canonical_text(name) or key in aliases:
            return name
    # Unknown names are retained rather than forced into an unrelated substance.
    return key


def substances_in(text: str) -> list[str]:
    text = canonical_text(text)
    return [name for name, aliases in SUBSTANCE_ALIASES.items()
            if any(re.search(r"(?<!\w)" + re.escape(a) + r"(?!\w)", text) for a in aliases)]


NUMBER = r"\d+(?:[.,]\d+)*"
UNIT = r"(?:kilôgam|kilogam|kg|gam|gr|g)"
MASS = re.compile(rf"(?P<n>{NUMBER})\s*(?P<u>{UNIT})(?!\w)", re.I)


def grams(number: str, unit: str) -> float:
    # Vietnamese prose: 9,6kg is decimal; 1.000 gam is a thousands separator.
    if "," in number:
        number = number.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(?:\.\d{3})+", number):
        number = number.replace(".", "")
    return float(number) * (1000 if unit.lower() in {"kg", "kilôgam", "kilogam"} else 1)


def parse_quantity(text: str) -> dict:
    """Keep qualifiers: an approximate mass must not become an exact legal fact."""
    matches = list(MASS.finditer(text))
    result = {"amount": text, "value_g": None, "qualifier": "unknown"}
    if len(matches) != 1 or "đến" in text:
        return result
    match = matches[0]
    prefix = canonical_text(text[:match.start()])
    qualifier = "exact"
    if any(x in prefix for x in ["khoảng", "gần", "xấp xỉ", "chừng"]):
        qualifier = "approximate"
    elif "hơn" in prefix or "trên" in prefix:
        qualifier = "lower_bound"
    elif "dưới" in prefix:
        qualifier = "upper_bound"
    result.update(value_g=grams(match["n"], match["u"]), qualifier=qualifier)
    return result


def parse_thresholds(article: dict) -> list[dict]:
    rules = []
    for clause in article["clauses"]:
        for point, text in re.findall(r"^([a-zđ])\)\s*(.+)$", clause["text"], re.M):
            # Only named, chemically unambiguous substances. Plant/resin forms,
            # mixtures and liquid volumes need additional modeling.
            names = [n for n in substances_in(text)
                     if n not in {"cần sa", "thuốc phiện", "côca"}]
            if not names or "khối lượng" not in text:
                continue
            masses = list(MASS.finditer(text))
            minimum = maximum = None
            if len(masses) == 2 and "đến dưới" in text:
                minimum = grams(masses[0]["n"], masses[0]["u"])
                maximum = grams(masses[1]["n"], masses[1]["u"])
            elif len(masses) == 1 and "trở lên" in text:
                minimum = grams(masses[0]["n"], masses[0]["u"])
            if minimum is None:
                continue
            for name in names:
                rules.append({"id": f"{clause['id']}:{point}:{name}",
                              "clause_id": clause["id"], "substance": name,
                              "point": point, "min_g": minimum, "max_g": maximum,
                              "text": text, "doc_id": article["doc_id"]})
    return rules


def threshold_matches(quantity: dict, threshold: dict) -> bool:
    value, qualifier = quantity.get("value_g"), quantity.get("qualifier")
    if value is None:
        return False
    low, high = threshold["min_g"], threshold.get("max_g")
    if qualifier == "lower_bound":
        return high is None and value >= low
    return qualifier == "exact" and value >= low and (high is None or value < high)


BONUS_EXTRACTION_RULES = """
YÊU CẦU BỔ SUNG:
- Chỉ trích các vụ chính của bài; bỏ đoạn giới thiệu/link bài liên quan ở cuối.
- Mỗi case thêm evidence: một đoạn nguyên văn chứng minh vụ đó.
- Mỗi person thêm stage (điều tra|truy tố|sơ thẩm|phúc thẩm|khác|không rõ),
  evidence (đoạn nguyên văn chứng minh role/charge/sentence), sentence_stage
  (giai đoạn bản án được tuyên; không gán án sơ thẩm cho phúc thẩm chưa xử).
- Tội danh từng người phải đúng người đó. Không lấy tội chung của vụ gán cho tất cả.
- Với substances, thêm evidence nguyên văn và amount giữ cả 'hơn', 'gần', 'khoảng'.
  Dùng tổng khối lượng được bài nói rõ cho vụ; không tự cộng những lần thu giữ.
- Giữ tên đầy đủ và biệt danh trong aliases; không suy đoán danh tính.
- Không biết thì để chuỗi rỗng; không tự suy mức án hoặc tội danh từ Điều luật.
"""


def extract_bonus_cases(doc, llm_fn, crimes):
    # One repair attempt for schema/grounding failures, measured by the same LLM.
    # Never discard a malformed extraction and claim the graph is complete.
    for attempt in range(2):
        try:
            return _extract_bonus_cases_once(doc, llm_fn, crimes, repair=bool(attempt))
        except ValueError:
            if attempt:
                raise
            print(f"[Extraction] Kiểm tra lại JSON/bằng chứng của {doc.id}.", flush=True)
    raise RuntimeError("Extraction retries exhausted")


def _extract_bonus_cases_once(doc, llm_fn, crimes, repair=False):
    template = NEWS_EXTRACTION_PROMPT.replace(
        '"summary": "1-2 câu tóm tắt",',
        '"summary": "1-2 câu tóm tắt", "evidence": "một đoạn nguyên văn trong bài",',
    ).replace(
        '"amount": "khối lượng nếu có"',
        '"amount": "khối lượng nếu có", "evidence": "đoạn nguyên văn nói về chất/khối lượng"',
    ).replace(
        '"sentence": "mức án nếu có, ví dụ: tử hình, 8 năm tù"',
        '"sentence": "mức án nếu có, ví dụ: tử hình, 8 năm tù", '
        '"stage": "điều tra|truy tố|sơ thẩm|phúc thẩm|không rõ", '
        '"sentence_stage": "sơ thẩm|phúc thẩm|không rõ", '
        '"evidence": "đoạn nguyên văn nói về người này"',
    )
    prompt = BONUS_EXTRACTION_RULES + template.format(
        crimes="; ".join(crimes), substances=", ".join(SUBSTANCE_ALIASES),
        title=doc.metadata.get("title", ""), content=doc.content,
    )
    prompt += "\nKẾT THÚC DỮ LIỆU BÀI BÁO.\n" + BONUS_EXTRACTION_RULES
    prompt += ('\nNếu chủ đề CHÍNH là tuyên truyền/hội nghị/chiến dịch thì trả {"cases": []}; '
               'không trích vụ ở dòng giới thiệu bài khác cuối trang. '
               'Mọi evidence phải là một đoạn LIÊN TIẾP sao chép nguyên văn, '
               'không diễn đạt lại và không dùng dấu ... để nối đoạn.')
    if repair:
        prompt += ('\nLần trước bị lỗi schema hoặc evidence. Kiểm tra lại từng evidence '
                   'trước khi trả JSON; nếu bài chính không có vụ cụ thể, cases phải rỗng.')
    raw = llm_fn(prompt, json_mode=True)
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid extraction JSON for {doc.id}") from error
    if not isinstance(payload, dict) or not isinstance(payload.get("cases"), list):
        raise ValueError(f"Expected cases list for {doc.id}")
    source = canonical_text(doc.content)
    cases = []
    for case in payload["cases"]:
        if not isinstance(case, dict):
            raise ValueError(f"Invalid case in {doc.id}")
        evidence = case.get("evidence", "")
        if not isinstance(evidence, str) or not evidence.strip() or canonical_text(evidence) not in source:
            raise ValueError(f"Case evidence is missing or not verbatim in {doc.id}")
        case["charges"] = list(dict.fromkeys(filter(None, (link_entity(x, crimes)
                                 for x in case.get("charges", []) if isinstance(x, str)))))
        people = []
        for p in case.get("people", []):
            if not isinstance(p, dict) or not isinstance(p.get("name"), str) or not p["name"].strip():
                continue
            quote = p.get("evidence", "")
            if not quote or canonical_text(quote) not in source:
                raise ValueError(f"Person evidence missing or not verbatim in {doc.id}")
            p["charge"] = link_entity(p.get("charge") or "", crimes) or ""
            people.append(p)
        case["people"] = people
        substances = []
        for s in case.get("substances", []):
            if not isinstance(s, dict) or not s.get("name"):
                continue
            quote = s.get("evidence", "")
            if not quote or canonical_text(quote) not in source:
                raise ValueError(f"Quantity evidence missing or not verbatim in {doc.id}")
            s["name"] = canonical_substance(s["name"])
            s.update(parse_quantity(s.get("amount") or ""))
            substances.append(s)
        case["substances"] = substances
        cases.append(case)
    return cases


def stable_id(*parts: str) -> str:
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()[:24]


def build_bonus_graph(graph, law_docs, news_docs, llm_fn):
    for label, key in [("Article", "id"), ("Clause", "id"), ("Crime", "name"),
                       ("Case", "id"), ("Person", "id"), ("Participation", "id"),
                       ("Substance", "name"), ("Location", "name"),
                       ("Quantity", "id"), ("Threshold", "id")]:
        graph.run(f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{label}) REQUIRE n.{key} IS UNIQUE")
    articles = [parse_law_article(doc) for doc in law_docs]
    for article in articles:
        for clause in article["clauses"]:
            clause["substances"] = substances_in(clause["text"])
        graph.add_law_article(article)
        for threshold in parse_thresholds(article):
            graph.run("""
                MATCH (cl:Clause {id: $clause_id})
                MERGE (t:Threshold {id: $id})
                SET t.point=$point, t.min_g=$min_g, t.max_g=$max_g,
                    t.text=$text, t.doc_id=$doc_id
                MERGE (cl)-[:HAS_THRESHOLD]->(t)
                MERGE (s:Substance {name: $substance})
                MERGE (t)-[:OF_SUBSTANCE]->(s)
            """, **threshold)
    crimes = [a["crime"] for a in articles if a["crime"]]
    for doc in news_docs:
        for index, case in enumerate(extract_bonus_cases(doc, llm_fn, crimes)):
            case_id = f"{doc.id}:case:{index}"
            graph.run("""
                MERGE (k:Case {id: $id})
                SET k.name=$name, k.summary=$summary, k.date=$date,
                    k.doc_id=$doc_id, k.source_title=$title, k.evidence=$evidence
                FOREACH (name IN $charges |
                    MERGE (c:Crime {name:name}) MERGE (k)-[:CHARGED_WITH]->(c))
                FOREACH (name IN CASE WHEN $location='' THEN [] ELSE [$location] END |
                    MERGE (l:Location {name:name}) MERGE (k)-[:LOCATED_IN]->(l))
            """, id=case_id, name=case.get("name") or doc.metadata.get("title", doc.id),
                      summary=case.get("summary") or "", date=case.get("date") or "",
                      doc_id=doc.id, title=doc.metadata.get("title", ""), evidence=case["evidence"],
                      charges=case["charges"], location=canonical_text(case.get("location") or ""))
            for p in case["people"]:
                name = unicodedata.normalize("NFC", p["name"]).strip()
                person_id = stable_id(canonical_text(name))
                # A person may occur in several reports; assertions are source-scoped.
                participation_id = stable_id(case_id, person_id, p.get("stage") or "không rõ",
                                             p.get("charge") or "", p.get("sentence") or "")
                aliases = [x for x in p.get("aliases", []) if isinstance(x, str) and x.strip()]
                graph.run("""
                    MATCH (k:Case {id:$case_id})
                    MERGE (p:Person {id:$person_id}) SET p.name=$name
                    SET p.aliases=reduce(acc=coalesce(p.aliases, []), x IN $aliases |
                        CASE WHEN x IN acc THEN acc ELSE acc + [x] END)
                    MERGE (v:Participation {id:$id})
                    SET v.doc_id=$doc_id, v.role=$role, v.stage=$stage,
                        v.sentence=$sentence, v.sentence_stage=$sentence_stage,
                        v.evidence=$evidence, v.charge=$charge
                    MERGE (p)-[:HAS_PARTICIPATION]->(v)
                    MERGE (v)-[:IN_CASE]->(k)
                    FOREACH (name IN CASE WHEN $charge='' THEN [] ELSE [$charge] END |
                        MERGE (c:Crime {name:name}) MERGE (v)-[:ACCUSED_OF]->(c)
                        MERGE (k)-[:CHARGED_WITH]->(c))
                """, case_id=case_id, person_id=person_id, id=participation_id, name=name,
                          aliases=aliases, doc_id=doc.id, role=p.get("role") or "",
                          stage=p.get("stage") or "không rõ", sentence=p.get("sentence") or "",
                          sentence_stage=p.get("sentence_stage") or "không rõ",
                          evidence=p["evidence"], charge=p["charge"])
            for qi, s in enumerate(case["substances"]):
                graph.run("""
                    MATCH (k:Case {id:$case_id})
                    MERGE (s:Substance {name:$name})
                    MERGE (q:Quantity {id:$id})
                    SET q.doc_id=$doc_id, q.amount=$amount, q.value_g=$value_g,
                        q.qualifier=$qualifier, q.evidence=$evidence
                    MERGE (k)-[:HAS_QUANTITY]->(q)
                    MERGE (q)-[:OF_SUBSTANCE]->(s)
                    MERGE (k)-[r:INVOLVES]->(s) SET r.amount=$amount
                """, case_id=case_id, id=f"{case_id}:quantity:{qi}", doc_id=doc.id,
                          name=s["name"], amount=s["amount"], value_g=s["value_g"],
                          qualifier=s["qualifier"], evidence=s["evidence"])


def retrieve_context(graph, question, doc_ids, max_facts, mode):
    """Question-directed expansion; substantive answers come from source text."""
    if max_facts <= 0:
        return []
    question_key = canonical_text(question)
    bonus = mode == "bonus"
    seed_ids, seed_edges = graph.seed_facts(question, doc_ids, limit=max_facts)
    facts = []
    substance_names = substances_in(question) if bonus else find_substances(question)
    aggregate = bool(substance_names and re.search(r"những vụ|các vụ|vụ việc nào|liệt kê", question_key))
    maximum = bool(re.search(r"tối đa|cao nhất|nặng nhất", question_key))
    basic = bool(re.search(r"cơ bản|khoản 1", question_key))
    named_people = graph.run("""
        MATCH (p:Person)
        WHERE toLower($q) CONTAINS toLower(p.name)
           OR any(a IN coalesce(p.aliases, []) WHERE toLower($q) CONTAINS toLower(a))
        RETURN elementId(p) AS id
    """, q=unicodedata.normalize("NFC", question))
    person_ids = [p["id"] for p in named_people]
    if bonus:
        cases = graph.run("""
            MATCH (k:Case)
            WHERE ($aggregate AND EXISTS {
                MATCH (k)-[:INVOLVES]->(s:Substance) WHERE s.name IN $substances })
            OR (NOT $aggregate AND size($people)>0 AND EXISTS {
                MATCH (p:Person)-[:HAS_PARTICIPATION]->(:Participation)-[:IN_CASE]->(k)
                WHERE elementId(p) IN $people })
            OR (NOT $aggregate AND size($people)=0 AND (elementId(k) IN $ids OR EXISTS {
                MATCH (s)--(k) WHERE elementId(s) IN $ids }))
            RETURN k.id AS key, k.name AS name, k.summary AS summary, k.doc_id AS doc_id
            ORDER BY k.id
        """, aggregate=aggregate, substances=substance_names, people=person_ids, ids=seed_ids)
    else:
        cases = graph.run("""
            MATCH (k:Case)
            WHERE elementId(k) IN $ids OR EXISTS { MATCH (s)--(k) WHERE elementId(s) IN $ids }
            RETURN k.name AS key, k.name AS name, k.summary AS summary, k.doc_id AS doc_id
            ORDER BY k.name
        """, ids=seed_ids)
    case_keys = [k["key"] for k in cases]
    for case in cases:
        facts.append(f"[{case['doc_id']}] Vụ việc '{case['name']}': {case['summary']}")
    if bonus:
        people = graph.run("""
            MATCH (p:Person)-[:HAS_PARTICIPATION]->(v:Participation)-[:IN_CASE]->(k:Case)
            WHERE k.id IN $keys AND (size($people)=0 OR elementId(p) IN $people)
            RETURN p.name AS name, k.id AS case_id, properties(v) AS assertion
            ORDER BY p.name
        """, keys=case_keys, people=person_ids)
        for p in people:
            v = p["assertion"]
            facts.append(f"[{v['doc_id']}] {p['name']}: vai trò {v['role']}; "
                         f"giai đoạn {v['stage']}; tội/hành vi {v['charge'] or 'chưa xác định'}; "
                         f"mức án {v['sentence'] or 'chưa có thông tin'} "
                         f"(giai đoạn bản án: {v['sentence_stage']}). Bằng chứng: {v['evidence']}")
    else:
        for p in graph.run("""
            MATCH (p:Person)-[r:INVOLVED_IN]->(k:Case) WHERE k.name IN $keys
            RETURN p.name AS name, properties(r) AS assertion
        """, keys=case_keys):
            facts.append(f"{p['name']}: {p['assertion']}")
    quantities = []
    if bonus:
        quantities = graph.run("""
            MATCH (k:Case)-[:HAS_QUANTITY]->(q:Quantity)-[:OF_SUBSTANCE]->(s:Substance)
            WHERE k.id IN $keys
            RETURN k.id AS case_id, s.name AS substance, properties(q) AS quantity
        """, keys=case_keys)
        for q in quantities:
            facts.append(f"[{q['quantity']['doc_id']}] {q['substance']}: "
                         f"{q['quantity']['amount']}; bằng chứng: {q['quantity']['evidence']}")

    # Retrieve each person's legal charge when available; case charges are used
    # for unnamed/general questions or when their personal charge is unknown.
    legal_cases = graph.run("""
        MATCH (k:Case)-[:CHARGED_WITH]->(c:Crime)<-[:DEFINES]-(a:Article)-[:HAS_CLAUSE]->(cl:Clause)
        WHERE (CASE WHEN $bonus THEN k.id ELSE k.name END) IN $keys
          AND (NOT $bonus OR size($people)=0 OR EXISTS {
              MATCH (p:Person)-[:HAS_PARTICIPATION]->(v:Participation)-[:IN_CASE]->(k)
              WHERE elementId(p) IN $people AND
                  (v.charge='' OR EXISTS { MATCH (v)-[:ACCUSED_OF]->(c) }) })
        OPTIONAL MATCH (cl)-[:HAS_THRESHOLD]->(t:Threshold)-[:OF_SUBSTANCE]->(s:Substance)
        RETURN k.id AS case_id, a.id AS article, a.title AS title,
               cl.id AS clause_id, cl.number AS number, cl.text AS text, cl.penalty AS penalty,
               collect(CASE WHEN t IS NULL THEN null ELSE
                   {min_g:t.min_g, max_g:t.max_g, substance:s.name, point:t.point} END) AS thresholds,
               EXISTS { MATCH (k)-[:INVOLVES]->(:Substance)<-[:MENTIONS]-(cl) } AS shared_substance
        ORDER BY a.id, cl.number
    """, bonus=bonus, keys=case_keys, people=person_ids)
    article_numbers = re.findall(r"[Đđ]iều\s+(\d+)", question)
    law_rows = graph.run("""
        MATCH (a:Article)-[:HAS_CLAUSE]->(cl:Clause)
        WHERE elementId(a) IN $ids OR elementId(cl) IN $ids
            OR any(n IN $numbers WHERE a.id STARTS WITH 'Điều '+n+' ')
        RETURN a.id AS article, a.title AS title, cl.number AS number,
               cl.text AS text, cl.penalty AS penalty, cl.id AS clause_id
        ORDER BY a.id, cl.number
    """, ids=seed_ids, numbers=article_numbers)
    selected = []
    for row in legal_cases:
        keep = row["number"] == 1
        if bonus and maximum:
            # Includes high clauses without substance mentions (e.g. Article 255).
            keep = bool(row["penalty"])
        elif bonus and not basic:
            for q in quantities:
                if q["case_id"] != row["case_id"]:
                    continue
                if substance_names and q["substance"] not in substance_names:
                    continue
                for t in row["thresholds"]:
                    if t["substance"] == q["substance"] and threshold_matches(q["quantity"], t):
                        keep = True
                        facts.append(f"[{row['article']}] Đối chiếu khối lượng {q['quantity']['amount']} "
                                     f"{q['substance']} với ngưỡng điểm {t['point']} khoản {row['number']}: "
                                     f"từ {t['min_g']:g} gam" +
                                     (f" đến dưới {t['max_g']:g} gam" if t['max_g'] is not None else " trở lên") +
                                     ". Đây là đối chiếu ngưỡng, không khẳng định quyết định của tòa.")
                if q["quantity"].get("qualifier") in {"unknown", "approximate", "upper_bound"}:
                    keep = keep or row["shared_substance"]
        elif not bonus:
            keep = keep or row["shared_substance"]
        if keep:
            selected.append(row)
    # Law-only questions need actual clause text, including definitions such as
    # 'tiền chất' in non-first clauses, rather than just graph edge names.
    if not cases or article_numbers or re.search(r"theo luật|là gì|định nghĩa", question_key):
        selected.extend(law_rows)
    seen = set()
    for row in selected:
        if row["clause_id"] not in seen:
            seen.add(row["clause_id"])
            facts.append(f"[{row['article']} - {row['title']}] khoản {row['number']}: {row['text']}")
    # Facts carrying evidence/legal text have priority over generic one-hop edges.
    if not bonus or not facts:
        facts.extend(seed_edges)
    return list(dict.fromkeys(facts))[:max_facts]
