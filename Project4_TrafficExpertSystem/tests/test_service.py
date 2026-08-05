from pathlib import Path

from traffic_es.service import TrafficESService

RULES_DIR = Path("traffic_es/knowledge/rules")


def test_service_answers_full():
    svc = TrafficESService.default(RULES_DIR)
    ans = svc.answer("Tôi lái ô tô, nồng độ cồn 0.42 mg/l, rồi đâm vào một xe máy")
    assert ans.ket_qua.tong_tien == 40000000  # tai nạn -> max khung 30-40
    assert "Điều 6" in ans.explanation
    assert ans.facts["tinhtiet.gay_tai_nan"] is True


def test_service_no_violation():
    svc = TrafficESService.default(RULES_DIR)
    ans = svc.answer("Tôi lái ô tô bình thường, không uống rượu")
    assert ans.ket_qua.tong_tien == 0
