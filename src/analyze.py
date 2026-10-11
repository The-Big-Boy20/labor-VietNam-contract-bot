"""Pipeline hybrid: kết hợp rule (Loại 1–2) và LLM (Loại 3–4), kèm căn cứ pháp lý.

- analyze: phân tích một hợp đồng, trả về danh sách vi phạm.
- hybrid_eval: đánh giá trên tập hợp đồng, báo Precision/Recall/F1 toàn bộ.
LLM chạy qua Ollama; tham số limit cho phép chạy thử trên một phần tập.
"""
import os, sys
from pathlib import Path
# Chạy được từ thư mục bất kỳ: nạp mã nguồn trong src/ và lấy gốc dự án làm thư mục làm việc.
_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))
os.chdir(_ROOT)

import csv
import yaml
from collections import defaultdict
from ingest import process_batch
from extract import extract_contract, load_wage_zones, build_prov_index
from rules import check
from detect_llm import load_bank, pick_examples, detect


def make_context(proj="."):
    proj = Path(proj)
    thresholds = yaml.safe_load(open(proj / "config/thresholds.yaml", encoding="utf-8"))
    prov_regions, prov_default = load_wage_zones(proj / "data/law/wage_zones_293.csv")
    build_prov_index(prov_regions)
    examples, _ = pick_examples(load_bank(proj / "data/hdld_clauses_merged.csv"))
    return thresholds, prov_regions, prov_default, examples


def analyze(clauses, thresholds, prov_regions, prov_default, examples, model="qwen2.5:7b"):
    """Phân tích các điều khoản của một hợp đồng -> danh sách vi phạm (rule + LLM)."""
    extracted = extract_contract(clauses, thresholds, prov_regions, prov_default)
    violations = check(extracted, thresholds)                 # Loại 1–2 (rule)
    rule_slots = {v["slot"] for v in violations}
    if model:                                                 # Loại 3–4 (LLM), bỏ qua slot rule đã gắn
        for slot, text in extracted["slot_text"].items():
            if slot in rule_slots:
                continue
            d = detect(text, examples, model)
            if d.get("mo_ho"):
                violations.append(dict(slot=slot, error_kind="mo_ho_llm", violation_type="mo_ho",
                                       severity="trung", legal_basis="(LLM)", ly_do=d.get("ly_do", "")))
            if d.get("bat_loi"):
                violations.append(dict(slot=slot, error_kind="bat_loi_llm", violation_type="bat_loi",
                                       severity="trung", legal_basis="(LLM)", ly_do=d.get("ly_do", "")))
    return violations


def hybrid_eval(proj=".", model="qwen2.5:7b", limit=None):
    thresholds, prov_regions, prov_default, examples = make_context(proj)
    clauses = process_batch(Path(proj) / "data/contracts")
    by_contract = defaultdict(list)
    for c in clauses:
        by_contract[c.contract_id].append(c)
    ids = sorted(by_contract)[:limit] if limit else sorted(by_contract)

    pred_cells = {
        (cid, v["slot"])
        for cid in ids
        for v in analyze(by_contract[cid], thresholds, prov_regions, prov_default, examples, model)
    }

    gold = {}
    for r in csv.DictReader(open(Path(proj) / "data/gold_answers.csv", encoding="utf-8-sig")):
        if r["slot"].strip() and r["violation_type"].strip() and r["contract_id"] in ids:
            gold[(r["contract_id"], r["slot"])] = r["violation_type"]

    g = set(gold)
    TP, FP, FN = len(pred_cells & g), len(pred_cells - g), len(g - pred_cells)
    P = TP / (TP + FP) if TP + FP else 0
    R = TP / (TP + FN) if TP + FN else 0
    F = 2 * P * R / (P + R) if P + R else 0
    by_type = defaultdict(lambda: [0, 0])
    for k, t in gold.items():
        by_type[t][1] += 1
        by_type[t][0] += int(k in pred_cells)
    print(f"Hybrid | {len(ids)} hợp đồng | P={P:.2f} R={R:.2f} F1={F:.2f} (TP={TP} FP={FP} FN={FN})")
    print("recall theo loại:", {t: f"{a}/{b}" for t, (a, b) in by_type.items()})
    return {"P": P, "R": R, "F1": F}


if __name__ == "__main__":
    hybrid_eval(model="qwen2.5:7b", limit=10)
