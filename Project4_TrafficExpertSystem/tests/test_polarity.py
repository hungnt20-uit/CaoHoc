from pathlib import Path

from traffic_es.knowledge.ontology import ConceptStore
from traffic_es.knowledge.knowledge_graph import KnowledgeGraph
from traffic_es.nlu.polarity import clause_before, is_negated
from traffic_es.nlu.question_graph import map_to_facts, subgraph_match
from traffic_es.nlu.semantic_infer import infer_circumstances
from traffic_es.service import TrafficESService

CONCEPTS = Path("traffic_es/knowledge/concepts.yaml")
RULES_DIR = Path("traffic_es/knowledge/rules")


def _kg():
    return KnowledgeGraph.from_store(ConceptStore.from_yaml(CONCEPTS))


def test_clause_before_stops_at_conjunction():
    text = "không thắt dây an toàn và vượt đèn đỏ"
    assert "không" not in clause_before(text, text.index("vượt"))


def test_negation_cue_detected():
    text = "tôi không vượt đèn đỏ"
    assert is_negated(text, text.index("vượt"))


def test_compliance_cue_detected():
    text = "tôi dừng đèn đỏ đúng luật"
    assert is_negated(text, text.index("đèn đỏ"))


def test_phrase_carrying_its_own_negation_is_not_flagged():
    text = "tôi không đội mũ bảo hiểm"
    assert not is_negated(text, text.index("không đội mũ"))


def test_subgraph_match_skips_negated_phrase():
    ms = subgraph_match("tôi dừng đèn đỏ đúng luật", _kg())
    assert "vượt đèn đỏ" not in {m.concept.name for m in ms}


def test_map_to_facts_still_detects_real_violation():
    facts = map_to_facts(subgraph_match("ô tô vượt đèn đỏ", _kg()))
    assert facts["hanhvi.vuot_den_do"] is True


def test_keyword_inferrer_skips_negated_event():
    assert infer_circumstances(["không gây tai nạn nào cả"]) == []
    assert infer_circumstances(["quẹt trúng một xe máy"])


def test_end_to_end_negated_sentence_has_no_penalty():
    svc = TrafficESService.default(RULES_DIR)
    ans = svc.answer("Tôi lái ô tô, tôi dừng đèn đỏ đúng luật và không gây tai nạn nào cả.")
    assert ans.ket_qua.tong_tien == 0
    assert ans.facts.get("hanhvi.vuot_den_do") is None
    assert ans.facts.get("tinhtiet.gay_tai_nan") is None


def test_end_to_end_real_violation_still_penalised():
    svc = TrafficESService.default(RULES_DIR)
    ans = svc.answer("Tôi lái ô tô vượt đèn đỏ và quẹt trúng một xe máy")
    assert ans.facts["hanhvi.vuot_den_do"] is True
    assert ans.facts["tinhtiet.gay_tai_nan"] is True
    assert ans.ket_qua.tong_tien > 0
