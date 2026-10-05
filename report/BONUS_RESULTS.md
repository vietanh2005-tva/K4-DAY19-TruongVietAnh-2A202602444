# Bằng chứng bonus từ lần chạy thật

Hai file benchmark giữ nguyên output của bench_kg.py --judge. Các context JSON là chẩn đoán Neo4j thật với cùng nguồn seed chọn thủ công, không phải vector search hoặc benchmark fixture.

| Câu | HINT Graph recall / judge | BONUS Graph recall / judge | Chênh lệch recall / judge |
| --- | --- | --- | --- |
| Q1 | 1.00 / 2 | 1.00 / 2 | +0.00 / +0 |
| Q2 | 1.00 / 2 | 1.00 / 2 | +0.00 / +0 |
| Q3 | 1.00 / 2 | 1.00 / 2 | +0.00 / +0 |
| Q4 | 0.67 / 1 | 1.00 / 2 | +0.33 / +1 |
| Q5 | 1.00 / 2 | 1.00 / 2 | +0.00 / +0 |
| Q6 | 0.67 / 1 | 1.00 / 2 | +0.33 / +1 |

## Quy mô graph và khả năng kiểm chứng

HINT: 197 node / 374 cạnh. BONUS: 384 node / 720 cạnh.

Label và relationship thực tế của BONUS:

| Loại | Số lượng |
| --- | --- |
| Article | 18 |
| Case | 14 |
| Clause | 99 |
| Crime | 13 |
| Location | 5 |
| Participation | 52 |
| Person | 43 |
| Quantity | 21 |
| Substance | 11 |
| Threshold | 108 |
| ACCUSED_OF | 27 |
| CHARGED_WITH | 15 |
| DEFINES | 13 |
| HAS_CLAUSE | 99 |
| HAS_PARTICIPATION | 52 |
| HAS_QUANTITY | 21 |
| HAS_THRESHOLD | 108 |
| INVOLVES | 21 |
| IN_CASE | 52 |
| LOCATED_IN | 14 |
| MENTIONS | 169 |
| OF_SUBSTANCE | 129 |

## Q4: câu trả lời trước/sau

HINT:

Dựa trên ngữ cảnh và dữ kiện từ knowledge graph:

- Giang hồ 'Hoàng Nato' (Dương Minh Tuấn) bị bắt về hành vi **tổ chức sử dụng trái phép chất ma túy**.
- Hành vi này được quy định tại **Điều 255 BLHS (Tội tổ chức sử dụng trái phép chất ma túy)**. Theo khoản 1 Điều 255 BLHS, hình phạt tù tối đa cho tội này là **07 năm** (mức phạt tù từ 02 năm đến 07 năm).

BONUS:

Dựa trên ngữ cảnh và dữ kiện từ knowledge graph:

- **Hành vi bị bắt:** Giang hồ "Hoàng Nato" (Dương Minh Tuấn) bị bắt để điều tra về hành vi **"tổ chức sử dụng trái phép chất ma túy"**.
- **Mức phạt tù tối đa:** Theo **Điều 255 BLHS (Tội tổ chức sử dụng trái phép chất ma túy)**, mức phạt tù cao nhất (tại khoản 4) là **20 năm hoặc tù chung thân** (nếu phạm tội thuộc các trường hợp gây tổn hại cho sức khỏe của 02 người trở lên mà tỷ lệ tổn thương cơ thể của mỗi người 61% trở lên hoặc làm chết 02 người trở lên).

## Q5: câu trả lời trước/sau

HINT:

Dựa trên ngữ cảnh và dữ kiện knowledge graph:

- **Tội danh:** Cái Quang Huy bị truy tố về **tội vận chuyển trái phép chất ma túy** (theo Điều 250 Bộ luật Hình sự).
- **Loại ma túy:** MDMA và Ketamine.
- **Khối lượng MDMA:** Hơn 9,6kg (tương đương 9.600 gam trở lên).
- **Khoản và khung hình phạt tương ứng:** 
  - Theo **khoản 4 Điều 250 BLHS**, tội vận chuyển trái phép chất ma túy đối với chất MDMA có khối lượng 100 gam trở lên sẽ áp dụng khung hình phạt: **phạt tù 20 năm, tù chung thân hoặc tử hình**.

BONUS:

Dựa trên ngữ cảnh và dữ kiện knowledge graph:

- **Tội danh:** Cái Quang Huy bị truy tố về tội "vận chuyển trái phép chất ma túy".
- **Loại ma túy:** MDMA và Ketamine.
- **Khối lượng MDMA:** Hơn 9,6kg.
- **Điều luật và khoản áp dụng:** Đối chiếu khối lượng hơn 9,6kg MDMA với điểm b khoản 4 **Điều 250 Bộ luật Hình sự (BLHS)** (ngưỡng từ 100 gam trở lên). 
- **Khung hình phạt:** Theo khoản 4 **Điều 250 BLHS**, hình phạt là **bị phạt tù 20 năm, tù chung thân hoặc tử hình**.

## Q6: câu trả lời trước/sau

HINT:

Dựa trên ngữ cảnh và dữ kiện từ knowledge graph, các vụ việc có liên quan đến ma túy MDMA bao gồm:

1. **Vụ vận chuyển hơn 10kg ma túy từ Đức về Việt Nam qua sân bay Nội Bài** (hoặc *Vụ vận chuyển ma túy qua sân bay Nội Bài do Cái Quang Huy thực hiện*): Vụ án liên quan đến việc vận chuyển hơn 9,6kg chất ma túy loại MDMA.
2. **Vụ mua bán trái phép chất ma túy do Lê Minh Thành và đồng phạm thực hiện**: Vụ án liên quan đến việc mua bán 5 viên ma túy loại MDMA.

BONUS:

Dựa trên ngữ cảnh và dữ kiện từ knowledge graph, các vụ việc liên quan đến ma túy MDMA bao gồm:

1. **Vụ việc 'Vụ vận chuyển ma túy từ Đức về Việt Nam qua sân bay Nội Bài'** (hoặc *Vụ vận chuyển ma túy qua sân bay Nội Bài*): Liên quan đến Cái Quang Huy bị cáo buộc vận chuyển ma túy (với tổng khối lượng MDMA là hơn 9,6kg, gồm gần 4,3kg MDMA phát hiện trong thùng hàng chứa viên nén màu xanh và hơn 5,3kg MDMA là các viên nén hình tam giác màu hồng - xám) và lôi kéo Nguyễn Tiến Đạt tham gia nhận hàng.
2. **Vụ việc 'Vụ mua bán trái phép chất ma túy tại Hà Nội'**: Liên quan đến Lê Minh Thành bị tuyên phạt 36 tháng tù và các đồng phạm (Trịnh Vũ Kiên, Kim Xuân Tuấn, Nguyễn Quang Hưng) bị tuyên phạt 24 tháng tù về tội mua bán trái phép chất ma túy khi mang 5 viên ma túy MDMA (ma túy "kẹo") đi bán tại khu vực đường Ngọc Thụy.
3. **Vụ việc 'Vụ sai phạm tại Viện Pháp y tâm thần Trung ương'** và **'Vụ tàng trữ và tổ chức sử dụng trái phép chất ma túy tại Viện Pháp y tâm thần Trung ương và bãi biển Sầm Sơn'**: Liên quan đến việc lực lượng công an thu giữ MDMA (0,686g MDMA theo cáo trạng) cùng các chất ma túy khác và dụng cụ sử dụng ma túy khi khám xét phòng điều trị của vợ chồng Nguyễn Thị Mai Anh và Lê Văn Đông tại Viện Pháp y tâm thần Trung ương.

## Điều kiện đọc số liệu

Cùng Gemini 3.5 Flash-Lite, Gemini embedding-001, top_k=3, chunk_size=800 và 176 chunk. LLM extraction và judge có thể biến động; đây là một cặp lượt chạy, không chứng minh cải thiện trên mọi dữ liệu.

Gemini embedding-001 không trả usage token qua endpoint đang dùng và không có giá trong bảng repo: số token/cost indexing thiếu phần embedding. USD là ước tính paid theo bảng giá, không phải hóa đơn tài khoản miễn phí. Không tính ratio USD có mẫu số 0.

BONUS có thêm giãn yêu cầu embedding để tránh quota 100/phút; không dùng chênh lệch thời gian indexing giữa HINT/BONUS làm bằng chứng tốc độ ontology. Thời gian query/indexing còn chịu chờ quota chat và mạng.

Cần đọc toàn bộ Per question; không chỉ dựa vào recall và judge. Bonus do giảng viên chấm, kết quả này không tự đảm bảo +15.
