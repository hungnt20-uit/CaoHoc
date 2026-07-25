from eval.metrics import slot_prf, set_match


def test_slot_prf_perfect():
    p, r, f = slot_prf({"a": 1, "b": 2}, {"a": 1, "b": 2})
    assert (p, r, f) == (1.0, 1.0, 1.0)


def test_slot_prf_partial():
    # dự đoán thiếu 1 slot đúng, thừa 1 slot sai
    p, r, f = slot_prf(pred={"a": 1, "c": 9}, gold={"a": 1, "b": 2})
    assert r == 0.5 and p == 0.5


def test_set_match_exact():
    assert set_match(["R1", "R2"], ["R2", "R1"]) == 1.0
    assert set_match([], []) == 1.0
    assert set_match(["R1"], ["R1", "R2"]) == 0.0
