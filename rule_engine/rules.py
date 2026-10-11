"""Rule engine: từ trường đã trích + ngưỡng pháp lý -> danh sách vi phạm.

Phạm vi: Loại 1 (trái luật — định lượng và từ khóa) và Loại 2 (thiếu điều khoản bắt buộc).
Rule được viết theo điều cấm của luật ở mức khái quát, không khớp một câu cụ thể.
Loại 3 (bất lợi) và Loại 4 (mập mờ) thuộc ngữ nghĩa mở, do tầng LLM đảm nhận.
"""

MANDATORY_SLOTS = ["thoi_han", "luong_phucap", "bao_hiem", "thoi_gio_lamviec"]  # BLLĐ 2019, Điều 21 (rút gọn)


def _has(t, *kw):
    """Mọi từ khóa đều xuất hiện trong văn bản."""
    return all(k in t for k in kw)


def _any(t, *kw):
    """Ít nhất một từ khóa xuất hiện trong văn bản."""
    return any(k in t for k in kw)


# Mỗi phần tử: (slot, error_kind, violation_type, severity, legal_basis, điều kiện trên slot_text đã lower).
KEYWORD_RULES = [
 ("quyen_nghiavu","giu_ban_chinh_giay_to","trai_luat","cao","BLLĐ 2019, Điều 17 khoản 1",
  lambda t: "giữ" in t and "bản chính" in t and _any(t,"bằng","căn cước","giấy tờ")),
 ("luong_phucap","giu_luong_ky_quy","trai_luat","cao","BLLĐ 2019, Điều 17 khoản 2; Điều 94",
  lambda t: "ký quỹ" in t or ("giữ" in t and "lương" in t and _any(t,"hoàn trả","nghỉ việc"))),
 ("quyen_nghiavu","buoc_lam_viec_tra_no","trai_luat","cao","BLLĐ 2019, Điều 17 khoản 3",
  lambda t: "nợ" in t and _any(t,"không được chấm dứt","cho đến khi trả","trả hết")),
 ("bao_hiem","khong_dong_bhxh","trai_luat","cao","Luật BHXH 2024, Điều 2; BLLĐ 2019, Điều 21",
  lambda t: _any(t,"không tham gia bảo hiểm","không đóng") and _any(t,"tiền mặt","tự lo")),
 ("cham_dut","cham_dut_thai_san","trai_luat","cao","BLLĐ 2019, Điều 37 khoản 1",
  lambda t: _any(t,"mang thai","nuôi con dưới 12 tháng") and "chấm dứt" in t),
 ("dieukhoan_khac","tuoc_quyen_khoi_kien","trai_luat","cao","BLLĐ 2019, Chương XIV",
  lambda t: _any(t,"không có quyền khiếu nại","không được khiếu nại") or ("không" in t and "khởi kiện" in t)),
 ("bao_ho","nld_tu_mua_bhld","trai_luat","cao","Luật ATVSLĐ 2015, Điều 7; BLLĐ 2019, Điều 21",
  lambda t: _any(t,"tự mua","tự trang bị","chi phí của mình") and _any(t,"bảo hộ","bảo vệ cá nhân")),
 ("cong_viec_diadiem","phan_biet_doi_xu","trai_luat","cao","BLLĐ 2019, Điều 8 khoản 1",
  lambda t: _any(t,"chỉ nhận nữ","độc thân","ngoại hình") or ("kết hôn" in t and "chấm dứt" in t)),
 ("nangluong_thuong","phan_biet_gioi_nang_luong_thuong","trai_luat","cao","BLLĐ 2019, Điều 8 khoản 1",
  lambda t: _any(t,"mang thai","nuôi con") and _any(t,"không được xét nâng lương","không được hưởng","không thưởng")),
 ("nangluong_thuong","quy_che_thuong_khong_cong_khai","trai_luat","trung","BLLĐ 2019, Điều 104 khoản 2",
  lambda t: _any(t,"không công bố công khai","không công khai","giữ bí mật") and "thưởng" in t),
 ("thoi_gio_lamviec","lam_them_khong_can_dong_y","trai_luat","cao","BLLĐ 2019, Điều 107 khoản 1",
  lambda t: "làm thêm" in t and _any(t,"không cần sự đồng ý","nghĩa vụ làm thêm","không cần đồng ý","bắt buộc")),
 ("cong_viec_diadiem","dieu_chuyen_vuot_gioi_han","trai_luat","cao","BLLĐ 2019, Điều 29",
  lambda t: _any(t,"điều chuyển","luân chuyển","chuyển") and _any(t,"không giới hạn","bất kỳ","không cần báo trước")),
 ("thu_viec","thu_viec_nhieu_lan","trai_luat","cao","BLLĐ 2019, Điều 25",
  lambda t: "thử việc" in t and _any(t,"lần hai","ký thêm","thêm 30 ngày","lần nữa","hợp đồng thử việc mới")),
 ("cham_dut","loai_tru_tro_cap","trai_luat","cao","BLLĐ 2019, Điều 46, 47",
  lambda t: _any(t,"không được hưởng trợ cấp","không hưởng trợ cấp","mất toàn bộ") and _any(t,"mọi trường hợp","thôi việc","mất việc")),
 ("bao_ho","cam_tu_choi_cong_viec_nguy_hiem","trai_luat","cao","Luật ATVSLĐ 2015, Điều 6",
  lambda t: _any(t,"không được từ chối","không được rời") and _any(t,"nguy","mất an toàn","bất kỳ trường hợp")),
 ("bao_ho","nld_tra_chi_phi_kham_huan_luyen","trai_luat","trung","Luật ATVSLĐ 2015, Điều 7, 21",
  lambda t: _any(t,"tự chi trả","tự trả","chi phí của mình") and _any(t,"khám sức khỏe","huấn luyện")),
 ("dieukhoan_khac","phu_luc_don_phuong_uu_tien","trai_luat","cao","BLLĐ 2019, Điều 22; Điều 33",
  lambda t: "phụ lục" in t and _any(t,"ưu tiên","không cần sự đồng ý","bất kỳ thời điểm")),
 ("hinhthuc_kyhan_traluong","phi_ngan_hang_nld_chiu","trai_luat","trung","BLLĐ 2019, Điều 96 khoản 2",
  lambda t: "phí" in t and _any(t,"người lao động chịu","nlđ chịu","trừ") and _any(t,"ngân hàng","tài khoản","chuyển")),
 ("hinhthuc_kyhan_traluong","ep_chi_tieu_luong","trai_luat","cao","BLLĐ 2019, Điều 94 khoản 2",
  lambda t: _any(t,"phiếu mua hàng","mua sản phẩm của công ty","hàng hóa") and _any(t,"phải","chỉ định")),
 ("quyen_nghiavu","boi_thuong_vuot_muc","trai_luat","cao","BLLĐ 2019, Điều 129; Điều 102",
  lambda t: _any(t,"100% giá trị","toàn bộ giá trị","bồi thường 100%") or ("khấu trừ toàn bộ" in t)),
 ("bao_hiem","dong_bh_thap_hon_luong_thuc","trai_luat","cao","Luật BHXH 2024, Điều 31",
  lambda t: _any(t,"không tính trên toàn bộ","mức lương tối thiểu vùng","phần lương còn lại") and _any(t,"bảo hiểm","đóng")),
 ("thoi_han","qua_30_ngay_khong_chuyen","trai_luat","trung","BLLĐ 2019, Điều 20 khoản 2",
  lambda t: _any(t,"vẫn được hiểu là hợp đồng xác định","kể cả sau 30 ngày","vẫn là hợp đồng xác định")),
 ("luong_phucap","luong_lam_them_thap","trai_luat","cao","BLLĐ 2019, Điều 98 khoản 1",
  lambda t: "làm thêm" in t and "100%" in t and not _any(t,"150%","200%","300%")),
]

# Mốc (stage) của từng rule, dùng để tái dựng tiến trình cải thiện: 1 = baseline, 2 = bổ sung, 3 = tinh chỉnh.
RULE_STAGE = {
 "luong_duoi_toi_thieu_vung":1,"gio_lam_vuot_48_tuan":1,"lam_them_vuot_tran":1,"thu_viec_vuot_han":1,
 "luong_thu_viec_duoi_85":1,"thoi_han_vuot_36_thang":1,"hop_dong_1_ban":1,"ky_han_tra_luong_qua_dai":1,
 "giu_ban_chinh_giay_to":1,"giu_luong_ky_quy":1,"buoc_lam_viec_tra_no":1,"khong_dong_bhxh":1,
 "cham_dut_thai_san":1,"tuoc_quyen_khoi_kien":1,"nld_tu_mua_bhld":1,"phan_biet_doi_xu":1,
 "thieu_dieu_khoan_bat_buoc":1,
 "phan_biet_gioi_nang_luong_thuong":2,"quy_che_thuong_khong_cong_khai":2,"lam_them_khong_can_dong_y":2,
 "dieu_chuyen_vuot_gioi_han":2,"thu_viec_nhieu_lan":2,"loai_tru_tro_cap":2,"cam_tu_choi_cong_viec_nguy_hiem":2,
 "nld_tra_chi_phi_kham_huan_luyen":2,"phu_luc_don_phuong_uu_tien":2,"phi_ngan_hang_nld_chiu":2,
 "ep_chi_tieu_luong":2,"boi_thuong_vuot_muc":2,"dong_bh_thap_hon_luong_thuc":2,"qua_30_ngay_khong_chuyen":2,
 "luong_gio_duoi_toi_thieu":2,
 "nld_bao_truoc_qua_dai":3,"luong_lam_them_thap":3,
}
STAGE_NAMES = {1: "Baseline (định lượng + 8 từ khóa)", 2: "+ bổ sung 15 rule", 3: "+ tinh chỉnh regex/rule cuối"}


def check(extracted, th, max_stage=99):
    """Áp dụng rule lên trường đã trích, trả về danh sách vi phạm (đã khử trùng theo slot+kind).

    max_stage dùng để tái dựng tiến trình: chỉ giữ rule có stage <= max_stage.
    """
    f = extracted["fields"]
    present = extracted["slots_present"]
    st = extracted["slot_text"]
    violations = []

    def add(slot, kind, vtype, sev, basis):
        violations.append(dict(slot=slot, error_kind=kind, violation_type=vtype,
                               severity=sev, legal_basis=basis))

    # --- Loại 1: vi phạm định lượng ---
    if f.get("luong_thang") is not None:
        if f["luong_thang"] < f["luong_min_threshold"]:
            add("luong_phucap", "luong_duoi_toi_thieu_vung", "trai_luat", "cao",
                f"BLLĐ 2019, Điều 90, 91; NĐ 293/2025 (Vùng {f['wage_region']}: {f['luong_min_threshold']:,}đ)")
        elif max_stage >= 2 and f["province"] is None and f["luong_thang"] < f["luong_vung1"]:
            # Địa điểm mập mờ, không xác định được vùng: gắn cờ nghi ngờ (bổ sung từ stage 2).
            add("luong_phucap", "luong_duoi_toi_thieu_vung", "trai_luat", "trung",
                "NĐ 293/2025 — nghi ngờ dưới tối thiểu, cần xác định địa điểm (vùng)")
    if f.get("luong_gio") is not None and f["luong_gio"] < f["luong_gio_min_threshold"]:
        add("luong_phucap", "luong_gio_duoi_toi_thieu", "trai_luat", "cao", "BLLĐ 2019, Điều 90; NĐ 293/2025")

    tg = th["thoi_gio_lam_viec"]
    if f.get("gio_tuan") and f["gio_tuan"] > tg["binh_thuong_gio_tuan"]:
        add("thoi_gio_lamviec", "gio_lam_vuot_48_tuan", "trai_luat", "cao", "BLLĐ 2019, Điều 105")
    lt = tg["lam_them"]
    if (f.get("lam_them_thang") and f["lam_them_thang"] > lt["gio_thang_toi_da"]) or \
       (f.get("lam_them_nam") and f["lam_them_nam"] > lt["gio_nam_toi_da_dac_biet"]):
        add("thoi_gio_lamviec", "lam_them_vuot_tran", "trai_luat", "cao", "BLLĐ 2019, Điều 107")

    tv = th["thu_viec"]
    if f.get("thu_viec_ngay"):
        cap = tv["so_ngay_toi_da"]["nguoi_quan_ly_dn"] if f.get("is_quanly") \
            else tv["so_ngay_toi_da"]["trinh_do_cao_dang_tro_len"]
        if f["thu_viec_ngay"] > cap:
            add("thu_viec", "thu_viec_vuot_han", "trai_luat", "cao", f"BLLĐ 2019, Điều 25 (trần {cap} ngày)")
    if f.get("thu_viec_pct") is not None and f["thu_viec_pct"] < tv["luong_thu_viec_toi_thieu_phan_tram"]:
        add("thu_viec", "luong_thu_viec_duoi_85", "trai_luat", "cao", "BLLĐ 2019, Điều 26")

    if f.get("thoi_han_thang") and f["thoi_han_thang"] > th["hop_dong"]["xac_dinh_thoi_han_thang_toi_da"]:
        add("thoi_han", "thoi_han_vuot_36_thang", "trai_luat", "cao", "BLLĐ 2019, Điều 20")
    if f.get("so_ban") == 1:
        add("dieukhoan_khac", "hop_dong_1_ban", "trai_luat", "trung", "BLLĐ 2019, Điều 14 khoản 1")
    if f.get("bao_truoc_ngay") and \
       f["bao_truoc_ngay"] > th["don_phuong_cham_dut_nld_bao_truoc_ngay"]["khong_xac_dinh_thoi_han"]:
        add("cham_dut", "nld_bao_truoc_qua_dai", "trai_luat", "cao", "BLLĐ 2019, Điều 35")
    stl = st.get("hinhthuc_kyhan_traluong", "").lower()
    if "3 tháng" in stl or "quý" in stl or "03 tháng một lần" in stl:
        add("hinhthuc_kyhan_traluong", "ky_han_tra_luong_qua_dai", "trai_luat", "cao", "BLLĐ 2019, Điều 97 khoản 2")

    # --- Loại 1: vi phạm theo từ khóa ---
    for slot, kind, vtype, sev, basis, fn in KEYWORD_RULES:
        if fn(st.get(slot, "").lower()):
            add(slot, kind, vtype, sev, basis)

    # --- Loại 2: thiếu điều khoản bắt buộc ---
    for s in MANDATORY_SLOTS:
        if s not in present:
            add(s, "thieu_dieu_khoan_bat_buoc", "thieu", "cao", "BLLĐ 2019, Điều 21")

    # Lọc theo stage (tái dựng tiến trình) và khử trùng theo (slot, error_kind).
    seen = set()
    out = []
    for v in violations:
        if RULE_STAGE.get(v["error_kind"], 1) > max_stage:
            continue
        key = (v["slot"], v["error_kind"])
        if key not in seen:
            seen.add(key)
            out.append(v)
    return out
