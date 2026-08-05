from __future__ import annotations

import re
from typing import Dict, List, Protocol, Tuple

from traffic_es.nlu.polarity import has_negated_occurrence_only

Facts = Dict[str, object]


class Extractor(Protocol):
    def extract(self, text: str) -> Tuple[Facts, Dict[str, str], List[str]]: ...


_XE = [
    ("o_to", [r"ô ?tô", r"oto", r"xe hơi", r"xe con", r"xe khách", r"xe tải"]),
    ("xe_may", [r"xe máy", r"mô ?tô", r"xe gắn máy"]),
    ("xe_dap", [r"xe đạp", r"xe thô sơ"]),
]
_EVENT_KW = [
    "đâm", "va chạm", "quẹt", "tông", "tai nạn",
    "tái phạm", "bỏ chạy", "không chấp hành",
]

# (fact_key, value, patterns) — boolean / enum facts từ regex
_BOOL_PATS: List[Tuple[str, object, Tuple[str, ...]]] = [
    ("nguoi.khong_mu_bao_hiem", True, (r"không\s+(?:đội\s+)?mũ",)),
    ("nguoi.khong_day_an_toan", True, (r"không\s+(?:thắt|cài)?\s*dây", "không dây an toàn")),
    ("nguoi.co_chat_ma_tuy", True, ("ma túy", "chất ma túy", "dương tính ma túy")),
    ("nguoi.chua_du_tuoi_lai_xe", True, ("chưa đủ tuổi", "tuổi chưa đủ")),
    ("nguoi.gplx_khong_dung_tham_quyen", True, ("bằng giả", "gplx giả", "giấy phép giả")),
    ("hanhvi.vuot_den_vang", True, ("vượt đèn vàng", "đèn vàng")),
    ("hanhvi.khong_chap_hanh_csgt", True, (
        "không chấp hành hiệu lệnh của csgt",
        "không chấp hành hiệu lệnh csgt",
        "không tuân thủ csgt",
        "hiệu lệnh của cảnh sát",
        "hiệu lệnh csgt",
    )),
    ("hanhvi.sai_lan", True, ("sai làn", "đi sai làn", "lấn làn", "không đúng làn")),
    ("hanhvi.sai_phan_duong", True, ("sai phần đường",)),
    ("hanhvi.chuyen_lan_khong_tin_hieu", True, (
        "chuyển làn không", "không xi nhan", "không bật xi nhan", "không báo hiệu khi chuyển làn",
    )),
    ("hanhvi.quay_dau_cam", True, ("quay đầu nơi cấm", "cấm quay đầu", "quay đầu trái phép")),
    ("hanhvi.vuot_cam", True, ("cấm vượt", "vượt nơi cấm", "vượt xe trái phép")),
    ("hanhvi.nguoc_chieu", True, ("ngược chiều", "đi ngược chiều", "đường một chiều")),
    ("hanhvi.dung_do_sai", True, ("đỗ nơi cấm", "đỗ xe cấm", "dừng đỗ trái", "đỗ sai", "dừng sai")),
    ("boicanh.vi_tri_cam_do", True, ("vị trí cấm đỗ", "biển cấm đỗ")),
    ("hanhvi.che_bien_so", True, ("che biển", "che biển số")),
    ("hanhvi.bien_so_gia", True, ("biển số giả", "làm giả biển")),
    ("hanhvi.sua_bien_so", True, ("sửa biển số", "bẻ biển số")),
    ("hanhvi.cho_qua_tai", True, ("quá tải", "chở quá tải", "vượt tải")),
    ("hanhvi.cho_qua_kho", True, ("quá khổ", "chở quá khổ")),
    ("hanhvi.cho_qua_so_nguoi", True, ("nhồi nhét", "chở quá số người", "quá số ghế")),
    ("hanhvi.don_tra_khach_sai", True, ("đón khách sai", "trả khách sai", "trên cao tốc")),
    ("hanhvi.thu_tien_qua_gia_ve", True, ("thu tiền quá", "giá vé cao hơn", "quá giá vé")),
    ("hanhvi.hanh_khach_gay_roi", True, ("hành khách gây rối", "gây rối trên xe", "đe dọa tài xế")),
    ("hanhvi.hanh_khach_du_bam", True, ("đu bám",)),
    ("hanhvi.hanh_khach_mo_cua_khi_xe_chay", True, ("mở cửa khi xe đang chạy", "tự ý mở cửa")),
    ("hanhvi.nguoi_di_bo_sai_phan_duong", True, ("đi bộ sai", "đi bộ dưới lòng đường")),
    ("hanhvi.vuot_dai_phan_cach", True, ("vượt dải phân cách",)),
    ("hanhvi.nguoi_di_bo_khong_chap_hanh_den", True, ("đi bộ vượt đèn", "đi bộ không chấp hành đèn")),
    ("hanhvi.giao_xe_nguoi_khong_du_dk", True, ("giao xe cho người không", "cho mượn xe không bằng")),
    ("hanhvi.thay_doi_may_khung", True, ("đổi máy", "thay khung", "cải tạo xe")),
    ("hanhvi.thay_doi_mau_son_trai_quy_dinh", True, ("đổi màu sơn",)),
    ("giayto.khong_mang_dang_ky_xe", True, ("không mang đăng ký", "quên cà vẹt", "không mang cà vẹt")),
    ("giayto.khong_co_dang_ky_xe", True, ("không có đăng ký xe",)),
    ("giayto.khong_mang_dang_kiem", True, ("không mang đăng kiểm", "quên đăng kiểm")),
    ("giayto.het_han_dang_kiem", True, ("hết hạn đăng kiểm",)),
]


class HeuristicExtractor:
    """Trích Facts bằng regex — chạy offline, không cần LLM."""

    def extract(self, text: str) -> Tuple[Facts, Dict[str, str], List[str]]:
        t = text.lower()
        facts: Facts = {}
        ev: Dict[str, str] = {}
        # loại xe — chọn loại được NHẮC SỚM NHẤT trong câu (đúng chủ thể)
        best = None  # (vị trí, loại, match)
        for loai, pats in _XE:
            for p in pats:
                m = re.search(p, t)
                if m and (best is None or m.start() < best[0]):
                    best = (m.start(), loai, m.group(0))
        if best:
            facts["phuongtien.loai"] = best[1]
            ev["phuongtien.loai"] = best[2]
        # nồng độ cồn
        m = re.search(r"(?:nồng độ cồn|cồn)[^0-9]{0,25}(\d+(?:[.,]\d+)?)", t)
        if not m:
            m = re.search(r"(?:thổi(?:\s+ra)?|khí thở|hơi thở)[^0-9]{0,20}(\d+(?:[.,]\d+)?)", t)
        if m:
            val = float(m.group(1).replace(",", "."))
            compact = t.replace(" ", "")
            is_mau = ("máu" in t) or ("100ml" in compact) or ("mg/100" in compact)
            key = "chiso.nongDoCon_mau" if is_mau else "chiso.nongDoCon_khiTho"
            facts[key] = val
            ev[key] = m.group(0)
        # tốc độ
        m = re.search(r"(?:chạy|tốc độ)[^0-9]{0,10}(\d+)\s*(?:km|km/h)", t)
        if m:
            facts["chiso.tocDo"] = float(m.group(1))
            ev["chiso.tocDo"] = m.group(0)
        m = re.search(r"(?:giới hạn|cho phép)[^0-9]{0,10}(\d+)", t)
        if m:
            facts["chiso.tocDoGioiHan"] = float(m.group(1))
        # khu vực
        if "khu dân cư" in t:
            facts["boicanh.khuVuc"] = "khu_dan_cu"
            ev["boicanh.khuVuc"] = "khu dân cư"
        elif "cao tốc" in t:
            facts["boicanh.khuVuc"] = "cao_toc"
        elif "đô thị" in t:
            facts["boicanh.khuVuc"] = "do_thi"
        # boolean patterns
        for key, value, pats in _BOOL_PATS:
            for p in pats:
                if p.startswith("không") or "\\" in p or "(" in p:
                    if re.search(p, t):
                        facts[key] = value
                        break
                elif p in t:
                    facts[key] = value
                    break
        # vượt đèn đỏ — tránh phủ định; tách khỏi CSGT
        if any(
            p in t and not has_negated_occurrence_only(t, p)
            for p in ("vượt đèn đỏ", "vượt đèn")
        ) or ("không chấp hành" in t and "đèn" in t and "csgt" not in t and "cảnh sát" not in t):
            facts["hanhvi.vuot_den_do"] = True
        if "không có giấy phép lái xe" in t or "không bằng lái" in t or "không có bằng" in t:
            facts["nguoi.coGPLX"] = False
        raw = [
            seg.strip()
            for seg in re.split(r"[.,;]| rồi | và ", text)
            if any(kw in seg.lower() for kw in _EVENT_KW)
        ]
        return facts, ev, raw
