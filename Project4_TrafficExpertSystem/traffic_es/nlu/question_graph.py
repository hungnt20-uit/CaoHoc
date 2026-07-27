"""Đồ thị câu hỏi → phân rã hình sao → so khớp đồ thị con (subgraph matching).

Theo pipeline hỏi–đáp trên Legal-Onto: câu hỏi được biểu diễn thành các "nút"
(cụm keyphrase kích hoạt). Mỗi Concept trong Knowledge Graph là một *ngôi sao*
(tâm = concept, cánh = keyphrase). So khớp đồ thị con = tìm các ngôi sao mà câu hỏi
phủ được, chấm điểm bằng trọng số TF-IDF của các cánh khớp. Kết quả ánh xạ trực tiếp
sang facts của Ontology (Bài toán 2: trích tri thức sự kiện, gán đúng nút ontology).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Set

from traffic_es.knowledge.knowledge_graph import KnowledgeGraph
from traffic_es.knowledge.ontology import Concept


@dataclass
class QMatch:
    concept: Concept
    score: float
    matched_keyphrases: List[str]


def subgraph_match(
    question: str, kg: KnowledgeGraph, min_score: float = 0.0
) -> List[QMatch]:
    """Các ngôi sao (concept) mà câu hỏi phủ được, giảm dần theo điểm."""
    q = question.lower()
    out: List[QMatch] = []
    for c in kg.store.concepts:
        matched = [p for p in list(c.keyphrases) + [c.name] if p.lower() in q]
        if not matched:
            continue
        score = sum(kg._phrase_weight(p) for p in matched)
        if score > min_score:
            out.append(QMatch(concept=c, score=score, matched_keyphrases=matched))
    out.sort(key=lambda m: m.score, reverse=True)
    return out


def to_nodes(question: str, kg: KnowledgeGraph) -> Set[str]:
    """Tập tên concept (nút ontology) mà câu hỏi kích hoạt."""
    return {m.concept.name for m in subgraph_match(question, kg)}


def _coerce(value: Any) -> Any:
    if isinstance(value, str):
        low = value.strip().lower()
        if low == "true":
            return True
        if low == "false":
            return False
    return value


def map_to_facts(matches: List[QMatch]) -> Dict[str, Any]:
    """Ánh xạ các concept khớp sang facts. Concept điểm cao thắng khi trùng key."""
    facts: Dict[str, Any] = {}
    for m in matches:  # đã sắp giảm dần theo điểm
        fact = m.concept.attrs.get("fact")
        if not fact:
            continue
        facts.setdefault(fact, _coerce(m.concept.attrs.get("value")))
    return facts
