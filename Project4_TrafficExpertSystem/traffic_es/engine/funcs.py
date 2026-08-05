from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List

from traffic_es.engine.working_memory import WorkingMemory
from traffic_es.engine.trace import Trace


@dataclass
class Func:
    """Hàm Deduce_Objects: từ inputs (các key) tính ra output (một key)."""

    name: str
    inputs: List[str]
    output: str
    fn: Callable[[WorkingMemory], object]


def apply_funcs(wm: WorkingMemory, funcs: List[Func], trace: Trace) -> None:
    """Chạy các Func lặp tới điểm bất động (fixpoint)."""
    changed = True
    while changed:
        changed = False
        for f in funcs:
            if wm.has(f.output):
                continue
            if all(wm.has(i) for i in f.inputs):
                value = f.fn(wm)
                wm.set(f.output, value, source=f"FUNC:{f.name}")
                trace.add(
                    "FUNC",
                    f"{f.output} = {value} (qua {f.name})",
                    {"func": f.name, "output": f.output, "value": value},
                )
                changed = True


def _vuot_toc_do_pct(wm: WorkingMemory) -> float:
    gh = wm.get("chiso.tocDoGioiHan")
    return round((wm.get("chiso.tocDo") - gh) / gh * 100, 2)


def _vuot_toc_do_kmh(wm: WorkingMemory) -> float:
    return wm.get("chiso.tocDo") - wm.get("chiso.tocDoGioiHan")


# Giới hạn tốc độ mặc định theo loại khu vực (QCVN / thực tiễn phổ biến).
# Chỉ điền khi chưa có chiso.tocDoGioiHan tường minh trong facts.
_GIOI_HAN_KHU_VUC = {
    "khu_dan_cu": 50.0,
    "do_thi": 60.0,
    "ngoai_do_thi": 80.0,
    "cao_toc": 120.0,
}


def _gioi_han_theo_khu_vuc(wm: WorkingMemory) -> float:
    return _GIOI_HAN_KHU_VUC[wm.get("boicanh.khuVuc")]


DEFAULT_FUNCS: List[Func] = [
    Func(
        "gioi_han_theo_khu_vuc",
        ["boicanh.khuVuc"],
        "chiso.tocDoGioiHan",
        _gioi_han_theo_khu_vuc,
    ),
    Func(
        "vuot_toc_do_pct",
        ["chiso.tocDo", "chiso.tocDoGioiHan"],
        "chiso.vuot_toc_do_pct",
        _vuot_toc_do_pct,
    ),
    Func(
        "vuot_toc_do_kmh",
        ["chiso.tocDo", "chiso.tocDoGioiHan"],
        "chiso.vuot_toc_do_kmh",
        _vuot_toc_do_kmh,
    ),
]
