from __future__ import annotations

import re

_ABBR = {
    r"\bnđc\b": "nồng độ cồn",
    r"\bkdc\b": "khu dân cư",
    r"\bgplx\b": "giấy phép lái xe",
    r"\btncgt\b": "tai nạn giao thông",
    # lỗi gõ thường gặp → để KG keyphrase "rượu" khớp được
    r"rựu": "rượu",
}


def normalize(text: str) -> str:
    t = text.strip()
    # 0,42 -> 0.42 (số thập phân), giữ nguyên dấu phẩy ngăn cách khác
    t = re.sub(r"(?<=\d),(?=\d)", ".", t)
    low = t.lower()
    for pat, full in _ABBR.items():
        low = re.sub(pat, full, low)
    return low
