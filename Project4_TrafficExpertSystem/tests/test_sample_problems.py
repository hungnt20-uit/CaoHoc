from traffic_es.knowledge.sample_problems import best_problem, match_problems


def test_speed_problem_matches():
    facts = {
        "phuongtien.loai": "o_to",
        "chiso.tocDo": 80.0,
        "chiso.tocDoGioiHan": 50.0,
    }
    p = best_problem(facts)
    assert p is not None and p.name == "Vi phạm tốc độ"
    assert any("vuot_toc_do_kmh" in s for s in p.sol)


def test_con_problem_matches_either_measure():
    p = best_problem({"phuongtien.loai": "o_to", "chiso.nongDoCon_mau": 60.0})
    assert p is not None and p.name == "Nồng độ cồn"


def test_no_match_without_relevant_facts():
    assert best_problem({"chiso.tocDo": 80.0}) is None
    # Chỉ có loại xe — không còn khớp mẫu “An toàn” chung chung
    assert best_problem({"phuongtien.loai": "o_to"}) is None


def test_specificity_prefers_speed_over_generic():
    facts = {
        "phuongtien.loai": "o_to",
        "chiso.tocDo": 80.0,
        "chiso.tocDoGioiHan": 50.0,
    }
    names = [p.name for p in match_problems(facts)]
    assert names[0] == "Vi phạm tốc độ"


def test_multi_violation_matches_several_samples():
    facts = {
        "phuongtien.loai": "xe_may",
        "hanhvi.sai_lan": True,
        "hanhvi.vuot_den_do": True,
        "hanhvi.thay_doi_may_khung": True,
    }
    names = {p.name for p in match_problems(facts)}
    assert "An toàn & tín hiệu" in names
    assert "Làn đường & dừng đỗ" in names
    assert "Chủ xe / cải tạo & biển số" in names
