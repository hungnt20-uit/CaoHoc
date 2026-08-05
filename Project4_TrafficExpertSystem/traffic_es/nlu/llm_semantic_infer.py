"""Bài toán 1 — nửa LLM: suy diễn tình tiết gián tiếp bằng mô hình ngôn ngữ lớn.

Bộ suy luận ký hiệu chỉ nhận ra tình tiết khi câu chứa đúng từ khóa. LLM xử lý được
diễn đạt vòng ("xe tôi hạ gục cái gương của người ta", "tôi bỏ đi luôn không đợi
công an") mà từ khóa bỏ sót.

Ràng buộc: LLM **chỉ được chọn trong `CLOSED_VOCAB`** và phải kèm `confidence` + lý do
+ trích dẫn nguồn. Mọi đề xuất ngoài danh mục, sai kiểu, hoặc confidence ngoài [0,1]
đều bị loại — LLM đề xuất, ontology phê duyệt.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from traffic_es.llm.client import LLMClient
from traffic_es.nlu.evidence import cites_source
from traffic_es.nlu.semantic_infer import (
    CLOSED_VOCAB,
    VOCAB_BY_FACT,
    CircumstanceInferrer,
    KeywordInferrer,
)

_VOCAB_DOC = "\n".join(
    f"- {tt.fact} ({'tăng nặng' if tt.loai == 'tang_nang' else 'giảm nhẹ'}): {tt.mo_ta}"
    for tt in CLOSED_VOCAB
)

SYSTEM = (
    "Bạn suy luận TÌNH TIẾT của vụ vi phạm giao thông từ mô tả sự kiện tiếng Việt.\n"
    "Chỉ được chọn trong danh mục sau, TUYỆT ĐỐI không tạo tên tình tiết mới:\n"
    f"{_VOCAB_DOC}\n"
    'Trả về JSON: {"tinh_tiet": [{"fact": "...", "value": true, "confidence": 0.0-1.0, '
    '"ly_do": "...", "nguon": "..."}]}\n'
    "'nguon' phải COPY Y HỆT một cụm chữ có trong câu gốc — không diễn giải, không thêm "
    "chữ, không viết kiểu \"cụm chữ '...'\". Tình tiết nào không trích dẫn được sẽ bị loại.\n"
    "Bản thân hành vi vi phạm KHÔNG phải tình tiết tăng nặng: vượt đèn đỏ hay không đội "
    "mũ bảo hiểm đã bị phạt riêng, đừng liệt kê chúng thành 'không chấp hành'. "
    "Tình tiết đó chỉ dành cho việc chống đối/bỏ chạy khỏi người thi hành công vụ.\n"
    "Chỉ liệt kê tình tiết THỰC SỰ xảy ra. Nếu câu phủ định (không gây tai nạn) thì "
    "KHÔNG liệt kê. Nếu không có tình tiết nào, trả mảng rỗng. Chỉ trả JSON."
)

_FENCE = re.compile(r"^```[a-zA-Z]*\n?|\n?```$")


def _parse(raw: str) -> List[Dict[str, Any]]:
    s = _FENCE.sub("", (raw or "").strip()).strip()
    data: Any = None
    for candidate in (s, s[s.find("{") : s.rfind("}") + 1] if "{" in s else ""):
        if not candidate:
            continue
        try:
            data = json.loads(candidate)
            break
        except (json.JSONDecodeError, TypeError):
            continue
    if isinstance(data, dict):
        items = data.get("tinh_tiet") or data.get("tinhtiet") or []
    elif isinstance(data, list):
        items = data
    else:
        return []
    return [i for i in items if isinstance(i, dict)]


def validate(items: List[Dict[str, Any]], text: str = "") -> List[Dict[str, object]]:
    """Giữ lại đề xuất hợp lệ theo closed vocabulary và có trích dẫn thật trong câu.

    Trích dẫn phải là cụm chữ nguyên văn. Khi LLM diễn giải lại thay vì trích — quan sát
    thấy Qwen trả về `cụm chữ 'không đội mũ bảo hiểm' và 'việt đèn đỏ'` — thì đó là dấu
    hiệu nó đang suy diễn từ kiến thức chung chứ không đọc từ câu người dùng nói.
    """
    out: List[Dict[str, object]] = []
    seen = set()
    for it in items:
        fact = it.get("fact")
        if not isinstance(fact, str) or fact not in VOCAB_BY_FACT or fact in seen:
            continue
        if it.get("value") is not True:  # danh mục hiện tại chỉ mang giá trị boolean
            continue
        try:
            conf = float(it.get("confidence", 0.0))
        except (TypeError, ValueError):
            continue
        if not 0.0 <= conf <= 1.0:
            continue
        nguon = str(it.get("nguon") or "")
        if text and not cites_source(text, nguon):
            continue
        seen.add(fact)
        out.append(
            {
                "fact": fact,
                "value": True,
                "confidence": conf,
                "ly_do": str(it.get("ly_do") or VOCAB_BY_FACT[fact].mo_ta),
                "nguon": nguon,
                "bo_suy_luan": "llm",
            }
        )
    return out


class LLMCircumstanceInferrer:
    """Suy diễn tình tiết bằng LLM, tự lùi về từ khóa khi LLM lỗi hoặc rỗng."""

    def __init__(
        self,
        llm: LLMClient,
        fallback: Optional[CircumstanceInferrer] = None,
    ):
        self.llm = llm
        self.fallback = fallback if fallback is not None else KeywordInferrer()

    def infer(self, raw_events: List[str], text: str = "") -> List[Dict[str, object]]:
        # Dùng cả câu chứ không chỉ sự kiện đã tách bằng từ khóa, vì chính những cách
        # diễn đạt không chứa từ khóa mới là phần cần tới LLM.
        prompt = (text or " ".join(raw_events)).strip()
        if not prompt:
            return []
        try:
            raw = self.llm.complete(system=SYSTEM, user=prompt)
            items = validate(_parse(raw), prompt)
        except Exception:  # mạng/quota/JSON lỗi -> không được làm sập luồng suy diễn
            items = []
        return items if items else self.fallback.infer(raw_events, text)
