"""Phân tích lỗi ở mức từng ô: liệt kê TP/FN/FP kèm trích đoạn điều khoản.

Mục đích là soi đúng chỗ rule sai để chỉnh, và xuất bảng ra data/error_analysis.csv.
"""
import os
import sys
from pathlib import Path
# Chạy được từ thư mục bất kỳ: nạp mã nguồn trong rule_engine/ và lấy gốc dự án làm thư mục làm việc.
_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "rule_engine"))
os.chdir(_ROOT)

import csv
from collections import defaultdict, Counter
from eval import run, metrics, SLOTS, INSCOPE_TYPES
from extract import title_to_slot


def gold_detail(path="data/gold_answers.csv"):
    """Nạp gold ở mức chi tiết: (contract_id, slot) -> (violation_type, error_kind)."""
    g = {}
    for r in csv.DictReader(open(path, encoding="utf-8-sig")):
        if r["slot"].strip() and r["violation_type"].strip():
            g[(r["contract_id"], r["slot"])] = (r["violation_type"], r["error_kind"])
    return g


def slot_text(by_hd):
    """Gộp văn bản theo (contract_id, slot) để trích đoạn minh họa cho mỗi ô."""
    st = defaultdict(dict)
    for cid, cs in by_hd.items():
        for c in cs:
            s = title_to_slot(c.tieu_de)
            if s:
                st[cid][s] = c.text
    return st


def build(by_hd, preds, gd):
    """Dựng bảng từng ô có nhãn hoặc có dự đoán; gán trạng thái TP/FN/FP và kèm trích đoạn."""
    st = slot_text(by_hd)
    pred = {}
    for cid, vs in preds.items():
        for v in vs:
            pred[(cid, v["slot"])] = v["error_kind"]

    rows = []
    all_cells = {(cid, s) for cid in by_hd for s in SLOTS}
    for cid, s in sorted(all_cells):
        g = gd.get((cid, s))
        p = pred.get((cid, s))
        gtype = g[0] if g else ""
        gkind = g[1] if g else ""
        if g and p:
            status = "TP"
        elif g and not p:
            status = "FN"
        elif p and not g:
            status = "FP"
        else:
            status = "TN"
        if status in ("FN", "FP", "TP"):
            rows.append(dict(contract_id=cid, slot=s, status=status, gold_type=gtype, gold_kind=gkind,
                             pred_kind=p or "", text=(st[cid].get(s, "")[:160]).replace("\n", " ")))
    return rows


if __name__ == "__main__":
    by_hd, preds, gold = run()
    m_in = metrics(by_hd, preds, gold)

    # Recall trên mọi loại (gồm cả mập mờ/bất lợi ngoài phạm vi rule).
    pred_cells = {(c, v["slot"]) for c, vs in preds.items() for v in vs}
    gold_any = set(gold)
    TP = len(pred_cells & gold_any)
    FP = len(pred_cells - gold_any)
    FN = len(gold_any - pred_cells)
    P = TP / len(pred_cells)
    R = TP / len(gold_any)
    F = 2 * P * R / (P + R)
    print(f"IN-SCOPE (trái luật + thiếu): P={m_in['precision']:.2f} R={m_in['recall_inscope']:.2f} F1={m_in['f1']:.2f}")
    print(f"MỌI LOẠI (gồm mập mờ + bất lợi): P={P:.2f} R={R:.2f} F1={F:.2f}  (TP={TP} FP={FP} FN={FN})")

    rows = build(by_hd, preds, gold_detail())
    with open("data/error_analysis.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["contract_id", "slot", "status", "gold_type", "gold_kind", "pred_kind", "text"])
        w.writeheader()
        w.writerows(rows)

    print("Thống kê ô:", Counter(r["status"] for r in rows))
    print("FN theo loại:", Counter(r["gold_type"] for r in rows if r["status"] == "FN"))
    print("Một số FN trái luật tiêu biểu:")
    for r in [r for r in rows if r["status"] == "FN" and r["gold_type"] == "trai_luat"][:5]:
        print(f"  {r['contract_id']} {r['slot']} [{r['gold_kind']}] {r['text'][:80]}")
