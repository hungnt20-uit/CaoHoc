from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple

from traffic_es.nlu.normalize import normalize
from traffic_es.nlu.extractor import Extractor, HeuristicExtractor
from traffic_es.nlu.grounding import ground
from traffic_es.nlu.semantic_infer import (
    CircumstanceInferrer,
    KeywordInferrer,
    drop_double_counted,
)
from traffic_es.knowledge.ontology import ConceptStore
from traffic_es.knowledge.knowledge_graph import KnowledgeGraph
from traffic_es.nlu.question_graph import subgraph_match, map_to_facts

_CONCEPTS_PATH = Path(__file__).resolve().parents[1] / "knowledge" / "concepts.yaml"

# Dưới ngưỡng này, tình tiết được giữ nhưng gắn cờ "cần xác nhận" (đặc tả §5.2).
CONFIDENCE_TOI_THIEU = 0.6


class NLUPipeline:
    def __init__(
        self,
        extractor: Optional[Extractor] = None,
        use_knowledge_graph: bool = True,
        inferrer: Optional[CircumstanceInferrer] = None,
    ):
        self.extractor = extractor or HeuristicExtractor()
        self.inferrer = inferrer or KeywordInferrer()
        self.kg: Optional[KnowledgeGraph] = None
        if use_knowledge_graph and _CONCEPTS_PATH.exists():
            self.kg = KnowledgeGraph.from_store(ConceptStore.from_yaml(_CONCEPTS_PATH))

    def run(self, text: str) -> Tuple[Dict[str, object], Dict[str, object]]:
        norm = normalize(text)
        facts, ev, raw = self.extractor.extract(norm)

        # Bài toán 1: suy diễn tình tiết gián tiếp (LLM hoặc từ khóa, closed vocabulary)
        inferred: List[Dict[str, object]] = self.inferrer.infer(raw, norm)
        # Chặn trước khi hợp nhất: tình tiết trùng với vi phạm đã tính không được vào WM.
        inferred, trung_lap_warns = drop_double_counted(inferred, facts)
        can_xac_nhan: List[str] = []
        for i in inferred:
            facts[i["fact"]] = i["value"]
            if float(i.get("confidence", 1.0)) < CONFIDENCE_TOI_THIEU:
                can_xac_nhan.append(str(i["fact"]))

        # Legal-Onto: đồ thị câu hỏi → so khớp đồ thị con → BỔ SUNG fact còn thiếu.
        matched_concepts: List[Dict[str, object]] = []
        kg_facts_added: List[str] = []
        negated: List[str] = []
        if self.kg is not None:
            matches = subgraph_match(norm, self.kg)
            matched_concepts = [
                {
                    "concept": m.concept.name,
                    "nhom": m.concept.attrs.get("nhom"),
                    "score": round(m.score, 3),
                    "keyphrases": m.matched_keyphrases,
                }
                for m in matches
            ]
            negated = sorted({p for m in matches for p in m.negated_keyphrases})
            for key, value in map_to_facts(matches).items():
                if key not in facts:  # chỉ điền chỗ trống, không ghi đè
                    facts[key] = value
                    kg_facts_added.append(key)

        clean, warns = ground(facts)
        # Fact bị loại vì thiếu căn cứ trong câu (chỉ bộ trích xuất LLM mới sinh ra).
        # Bỏ qua fact đã được đồ thị tri thức bổ sung lại: nó không thực sự mất.
        dropped: Dict[str, str] = getattr(self.extractor, "last_dropped", {})
        warns = (
            [msg for key, msg in dropped.items() if key not in clean]
            + list(getattr(self.extractor, "last_warnings", []))
            + warns
            + trung_lap_warns
        )
        if can_xac_nhan:
            warns.append(
                "Tình tiết có độ tin cậy thấp, cần xác nhận: " + ", ".join(can_xac_nhan)
            )
        meta = {
            "normalized": norm,
            "evidences": ev,
            "raw_events": raw,
            "inferred": inferred,
            "matched_concepts": matched_concepts,
            "kg_facts_added": kg_facts_added,
            "negated_keyphrases": negated,
            "can_xac_nhan": can_xac_nhan,
            "warnings": warns,
        }
        return clean, meta
