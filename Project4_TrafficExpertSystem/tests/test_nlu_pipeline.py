from traffic_es.nlu.pipeline import NLUPipeline


def test_pipeline_end_to_end_facts():
    facts, meta = NLUPipeline().run("Lái ô tô, nồng độ cồn 0.42, rồi đâm vào xe máy")
    assert facts["phuongtien.loai"] == "o_to"
    assert facts["chiso.nongDoCon_khiTho"] == 0.42
    assert facts["tinhtiet.gay_tai_nan"] is True
    assert "evidences" in meta and "inferred" in meta


def test_pipeline_kg_augments_missing_fact():
    # Câu chỉ nêu hành vi "không đội mũ" — bộ trích heuristic bắt được;
    # KG khớp concept và ghi vào matched_concepts (glass-box Bài toán 2).
    facts, meta = NLUPipeline().run("Đi xe máy không đội mũ bảo hiểm")
    assert facts["phuongtien.loai"] == "xe_may"
    names = {m["concept"] for m in meta["matched_concepts"]}
    assert "không đội mũ bảo hiểm" in names
    assert "xe mô tô" in names


def test_pipeline_kg_does_not_override_extractor():
    # Extractor đã xác định o_to; KG không được ghi đè bằng giá trị khác.
    facts, meta = NLUPipeline().run("Ô tô chạy 80 km/h ở khu dân cư")
    assert facts["phuongtien.loai"] == "o_to"
    assert "phuongtien.loai" not in meta["kg_facts_added"]


def test_pipeline_disable_kg():
    facts, meta = NLUPipeline(use_knowledge_graph=False).run("Đi xe máy không đội mũ")
    assert meta["matched_concepts"] == []
