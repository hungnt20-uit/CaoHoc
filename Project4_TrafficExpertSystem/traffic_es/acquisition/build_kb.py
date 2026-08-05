from __future__ import annotations

from pathlib import Path
from typing import List

import yaml

from traffic_es.acquisition.segmenter import segment
from traffic_es.acquisition.money import money_range
from traffic_es.acquisition.rule_extractor import extract_rules
from traffic_es.llm.client import LLMClient
from traffic_es.knowledge.rules import Rule


def build_kb_from_text(text: str, nghi_dinh: str, llm: LLMClient) -> List[Rule]:
    rules: List[Rule] = []
    last_range = None
    for clause in segment(text):
        mr = money_range(clause.text)
        if mr:
            last_range = mr  # khoản mẹ mang mức tiền, áp cho các điểm con
        if last_range is None:
            continue
        tien_min, tien_max = last_range
        rules.extend(extract_rules(clause, nghi_dinh, llm, tien_min, tien_max))
    return rules


def write_rules_yaml(rules: List[Rule], path: Path) -> None:
    data = {"rules": [r.model_dump(exclude_none=True) for r in rules]}
    Path(path).write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
