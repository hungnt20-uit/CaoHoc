"""Nhận diện cực tính (polarity) của cụm từ trong câu tiếng Việt.

Bài toán 2 đòi "ánh xạ CHÍNH XÁC vào node ontology". Khớp cụm thuần theo chuỗi con
sẽ quy kết vi phạm cho cả câu phủ định: "dừng đèn đỏ đúng luật" chứa cụm "đèn đỏ",
"không gây tai nạn" chứa cụm "tai nạn". Module này quyết định một lần khớp có nằm
trong ngữ cảnh phủ định/tuân thủ hay không, để tầng trên loại bỏ nó.

Phạm vi xét là *mệnh đề* chứa cụm khớp, không phải cả câu: cắt tại dấu ngắt hoặc
liên từ gần nhất phía trước. Nhờ vậy "không thắt dây an toàn, và vượt đèn đỏ" vẫn
nhận đúng "vượt đèn đỏ" là vi phạm thật, dù phía trước có chữ "không".
"""

from __future__ import annotations

import re
from typing import Tuple

# Phủ định trực tiếp.
NEGATION_CUES: Tuple[str, ...] = (
    "không",
    "chẳng",
    "chả",
    "chưa",
    "đâu có",
    "khỏi",
    "phủ nhận",
)

# Tuân thủ / bất thành: nhắc tới hành vi nhưng KHÔNG vi phạm.
COMPLIANCE_CUES: Tuple[str, ...] = (
    "dừng",
    "dừng lại",
    "chấp hành",
    "tuân thủ",
    "đúng luật",
    "đúng quy định",
    "nhường",
    "chờ",
    "đợi",
    "tránh",
    "tránh được",
    "suýt",
    "may mà",
    "may là",
)

_CLAUSE_SEP = re.compile(r"[,;.:!?()]|\bvà\b|\brồi\b|\bnhưng\b|\bcòn\b|\bsong\b")


def clause_before(text: str, start: int) -> str:
    """Đoạn văn bản từ ranh giới mệnh đề gần nhất tới vị trí `start`."""
    left = text[:start]
    last = 0
    for m in _CLAUSE_SEP.finditer(left):
        last = m.end()
    return left[last:]


def _has_cue(fragment: str, cues: Tuple[str, ...]) -> bool:
    return any(re.search(rf"(?<!\w){re.escape(c)}(?!\w)", fragment) for c in cues)


def is_negated(text: str, start: int) -> bool:
    """Cụm bắt đầu tại `start` có nằm trong ngữ cảnh phủ định/tuân thủ không?

    Chỉ xét phần mệnh đề phía TRƯỚC cụm, nên cụm tự mang phủ định như
    "không đội mũ bảo hiểm" vẫn được coi là vi phạm thật.
    """
    fragment = clause_before(text.lower(), start)
    return _has_cue(fragment, NEGATION_CUES) or _has_cue(fragment, COMPLIANCE_CUES)


def has_negated_occurrence_only(text: str, phrase: str) -> bool:
    """True nếu `phrase` chỉ xuất hiện trong ngữ cảnh phủ định (hoặc không xuất hiện)."""
    low = text.lower()
    p = phrase.lower()
    i = low.find(p)
    if i < 0:
        return False
    while i >= 0:
        if not is_negated(low, i):
            return False
        i = low.find(p, i + 1)
    return True
