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


def _keys_in_leaf(cond: str) -> set:
    """Các toán hạng dạng key (namespace.attr), bỏ literal số/chuỗi/bool."""
    op = next((o for o in _OPS if o in cond), None)
    parts = [cond] if op is None else cond.split(op, 1)
    keys = set()
    for tok in parts:
        t = tok.strip()
        if not t or t.startswith('"') or t.lower() in ("true", "false"):
            continue
        try:
            float(t)
            continue
        except ValueError:
            pass
        keys.add(t)
    return keys


def referenced_keys(node: object) -> set:
    """Tập khóa thuộc tính được tham chiếu trong node điều kiện (đệ quy)."""
    if isinstance(node, str):
        return _keys_in_leaf(node)
    if isinstance(node, dict):
        out: set = set()
        for k in ("any", "all"):
            for child in node.get(k, []):
                out |= referenced_keys(child)
        return out
    return set()


def eval_cond_node(node: object, wm: WorkingMemory) -> bool:
    """Đánh giá node điều kiện: str | {'any':[...]} | {'all':[...]} (đệ quy)."""
    if isinstance(node, str):
        return eval_condition(node, wm)
    if isinstance(node, dict):
        if "any" in node:
            return any(eval_cond_node(c, wm) for c in node["any"])
        if "all" in node:
            return all(eval_cond_node(c, wm) for c in node["all"])
    raise ValueError(f"Node điều kiện không hợp lệ: {node!r}")
