from pathlib import Path

from traffic_es.engine.reasoner import Reasoner
from traffic_es.explain.generator import render_explanation
from traffic_es.nlu.clarify import (
    needed_clarifications,
    apply_clarification,
    VEHICLE_FIELD,
    BEHAVIOR_FIELD,
    PENDING_FIELD,
)
from traffic_es.nlu.pipeline import NLUPipeline
from traffic_es.nlu.extractor import HeuristicExtractor
from traffic_es.service import TrafficESService

RULES_DIR = Path("traffic_es/knowledge/rules")


def test_needed_clarifications_when_vehicle_missing():
    rules = Reasoner.from_rules_dir(RULES_DIR).rules
    qs = needed_clarifications({"hanhvi.vuot_den_do": True}, rules)
    assert len(qs) == 1
    assert qs[0].field == VEHICLE_FIELD


def test_no_clarification_when_complete():
    rules = Reasoner.from_rules_dir(RULES_DIR).rules
    qs = needed_clarifications(
        {"hanhvi.vuot_den_do": True, "phuongtien.loai": "xe_may"}, rules
    )
    assert qs == []


def test_ask_behavior_when_no_matching_violation():
    rules = Reasoner.from_rules_dir(RULES_DIR).rules
    for facts in ({}, {"phuongtien.loai": "o_to"}):
        qs = needed_clarifications(facts, rules)
        assert len(qs) == 1
        assert qs[0].field == BEHAVIOR_FIELD


def test_service_asks_then_continues_with_vehicle():
    nlu = NLUPipeline(HeuristicExtractor())
    svc = TrafficESService(Reasoner.from_rules_dir(RULES_DIR), nlu)

    ans = svc.answer("Tôi chạy vượt đèn đỏ bị phạt bao nhiêu tiền")
    assert ans.clarifications
    assert ans.clarifications[0].field == VEHICLE_FIELD
    assert ans.ket_qua.tong_tien == 0
    assert "loại phương tiện" in ans.explanation.lower()

    for loai, expected_min, expected_max in (
        ("xe_may", 4_000_000, 6_000_000),
        ("o_to", 18_000_000, 20_000_000),
    ):
        cont = svc.continue_with({**ans.facts, VEHICLE_FIELD: loai}, ans.nlu_meta)
        assert cont.clarifications == []
        assert expected_min <= cont.ket_qua.tong_tien <= expected_max


def test_service_asks_behavior_then_vehicle_for_vague_query():
    nlu = NLUPipeline(HeuristicExtractor())
    svc = TrafficESService(Reasoner.from_rules_dir(RULES_DIR), nlu)

    ans = svc.answer("Tôi chạy xe sai luật thì bị phạt bao nhiêu tiền?")
    assert ans.clarifications
    assert ans.clarifications[0].field == BEHAVIOR_FIELD
    assert "hành vi" in ans.explanation.lower()

    q = ans.clarifications[0]
    after_beh = svc.continue_with(
        apply_clarification(ans.facts, q, "vuot_den_do"), ans.nlu_meta
    )
    assert after_beh.facts.get("hanhvi.vuot_den_do") is True
    assert after_beh.clarifications
    assert after_beh.clarifications[0].field == VEHICLE_FIELD

    final = svc.continue_with(
        apply_clarification(after_beh.facts, after_beh.clarifications[0], "xe_may"),
        after_beh.nlu_meta,
    )
    assert final.clarifications == []
    assert 4_000_000 <= final.ket_qua.tong_tien <= 6_000_000


def test_alcohol_hint_skips_behavior_question():
    nlu = NLUPipeline(HeuristicExtractor())
    svc = TrafficESService(Reasoner.from_rules_dir(RULES_DIR), nlu)
    ans = svc.answer("tôi uống rượu thì bị phạt nhiêu tiền")
    assert ans.clarifications
    assert ans.clarifications[0].id == "ask_nong_do_con_muc"
    assert ans.clarifications[0].field != BEHAVIOR_FIELD
    assert "khung" in ans.explanation.lower() or "mức" in ans.explanation.lower()


def test_speed_hint_skips_behavior_question():
    nlu = NLUPipeline(HeuristicExtractor())
    svc = TrafficESService(Reasoner.from_rules_dir(RULES_DIR), nlu)
    ans = svc.answer("tôi chạy quá tốc độ bị phạt bao nhiêu")
    assert ans.clarifications
    assert ans.clarifications[0].id == "ask_vuot_toc_do_muc"


def test_alcohol_band_then_vehicle():
    nlu = NLUPipeline(HeuristicExtractor())
    svc = TrafficESService(Reasoner.from_rules_dir(RULES_DIR), nlu)
    rules = svc.reasoner.rules

    q0 = needed_clarifications({}, rules)[0]
    pending = apply_clarification({}, q0, "nong_do_con")
    assert pending[PENDING_FIELD] == "nong_do_con"

    q1 = needed_clarifications(pending, rules)[0]
    assert q1.id == "ask_nong_do_con_muc"
    with_band = apply_clarification(pending, q1, "con_muc2")
    assert PENDING_FIELD not in with_band
    assert with_band["chiso.nongDoCon_khiTho"] == 0.3

    mid = svc.continue_with(with_band, {})
    assert mid.clarifications[0].field == VEHICLE_FIELD
    final = svc.continue_with(
        apply_clarification(mid.facts, mid.clarifications[0], "o_to"), mid.nlu_meta
    )
    assert final.clarifications == []
    assert 18_000_000 <= final.ket_qua.tong_tien <= 20_000_000


def test_speed_band_choices_no_number_input():
    rules = Reasoner.from_rules_dir(RULES_DIR).rules
    q0 = needed_clarifications({}, rules)[0]
    pending = apply_clarification({}, q0, "vuot_toc_do")
    q1 = needed_clarifications(pending, rules)[0]
    assert q1.id == "ask_vuot_toc_do_muc"
    assert "toc_5_10" in q1.choices
    assert "toc_over_35" in q1.choices
    facts = apply_clarification(pending, q1, "toc_5_10")
    assert facts["chiso.vuot_toc_do_kmh"] == 7.0
    assert PENDING_FIELD not in facts


def test_apply_behavior_helmet_sets_vehicle():
    rules = Reasoner.from_rules_dir(RULES_DIR).rules
    q = needed_clarifications({}, rules)[0]
    facts = apply_clarification({}, q, "khong_mu")
    assert facts["nguoi.khong_mu_bao_hiem"] is True
    assert facts[VEHICLE_FIELD] == "xe_may"
    assert needed_clarifications(facts, rules) == []


def test_render_explanation_missing_vehicle_message():
    r = Reasoner.from_rules_dir(RULES_DIR)
    res = r.infer({"hanhvi.vuot_den_do": True})
    text = render_explanation(res.trace, res.ket_qua, missing_vehicle=True)
    assert "loại phương tiện" in text.lower()
    assert "Không phát hiện hành vi" not in text


def test_render_explanation_missing_behavior_message():
    r = Reasoner.from_rules_dir(RULES_DIR)
    res = r.infer({})
    text = render_explanation(res.trace, res.ket_qua, missing_behavior=True)
    assert "hành vi" in text.lower()
