"""Đánh giá rule engine trên tập hợp đồng, đối chiếu với gold.

Độ phân giải tính theo ô (hợp đồng × slot). Báo precision, recall (in-scope và mọi loại),
F1, kèm recall theo từng loại vi phạm. Hỗ trợ chia dev/test phân tầng để kiểm tra tính
tổng quát của rule khi chỉ có 50 mẫu.
"""
import csv
import os
import random
import yaml
from pathlib import Path
from collections import defaultdict
from ingest import process_batch
from extract import extract_contract, load_wage_zones, build_prov_index
from rules import check

INSCOPE_TYPES = {"trai_luat", "thieu"}  # phạm vi rule engine nhắm tới
SLOTS = ["cong_viec_diadiem", "thoi_han", "thoi_gio_lamviec", "luong_phucap", "hinhthuc_kyhan_traluong",
         "bao_hiem", "thu_viec", "nangluong_thuong", "bao_ho", "quyen_nghiavu", "cham_dut", "dieukhoan_khac"]


def run(proj=".", max_stage=99):
    """Chạy rule engine trên toàn tập hợp đồng. Trả về (by_hd, preds, gold_type)."""
    proj = Path(proj)
    th = yaml.safe_load(open(proj / "config/thresholds.yaml", encoding="utf-8"))
    prov_regions, prov_default = load_wage_zones(proj / "data/law/wage_zones_293.csv")
    build_prov_index(prov_regions)

    clauses = process_batch(proj / "data/contracts")
    by_hd = defaultdict(list)
    for c in clauses:
        by_hd[c.contract_id].append(c)

    preds = {}  # contract_id -> danh sách vi phạm
    for cid, cs in by_hd.items():
        preds[cid] = check(extract_contract(cs, th, prov_regions, prov_default), th, max_stage)

    gold_type = {}  # (contract_id, slot) -> violation_type
    for r in csv.DictReader(open(proj / "data/gold_answers.csv", encoding="utf-8-sig")):
        if r["slot"].strip() and r["violation_type"].strip():
            gold_type[(r["contract_id"], r["slot"])] = r["violation_type"]
    return by_hd, preds, gold_type


def load_buckets(path="data/contracts/contracts_manifest.csv"):
    """Đọc nhãn phân tầng (bucket) của từng hợp đồng; trả về dict rỗng nếu không có manifest."""
    if not os.path.exists(path):
        return {}
    return {r["contract_id"]: r["bucket"] for r in csv.DictReader(open(path, encoding="utf-8-sig"))}


def split_dev_test(ids, buckets, test_frac=0.3, seed=7):
    """Chia dev/test phân tầng theo bucket để tập test phản ánh cùng phân phối mức lỗi."""
    rnd = random.Random(seed)
    by = defaultdict(list)
    for i in ids:
        by[buckets.get(i, "?")].append(i)
    test = set()
    for _, lst in by.items():
        lst = sorted(lst)
        rnd.shuffle(lst)
        k = max(1, round(len(lst) * test_frac))
        test |= set(lst[:k])
    return set(ids) - test, test


def metrics(by_hd, preds, gold_type, ids=None):
    """Tính precision/recall/F1 trên tập hợp đồng chỉ định (mặc định: toàn bộ)."""
    if ids is None:
        ids = set(by_hd)
    pred_cells = {(cid, v["slot"]) for cid, vs in preds.items() if cid in ids for v in vs}
    gold_any = {k for k in gold_type if k[0] in ids}
    gold_inscope = {k for k, t in gold_type.items() if t in INSCOPE_TYPES and k[0] in ids}

    TP = len(pred_cells & gold_any)
    FP = len(pred_cells - gold_any)
    prec = TP / len(pred_cells) if pred_cells else 0
    rec_in = len(gold_inscope & pred_cells) / len(gold_inscope) if gold_inscope else 0
    rec_all = TP / len(gold_any) if gold_any else 0
    f1 = 2 * prec * rec_in / (prec + rec_in) if prec + rec_in else 0

    by_type = defaultdict(lambda: [0, 0])
    for k, t in gold_type.items():
        by_type[t][1] += 1
        if k in pred_cells:
            by_type[t][0] += 1
    return dict(TP=TP, FP=FP, pred=len(pred_cells), gold_any=len(gold_any), gold_inscope=len(gold_inscope),
                precision=prec, recall_inscope=rec_in, recall_all=rec_all, f1=f1,
                recall_by_type={t: (a, b) for t, (a, b) in by_type.items()})


if __name__ == "__main__":
    by_hd, preds, gold_type = run()
    for k, v in metrics(by_hd, preds, gold_type).items():
        print(k, v)
