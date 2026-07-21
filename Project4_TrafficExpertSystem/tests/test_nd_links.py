from pathlib import Path

from traffic_es.knowledge.nghi_dinh_links import NghiDinhLinks

LINKS = Path("traffic_es/knowledge/nghi_dinh_links.yaml")


def test_168_supersedes_100_duongbo():
    links = NghiDinhLinks.load(LINKS)
    assert links.hieu_luc_hien_hanh("duong_bo") == "168/2024/NĐ-CP"
    assert "100/2019/NĐ-CP" in links.bi_thay_the_boi("168/2024/NĐ-CP")


def test_100_con_hieu_luc_duongsat():
    links = NghiDinhLinks.load(LINKS)
    assert links.hieu_luc_hien_hanh("duong_sat") == "100/2019/NĐ-CP"
