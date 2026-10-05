"""Generate an evidence table from unedited benchmark and live diagnostics."""
import json
from pathlib import Path
import re


def read_scores(path):
    text = Path(path).read_text(encoding="utf-8")
    rows = {}
    for match in re.finditer(r"^--- (Q\d+) \[.*?\] (flat|graph) recall=([\d.]+) judge=(\d+) ([\d.]+)s\n", text, re.M):
        start = match.end()
        end = text.find("\n--- ", start)
        rows[(match[1], match[2])] = dict(recall=float(match[3]), judge=int(match[4]),
                                       seconds=float(match[5]), answer=text[start:end if end >= 0 else None].strip())
    if len(rows) != 12:
        raise ValueError(f"Expected all 12 judged answers in {path}")
    return text, rows


def main():
    hint_text, hint = read_scores("ket_qua_benchmark_kg.hint.txt")
    bonus_text, bonus = read_scores("ket_qua_benchmark_kg.txt")
    h = json.loads(Path("report/evidence/hint.json").read_text(encoding="utf-8"))
    b = json.loads(Path("report/evidence/bonus.json").read_text(encoding="utf-8"))
    lines = ["# Bằng chứng bonus từ lần chạy thật", "",
             "Hai file benchmark giữ nguyên output của bench_kg.py --judge. Các context JSON là chẩn đoán Neo4j thật với cùng nguồn seed chọn thủ công, không phải vector search hoặc benchmark fixture.", "",
             "| Câu | HINT Graph recall / judge | BONUS Graph recall / judge | Chênh lệch recall / judge |",
             "| --- | --- | --- | --- |"]
    for qi in range(1, 7):
        a, z = hint[(f"Q{qi}", "graph")], bonus[(f"Q{qi}", "graph")]
        lines.append(f"| Q{qi} | {a['recall']:.2f} / {a['judge']} | {z['recall']:.2f} / {z['judge']} | {z['recall']-a['recall']:+.2f} / {z['judge']-a['judge']:+d} |")
    lines += ["", "## Quy mô graph và khả năng kiểm chứng", "",
              f"HINT: {h['stats']['nodes']} node / {h['stats']['relationships']} cạnh. BONUS: {b['stats']['nodes']} node / {b['stats']['relationships']} cạnh.", "",
              "Label và relationship thực tế của BONUS:", "", "| Loại | Số lượng |", "| --- | --- |"]
    for row in b["queries"]["labels"]["rows"]:
        lines.append(f"| {row['label']} | {row['n']} |")
    for row in b["queries"]["relationships"]["rows"]:
        lines.append(f"| {row['rel']} | {row['n']} |")
    for qid in ["Q4", "Q5", "Q6"]:
        lines += ["", f"## {qid}: câu trả lời trước/sau", "", "HINT:", "", hint[(qid, "graph")]["answer"],
                  "", "BONUS:", "", bonus[(qid, "graph")]["answer"]]
    lines += ["", "## Điều kiện đọc số liệu", "",
              "Cùng Gemini 3.5 Flash-Lite, Gemini embedding-001, top_k=3, chunk_size=800 và 176 chunk. LLM extraction và judge có thể biến động; đây là một cặp lượt chạy, không chứng minh cải thiện trên mọi dữ liệu.", "",
              "Gemini embedding-001 không trả usage token qua endpoint đang dùng và không có giá trong bảng repo: số token/cost indexing thiếu phần embedding. USD là ước tính paid theo bảng giá, không phải hóa đơn tài khoản miễn phí. Không tính ratio USD có mẫu số 0.", "",
              "BONUS có thêm giãn yêu cầu embedding để tránh quota 100/phút; không dùng chênh lệch thời gian indexing giữa HINT/BONUS làm bằng chứng tốc độ ontology. Thời gian query/indexing còn chịu chờ quota chat và mạng.", "",
              "Cần đọc toàn bộ Per question; không chỉ dựa vào recall và judge. Bonus do giảng viên chấm, kết quả này không tự đảm bảo +15."]
    target = Path("report/BONUS_RESULTS.md")
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Saved measured comparison: {target}")


if __name__ == "__main__":
    main()
