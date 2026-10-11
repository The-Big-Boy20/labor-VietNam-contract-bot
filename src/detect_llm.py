"""Phát hiện điều khoản mập mờ (mo_ho) và bất lợi (bat_loi) bằng LLM với few-shot.

Ví dụ few-shot lấy từ ngân hàng điều khoản và được loại khỏi tập kiểm thử để tránh rò rỉ dữ liệu.
"""
import os, sys
from pathlib import Path
# Chạy được từ thư mục bất kỳ: nạp mã nguồn trong src/ và lấy gốc dự án làm thư mục làm việc.
_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))
os.chdir(_ROOT)

import csv
import json
import re
import random
from qa import ollama_generate

BANK = "data/hdld_clauses_merged.csv"


def load_bank(path=BANK):
    return list(csv.DictReader(open(path, encoding="utf-8-sig")))


def pick_examples(rows, k_each=2, k_ok=5, seed=1):
    """Chọn ví dụ few-shot: k_each mập mờ, k_each bất lợi, k_ok hợp lệ.
    Nhiều ví dụ hợp lệ giúp mô hình hạn chế gắn cờ nhầm. Trả về tập id để loại khỏi tập kiểm thử."""
    rnd = random.Random(seed)
    mo = rnd.sample([r for r in rows if r["violation_type"] == "mo_ho"], k_each)
    bat = rnd.sample([r for r in rows if r["violation_type"] == "bat_loi"], k_each)
    ok = rnd.sample([r for r in rows if r["is_violation"] == "0"], k_ok)
    examples = mo + bat + ok
    return examples, {r["clause_id"] for r in examples}


def _label(r):
    return {"mo_ho": r["violation_type"] == "mo_ho", "bat_loi": r["violation_type"] == "bat_loi"}


def build_prompt(clause_text, examples):
    shots = "\n\n".join(
        f'Điều khoản: {e["text"]}\n'
        f'Kết quả: {{"mo_ho": {str(_label(e)["mo_ho"]).lower()}, '
        f'"bat_loi": {str(_label(e)["bat_loi"]).lower()}, "ly_do": "{e["explanation"]}"}}'
        for e in examples
    )
    return f"""Bạn là chuyên gia pháp luật lao động Việt Nam. Phân loại điều khoản hợp đồng.

Quy tắc:
- Mặc định cả hai nhãn là false. Điều khoản đầy đủ, rõ ràng, đúng quy định giữ nguyên false.
- Đặt mo_ho=true chỉ khi điều khoản thiếu thông tin cụ thể hoặc dùng từ tùy nghi
  ("theo quyết định của công ty", "khi cần thiết", "tùy tình hình", tham chiếu văn bản không đính kèm).
- Đặt bat_loi=true chỉ khi điều khoản gây thiệt hại hoặc ràng buộc vô lý cho người lao động.
- Khi phân vân, chọn false.

Chỉ trả về một dòng JSON: {{"mo_ho": true/false, "bat_loi": true/false, "ly_do": "..."}}.

VÍ DỤ:
{shots}

Điều khoản: {clause_text}
Kết quả:"""


def detect(clause_text, examples, model="qwen2.5:7b"):
    raw = ollama_generate(build_prompt(clause_text, examples), model)
    m = re.search(r"\{.*\}", raw, re.S)
    try:
        return json.loads(m.group())
    except Exception:
        return {"error": "parse_fail", "raw": raw}


def evaluate(model="qwen2.5:7b", n_each=15, seed=1):
    """Đo Precision/Recall/F1 cho mo_ho và bat_loi trên tập kiểm thử (loại trừ few-shot)."""
    rows = load_bank()
    examples, used = pick_examples(rows, seed=seed)
    pool = [r for r in rows if r["clause_id"] not in used]
    rnd = random.Random(seed)

    def sample(cond):
        xs = [r for r in pool if cond(r)]
        return rnd.sample(xs, min(n_each, len(xs)))

    test = (sample(lambda r: r["violation_type"] == "mo_ho")
            + sample(lambda r: r["violation_type"] == "bat_loi")
            + sample(lambda r: r["is_violation"] == "0"))

    from collections import Counter
    stat = {"mo_ho": Counter(), "bat_loi": Counter()}
    for r in test:
        pred = detect(r["text"], examples, model)
        gold = _label(r)
        for key in ("mo_ho", "bat_loi"):
            p, g = bool(pred.get(key)), gold[key]
            if p and g:
                stat[key]["tp"] += 1
            elif p and not g:
                stat[key]["fp"] += 1
            elif g and not p:
                stat[key]["fn"] += 1
    for key in ("mo_ho", "bat_loi"):
        tp, fp, fn = stat[key]["tp"], stat[key]["fp"], stat[key]["fn"]
        P = tp / (tp + fp) if tp + fp else 0
        R = tp / (tp + fn) if tp + fn else 0
        F = 2 * P * R / (P + R) if P + R else 0
        print(f"{key}: P={P:.2f} R={R:.2f} F1={F:.2f} (tp={tp} fp={fp} fn={fn})")
    return stat


if __name__ == "__main__":
    rows = load_bank()
    examples, used = pick_examples(rows)
    test = next(r for r in rows if r["clause_id"] not in used and r["violation_type"] == "mo_ho")
    print("Điều khoản:", test["clause_id"], "| nhãn:", test["violation_type"])
    print(detect(test["text"], examples, model="qwen2.5:7b"))
