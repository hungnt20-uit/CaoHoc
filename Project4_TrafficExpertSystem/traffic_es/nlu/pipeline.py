from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from traffic_es.nlu.normalize import normalize
from traffic_es.nlu.extractor import Extractor, HeuristicExtractor
from traffic_es.nlu.grounding import ground
from traffic_es.nlu.semantic_infer import infer_circumstances


class NLUPipeline:
    def __init__(self, extractor: Optional[Extractor] = None):
        self.extractor = extractor or HeuristicExtractor()

    def run(self, text: str) -> Tuple[Dict[str, object], Dict[str, object]]:
        norm = normalize(text)
        facts, ev, raw = self.extractor.extract(norm)
        inferred: List[Dict[str, object]] = infer_circumstances(raw)
        for i in inferred:
            facts[i["fact"]] = i["value"]
        clean, warns = ground(facts)
        meta = {
            "normalized": norm,
            "evidences": ev,
            "raw_events": raw,
            "inferred": inferred,
            "warnings": warns,
        }
        return clean, meta
