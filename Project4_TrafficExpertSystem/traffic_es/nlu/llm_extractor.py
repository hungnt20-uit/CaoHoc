from __future__ import annotations

import json
from typing import Dict, List, Tuple

from traffic_es.llm.client import LLMClient

SYSTEM = (
    "Trích thông tin hiện trường giao thông thành JSON gồm 'facts' (ánh xạ node ontology: "
    "phuongtien.loai [o_to|xe_may], chiso.nongDoCon_khiTho, chiso.tocDo, chiso.tocDoGioiHan, "
    "boicanh.khuVuc) và 'raw_events' (danh sách câu sự kiện thô như va chạm/tái phạm). "
    "Chỉ dùng node hợp lệ, không bịa số."
)


class LLMExtractor:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    def extract(self, text: str) -> Tuple[Dict[str, object], Dict[str, str], List[str]]:
        raw = self.llm.complete(system=SYSTEM, user=text)
        if not raw.strip():
            return {}, {}, []
        data = json.loads(raw)
        return data.get("facts", {}), {}, data.get("raw_events", [])
