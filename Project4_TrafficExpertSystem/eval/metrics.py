from __future__ import annotations

from typing import Any, Dict, List, Tuple


def slot_prf(pred: Dict[str, Any], gold: Dict[str, Any]) -> Tuple[float, float, float]:
    """Precision/Recall/F1 theo cặp (key, value) đúng."""
    correct = sum(1 for k, v in gold.items() if k in pred and pred[k] == v)
    p = correct / len(pred) if pred else (1.0 if not gold else 0.0)
    r = correct / len(gold) if gold else 1.0
    f = 2 * p * r / (p + r) if (p + r) else 0.0
    return p, r, f


def set_match(pred: List[str], gold: List[str]) -> float:
    """1.0 nếu tập bằng nhau, ngược lại 0.0 (exact-set)."""
    return 1.0 if set(pred) == set(gold) else 0.0
