from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import yaml


@dataclass
class NghiDinhLinks:
    """Quan hệ hiệu lực & thay thế giữa các Nghị định (168 ↔ 100 ↔ 123)."""

    items: List[dict]
    hieu_luc_map: Dict[str, str]

    @classmethod
    def load(cls, path: Path) -> "NghiDinhLinks":
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        return cls(raw.get("nghi_dinh", []), raw.get("hieu_luc_theo_linh_vuc", {}))

    def hieu_luc_hien_hanh(self, linh_vuc: str) -> str:
        """Nghị định còn hiệu lực cho lĩnh vực (duong_bo | duong_sat)."""
        return self.hieu_luc_map.get(linh_vuc, "")

    def bi_thay_the_boi(self, nghi_dinh_id: str) -> List[str]:
        """Danh sách Nghị định bị `nghi_dinh_id` thay thế."""
        for it in self.items:
            if it["id"] == nghi_dinh_id:
                return it.get("thay_the", [])
        return []
