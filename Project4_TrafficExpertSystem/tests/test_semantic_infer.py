from traffic_es.nlu.semantic_infer import infer_circumstances


def test_infer_tai_nan():
    inf = infer_circumstances(["đâm vào người đi bộ"])
    assert any(i["fact"] == "tinhtiet.gay_tai_nan" and i["value"] is True for i in inf)


def test_infer_tai_pham():
    inf = infer_circumstances(["đây là lần tái phạm"])
    assert any(i["fact"] == "tinhtiet.tai_pham" for i in inf)


def test_no_event_no_infer():
    assert infer_circumstances(["trời mưa nhẹ"]) == []
