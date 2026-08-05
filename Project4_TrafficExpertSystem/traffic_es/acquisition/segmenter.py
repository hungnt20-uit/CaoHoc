from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional

_RE_DIEU = re.compile(r"^Điều\s+(\d+)\.\s*(.*)$")
_RE_KHOAN = re.compile(r"^(\d+)\.\s+(.*)$")
_RE_DIEM = re.compile(r"^([a-zđ])\)\s+(.*)$")


@dataclass
class Clause:
    dieu: Optional[int]
    dieu_title: str
    khoan: Optional[int]
    diem: Optional[str]
    text: str


def segment(text: str) -> List[Clause]:
    clauses: List[Clause] = []
    dieu: Optional[int] = None
    dieu_title = ""
    khoan: Optional[int] = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        m = _RE_DIEU.match(line)
        if m:
            dieu = int(m.group(1))
            dieu_title = m.group(2).strip()
            khoan = None
            continue
        m = _RE_DIEM.match(line)  # điểm 'a)' phân biệt với khoản '11.'
        if m:
            clauses.append(Clause(dieu, dieu_title, khoan, m.group(1), m.group(2).strip()))
            continue
        m = _RE_KHOAN.match(line)
        if m:
            khoan = int(m.group(1))
            clauses.append(Clause(dieu, dieu_title, khoan, None, m.group(2).strip()))
            continue
        # dòng nối tiếp: gắn vào clause cuối cùng
        if clauses:
            clauses[-1].text += " " + line
    return clauses
