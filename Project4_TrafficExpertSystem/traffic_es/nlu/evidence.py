"""Kiểm chứng fact do LLM đề xuất phải có căn cứ trong chính câu người dùng nói.

Model nhỏ chạy local bịa fact khá đều tay: quan sát Qwen2.5-Coder-7B thấy nó tự thêm
`chiso.tocDoGioiHan = 0.8` vào câu chỉ nói về nồng độ cồn, hay tự gán
`boicanh.khuVuc = khu_dan_cu` cho câu không nhắc gì tới khu dân cư. Trong hệ chuyên
gia pháp lý, một con số bịa có thể đẻ ra cả một lỗi vi phạm không tồn tại.

Hai tầng kiểm chứng ở đây bổ khuyết cho nhau:

* `number_appears` — tất định, không phụ thuộc model: giá trị số phải xuất hiện nguyên
  dạng trong câu. Chốt này chặn được cả khi LLM bịa luôn cả phần trích dẫn.
* `cites_source` — trích dẫn LLM đưa ra phải là cụm chữ có thật trong câu. Chốt này
  bắt được fact dạng enum/bool vốn không mang số để đối chiếu.
"""

from __future__ import annotations

import re
from typing import Set

_WS = re.compile(r"\s+")


def canon(text: str) -> str:
    """Hạ chữ thường và gộp khoảng trắng để so khớp không vướng lỗi trình bày."""
    return _WS.sub(" ", (text or "").strip().lower())


def _number_tokens(value: float) -> Set[str]:
    """Các cách viết một con số có thể gặp trong câu tiếng Việt (0.45 và 0,45)."""
    number = float(value)
    if number.is_integer():
        return {str(int(number))}
    plain = "%g" % number
    return {plain, plain.replace(".", ",")}


def number_appears(text: str, value: float) -> bool:
    """Con số có xuất hiện nguyên dạng trong câu không?

    Chặn hai đầu để `50` không khớp nhầm vào `150`, `0.50` hay `50.5`. Dấu chấm cuối
    câu vẫn được chấp nhận vì chỉ phần thập phân *có chữ số theo sau* mới bị loại.
    """
    haystack = canon(text)
    return any(
        re.search(
            rf"(?<![\d])(?<![\d][.,]){re.escape(tok)}(?![\d])(?![.,]\d)",
            haystack,
        )
        for tok in _number_tokens(value)
    )


# Trích dẫn dài hơn ngần này so với câu thì coi như trỏ vào cả câu, không còn là dẫn chứng.
TY_LE_TRICH_TOI_DA = 0.7
_DAI_TOI_THIEU_DE_XET_TY_LE = 30


def cites_source(text: str, nguon: str) -> bool:
    """Trích dẫn có phải một cụm chữ cụ thể, có thật trong câu không?

    Đòi trùng khít chứ không so gần đúng: LLM diễn giải lại thay vì trích nguyên văn
    (kiểu `cụm chữ 'không đội mũ bảo hiểm' và 'việt đèn đỏ'`) chính là dấu hiệu nó đang
    suy diễn chứ không đọc từ câu gốc — đúng thứ cần loại.

    Trích nguyên cả câu cũng bị loại: Qwen từng "dẫn chứng" cho tình tiết gây tai nạn
    bằng chính toàn bộ câu vốn không hề nhắc tới tai nạn. Dẫn cả câu thì luôn trùng khít
    mà chẳng chỉ ra bằng chứng nào, nên nó vô hiệu hóa phép kiểm này.
    """
    quote = canon(nguon)
    haystack = canon(text)
    if not quote or quote not in haystack:
        return False
    if len(haystack) >= _DAI_TOI_THIEU_DE_XET_TY_LE:
        return len(quote) / len(haystack) <= TY_LE_TRICH_TOI_DA
    return True
