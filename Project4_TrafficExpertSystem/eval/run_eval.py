from __future__ import annotations

from pathlib import Path

from eval.dataset import load_cases
from eval.runner import evaluate
from eval.report import to_markdown

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    cases = load_cases(ROOT / "eval" / "testset.jsonl")
    rep = evaluate(cases, ROOT / "traffic_es" / "knowledge" / "rules")
    md = to_markdown(rep)
    out = ROOT / "docs" / "bao-cao-hieu-nang.md"
    out.write_text(md, encoding="utf-8")
    print(md)
    print(f"\n>> Đã ghi báo cáo: {out}")


if __name__ == "__main__":
    main()
