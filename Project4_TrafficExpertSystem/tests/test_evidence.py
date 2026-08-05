"""Fact do LLM đề xuất phải truy được về cụm chữ có thật trong câu."""

import json

import pytest

from traffic_es.llm.client import FakeLLM
from traffic_es.nlu.evidence import cites_source, number_appears
from traffic_es.nlu.llm_extractor import LLMExtractor


@pytest.mark.parametrize(
    "text, value, expected",
    [
        ("thổi ra 0.45 mg/l khí thở", 0.45, True),
        ("thổi ra 0,45 mg/l khí thở", 0.45, True),  # dấu phẩy thập phân
        ("thổi ra 0.45 mg/l khí thở", 0.8, False),  # ảo giác quan sát thật ở Qwen 7B
        ("kim đồng hồ chỉ 70 trong khi biển ghi 50", 70, True),
        ("kim đồng hồ chỉ 70 trong khi biển ghi 50", 50, True),
        ("vượt đèn đỏ rồi bỏ chạy", 50, False),
        ("chạy 150 km/h", 50, False),  # không khớp lẫn vào giữa con số khác
        ("chạy 0.50 mg/l", 50, False),
        ("biển ghi 50.5 km/h", 50, False),
        ("biển ghi 50.", 50, True),  # dấu chấm cuối câu vẫn tính
    ],
)
def test_number_must_appear_verbatim(text, value, expected):
    assert number_appears(text, value) is expected


@pytest.mark.parametrize(
    "nguon, expected",
    [
        ("không đội mũ bảo hiểm", True),
        ("KHÔNG ĐỘI  mũ bảo hiểm", True),  # khác hoa thường và khoảng trắng
        ("cụm chữ 'không đội mũ bảo hiểm'", False),  # LLM diễn giải thay vì trích
        ("việt đèn đỏ", False),  # LLM viết sai chính tả -> không phải trích dẫn thật
        ("", False),
        # Dẫn cả câu thì luôn khớp mà không chỉ ra bằng chứng nào — vô hiệu phép kiểm.
        ("tôi đi xe máy không đội mũ bảo hiểm và vượt đèn đỏ ở ngã tư.", False),
        ("tôi đi xe máy không đội mũ bảo hiểm và vượt đèn đỏ", False),
    ],
)
def test_citation_must_be_verbatim(nguon, expected):
    text = "tôi đi xe máy không đội mũ bảo hiểm và vượt đèn đỏ ở ngã tư."
    assert cites_source(text, nguon) is expected


def test_short_input_may_be_quoted_whole():
    """Câu quá ngắn thì tỉ lệ mất ý nghĩa, không nên chặn."""
    assert cites_source("cồn 0.45", "cồn 0.45") is True


@pytest.mark.parametrize(
    "raw, expected",
    [("0.45 mg/l", 0.45), ("50 km/h", 50), ("0,45mg/l", 0.45), ("o_to", "o_to")],
)
def test_numeric_value_with_unit_is_parsed(raw, expected):
    from traffic_es.nlu.llm_extractor import _coerce_value

    assert _coerce_value(raw) == expected


def _extract(payload, text):
    # Khóa rỗng khớp mọi câu — câu tiếng Việt có dấu không chắc chứa ký tự ASCII nào.
    llm = FakeLLM(responses={"": json.dumps(payload, ensure_ascii=False)})
    ext = LLMExtractor(llm)
    return ext, ext.extract(text)


def test_fabricated_number_is_dropped_even_with_citation():
    """Chốt số phải chặn được cả khi LLM bịa luôn phần trích dẫn."""
    ext, (facts, _ev, _raw) = _extract(
        {
            "facts": {
                "chiso.nongDoCon_khiTho": {"value": 0.45, "nguon": "0.45 mg/l"},
                "chiso.tocDoGioiHan": {"value": 0.8, "nguon": "0.45 mg/l"},
            }
        },
        "thổi ra 0.45 mg/l khí thở",
    )
    assert facts == {"chiso.nongDoCon_khiTho": 0.45}
    assert "chiso.tocDoGioiHan" in ext.last_dropped


def test_fact_without_citation_is_dropped():
    ext, (facts, _ev, _raw) = _extract(
        {"facts": {"boicanh.khuVuc": {"value": "khu_dan_cu"}}},
        "tôi vượt đèn đỏ rồi bỏ chạy khi csgt ra hiệu dừng xe.",
    )
    assert facts == {}
    assert "không trích dẫn" in ext.last_dropped["boicanh.khuVuc"]


def test_fact_with_invented_citation_is_dropped():
    ext, (facts, _ev, _raw) = _extract(
        {"facts": {"boicanh.khuVuc": {"value": "khu_dan_cu", "nguon": "trong khu dân cư"}}},
        "tôi vượt đèn đỏ rồi bỏ chạy khi csgt ra hiệu dừng xe.",
    )
    assert facts == {}
    assert "không dẫn đúng câu gốc" in ext.last_dropped["boicanh.khuVuc"]


def test_well_cited_facts_survive():
    _ext, (facts, ev, _raw) = _extract(
        {
            "facts": {
                "phuongtien.loai": {"value": "xe_may", "nguon": "xe máy"},
                "chiso.tocDo": {"value": 70, "nguon": "kim đồng hồ chỉ 70"},
                "chiso.tocDoGioiHan": {"value": 50, "nguon": "biển ghi 50"},
                "boicanh.khuVuc": {"value": "khu_dan_cu", "nguon": "khu dân cư"},
            }
        },
        "chạy xe máy trong khu dân cư mà kim đồng hồ chỉ 70 trong khi biển ghi 50.",
    )
    assert facts == {
        "phuongtien.loai": "xe_may",
        "chiso.tocDo": 70,
        "chiso.tocDoGioiHan": 50,
        "boicanh.khuVuc": "khu_dan_cu",
    }
    assert ev["chiso.tocDo"] == "kim đồng hồ chỉ 70"
