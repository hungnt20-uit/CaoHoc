from traffic_es.nlu.extractor import HeuristicExtractor


def test_extract_oto_con():
    ex = HeuristicExtractor()
    facts, ev, raw = ex.extract("tôi lái ô tô, thổi nồng độ cồn 0.42 mg/l")
    assert facts["phuongtien.loai"] == "o_to"
    assert facts["chiso.nongDoCon_khiTho"] == 0.42


def test_extract_xemay_and_event():
    ex = HeuristicExtractor()
    facts, ev, raw = ex.extract("chạy xe máy sau khi uống rượu rồi đâm vào người đi bộ")
    assert facts["phuongtien.loai"] == "xe_may"
    assert any("đâm" in r for r in raw)


def test_extract_con_mau_vs_khitho():
    ex = HeuristicExtractor()
    f1, _, _ = ex.extract("nồng độ cồn trong máu 60 mg/100ml")
    assert f1["chiso.nongDoCon_mau"] == 60
    f2, _, _ = ex.extract("thổi nồng độ cồn 0.42 mg/l")
    assert f2["chiso.nongDoCon_khiTho"] == 0.42


def test_extract_boolean_facts():
    ex = HeuristicExtractor()
    f, _, _ = ex.extract("chạy xe máy không đội mũ bảo hiểm, vượt đèn đỏ, không có giấy phép lái xe")
    assert f["nguoi.khong_mu_bao_hiem"] is True
    assert f["hanhvi.vuot_den_do"] is True
    assert f["nguoi.coGPLX"] is False


def test_extract_comma_decimal_breathalyzer_phrase():
    ex = HeuristicExtractor()
    facts, _, _ = ex.extract(
        "Tối qua nhậu xong tôi vẫn cầm lái con xe hơi về nhà, bị thổi ra 0,45 mg/l khí thở, "
        "lại còn quẹt trúng một xe máy."
    )
    assert facts["phuongtien.loai"] == "o_to"
    assert facts["chiso.nongDoCon_khiTho"] == 0.45
