"""Trích xuất trường định lượng và địa điểm từ hợp đồng đã cắt Điều.

Mỗi Điều được ánh xạ về một slot chuẩn; các trường số (lương, giờ làm, thử việc...)
được trích bằng biểu thức chính quy. Địa điểm làm việc được quy về tỉnh rồi về vùng
lương tối thiểu để so với ngưỡng. Khi không xác định được vùng, chọn vùng có mức
lương thấp nhất để tránh báo sai (false positive).
"""
import re
import csv
from collections import defaultdict

# Ánh xạ tiêu đề Điều -> slot chuẩn (theo khung sinh hợp đồng); nếu không khớp thì dò theo từ khóa.
TITLE2SLOT = {
    "CÔNG VIỆC VÀ ĐỊA ĐIỂM LÀM VIỆC": "cong_viec_diadiem",
    "LOẠI VÀ THỜI HẠN HỢP ĐỒNG": "thoi_han",
    "THỜI GIỜ LÀM VIỆC, NGHỈ NGƠI": "thoi_gio_lamviec",
    "LƯƠNG VÀ PHỤ CẤP": "luong_phucap",
    "HÌNH THỨC VÀ KỲ HẠN TRẢ LƯƠNG": "hinhthuc_kyhan_traluong",
    "BẢO HIỂM": "bao_hiem",
    "THỬ VIỆC": "thu_viec",
    "NÂNG LƯƠNG, THƯỞNG": "nangluong_thuong",
    "BẢO HỘ LAO ĐỘNG": "bao_ho",
    "QUYỀN VÀ NGHĨA VỤ HAI BÊN": "quyen_nghiavu",
    "CHẤM DỨT HỢP ĐỒNG": "cham_dut",
    "ĐIỀU KHOẢN KHÁC": "dieukhoan_khac",
}
SLOT_KW = [
    ("thử việc", "thu_viec"), ("bảo hiểm", "bao_hiem"), ("thời giờ", "thoi_gio_lamviec"),
    ("lương", "luong_phucap"), ("thời hạn", "thoi_han"), ("chấm dứt", "cham_dut"),
    ("bảo hộ", "bao_ho"), ("địa điểm", "cong_viec_diadiem"),
]


def title_to_slot(t):
    """Trả về slot chuẩn cho tiêu đề Điều, ưu tiên khớp chính xác rồi mới dò từ khóa."""
    tu = t.upper().strip()
    if tu in TITLE2SLOT:
        return TITLE2SLOT[tu]
    for kw, s in SLOT_KW:
        if kw in t.lower():
            return s
    return None


# Biểu thức chính quy cho từng trường định lượng. thu_viec_pct để chữ "mức" là tùy chọn
# nhằm bắt cả cách ghi "85% lương" lẫn "85% mức lương".
FIELDS = {
    "luong_thang":    r"([\d.]{7,})\s*đồng/tháng",
    "luong_gio":      r"([\d.]{4,})\s*đồng/giờ",
    "gio_tuan":       r"(\d{1,2})\s*giờ/tuần",
    "gio_ngay":       r"(\d{1,2})\s*giờ/ngày",
    "lam_them_thang": r"(\d{1,3})\s*giờ(?:\s*làm thêm)?/tháng",
    "lam_them_nam":   r"(\d{2,3})\s*giờ(?:\s*làm thêm)?/năm",
    "thu_viec_ngay":  r"thử việc\s+(\d{1,3})\s*ngày",
    "thu_viec_pct":   r"(\d{2,3})\s*%\s*(?:mức\s+)?lương",
    "thoi_han_thang": r"(?:thời hạn|xác định thời hạn)[^\d]{0,20}(\d{1,2})\s*tháng",
    "so_ban":         r"thành\s+(\d{1,2})\s*bản",
    "bao_truoc_ngay": r"báo trước[^\d]{0,35}?(\d{1,3})\s*ngày",
}

# Các trường lấy giá trị LỚN NHẤT khi khớp nhiều lần (phần còn lại lấy nhỏ nhất).
_MAX_FIELDS = {"luong_thang", "luong_gio", "gio_tuan", "gio_ngay", "lam_them_thang",
               "lam_them_nam", "thu_viec_ngay", "thoi_han_thang", "bao_truoc_ngay"}

ROMAN2VUNG = {"I": "vung_1", "II": "vung_2", "III": "vung_3", "IV": "vung_4"}


def _nums(text, pattern):
    """Trả về danh sách số nguyên khớp pattern (bỏ dấu chấm phân cách nghìn)."""
    return [int(x.replace(".", "")) for x in re.findall(pattern, text, re.IGNORECASE)]


def load_wage_zones(csv_path):
    """Đọc bảng vùng lương: province -> tập vùng, và province -> vùng mặc định (catch_all)."""
    prov_regions = defaultdict(set)
    prov_default = {}
    for r in csv.DictReader(open(csv_path, encoding="utf-8-sig")):
        if r["region"]:
            prov_regions[r["province"]].add(r["region"])
        if r["catch_all"].strip() == "yes":
            prov_default[r["province"]] = r["region"]
    return prov_regions, prov_default


# Chỉ mục tên tỉnh rút gọn -> tên đầy đủ, dựng từ bảng vùng lương.
PROV_CORE = {}


def build_prov_index(prov_regions):
    """Dựng chỉ mục tên tỉnh rút gọn (bỏ tiền tố 'Thành phố'/'Tỉnh') để dò trong văn bản."""
    for full in prov_regions:
        core = full.replace("Thành phố ", "").replace("Tỉnh ", "").lower()
        PROV_CORE[core] = full


def detect_province(diadiem_text):
    """Dò tỉnh xuất hiện trong mô tả địa điểm; ưu tiên tên khớp dài nhất."""
    t = diadiem_text.lower()
    best = None
    for core, full in PROV_CORE.items():
        if core in t and (best is None or len(core) > len(best[0])):
            best = (core, full)
    return best[1] if best else None


def lowest_wage_region(regions):
    """Chọn vùng có mức lương thấp nhất (số La Mã lớn nhất) — hướng bảo thủ, tránh báo sai."""
    for r in ["IV", "III", "II", "I"]:
        if r in regions:
            return r
    return "IV"


def extract_contract(clauses, thresholds, prov_regions, prov_default):
    """Trích trường định lượng và slot cho một hợp đồng.

    Trả về dict gồm: fields (giá trị số + ngưỡng lương theo vùng),
    slots_present (các slot có mặt), slot_text (văn bản gộp theo slot).
    """
    slot_text = defaultdict(str)
    slots_present = set()
    for c in clauses:
        s = title_to_slot(c.tieu_de)
        if s:
            slots_present.add(s)
            slot_text[s] += " " + c.text
    whole = " ".join(c.text for c in clauses)
    tv_text = slot_text.get("thu_viec", "")  # bó các trường thử việc trong slot của nó

    f = {}
    for k, pat in FIELDS.items():
        src = tv_text if k.startswith("thu_viec") else whole
        vals = _nums(src, pat)
        if not vals:
            f[k] = None
        elif k in _MAX_FIELDS:
            f[k] = max(vals)
        else:
            f[k] = min(vals)
    pcts = [v for v in _nums(tv_text, FIELDS["thu_viec_pct"]) if v <= 100]
    f["thu_viec_pct"] = min(pcts) if pcts else None

    # Địa điểm -> tỉnh -> vùng mặc định (catch_all) của tỉnh; không rõ thì lấy vùng thấp nhất.
    prov = detect_province(slot_text.get("cong_viec_diadiem", ""))
    region = (prov_default.get(prov) or lowest_wage_region(prov_regions.get(prov, set()))) if prov else "IV"
    f["province"] = prov
    f["wage_region"] = region
    f["luong_min_threshold"] = thresholds["luong_toi_thieu_vung"]["thang"][ROMAN2VUNG[region]]
    f["luong_gio_min_threshold"] = thresholds["luong_toi_thieu_vung"]["gio"][ROMAN2VUNG[region]]
    f["luong_vung1"] = thresholds["luong_toi_thieu_vung"]["thang"]["vung_1"]
    f["is_quanly"] = "quản lý" in whole.lower() or "giám đốc" in whole.lower()
    return {"fields": f, "slots_present": slots_present, "slot_text": dict(slot_text)}
