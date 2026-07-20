from __future__ import annotations

from typing import Any

from traffic_es.engine.working_memory import WorkingMemory

_OPS = ["==", "!=", ">=", "<=", ">", "<"]  # khớp toán tử 2 ký tự trước


def _parse_operand(tok: str, wm: WorkingMemory) -> Any:
    tok = tok.strip()
    if tok.startswith('"') and tok.endswith('"'):
        return tok[1:-1]
    low = tok.lower()
    if low == "true":
        return True
    if low == "false":
        return False
    try:
        return float(tok)
    except ValueError:
        pass
    # coi như tham chiếu key trong WorkingMemory
    return wm.get(tok, None)


def eval_condition(cond: str, wm: WorkingMemory) -> bool:
    op = next((o for o in _OPS if o in cond), None)
    if op is None:
        raise ValueError(f"Điều kiện thiếu toán tử: {cond!r}")
    left_raw, right_raw = cond.split(op, 1)
    left = _parse_operand(left_raw, wm)
    right = _parse_operand(right_raw, wm)
    if left is None or right is None:
        return False  # thiếu dữ kiện -> không khớp
    try:
        if op == "==":
            return left == right
        if op == "!=":
            return left != right
        if op == ">":
            return left > right
        if op == "<":
            return left < right
        if op == ">=":
            return left >= right
        if op == "<=":
            return left <= right
    except TypeError:
        return False
    raise ValueError(f"Toán tử không hỗ trợ: {op}")
