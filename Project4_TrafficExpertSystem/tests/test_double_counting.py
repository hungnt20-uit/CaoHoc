"""Điều 10 khoản 2 Luật XLVPHC 2012: hành vi đã bị phạt riêng không là tình tiết tăng nặng.

Qwen2.5-Coder-7B suy ra `tinhtiet.khong_chap_hanh` từ chính hành vi "vượt đèn đỏ", làm
tiền phạt nhảy từ 5,5 lên 6,6 triệu vì meta-rule áp mức tối đa của khung. Chặn ở tầng
suy diễn nên luật đúng bất kể model nào đề xuất.
"""

from traffic_es.nlu.semantic_infer import drop_double_counted


def _tinh_tiet(nguon, fact="tinhtiet.khong_chap_hanh"):
    return {"fact": fact, "value": True, "confidence": 0.9, "nguon": nguon}


def test_drops_circumstance_cited_from_the_punished_behaviour():
    kept, warns = drop_double_counted(
        [_tinh_tiet("vượt đèn đỏ")], {"hanhvi.vuot_den_do": True}
    )
    assert kept == []
    assert "Điều 10 khoản 2" in warns[0]


def test_keeps_independent_circumstance_alongside_same_violation():
    """Vừa vượt đèn đỏ vừa bỏ chạy khỏi CSGT thì tình tiết là thật, phải giữ."""
    kept, warns = drop_double_counted(
        [_tinh_tiet("bỏ chạy")], {"hanhvi.vuot_den_do": True}
    )
    assert [k["nguon"] for k in kept] == ["bỏ chạy"]
    assert warns == []


def test_keeps_circumstance_when_behaviour_was_not_punished():
    kept, _warns = drop_double_counted([_tinh_tiet("vượt đèn đỏ")], {})
    assert len(kept) == 1


def test_other_circumstances_are_untouched():
    kept, _warns = drop_double_counted(
        [_tinh_tiet("va chạm", fact="tinhtiet.gay_tai_nan")],
        {"hanhvi.vuot_den_do": True},
    )
    assert len(kept) == 1


def test_pipeline_does_not_inflate_penalty_for_red_light_case():
    from pathlib import Path

    from traffic_es.engine.reasoner import Reasoner
    from traffic_es.nlu.pipeline import NLUPipeline
    from traffic_es.service import TrafficESService

    class _FakeInferrer:
        """Bắt chước đúng đề xuất sai mà Qwen đưa ra khi quan sát thực tế."""

        def infer(self, raw_events, text=""):
            return [
                {
                    "fact": "tinhtiet.khong_chap_hanh",
                    "value": True,
                    "confidence": 1.0,
                    "ly_do": "vượt đèn đỏ là hành vi vi phạm nghiêm trọng",
                    "nguon": "vượt đèn đỏ",
                    "bo_suy_luan": "llm",
                }
            ]

    rules = Path(__file__).resolve().parents[1] / "traffic_es" / "knowledge" / "rules"
    svc = TrafficESService(
        Reasoner.from_rules_dir(rules), NLUPipeline(inferrer=_FakeInferrer())
    )
    ans = svc.answer("Tôi đi xe máy không đội mũ bảo hiểm và vượt đèn đỏ ở ngã tư.")

    assert ans.facts.get("tinhtiet.khong_chap_hanh") is None
    assert not any(s.kind == "META" for s in ans.trace.steps)
    assert ans.ket_qua.tong_tien == 5_500_000
