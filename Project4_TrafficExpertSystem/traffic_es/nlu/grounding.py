from __future__ import annotations

from typing import Dict, List, Tuple

_KNOWN_PREFIX = ("phuongtien.", "nguoi.", "chiso.", "boicanh.", "tinhtiet.")
_RANGES = {
    "chiso.nongDoCon_khiTho": (0.0, 5.0),
    "chiso.nongDoCon_mau": (0.0, 500.0),
    "chiso.tocDo": (0.0, 300.0),
    "chiso.tocDoGioiHan": (0.0, 150.0),
}


def ground(facts: Dict[str, object]) -> Tuple[Dict[str, object], List[str]]:
    clean: Dict[str, object] = {}
    warns: List[str] = []
    for k, v in facts.items():
        if not k.startswith(_KNOWN_PREFIX):
            warns.append(f"Bỏ node lạ ngoài ontology: {k}")
            continue
        if k in _RANGES and isinstance(v, (int, float)) and not isinstance(v, bool):
            lo, hi = _RANGES[k]
            if not (lo <= v <= hi):
                warns.append(f"{k}={v} ngoài miền [{lo},{hi}] → loại")
                continue
        clean[k] = v
    return clean, warns
