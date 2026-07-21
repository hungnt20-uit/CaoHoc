from __future__ import annotations

from traffic_es.engine.trace import Trace
from traffic_es.engine.penalty import KetQua


def _tien(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def render_explanation(trace: Trace, ket_qua: KetQua) -> str:
    if not ket_qua.chi_tiet:
        return "Không phát hiện hành vi vi phạm từ thông tin cung cấp."
    lines = ["**Phân tích hành vi & căn cứ pháp lý:**"]
    has_meta = any(s.kind == "META" for s in trace.steps)
    for i, d in enumerate(ket_qua.chi_tiet, 1):
        lines.append(
            f"{i}. **{d.hanh_vi}**\n"
            f"   - Căn cứ: {d.can_cu}\n"
            f"   - Tiền phạt: {_tien(d.tien)}đ · Hình phạt bổ sung: {d.phat_bo_sung}"
        )
    if has_meta:
        lines.append("> Có **tình tiết tăng nặng** → áp mức tiền tối đa của khung.")
    tong = (
        f"\n**Tổng hợp:** {len(ket_qua.chi_tiet)} lỗi · "
        f"tổng tiền **{_tien(ket_qua.tong_tien)}đ**"
    )
    if ket_qua.tuoc_gplx_thang_max:
        tong += f" · tước GPLX tối đa **{ket_qua.tuoc_gplx_thang_max} tháng**"
    lines.append(tong)
    return "\n".join(lines)
