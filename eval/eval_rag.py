"""Đánh giá retriever: hit@1, hit@3, MRR trên bộ câu hỏi có điều luật tham chiếu."""
import os, sys
from pathlib import Path
# Chạy được từ thư mục bất kỳ: nạp mã nguồn trong src/ và lấy gốc dự án làm thư mục làm việc.
_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))
os.chdir(_ROOT)

from rag import Retriever

# (câu hỏi, số hiệu văn bản, tập Điều được coi là đúng)
QA_SET = [
    ("mức lương tối thiểu vùng là bao nhiêu", "293/2025", {"3"}),
    ("mức lương tối thiểu theo quy định", "45/2019", {"90", "91"}),
    ("thời gian thử việc tối đa bao nhiêu ngày", "45/2019", {"25"}),
    ("tiền lương trong thời gian thử việc ít nhất bao nhiêu", "45/2019", {"26"}),
    ("số giờ làm thêm tối đa trong một năm", "45/2019", {"107"}),
    ("tiền lương làm thêm giờ ngày thường ngày lễ", "45/2019", {"98"}),
    ("người sử dụng lao động được giữ bản chính giấy tờ không", "45/2019", {"17"}),
    ("các loại hợp đồng lao động xác định thời hạn", "45/2019", {"20"}),
    ("người lao động đơn phương chấm dứt phải báo trước bao nhiêu ngày", "45/2019", {"35"}),
    ("trợ cấp thôi việc tính thế nào", "45/2019", {"46"}),
    ("thời giờ làm việc bình thường tối đa mỗi tuần", "45/2019", {"105"}),
    ("hợp đồng lao động lập thành mấy bản", "45/2019", {"14"}),
]


def evaluate(retriever, k=3):
    hit1 = hit_k = 0
    mrr = 0.0
    rows = []
    for q, doc, dieus in QA_SET:
        results = retriever.search(q, k=k)
        rank = next((i + 1 for i, h in enumerate(results)
                     if doc in h["doc"] and h["dieu"] in dieus), None)
        rows.append((q, rank, results[0]["doc"], results[0]["dieu"]))
        if rank == 1:
            hit1 += 1
        if rank:
            hit_k += 1
            mrr += 1 / rank
    n = len(QA_SET)
    return {"hit1": hit1 / n, "hit_at_k": hit_k / n, "mrr": mrr / n, "k": k, "n": n}, rows


if __name__ == "__main__":
    retriever = Retriever(backend="tfidf").build("data/law/chunks_v3.json")
    metrics, rows = evaluate(retriever, k=3)
    print(f"n={metrics['n']} | hit@1={metrics['hit1']:.2f} "
          f"| hit@3={metrics['hit_at_k']:.2f} | MRR={metrics['mrr']:.2f}\n")
    for q, rank, doc, dieu in rows:
        tag = f"top-{rank}" if rank else "miss"
        print(f"  [{tag:6s}] {q[:46]:46s} | top1 = {doc} Điều {dieu}")
