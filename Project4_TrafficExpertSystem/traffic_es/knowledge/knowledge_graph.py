"""Legal-Onto Knowledge Graph với trọng số keyphrase theo TF-IDF.

Mỗi Concept là một "tài liệu" gồm các keyphrase. Ta tính IDF ở mức token trên
toàn bộ concept (token phổ biến như "xe", "không" bị hạ trọng số; token hiếm như
"mũ", "cồn" được nâng). Điểm khớp một câu hỏi với concept = tổng IDF của các token
thuộc những keyphrase XUẤT HIỆN (dạng cụm) trong câu hỏi — cách chấm "phrase-anchored
TF-IDF" giúp tránh nhiễu do token đơn lẻ.
"""

from __future__ import annotations

import math
import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from traffic_es.knowledge.ontology import Concept, ConceptStore

_TOKEN_RE = re.compile(r"[0-9a-zà-ỹ/]+", re.IGNORECASE)


def _tokens(text: str) -> List[str]:
    return _TOKEN_RE.findall(text.lower())


@dataclass
class KnowledgeGraph:
    store: ConceptStore
    idf: Dict[str, float]

    @classmethod
    def from_store(cls, store: ConceptStore) -> "KnowledgeGraph":
        df: Dict[str, int] = defaultdict(int)
        for c in store.concepts:
            toks = set()
            for phrase in list(c.keyphrases) + [c.name]:
                toks.update(_tokens(phrase))
            for t in toks:
                df[t] += 1
        n = max(len(store.concepts), 1)
        idf = {t: math.log((n + 1) / (d + 1)) + 1.0 for t, d in df.items()}
        return cls(store=store, idf=idf)

    def _phrase_weight(self, phrase: str) -> float:
        return sum(self.idf.get(t, 0.0) for t in _tokens(phrase))

    def match(
        self,
        question: str,
        top_k: Optional[int] = None,
        min_score: float = 0.0,
    ) -> List[Tuple[Concept, float]]:
        """Danh sách (concept, score) giảm dần, chỉ giữ concept có cụm khớp."""
        q = question.lower()
        scored: List[Tuple[Concept, float]] = []
        for c in self.store.concepts:
            score = 0.0
            for phrase in list(c.keyphrases) + [c.name]:
                if phrase.lower() in q:
                    score += self._phrase_weight(phrase)
            if score > min_score:
                scored.append((c, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k] if top_k else scored
