"""Additional tests; original lab tests remain intact."""
import unittest
from src.bonus_graph import (canonical_substance, canonical_text, parse_quantity,
                             parse_thresholds, threshold_matches, substances_in,
                             retrieve_context, extract_bonus_cases)
from src.graph import load_markdown_docs, parse_law_article


class TestBonusOntology(unittest.TestCase):
    def test_mass_units_and_uncertainty(self):
        self.assertEqual(parse_quantity("hơn 9,6kg")["value_g"], 9600)
        self.assertEqual(parse_quantity("hơn 9,6kg")["qualifier"], "lower_bound")
        self.assertEqual(parse_quantity("1.000 gam")["value_g"], 1000)
        self.assertEqual(parse_quantity("gần 406g")["qualifier"], "approximate")
        self.assertIsNone(parse_quantity("5 viên")["value_g"])
        self.assertIsNone(parse_quantity("5g và 7g")["value_g"])

    def test_threshold_boundaries(self):
        finite = {"min_g": 30, "max_g": 100}
        top = {"min_g": 100, "max_g": None}
        self.assertTrue(threshold_matches(parse_quantity("30g"), finite))
        self.assertFalse(threshold_matches(parse_quantity("100g"), finite))
        self.assertTrue(threshold_matches(parse_quantity("100g"), top))
        self.assertTrue(threshold_matches(parse_quantity("hơn 9,6kg"), top))
        self.assertFalse(threshold_matches(parse_quantity("hơn 50g"), finite))
        self.assertFalse(threshold_matches(parse_quantity("gần 100g"), top))
        self.assertFalse(threshold_matches(parse_quantity("dưới 100g"), top))

    def test_substance_normalization(self):
        self.assertEqual(canonical_substance(" KETAMIN "), "Ketamine")
        self.assertEqual(canonical_substance("thuốc lắc"), "MDMA")
        self.assertEqual(substances_in("Methamphetamine"), ["Methamphetamine"])
        self.assertEqual(canonical_text("Tòa   án"), "tòa án")

    def test_rules_from_corpus(self):
        docs = load_markdown_docs("data/drug_law")
        article = parse_law_article(next(d for d in docs if d.id == "blhs-dieu-250"))
        mdma = [r for r in parse_thresholds(article) if r["substance"] == "MDMA"]
        self.assertEqual([(r["min_g"], r["max_g"]) for r in mdma],
                         [(0.1, 5), (5, 30), (30, 100), (100, None)])
        self.assertTrue(all(r["doc_id"] == "blhs-dieu-250" for r in mdma))

    def test_missing_evidence_is_not_silently_dropped(self):
        from src.models import Document
        doc = Document("fixture-news", "Một bài báo thử nghiệm", {})
        with self.assertRaisesRegex(ValueError, "evidence"):
            extract_bonus_cases(doc, lambda *a, **k: '{"cases":[{"name":"vụ"}]}', [])

    def test_maximum_penalty_includes_clause_without_substance_mentions(self):
        # Controlled fixture: isolates the retrieval defect; not a live benchmark.
        class FixtureGraph:
            def seed_facts(self, *args, **kwargs):
                return ["seed"], []

            def run(self, cypher, **params):
                if "AS thresholds" in cypher:
                    return [dict(case_id="fixture-case", article="Điều 255 BLHS",
                                 title="Tội tổ chức sử dụng", clause_id=f"255:{n}",
                                 number=n, penalty=penalty, text=penalty,
                                 thresholds=[], shared_substance=False)
                            for n, penalty in [(1, "02 năm đến 07 năm"),
                                               (4, "20 năm hoặc tù chung thân")]]
                if "AS key" in cypher:
                    return [dict(key="fixture-case", name="vụ thử", summary="",
                                 doc_id="fixture-news")]
                return []

        question = "Hành vi tổ chức sử dụng có thể bị phạt tù tối đa bao nhiêu?"
        bonus = retrieve_context(FixtureGraph(), question, [], 60, "bonus")
        hint = retrieve_context(FixtureGraph(), question, [], 60, "hint")
        self.assertTrue(any("chung thân" in f for f in bonus))
        self.assertFalse(any("chung thân" in f for f in hint))

    def test_mass_retrieval_selects_only_matching_nonbasic_clause(self):
        class FixtureGraph:
            def seed_facts(self, *args, **kwargs):
                return ["seed"], []

            def run(self, cypher, **params):
                if "AS key" in cypher:
                    return [dict(key="fixture-case", name="vụ thử", summary="",
                                 doc_id="fixture-news")]
                if "properties(q) AS quantity" in cypher:
                    return [dict(case_id="fixture-case", substance="MDMA",
                                 quantity=dict(parse_quantity("hơn 9,6kg"),
                                               doc_id="fixture-news", evidence="hơn 9,6kg MDMA"))]
                if "AS thresholds" in cypher:
                    return [dict(case_id="fixture-case", article="Điều 250 BLHS", title="vận chuyển",
                                 clause_id=f"250:{n}", number=n, text=f"Nội dung khoản {n}",
                                 penalty="phạt tù", shared_substance=True,
                                 thresholds=[dict(min_g=low, max_g=high, substance="MDMA", point="b")])
                            for n, low, high in [(1, .1, 5), (2, 5, 30), (3, 30, 100), (4, 100, None)]]
                return []

        facts = retrieve_context(FixtureGraph(), "Khối lượng MDMA thuộc khoản nào?", [], 60, "bonus")
        self.assertTrue(any("Nội dung khoản 4" in f for f in facts))
        self.assertFalse(any("Nội dung khoản 2" in f or "Nội dung khoản 3" in f for f in facts))
