"""Bài toán 1 — suy diễn tình tiết/hành vi vi phạm gián tiếp từ sự kiện thô.

Danh mục tình tiết là *closed vocabulary*: mọi bộ suy luận (từ khóa hay LLM) chỉ được
chọn trong `CLOSED_VOCAB`, không được sinh fact mới. Nhờ vậy LLM chỉ *đề xuất*, còn
ontology *phê duyệt* — đúng nguyên tắc chống ảo giác pháp lý.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Mapping, Protocol, Tuple

from traffic_es.nlu.polarity import has_negated_occurrence_only

TANG_NANG = "tang_nang"
GIAM_NHE = "giam_nhe"


@dataclass(frozen=True)
class TinhTiet:
    fact: str
    loai: str
    mo_ta: str
    keywords: Tuple[str, ...]


CLOSED_VOCAB: Tuple[TinhTiet, ...] = (
    TinhTiet(
        "tinhtiet.gay_tai_nan",
        TANG_NANG,
        "va chạm/gây thiệt hại cho người hoặc phương tiện khác",
        ("đâm", "va chạm", "quẹt", "tông", "tai nạn", "gây thương tích"),
    ),
    TinhTiet(
        "tinhtiet.tai_pham",
        TANG_NANG,
        "hành vi lặp lại",
        ("tái phạm", "nhiều lần", "lần thứ hai", "tái diễn"),
    ),
    TinhTiet(
        "tinhtiet.khong_chap_hanh",
        TANG_NANG,
        "không chấp hành yêu cầu của người thi hành công vụ",
        ("bỏ chạy", "không chấp hành", "chống đối", "cãi lại", "cản trở"),
    ),
    TinhTiet(
        "tinhtiet.tu_nguyen_khai_bao",
        GIAM_NHE,
        "tự nguyện khai báo, thành thật hối lỗi (Điều 9 Luật XLVPHC)",
        ("tự nguyện khai", "thành thật", "hối lỗi", "tự giác trình báo", "xin nhận lỗi"),
    ),
)

VOCAB_BY_FACT: Dict[str, TinhTiet] = {t.fact: t for t in CLOSED_VOCAB}


@dataclass(frozen=True)
class TrungLap:
    """Một hành vi đã bị xử phạt riêng, kèm những cụm chữ mô tả chính hành vi đó."""

    fact: str
    cues: Tuple[str, ...]


# Điều 10 khoản 2 Luật XLVPHC 2012: tình tiết đã được quy định là hành vi vi phạm hành
# chính thì KHÔNG được coi là tình tiết tăng nặng. "Vượt đèn đỏ" đã bị phạt riêng theo
# Điều 7 khoản 7 điểm c NĐ 168/2024, nên không được tính thêm lần nữa dưới danh nghĩa
# "không chấp hành" — nếu không, một lỗi bị phạt hai lần.
TRUNG_LAP: Dict[str, Tuple[TrungLap, ...]] = {
    "tinhtiet.khong_chap_hanh": (
        TrungLap(
            "hanhvi.vuot_den_do",
            ("đèn đỏ", "đèn tín hiệu", "hiệu lệnh đèn", "tín hiệu giao thông", "vượt đèn"),
        ),
        TrungLap(
            "hanhvi.vuot_den_vang",
            ("đèn vàng", "vượt đèn vàng"),
        ),
        TrungLap(
            "hanhvi.khong_chap_hanh_csgt",
            ("csgt", "cảnh sát giao thông", "hiệu lệnh của cảnh sát"),
        ),
    ),
}


def drop_double_counted(
    inferred: List[Dict[str, object]], facts: Mapping[str, object]
) -> Tuple[List[Dict[str, object]], List[str]]:
    """Loại tình tiết tăng nặng vốn chính là vi phạm đã bị tính thành lỗi riêng.

    Chặn ở tầng suy diễn chứ không nhờ prompt, vì đây là quy tắc pháp lý: nó phải đúng
    bất kể bộ suy luận nào đề xuất, kể cả khi đổi sang model khác.

    Chỉ loại khi tình tiết được viện dẫn bằng chính cụm chữ mô tả hành vi trùng. Người
    vừa vượt đèn đỏ vừa bỏ chạy khỏi CSGT thì "bỏ chạy" vẫn là tình tiết tăng nặng thật
    và phải được giữ.
    """
    kept: List[Dict[str, object]] = []
    warnings: List[str] = []
    for item in inferred:
        nguon = str(item.get("nguon") or "").lower()
        trung = next(
            (
                t
                for t in TRUNG_LAP.get(str(item.get("fact")), ())
                if facts.get(t.fact) is True and any(c in nguon for c in t.cues)
            ),
            None,
        )
        if trung is None:
            kept.append(item)
            continue
        warnings.append(
            f"Bỏ tình tiết '{item.get('fact')}' vì được viện dẫn từ chính hành vi "
            f"'{trung.fact}' đã bị xử phạt riêng "
            f"(Điều 10 khoản 2 Luật Xử lý vi phạm hành chính 2012)."
        )
    return kept, warnings


class CircumstanceInferrer(Protocol):
    def infer(
        self, raw_events: List[str], text: str = ""
    ) -> List[Dict[str, object]]:
        """`raw_events` là sự kiện thô đã tách; `text` là cả câu đã chuẩn hóa.

        Bộ suy luận từ khóa chỉ cần `raw_events`, nhưng bộ dùng LLM cần `text` vì cách
        diễn đạt vòng ("hạ gục cái gương của người ta") không chứa từ khóa nào nên đã
        bị bộ tách sự kiện loại từ trước.
        """
        ...


def infer_circumstances(raw_events: List[str]) -> List[Dict[str, object]]:
    """Suy diễn bằng từ khóa (offline). Bỏ qua từ khóa chỉ xuất hiện ở thể phủ định."""
    joined = " ".join(raw_events).lower()
    out: List[Dict[str, object]] = []
    for tt in CLOSED_VOCAB:
        hit = next(
            (
                kw
                for kw in tt.keywords
                if kw in joined and not has_negated_occurrence_only(joined, kw)
            ),
            None,
        )
        if hit:
            out.append(
                {
                    "fact": tt.fact,
                    "value": True,
                    "confidence": 0.9,
                    "ly_do": tt.mo_ta,
                    "nguon": hit,
                    "bo_suy_luan": "keyword",
                }
            )
    return out


class KeywordInferrer:
    """Bọc `infer_circumstances` cho khớp giao diện `CircumstanceInferrer`."""

    def infer(self, raw_events: List[str], text: str = "") -> List[Dict[str, object]]:
        return infer_circumstances(raw_events)
