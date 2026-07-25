from __future__ import annotations

import json
import re
from typing import Dict, List, Tuple

from traffic_es.llm.client import LLMClient
from traffic_es.nlu.grounding import ground

SYSTEM = (
    "Bạn trích thông tin hiện trường giao thông từ câu tiếng Việt thành JSON gồm 2 khóa: "
    "'facts' (map node ontology hợp lệ) và 'raw_events' (mảng câu sự kiện thô). "
    "Node hợp lệ: phuongtien.loai ('o_to'|'xe_may'); chiso.nongDoCon_khiTho (mg/l); "
    "chiso.nongDoCon_mau (mg/100ml); chiso.tocDo; chiso.tocDoGioiHan (km/h); "
    "boicanh.khuVuc ('khu_dan_cu'); nguoi.khong_mu_bao_hiem/khong_day_an_toan (bool); "
    "nguoi.coGPLX (bool); hanhvi.vuot_den_do (bool). "
    "Sự kiện va chạm/tái phạm/bỏ chạy để trong raw_events. TUYỆT ĐỐI không bịa số. "
    "Chỉ trả JSON."
)

_FENCE = re.compile(r"^```[a-zA-Z]*\n?|\n?```$")


def _parse(raw: str) -> dict:
    s = (raw or "").strip()
    s = _FENCE.sub("", s).strip()
    try:
        data = json.loads(s)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def _coerce(facts: Dict[str, object]) -> Dict[str, object]:
    out: Dict[str, object] = {}
    for k, v in facts.items():
        if isinstance(v, str):
            low = v.strip().lower()
            if low in ("true", "false"):
                out[k] = low == "true"
                continue
            try:
                out[k] = float(v)
                continue
            except ValueError:
                pass
        out[k] = v
    return out


class LLMExtractor:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    def extract(self, text: str) -> Tuple[Dict[str, object], Dict[str, str], List[str]]:
        data = _parse(self.llm.complete(system=SYSTEM, user=text))
        if not data:
            return {}, {}, []
        facts = _coerce(data.get("facts", {}) or {})
        facts, _warns = ground(facts)  # grounding chống ảo giác / node lạ
        return facts, {}, list(data.get("raw_events", []) or [])
