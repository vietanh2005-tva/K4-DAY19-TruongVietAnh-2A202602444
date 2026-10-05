# Kiểm chứng bonus

Mặc định GRAPH_ONTOLOGY=bonus. Không sửa tests gốc hoặc bench_kg.py.

```powershell
python -m pytest tests/ -q
$env:PYTHONIOENCODING="utf-8"
$env:GRAPH_ONTOLOGY="hint"
python bench_kg.py --judge --out ket_qua_benchmark_kg.hint.txt
# Chỉ tiếp tục khi lượt hint thành công.
$env:GRAPH_ONTOLOGY="bonus"
python bench_kg.py --check
python bench_kg.py --judge --out ket_qua_benchmark_kg.txt
```

Mỗi lệnh bench xóa và dựng lại graph: chỉ dùng database lab. Lượt cuối để lại graph bonus đầy đủ. Hai benchmark cần cùng provider, model, top-k, chunk-size. Kết quả có biến động LLM, không sửa tay số liệu. HINT dùng helper gốc và chọn khoản 1 + khoản chung chất; BONUS dùng bonus_graph.py.

Gemini mặc định được đổi sang gemini-3.5-flash-lite vì model cũ trả 404. src/llm.py bổ sung giá chat Standard ($0.30/$2.50 cho 1M token input/output) theo https://ai.google.dev/gemini-api/docs/pricing ngày 2026-10-05. Đây là ước tính theo bảng giá paid, không phải hóa đơn tài khoản. Gemini embedding-001 không có giá trong bảng repo: phần embedding hiện chưa tính USD, nên USD indexing là cận dưới; cần ghi rõ hạn chế này trong báo cáo. Không coi con số 0 của embedding là xác nhận miễn phí.

Gemini chat được giãn tối thiểu 4,2 giây giữa yêu cầu để phù hợp mức 15 request/phút của project hiện tại; retry tối đa 2 lần theo retryDelay khi gặp 429. Wall time benchmark gồm thời gian chờ quota, không phải chỉ độ trễ model. Cùng cấu hình này được áp dụng cho cả HINT/BONUS. Có thể cấu hình GEMINI_CHAT_INTERVAL theo quota của tài khoản, không đổi giữa hai lượt đối chứng.

Embedding Gemini được giãn tối thiểu 0,65 giây giữa yêu cầu (quota project 100/phút), có retry tối đa 2 lần; cấu hình GEMINI_EMBED_INTERVAL. Lượt HINT ban đầu hoàn tất trước khi thêm giới hạn embedding này; do đó không dùng chênh lệch thời gian indexing giữa HINT/BONUS để kết luận tốc độ ontology. Chất lượng, số token và graph diagnostics vẫn so sánh được với cùng model/dữ liệu.

BONUS yêu cầu evidence nguyên văn và bỏ các dòng giới thiệu bài khác cuối nguồn. JSON hoặc evidence sai được trích lại tối đa một lần, vẫn qua client có đo chi phí; không âm thầm bỏ dữ liệu. Vì vậy số lần gọi dựng graph có thể nhiều hơn số bài báo.

Sau benchmark, thu bằng chứng trên graph vừa dựng:

```powershell
python scripts/collect_bonus_evidence.py --mode hint
# Chạy ngay sau lượt HINT, trước khi dựng BONUS.
python scripts/collect_bonus_evidence.py --mode bonus
# Chạy ngay sau lượt BONUS.
```

File report/evidence/hint.json và bonus.json ghi Cypher, kết quả live và context Q3–Q5. Context chẩn đoán dùng cùng doc_ids chọn thủ công theo bài liên quan; không giả là vector retrieval và không thay điểm benchmark thật.

## Truy vấn bằng chứng và chụp ảnh

```cypher
// Q-A: ảnh kg_count.png
MATCH (n) RETURN labels(n)[0] AS label, count(*) AS n ORDER BY n DESC;

// Q-B: ảnh kg_cross_kb.png
MATCH p=(:Person)-[:HAS_PARTICIPATION]->(:Participation)-[:ACCUSED_OF]->(:Crime)<-[:DEFINES]-(:Article)
RETURN p LIMIT 25;

// Q-D: ảnh kg_my_case.png; kiểm tra người có trong graph trước.
MATCH p=(:Person {name:'Cái Quang Huy'})-[:HAS_PARTICIPATION]->(:Participation)-[:ACCUSED_OF]->(:Crime)<-[:DEFINES]-(:Article)
RETURN p;

// Ngưỡng MDMA Điều 250.
MATCH (:Article {id:'Điều 250 BLHS'})-[:HAS_CLAUSE]->(cl:Clause)-[:HAS_THRESHOLD]->(t:Threshold)-[:OF_SUBSTANCE]->(:Substance {name:'MDMA'})
RETURN cl.number, cl.penalty, t.point, t.min_g, t.max_g ORDER BY cl.number;

// Lượng và bằng chứng từ tin.
MATCH (k:Case)-[:HAS_QUANTITY]->(q:Quantity)-[:OF_SUBSTANCE]->(:Substance {name:'MDMA'})
RETURN k.name, q.doc_id, q.amount, q.value_g, q.qualifier, q.evidence;

// Tội, giai đoạn, mức án theo người/nguồn.
MATCH (p:Person)-[:HAS_PARTICIPATION]->(v:Participation)-[:IN_CASE]->(k:Case)
RETURN p.name, v.charge, v.stage, v.sentence, v.sentence_stage, v.doc_id, v.evidence;

// Tổng hợp Q6 từ graph.
MATCH (k:Case)-[:INVOLVES]->(:Substance {name:'MDMA'})
RETURN k.name, k.doc_id, k.summary ORDER BY k.doc_id;
```

Trước mỗi ảnh gõ :clear. Ảnh thấy ô query và Results overview. Dùng kết quả thực để điền ONTOLOGY mục 7 và REPORT_KG; không dùng ảnh mẫu hay số liệu fixture thay cho kết quả benchmark.
