from pathlib import Path

from traffic_es.knowledge.ontology import ConceptStore
from traffic_es.knowledge.knowledge_graph import KnowledgeGraph
from traffic_es.nlu.question_graph import subgraph_match, to_nodes, map_to_facts

CONCEPTS = Path("traffic_es/knowledge/concepts.yaml")


def _kg():
    return KnowledgeGraph.from_store(ConceptStore.from_yaml(CONCEPTS))


def test_subgraph_match_records_matched_keyphrases():
    kg = _kg()
    ms = subgraph_match("xe máy không đội mũ bảo hiểm", kg)
    top = {m.concept.name for m in ms}
    assert "không đội mũ bảo hiểm" in top and "xe mô tô" in top
    m0 = next(m for m in ms if m.concept.name == "không đội mũ bảo hiểm")
    assert m0.matched_keyphrases  # có cánh khớp


def test_map_to_facts_helmet():
    kg = _kg()
    facts = map_to_facts(subgraph_match("xe máy không đội mũ bảo hiểm", kg))
    assert facts["phuongtien.loai"] == "xe_may"
    assert facts["nguoi.khong_mu_bao_hiem"] is True


def test_map_to_facts_no_gplx_is_false():
    kg = _kg()
    facts = map_to_facts(subgraph_match("ô tô không có giấy phép lái xe", kg))
    assert facts["phuongtien.loai"] == "o_to"
    assert facts["nguoi.coGPLX"] is False


def test_map_to_facts_accident_circumstance():
    kg = _kg()
    facts = map_to_facts(subgraph_match("xe máy đâm vào người đi bộ gây tai nạn", kg))
    assert facts["tinhtiet.gay_tai_nan"] is True


def test_to_nodes_empty_for_irrelevant():
    kg = _kg()
    assert to_nodes("hôm nay trời đẹp", kg) == set()
