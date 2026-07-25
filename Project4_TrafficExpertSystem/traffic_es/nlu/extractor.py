from __future__ import annotations

import re
from typing import Dict, List, Protocol, Tuple

Facts = Dict[str, object]


class Extractor(Protocol):
    def extract(self, text: str) -> Tuple[Facts, Dict[str, str], List[str]]: ...


_XE = [
    ("o_to", [r"ô ?tô", r"oto", r"xe hơi", r"xe con"]),
    ("xe_may", [r"xe máy", r"mô ?tô", r"xe gắn máy"]),
]
_EVENT_KW = [
    "đâm", "va chạm", "quẹt", "tông", "tai nạn",
    "tái phạm", "bỏ chạy", "không chấp hành",
]


class HeuristicExtractor:
    """Trích Facts bằng regex — chạy offline, không cần LLM."""

    def extract(self, text: str) -> Tuple[Facts, Dict[str, str], List[str]]:
        t = text.lower()
        facts: Facts = {}
        ev: Dict[str, str] = {}
        # loại xe — chọn loại được NHẮC SỚM NHẤT trong câu (đúng chủ thể),
        # tránh nhầm khi câu nhắc nhiều loại (vd "xe máy đâm vào ô tô")
        best = None  # (vị trí, loại, match)
        for loai, pats in _XE:
            for p in pats:
                m = re.search(p, t)
                if m and (best is None or m.start() < best[0]):
                    best = (m.start(), loai, m.group(0))
        if best:
            facts["phuongtien.loai"] = best[1]
            ev["phuongtien.loai"] = best[2]
        # nồng độ cồn — phân biệt máu (mg/100ml) vs khí thở (mg/l)
        m = re.search(r"(?:nồng độ cồn|cồn)[^0-9]{0,25}(\d+(?:\.\d+)?)", t)
        if m:
            val = float(m.group(1))
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
        # hành vi/điều kiện dạng boolean
        if re.search(r"không\s+(?:đội\s+)?mũ", t):
            facts["nguoi.khong_mu_bao_hiem"] = True
        if re.search(r"không\s+(?:thắt|cài)?\s*dây", t) or "không dây an toàn" in t:
            facts["nguoi.khong_day_an_toan"] = True
        if "vượt đèn đỏ" in t or "vượt đèn" in t or "không chấp hành" in t and "đèn" in t:
            facts["hanhvi.vuot_den_do"] = True
        if "không có giấy phép lái xe" in t or "không bằng lái" in t or "không có bằng" in t:
            facts["nguoi.coGPLX"] = False
        # sự kiện thô cho Bài toán 1
        raw = [
            seg.strip()
            for seg in re.split(r"[.,;]| rồi | và ", text)
            if any(kw in seg.lower() for kw in _EVENT_KW)
        ]
        return facts, ev, raw
