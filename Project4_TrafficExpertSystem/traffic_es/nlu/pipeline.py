from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple

from traffic_es.nlu.normalize import normalize
from traffic_es.nlu.extractor import Extractor, HeuristicExtractor
from traffic_es.nlu.grounding import ground
from traffic_es.nlu.semantic_infer import infer_circumstances
from traffic_es.knowledge.ontology import ConceptStore
from traffic_es.knowledge.knowledge_graph import KnowledgeGraph
from traffic_es.nlu.question_graph import subgraph_match, map_to_facts

_CONCEPTS_PATH = Path(__file__).resolve().parents[1] / "knowledge" / "concepts.yaml"


class NLUPipeline:
    def __init__(
        self,
        extractor: Optional[Extractor] = None,
        use_knowledge_graph: bool = True,
    ):
        self.extractor = extractor or HeuristicExtractor()
        self.kg: Optional[KnowledgeGraph] = None
        if use_knowledge_graph and _CONCEPTS_PATH.exists():
            self.kg = KnowledgeGraph.from_store(ConceptStore.from_yaml(_CONCEPTS_PATH))

    def run(self, text: str) -> Tuple[Dict[str, object], Dict[str, object]]:
        norm = normalize(text)
        facts, ev, raw = self.extractor.extract(norm)
        inferred: List[Dict[str, object]] = infer_circumstances(raw)
        for i in inferred:
            facts[i["fact"]] = i["value"]

        # Legal-Onto: đồ thị câu hỏi → so khớp đồ thị con → BỔ SUNG fact còn thiếu.
        matched_concepts: List[Dict[str, object]] = []
        kg_facts_added: List[str] = []
        if self.kg is not None:
            matches = subgraph_match(norm, self.kg)
            matched_concepts = [
                {"concept": m.concept.name, "score": round(m.score, 3),
                 "keyphrases": m.matched_keyphrases}
                for m in matches
            ]
            for key, value in map_to_facts(matches).items():
                if key not in facts:  # chỉ điền chỗ trống, không ghi đè
                    facts[key] = value
                    kg_facts_added.append(key)

        clean, warns = ground(facts)
        meta = {
            "normalized": norm,
            "evidences": ev,
            "raw_events": raw,
            "inferred": inferred,
            "matched_concepts": matched_concepts,
            "kg_facts_added": kg_facts_added,
            "warnings": warns,
        }
        return clean, meta
