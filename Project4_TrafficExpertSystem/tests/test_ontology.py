from pathlib import Path

from traffic_es.knowledge.ontology import Concept, ConceptStore


def test_concept_fields():
    c = Concept(
        name="xe mô tô",
        content="Phương tiện cơ giới hai bánh",
        inner_rul="Điều 3.39 QCVN 41:2016/BGTVT",
        attrs={"loai": "xe_may"},
        keyphrases=["xe máy", "mô tô", "xe gắn máy"],
    )
    assert c.name == "xe mô tô"
    assert "mô tô" in c.keyphrases


def test_store_lookup_by_keyphrase():
    store = ConceptStore.from_yaml(Path("traffic_es/knowledge/concepts.yaml"))
    c = store.find_by_keyphrase("xe gắn máy")
    assert c is not None
    assert c.attrs.get("fact") == "phuongtien.loai"
    assert c.attrs.get("value") == "xe_may"
