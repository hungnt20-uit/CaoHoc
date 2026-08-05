from __future__ import annotations

import re
from typing import Optional, Tuple

_NUM = re.compile(r"\d{1,3}(?:\.\d{3})+|\d+")


def parse_money(s: str) -> int:
    m = _NUM.search(s)
    if not m:
        raise ValueError(f"Không tìm thấy số tiền trong: {s!r}")
    return int(m.group(0).replace(".", ""))


def money_range(text: str) -> Optional[Tuple[int, int]]:
    nums = [int(x.replace(".", "")) for x in _NUM.findall(text)]
    # chỉ giữ số lớn (>= 10.000) để tránh dính "1 lít", "0,4", số điều/khoản
    money = [n for n in nums if n >= 10000]
    if not money:
        return None
    if len(money) == 1:
        return (money[0], money[0])
    return (money[0], money[1])
