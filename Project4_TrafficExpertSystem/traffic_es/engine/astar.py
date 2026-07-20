from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from typing import List, Optional, Set


@dataclass
class DedRule:
    """Luật suy diễn trong mạng (M,R): inputs (tập key) -> output (một key), trọng số w."""

    id: str
    inputs: frozenset
    output: str
    w: float = 1.0

    def __post_init__(self) -> None:
        self.inputs = frozenset(self.inputs)


def _h(state: Set[str], goal: Set[str]) -> int:
    """Heuristic: số key mục tiêu còn thiếu (admissible khi mỗi luật thêm tối đa 1 key)."""
    return len(goal - state)


def astar_solve(
    H: Set[str], goal: Set[str], rules: List[DedRule]
) -> Optional[List[DedRule]]:
    """A* tìm 'lời giải tốt' (tổng trọng số nhỏ nhất).

    Trả về danh sách luật; [] nếu goal ⊆ H; None nếu vô nghiệm.
    """
    start = frozenset(H)
    goal = set(goal)
    if goal <= start:
        return []
    counter = 0
    # (f, g, counter, state, path)
    frontier = [(_h(set(start), goal), 0.0, counter, start, [])]
    best_g = {start: 0.0}
    while frontier:
        _f, g, _c, state, path = heapq.heappop(frontier)
        sset = set(state)
        if goal <= sset:
            return path
        for r in rules:
            if r.output in sset:
                continue
            if r.inputs <= sset:
                nstate = frozenset(sset | {r.output})
                ng = g + r.w
                if ng < best_g.get(nstate, float("inf")):
                    best_g[nstate] = ng
                    counter += 1
                    heapq.heappush(
                        frontier,
                        (ng + _h(set(nstate), goal), ng, counter, nstate, path + [r]),
                    )
    return None
