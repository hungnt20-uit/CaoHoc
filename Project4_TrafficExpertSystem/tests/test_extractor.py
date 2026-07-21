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
