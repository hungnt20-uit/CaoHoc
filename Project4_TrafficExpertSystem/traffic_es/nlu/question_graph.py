"""Đồ thị câu hỏi → phân rã hình sao → so khớp đồ thị con (subgraph matching).

Theo pipeline hỏi–đáp trên Legal-Onto: câu hỏi được biểu diễn thành các "nút"
(cụm keyphrase kích hoạt). Mỗi Concept trong Knowledge Graph là một *ngôi sao*
(tâm = concept, cánh = keyphrase). So khớp đồ thị con = tìm các ngôi sao mà câu hỏi
phủ được, chấm điểm bằng trọng số TF-IDF của các cánh khớp. Kết quả ánh xạ trực tiếp
sang facts của Ontology (Bài toán 2: trích tri thức sự kiện, gán đúng nút ontology).

Cực tính được xét trước khi ánh xạ: cánh nào rơi vào mệnh đề phủ định/tuân thủ thì
bị loại, nên "dừng đèn đỏ đúng luật" không còn bị quy thành lỗi vượt đèn đỏ.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Set

from traffic_es.knowledge.knowledge_graph import KnowledgeGraph
from traffic_es.knowledge.ontology import Concept
from traffic_es.nlu.polarity import is_negated


@dataclass
class QMatch:
    concept: Concept
    score: float
    matched_keyphrases: List[str]
    negated_keyphrases: List[str] = field(default_factory=list)


def _negation_filter(question: str, start: int) -> bool:
    return is_negated(question, start)


def subgraph_match(
    question: str, kg: KnowledgeGraph, min_score: float = 0.0
) -> List[QMatch]:
    """Các ngôi sao (concept) mà câu hỏi phủ được, giảm dần theo điểm."""
    out: List[QMatch] = []
    for c in kg.store.concepts:
        hits, rejected = kg.phrase_hits(c, question, hit_filter=_negation_filter)
        score = sum(h.weight for h in hits)
        if not hits or score <= min_score:
            continue
        out.append(
            QMatch(
                concept=c,
                score=score,
                matched_keyphrases=[h.phrase for h in hits],
                negated_keyphrases=rejected,
            )
        )
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
