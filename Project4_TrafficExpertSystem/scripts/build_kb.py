"""Chạy trích KB thật từ các Nghị định. Cần API key + file .doc/.docx đã tải về máy.

Ví dụ:
    OPENAI_API_KEY=... .venv/bin/python scripts/build_kb.py \\
        --doc "/path/168_2024_ND-CP.docx" --nghi-dinh "168/2024/NĐ-CP" \\
        --dieu 6 --out traffic_es/knowledge/rules/168_dieu6.yaml

Provider thật cài trong lớp OpenAILLM bên dưới. Không chạy trong test.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

from traffic_es.acquisition.doc_to_text import to_text
from traffic_es.acquisition.build_kb import build_kb_from_text, write_rules_yaml
from traffic_es.acquisition.segmenter import segment
from traffic_es.llm.client import CachingLLM
from traffic_es.llm.providers import OpenAILLM  # provider dùng chung (DRY)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--doc", required=True)
    ap.add_argument("--nghi-dinh", required=True)
    ap.add_argument("--dieu", type=int, default=None, help="chỉ trích 1 Điều để tiết kiệm token")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    text = to_text(Path(args.doc))
    if args.dieu is not None:
        clauses = [c for c in segment(text) if c.dieu == args.dieu]
        text = "\n".join(
            [f"Điều {args.dieu}. {clauses[0].dieu_title}"]
            + [
                f"{c.khoan}. {c.text}" if c.diem is None else f"{c.diem}) {c.text}"
                for c in clauses
            ]
        )
    llm = CachingLLM(OpenAILLM())
    rules = build_kb_from_text(text, args.nghi_dinh, llm)
    write_rules_yaml(rules, Path(args.out))
    print(f"Đã ghi {len(rules)} luật -> {args.out}")


if __name__ == "__main__":
    main()
