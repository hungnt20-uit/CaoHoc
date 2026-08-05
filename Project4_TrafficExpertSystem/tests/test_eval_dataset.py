from pathlib import Path

from eval.dataset import load_cases


def test_load_cases():
    cases = load_cases(Path("eval/testset.jsonl"))
    assert len(cases) >= 15
    c = cases[0]
    assert c.id and c.text and "rule_ids" in c.expected
