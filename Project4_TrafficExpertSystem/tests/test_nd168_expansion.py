"""Smoke tests cho đợt mở rộng KB NĐ 168 (PLAN_BO_SUNG_ND168)."""

from pathlib import Path

from traffic_es.engine.funcs import DEFAULT_FUNCS
from traffic_es.engine.reasoner import Reasoner
from traffic_es.knowledge.kb_loader import load_rules
from traffic_es.knowledge.ontology import ConceptStore
from traffic_es.nlu.extractor import HeuristicExtractor
from traffic_es.nlu.pipeline import NLUPipeline
from traffic_es.service import TrafficESService

RULES_DIR = Path("traffic_es/knowledge/rules")
CONCEPTS = Path("traffic_es/knowledge/concepts.yaml")


def test_gioi_han_khu_dan_cu_func_exists():
    names = {f.name for f in DEFAULT_FUNCS}
    assert "gioi_han_theo_khu_vuc" in names


def test_c19_khu_dan_cu_fires_toc_do():
    svc = TrafficESService(Reasoner.from_rules_dir(RULES_DIR), NLUPipeline())
    ans = svc.answer("Ô tô chạy 75 km/h trong khu dân cư")
    fired = [s.data.get("rule_id") for s in ans.trace.steps if s.kind == "RULE"]
    assert "R_TOCDO_OTO_M3" in fired
    assert ans.ket_qua.tong_tien == 7_000_000


def test_new_rule_files_loaded():
    ids = {r.id for r in load_rules(RULES_DIR)}
    for rid in (
        "R_MATUY_OTO",
        "R_CSGT_OTO",
        "R_DENVANG_OTO",
        "R_SAI_LAN_OTO",
        "R_NGUOC_CHIEU_OTO",
        "R_DUNG_DO_SAI_XEMAY",
        "R_BIEN_SO_GIA_OTO",
        "R_CHO_QUA_TAI",
        "R_HANH_KHACH_GAY_ROI",
        "R_NGB_SAI_PHAN_DUONG",
        "R_GIAO_XE_KHONG_DU_DK",
        "R_GPLX_CHUA_DU_TUOI_OTO",
        "R_SAI_LAN_XEDAP",
    ):
        assert rid in ids, rid


def test_concepts_cover_new_groups():
    store = ConceptStore.from_yaml(CONCEPTS)
    names = {c.name for c in store.concepts}
    assert "ma túy" in names
    assert "xe đạp" in names
    assert "không chấp hành hiệu lệnh CSGT" in names
    assert "biển số giả hoặc che biển" in names


def test_heuristic_extracts_expansion_facts():
    ext = HeuristicExtractor()
    facts, _, _ = ext.extract("Ô tô không chấp hành hiệu lệnh của CSGT")
    assert facts.get("hanhvi.khong_chap_hanh_csgt") is True
    facts2, _, _ = ext.extract("Xe máy dương tính ma túy")
    assert facts2.get("nguoi.co_chat_ma_tuy") is True


def test_engine_fires_csgt_and_matuy():
    r = Reasoner.from_rules_dir(RULES_DIR)
    res = r.infer({"phuongtien.loai": "o_to", "hanhvi.khong_chap_hanh_csgt": True})
    fired = [s.data.get("rule_id") for s in res.trace.steps if s.kind == "RULE"]
    assert fired == ["R_CSGT_OTO"]
    res2 = r.infer({"phuongtien.loai": "xe_may", "nguoi.co_chat_ma_tuy": True})
    fired2 = [s.data.get("rule_id") for s in res2.trace.steps if s.kind == "RULE"]
    assert fired2 == ["R_MATUY_XEMAY"]


def test_sai_lan_dung_do_amounts_match_nd168_docx():
    """Đối chiếu mức phạt với 168_2024_ND-CP (Điều 6/7/9)."""
    svc = TrafficESService(Reasoner.from_rules_dir(RULES_DIR), NLUPipeline())
    cases = [
        ("Ô tô đi không đúng làn đường quy định", "R_SAI_LAN_OTO", 5_000_000),
        ("Xe máy lấn làn", "R_SAI_LAN_XEMAY", 700_000),
        ("Ô tô đậu nơi cấm đỗ", "R_DUNG_DO_SAI_OTO", 900_000),
        ("Xe máy đỗ nơi cấm", "R_DUNG_DO_SAI_XEMAY", 500_000),
        ("Xe máy chạy 65 km/h trong khu dân cư", "R_TOCDO_XEMAY_M2", 900_000),
        ("Xe đạp đi sai phần đường", "R_SAI_LAN_XEDAP", 150_000),
    ]
    for text, rid, money in cases:
        ans = svc.answer(text)
        fired = [s.data.get("rule_id") for s in ans.trace.steps if s.kind == "RULE"]
        assert rid in fired, (text, fired)
        assert ans.ket_qua.tong_tien == money, (text, ans.ket_qua.tong_tien)


def test_clarify_offers_sai_lan_and_dung_do():
    from traffic_es.nlu.clarify import BEHAVIOR_SPECS

    assert "sai_lan" in BEHAVIOR_SPECS
    assert "dung_do_sai" in BEHAVIOR_SPECS


def test_cam_dien_thoai_and_tai_nghe():
    svc = TrafficESService(Reasoner.from_rules_dir(RULES_DIR), NLUPipeline())
    ans = svc.answer("Tôi chạy xe máy cầm điện thoại")
    fired = [s.data.get("rule_id") for s in ans.trace.steps if s.kind == "RULE"]
    assert "R_CAM_DIEN_THOAI_XEMAY" in fired
    assert ans.ket_qua.tong_tien == 900_000
    assert ans.ket_qua.tru_diem_max == 4
    assert "trừ 4 điểm" in ans.ket_qua.chi_tiet[0].phat_bo_sung

    ans2 = svc.answer("Tôi chạy xe máy đeo tai nghe")
    fired2 = [s.data.get("rule_id") for s in ans2.trace.steps if s.kind == "RULE"]
    assert "R_CAM_DIEN_THOAI_XEMAY" in fired2
    assert ans2.ket_qua.tong_tien == 900_000

    ans3 = svc.answer("Ô tô dùng tay cầm điện thoại khi lái")
    fired3 = [s.data.get("rule_id") for s in ans3.trace.steps if s.kind == "RULE"]
    assert "R_CAM_DIEN_THOAI_OTO" in fired3
    assert ans3.ket_qua.tong_tien == 5_000_000
