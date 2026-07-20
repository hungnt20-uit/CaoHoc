from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Tuple

import yaml

from traffic_es.knowledge.rules import Rule, MetaRule


def _load_yaml_files(rules_dir: Path) -> Iterable[dict]:
    for path in sorted(Path(rules_dir).glob("*.yaml")):
        with open(path, "r", encoding="utf-8") as f:
            yield yaml.safe_load(f) or {}


def load_rules(rules_dir: Path) -> List[Rule]:
    out: List[Rule] = []
    for doc in _load_yaml_files(rules_dir):
        for raw in doc.get("rules", []):
            out.append(Rule(**raw))
    return out


def load_meta_rules(rules_dir: Path) -> List[MetaRule]:
    out: List[MetaRule] = []
    for doc in _load_yaml_files(rules_dir):
        for raw in doc.get("meta_rules", []):
            out.append(MetaRule(**raw))
    return out


def load_kb(rules_dir: Path) -> Tuple[List[Rule], List[MetaRule]]:
    return load_rules(rules_dir), load_meta_rules(rules_dir)
