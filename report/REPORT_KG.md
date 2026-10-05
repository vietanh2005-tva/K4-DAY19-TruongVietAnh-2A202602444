# Báo cáo Day 19 — Flat RAG vs GraphRAG

**Họ tên:** Trương Việt Anh  **MSSV:** 2A202602444  **Ngày:** 05/10/2026

## 1. Chi phí

Cấu hình: Gemini 3.5 Flash-Lite, Gemini embedding-001, `top_k=3`, `chunk_size=800`, 176 chunk; graph gồm 384 node và 720 cạnh. Số liệu lấy từ `ket_qua_benchmark_kg.txt`.

```text
== Indexing (one-off)
pipeline  calls    in_tok  out_tok       USD  seconds
flat        176         0        0   0.00000    129.5
graph       197     50859    13852   0.04989    219.0

== Querying (mean per question)
pipeline  recall  judge   in_tok  out_tok       USD  seconds
flat        0.51   1.50      696       66   0.00037     4.54
graph       1.00   2.00     4404      153   0.00170     4.77
```

| Chỉ số | Flat | Graph | Graph / Flat |
| --- | ---: | ---: | ---: |
| Indexing USD | 0.00000 | 0.04989 | Không xác định |
| Indexing giây | 129.5 | 219.0 | 1.69× |
| Mỗi câu: USD | 0.00037 | 0.00170 | 4.59× |
| Mỗi câu: giây | 4.54 | 4.77 | 1.05× |
| Mỗi câu: in_tok | 696 | 4404 | 6.33× |

GraphRAG tốn thêm chi phí dựng graph do gọi LLM để trích xuất thực thể, quan hệ và bằng chứng từ tin tức, trong đó có một lần gọi lại khi kết quả trích xuất không hợp lệ. Khi trả lời, ngữ cảnh chứa thêm dữ kiện đi qua nhiều quan hệ và các khoản luật nên số token đầu vào lớn hơn Flat RAG. Thời gian đo còn bao gồm chờ giới hạn số yêu cầu và mạng, không chỉ thời gian truy vấn Neo4j.

Endpoint embedding đang dùng không trả usage token, và bảng giá trong repo chưa ghi giá embedding-001; vì vậy số 0 ở Flat indexing là phần chi phí chưa đo được, không có nghĩa embedding miễn phí. Chi phí indexing hiện chưa gồm embedding; USD là ước tính theo giá paid, không phải hóa đơn tài khoản. Không tính tỷ lệ USD indexing vì mẫu số bằng 0; các tỷ lệ còn lại tính từ số đã làm tròn trong file kết quả.

## 2. Từng câu hỏi

| Câu | Loại | Flat recall / judge | Graph recall / judge | Thắng | Vì sao |
| --- | --- | --- | --- | --- | --- |
| Q1 | single-hop-law | 1.00 / 2 | 1.00 / 2 | Hòa; Flat tiết kiệm hơn | Định nghĩa tiền chất nằm ngay trong văn bản luật, chưa cần đi qua quan hệ. |
| Q2 | single-hop-news | 1.00 / 2 | 1.00 / 2 | Hòa; Flat tiết kiệm hơn | Một bài báo đã nêu đủ Trần Thanh Tuấn và Trần Minh Tâm bị tuyên tử hình. |
| Q3 | cross-kb | 0.33 / 1 | 1.00 / 2 | Graph | Graph nối Lê Minh Thành với tội mua bán và Điều 251 khoản 1; Flat chỉ tìm được mức án 36 tháng. |
| Q4 | cross-kb | 0.33 / 1 | 1.00 / 2 | Graph | Graph đưa cả khoản có khung cao nhất của Điều 255 vào ngữ cảnh; Flat thiếu thông tin mức phạt tối đa. |
| Q5 | cross-kb-multi-hop | 0.40 / 1 | 1.00 / 2 | Graph | Graph nối Cái Quang Huy, tội vận chuyển, lượng MDMA và ngưỡng khoản 4 Điều 250; Flat thiếu khoản và khung phạt. |
| Q6 | aggregation | 0.00 / 2 | 1.00 / 2 | Graph khi đọc nội dung | Graph tìm trên toàn bộ các vụ có MDMA; Flat lặp hai kiện hàng cùng một vụ và bỏ sót vụ Viện Pháp y tâm thần. |

Q3–Q5 cho thấy lợi ích của cầu nối giữa tin tức và luật. Riêng Q6, judge của hai hệ thống bằng nhau nhưng câu trả lời không có chất lượng tương đương; cần đọc nội dung chứ không chỉ nhìn điểm tổng hợp. Q4 và Q5 là đối chiếu với phiên bản luật trong dữ liệu lab, không phải khẳng định mức án đã tuyên cho người trong tin tức.

## 3. Phân tích lỗi

### Lỗi E3: Một vụ việc có nhiều node theo nguồn bài báo

- **Hiện tượng:** graph có 5 node Case liên quan MDMA, trong khi benchmark gom thành 3 nhóm vụ việc. Vụ Cái Quang Huy có hai tên và hai nguồn; hai bài về Viện Pháp y tâm thần cũng tạo hai Case riêng.
- **Bằng chứng:** truy vấn và kết quả lưu trong `report/evidence/bonus.json`, mục `mdma_cases`:

```cypher
MATCH (k:Case)-[:INVOLVES]->(:Substance {name:'MDMA'})
RETURN k.name AS name, k.doc_id AS doc_id ORDER BY doc_id;
```

| name | doc_id |
| --- | --- |
| Vụ vận chuyển ma túy từ Đức về Việt Nam qua sân bay Nội Bài | news-100260917203001265 |
| Vụ vận chuyển ma túy qua sân bay Nội Bài | news-100260918080821054 |
| Vụ mua bán trái phép chất ma túy tại Hà Nội | news-100260918080821054 |
| Vụ sai phạm tại Viện Pháp y tâm thần Trung ương | news-100260924105118645 |
| Vụ tàng trữ và tổ chức sử dụng trái phép chất ma túy tại Viện Pháp y tâm thần Trung ương và bãi biển Sầm Sơn | news-100260930085028036 |

Trong câu trả lời Graph Q6, mục 3 còn liệt kê hai tên vụ Viện Pháp y tâm thần cùng nhau. Kết quả đạt recall 1.00 và judge 2 nhưng chưa chứng minh Case đã được hợp nhất đúng ngoài đời.

- **Nguyên nhân:** `src/bonus_graph.py` dùng khóa Case theo `doc_id` và vị trí vụ trong nguồn. Cách này giữ được xuất xứ, nhưng `MERGE` chỉ gộp cùng khóa, không nhận ra hai bài nói về cùng một sự kiện. Tên vụ do LLM đặt nên không đủ làm khóa toàn cục; bản thân hai bài Viện Pháp y có thể mô tả các phần khác nhau của cùng vụ án, không nên gộp chỉ vì trùng tên người.
- **Đề xuất sửa:** thêm bước phân giải vụ việc trong `src/bonus_graph.py`: tạo ứng viên từ người, địa điểm, thời gian và hành vi, rồi đối chiếu nội dung để liên kết các Case nguồn với một `CanonicalCase`. Giữ các assertion nguồn và giai đoạn tố tụng riêng; `bonus_context` tổng hợp theo CanonicalCase sau khi xác nhận. Đánh đổi là thêm logic, chi phí đối chiếu và nguy cơ gộp nhầm hai sự kiện liên quan; trường hợp chưa chắc chắn cần giữ riêng.

### Lỗi E4: Judge cho điểm đủ dù câu trả lời Flat Q6 thiếu và trùng vụ

- **Hiện tượng:** Flat Q6 có `recall=0.00` nhưng `judge=2`. Điểm judge biểu thị trả lời đủ, trong khi nội dung không bao phủ đủ ba nhóm vụ trong dữ liệu.
- **Bằng chứng:** trích `ket_qua_benchmark_kg.txt`:

```text
--- Q6 [aggregation] flat recall=0.00 judge=2 4.36s
Dựa trên ngữ cảnh, cả 3 vụ việc đều có liên quan đến ma túy MDMA:

1. **Vụ việc thứ nhất:** Lực lượng chức năng phát hiện các viên nén màu xanh bên trong thùng hàng là MDMA (Ngữ cảnh [1]).
2. **Vụ việc thứ hai:** Công an bắt quả tang Thành mang 5 viên nén màu trắng đi bán, kết quả giám định xác định đây là ma túy MDMA (Ngữ cảnh [2]).
3. **Vụ việc thứ ba:** Kết quả giám định xác định số viên nén hình tam giác màu hồng - xám trong kiện hàng là MDMA (Ngữ cảnh [3]).
```

Ba từ khóa bắt buộc của Q6 trong `data/benchmark_kg.json` là `Cái Quang Huy`, `Lê Minh Thành`, `Pháp y tâm thần`. Hai kiện hàng màu xanh và hồng–xám đều thuộc bài `news-100260917203001265`, không phải hai vụ độc lập. Câu trả lời cũng không nhắc vụ Viện Pháp y tâm thần Trung ương.

- **Nguyên nhân:** judge dựa vào đánh giá của LLM và đã chấp nhận danh sách ba tình tiết như ba vụ đầy đủ, không kiểm tra định danh vụ hoặc độ bao phủ nguồn. Recall dùng chuỗi từ khóa nên cũng không phản ánh hoàn toàn mức hiểu nội dung: gọi “Thành” vẫn có thể chỉ đúng Lê Minh Thành nhưng không khớp chuỗi tên đầy đủ.
- **Đề xuất sửa:** bổ sung kiểm tra ở tầng đánh giá trong một script riêng: ánh xạ tên/alias về định danh vụ, tính coverage theo nhóm vụ và kiểm tra trùng sự kiện trước khi gọi judge. Prompt judge cần yêu cầu đối chiếu từng nhóm vụ trong gold và nêu vụ bị bỏ sót; có thể kiểm tra thủ công những trường hợp recall và judge trái nhau. Không sửa kết quả hoặc phép chấm của benchmark nộp bài. Đánh đổi là phải chuẩn bị danh sách alias/nhóm vụ, và việc yêu cầu judge giải thích tăng token.

## 4. Kết luận

Flat RAG đủ cho câu hỏi lấy thông tin trực tiếp từ một tài liệu như Q1 và Q2: cả hai hệ thống đều đạt recall 1.00, judge 2, trong khi Flat có chi phí trung bình mỗi câu 0.00037 USD, thấp hơn Graph 0.00170 USD. GraphRAG phù hợp hơn khi câu hỏi nối tin tức với luật hoặc cần tổng hợp nhiều nguồn: Q3–Q5 tăng recall từ 0.33–0.40 lên 1.00, và Q6 tìm đủ ba nhóm vụ mà Flat bỏ sót.

Trong lượt chạy này, Graph đạt recall trung bình 1.00 so với 0.51 của Flat, judge 2.00 so với 1.50; đổi lại indexing lâu hơn 1.69 lần và token đầu vào mỗi câu lớn hơn 6.33 lần. Đây là kết quả trên 6 câu hỏi, không đủ để kết luận hệ thống luôn đúng; lỗi trùng Case và judge Q6 cho thấy vẫn cần kiểm tra bằng chứng gốc. Thiết kế bonus cải thiện Graph Q4 và Q6 từ recall 0.67/judge 1 lên 1.00/2 so với bản gợi ý; số liệu trước–sau ở `ket_qua_benchmark_kg.hint.txt` và `report/BONUS_RESULTS.md`.

## 5. Tự kiểm

```text
$ python -m pytest tests/ -q -p no:cacheprovider
.......................................................                  [100%]
55 passed in 0.10s
```

Gồm 48 bài kiểm tra gốc và 7 bài kiểm tra bổ sung cho ontology bonus. Tắt cache chỉ để tránh ghi cache trong lần kiểm tra, không bỏ qua test.

Kết quả `--check` đã chạy, lưu tại `report/self_check.txt`:

```text
$ python bench_kg.py --check
[OK] Dữ liệu: 18 điều luật, 20 bài báo
[OK] KG-1 link_entity
[OK] Neo4j kết nối được
[provider] chat = gemini:gemini-3.5-flash-lite | embedding = gemini:gemini-embedding-001
[OK] KG-2 build_graph: 265 node / 526 cạnh, đường xuyên 2 KB dài 2 cạnh
[OK] KG-3 context: 8 dữ kiện, có Điều 251
[OK] KG-4 GraphRAGAgent.answer
[OK] Chi phí check: 1 lần gọi LLM, $0.00381. Graph nhỏ (luật + 1 bài) vẫn còn trong Neo4j để bạn xem; chạy --judge để dựng graph đầy đủ.
```

Sau `--check` đã chạy lại `--judge`; graph dùng để chụp ảnh là graph đầy đủ 384 node/720 cạnh, không phải graph nhỏ của self-check.

Ảnh Neo4j: `report/img/kg_count.png`, `report/img/kg_cross_kb.png`, `report/img/kg_my_case.png`. Người chọn cho ảnh vụ án: **Cái Quang Huy**. Truy vấn dùng `HAS_PARTICIPATION` và `IN_CASE` thay cho `INVOLVED_IN` để khớp ontology bonus.
