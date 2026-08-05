from pathlib import Path

from traffic_es.knowledge.ontology import ConceptStore
from traffic_es.knowledge.knowledge_graph import KnowledgeGraph

CONCEPTS = Path("traffic_es/knowledge/concepts.yaml")


def _kg():
    return KnowledgeGraph.from_store(ConceptStore.from_yaml(CONCEPTS))


def test_speed_and_vehicle_matched():
    kg = _kg()
    hits = {c.name for c, _ in kg.match("ô tô chạy 80 km/h vượt tốc độ cho phép")}
    assert "tốc độ" in hits
    assert "xe ô tô" in hits


def test_helmet_matched_over_generic():
    kg = _kg()
    ranked = kg.match("xe máy không đội mũ bảo hiểm")
    names = [c.name for c, _ in ranked]
    assert "không đội mũ bảo hiểm" in names
    assert "xe mô tô" in names


def test_rare_token_has_higher_idf_than_common():
    kg = _kg()
    # "xe" xuất hiện ở nhiều concept -> idf thấp hơn token hiếm "cồn"
    assert kg.idf["cồn"] > kg.idf["xe"]


def test_no_match_returns_empty():
    kg = _kg()
    assert kg.match("hôm nay trời đẹp") == []
