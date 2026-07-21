from __future__ import annotations

from typing import Dict, List

# closed-vocabulary: chỉ suy ra tình tiết đã định nghĩa
_RULES = [
    (
        "tinhtiet.gay_tai_nan",
        ["đâm", "va chạm", "quẹt", "tông", "tai nạn"],
        "va chạm/gây thiệt hại cho người hoặc phương tiện khác",
    ),
    (
        "tinhtiet.tai_pham",
        ["tái phạm", "nhiều lần", "lần thứ hai"],
        "hành vi lặp lại",
    ),
    (
        "tinhtiet.khong_chap_hanh",
        ["bỏ chạy", "không chấp hành", "chống đối"],
        "không chấp hành yêu cầu của người thi hành công vụ",
    ),
]


def infer_circumstances(raw_events: List[str]) -> List[Dict[str, object]]:
    joined = " ".join(raw_events).lower()
    out: List[Dict[str, object]] = []
    for fact, kws, ly_do in _RULES:
        hit = next((kw for kw in kws if kw in joined), None)
        if hit:
            out.append(
                {
                    "fact": fact,
                    "value": True,
                    "confidence": 0.9,
                    "ly_do": ly_do,
                    "nguon": hit,
                }
            )
    return out
