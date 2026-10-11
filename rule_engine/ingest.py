"""Nạp hợp đồng .docx và cắt thành danh sách Điều khoản.

Mỗi tệp .docx trong thư mục đầu vào tương ứng một hợp đồng; nội dung được tách
theo mẫu "Điều N" thành các đối tượng Clause để các bước sau trích xuất và kiểm tra.
"""
import re
from pathlib import Path
from dataclasses import dataclass
from docx import Document


@dataclass
class Clause:
    contract_id: str
    dieu_so: int
    tieu_de: str
    text: str


DIEU_PATTERN = re.compile(r"^Điều\s+(\d+)\.?\s*[:\-]?\s*(.*)$", re.IGNORECASE)


def extract_clauses(docx_path: Path, contract_id: str) -> list[Clause]:
    """Đọc một tệp .docx và trả về danh sách Điều khoản theo thứ tự xuất hiện."""
    doc = Document(docx_path)
    clauses: list[Clause] = []
    current = None
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        m = DIEU_PATTERN.match(text)
        if m:
            if current:
                clauses.append(Clause(contract_id, current["dieu_so"],
                                      current["tieu_de"], "\n".join(current["lines"])))
            current = {"dieu_so": int(m.group(1)), "tieu_de": m.group(2).strip(), "lines": []}
        elif current:
            current["lines"].append(text)
    if current:
        clauses.append(Clause(contract_id, current["dieu_so"],
                              current["tieu_de"], "\n".join(current["lines"])))
    return clauses


def process_batch(input_dir: Path) -> list[Clause]:
    """Cắt toàn bộ hợp đồng .docx trong thư mục; cảnh báo tệp không tách được Điều nào."""
    out: list[Clause] = []
    for p in sorted(Path(input_dir).glob("*.docx")):
        cs = extract_clauses(p, p.stem)
        if not cs:
            print(f"[CẢNH BÁO] {p.name}: không cắt được Điều nào.")
        out.extend(cs)
    return out
