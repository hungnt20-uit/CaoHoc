from traffic_es.nlu.pipeline import NLUPipeline


def test_pipeline_end_to_end_facts():
    facts, meta = NLUPipeline().run("Lái ô tô, nồng độ cồn 0.42, rồi đâm vào xe máy")
    assert facts["phuongtien.loai"] == "o_to"
    assert facts["chiso.nongDoCon_khiTho"] == 0.42
    assert facts["tinhtiet.gay_tai_nan"] is True
    assert "evidences" in meta and "inferred" in meta
