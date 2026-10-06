import re
import jsonschema
import argparse
import json
from pathlib import Path
from dataclasses import dataclass, asdict
from docx import Document

@dataclass
class Clause:
    contract_id: str
    dieu_so: str
    tieu_de: str
    text: str
    def __repr__(self):
        return f"""
contract_id='{self.contract_id}',
dieu_so={self.dieu_so}, 
tieu_de='{self.tieu_de}', 
text='{self.text}'
"""
from docx import Document

DIEU_PATTERN = re.compile(r"^Điều\s+(\d+)\.?\s*[:\-]?\s*(.*)$", re.IGNORECASE)

def extract_clauses(docx_path: Path, contract_id: str) -> list[Clause]:
    doc = Document(docx_path)
    clauses = []
    current = None
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        m = DIEU_PATTERN.match(text)
        if m:
            if current:
                clauses.append(Clause(contract_id, current["dieu_so"], current["tieu_de"],
                                       "\n".join(current["lines"])))
            current = {"dieu_so": int(m.group(1)), "tieu_de": m.group(2).strip(), "lines": []}
        elif current:
            current["lines"].append(text)
    if current:
        clauses.append(Clause(contract_id, current["dieu_so"], current["tieu_de"],
                               "\n".join(current["lines"])))
    return clauses

def process_batch(input_dir: Path) -> list[Clause]:
    all_clauses = []
    for docx_path in sorted(input_dir.glob("*.docx")):
        clauses = extract_clauses(docx_path, docx_path.stem)
        if not clauses:
            print(f"[CẢNH BÁO] {docx_path.name}: không cắt được Điều nào.")
        all_clauses.extend(clauses)
    return all_clauses


def save_clauses(clauses: list[Clause], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps([asdict(c) for c in clauses], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
if __name__ == "__main__":
    clauses = process_batch(Path("data/contracts"))
    save_clauses(clauses, Path("data/clauses_extracted.json"))
    print(f"Tổng: {len(clauses)} điều khoản từ {len(list(Path('data/contracts').glob('*.docx')))} file.")