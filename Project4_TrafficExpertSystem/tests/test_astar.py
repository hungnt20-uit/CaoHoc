from traffic_es.engine.astar import DedRule, astar_solve


def test_finds_minimal_chain():
    rules = [
        DedRule("r1", {"U", "I"}, "S", w=1),
        DedRule("r2", {"S", "cos"}, "P", w=1),
        DedRule("r3", {"U", "I", "cos"}, "P", w=5),  # đường tắt nhưng đắt
    ]
    sol = astar_solve(H={"U", "I", "cos"}, goal={"P"}, rules=rules)
    assert [r.id for r in sol] == ["r1", "r2"]  # tổng w=2 < 5


def test_unsolvable_returns_none():
    rules = [DedRule("r1", {"A"}, "B", w=1)]
    assert astar_solve(H={"X"}, goal={"B"}, rules=rules) is None


def test_goal_already_known_returns_empty():
    assert astar_solve(H={"P"}, goal={"P"}, rules=[]) == []
