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
        # loại xe
        for loai, pats in _XE:
            for p in pats:
                m = re.search(p, t)
                if m:
                    facts["phuongtien.loai"] = loai
                    ev["phuongtien.loai"] = m.group(0)
                    break
            if "phuongtien.loai" in facts:
                break
        # nồng độ cồn (mg/l khí thở)
        m = re.search(r"(?:nồng độ cồn|cồn)[^0-9]{0,20}(\d+(?:\.\d+)?)", t)
        if m:
            facts["chiso.nongDoCon_khiTho"] = float(m.group(1))
            ev["chiso.nongDoCon_khiTho"] = m.group(0)
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
        # sự kiện thô cho Bài toán 1
        raw = [
            seg.strip()
            for seg in re.split(r"[.,;]| rồi | và ", text)
            if any(kw in seg.lower() for kw in _EVENT_KW)
        ]
        return facts, ev, raw
