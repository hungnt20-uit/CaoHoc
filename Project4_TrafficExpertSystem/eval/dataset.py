from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class Case:
    id: str
    text: str
    expected: Dict[str, Any]


def load_cases(path: Path) -> List[Case]:
    out: List[Case] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("//"):
            continue
        d = json.loads(line)
        out.append(Case(d["id"], d["text"], d["expected"]))
    return out
