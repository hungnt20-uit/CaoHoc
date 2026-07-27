"""Mạng tính toán (M,R) + mô hình bài toán (H, Goal) + A* cho Deduce_Objects.

Thay cho việc chạy tất cả Func tới fixpoint một cách "mù", ở đây ta:
  1. Dựng mạng (M,R): M = các thuộc tính (key), R = các Func xem như luật
     inputs -> output.
  2. Xác định Goal = các thuộc tính DẪN XUẤT mà tập luật nghiệp vụ cần nhưng
     working memory chưa có (H = các key đang có).
  3. Dùng A* tìm "lời giải tốt" S (chuỗi Func tối thiểu theo tổng trọng số) rồi
     áp dụng đúng theo thứ tự đó, ghi vết [ASTAR] + [FUNC].
Phần Func còn lại (nếu có) vẫn chạy fixpoint để đảm bảo tính đầy đủ.
"""

from __future__ import annotations

from typing import List, Set

from traffic_es.engine.astar import DedRule, astar_solve
from traffic_es.engine.conditions import referenced_keys
from traffic_es.engine.funcs import Func, apply_funcs
from traffic_es.engine.trace import Trace
from traffic_es.engine.working_memory import WorkingMemory


def funcs_to_network(funcs: List[Func]) -> List[DedRule]:
    """M,R: mỗi Func trở thành một luật suy diễn inputs -> output (w=1)."""
    return [DedRule(f.name, frozenset(f.inputs), f.output, w=1.0) for f in funcs]


def goal_attrs(rules, funcs: List[Func], wm: WorkingMemory) -> Set[str]:
    """Goal = thuộc tính dẫn xuất (output của Func) mà luật cần & wm chưa có."""
    outputs = {f.output for f in funcs}
    goals: Set[str] = set()
    for r in rules:
        for node in r.dieu_kien:
            for key in referenced_keys(node):
                if key in outputs and not wm.has(key):
                    goals.add(key)
    return goals


def solve_and_apply(
    wm: WorkingMemory, funcs: List[Func], rules, trace: Trace
) -> None:
    """Suy diễn có hướng bằng A* rồi bổ sung fixpoint phần còn lại."""
    goals = goal_attrs(rules, funcs, wm)
    if goals:
        net = funcs_to_network(funcs)
        H = set(wm.as_dict().keys())
        solution = astar_solve(H, goals, net)
        if solution:
            names = [dr.id for dr in solution]
            total = sum(dr.w for dr in solution)
            trace.add(
                "ASTAR",
                "Mạng tính toán (M,R): lời giải S = ["
                + ", ".join(names)
                + f"] cho Goal {{{', '.join(sorted(goals))}}} (tổng trọng số {total:g})",
                {"solution": names, "goals": sorted(goals), "cost": total},
            )
            fmap = {f.name: f for f in funcs}
            for dr in solution:
                f = fmap.get(dr.id)
                if f is None or wm.has(f.output):
                    continue
                if all(wm.has(i) for i in f.inputs):
                    value = f.fn(wm)
                    wm.set(f.output, value, source=f"FUNC:{f.name}")
                    trace.add(
                        "FUNC",
                        f"{f.output} = {value} (qua {f.name})",
                        {"func": f.name, "output": f.output, "value": value},
                    )
    # Đảm bảo đầy đủ: các Func còn lại (không nằm trong Goal) chạy fixpoint.
    apply_funcs(wm, funcs, trace)
