from traffic_es.engine.trace import Trace, TraceStep


def test_add_and_iterate():
    tr = Trace()
    tr.add("FUNC", "tính vượt tốc độ", {"vuot_pct": 80.0})
    tr.add("RULE", "khớp R_TOCDO", {"rule_id": "R1"})
    kinds = [s.kind for s in tr.steps]
    assert kinds == ["FUNC", "RULE"]
    assert tr.steps[0].data["vuot_pct"] == 80.0


def test_render_contains_detail():
    tr = Trace()
    tr.add("META", "áp mức tối đa", {})
    out = tr.render()
    assert "META" in out and "áp mức tối đa" in out
