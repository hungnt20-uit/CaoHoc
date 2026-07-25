from eval.report import to_markdown


def test_markdown_has_metrics():
    rep = {
        "n": 10,
        "conclusion_acc": 0.9,
        "money_acc": 0.8,
        "slot_f1": 0.85,
        "slot_p": 0.85,
        "slot_r": 0.85,
        "avg_t_nlu_ms": 1.2,
        "avg_t_engine_ms": 0.3,
        "per_case": [],
    }
    md = to_markdown(rep)
    assert "90.0%" in md and "Kết luận" in md
