"""Legal-Onto Knowledge Graph với trọng số keyphrase theo TF-IDF.

Mỗi Concept là một "tài liệu" gồm các keyphrase. Ta tính IDF ở mức token trên
toàn bộ concept (token phổ biến như "xe", "không" bị hạ trọng số; token hiếm như
"mũ", "cồn" được nâng). Điểm khớp một câu hỏi với concept = tổng IDF của các token
thuộc những keyphrase XUẤT HIỆN (dạng cụm) trong câu hỏi — cách chấm "phrase-anchored
TF-IDF" giúp tránh nhiễu do token đơn lẻ.

Việc chấm điểm dựa trên *span*: mỗi vị trí trong câu chỉ được tính cho MỘT cụm khớp
dài nhất. Nếu không làm vậy, cụm lồng nhau sẽ cộng dồn — "gây tai nạn" khớp cả
"gây tai nạn" lẫn cụm con "tai nạn" (và cả tên concept trùng keyphrase) khiến điểm
bị thổi lên gấp ba, làm méo xếp hạng concept.
"""

from __future__ import annotations

import math
import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

from traffic_es.knowledge.ontology import Concept, ConceptStore

_TOKEN_RE = re.compile(r"[0-9a-zà-ỹ/]+", re.IGNORECASE)

# Bộ lọc một lần khớp: (câu hỏi, vị trí bắt đầu) -> True nếu phải BỎ lần khớp này.
HitFilter = Callable[[str, int], bool]


def _tokens(text: str) -> List[str]:
    return _TOKEN_RE.findall(text.lower())


@dataclass(frozen=True)
class PhraseHit:
    """Một lần khớp cụm keyphrase vào câu hỏi, tại span [start, end)."""

    phrase: str
    start: int
    end: int
    weight: float


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

    @staticmethod
    def _candidates(concept: Concept) -> List[str]:
        """Keyphrase + tên concept, bỏ trùng, ưu tiên cụm dài trước."""
        seen = set()
        uniq: List[str] = []
        for p in list(concept.keyphrases) + [concept.name]:
            low = p.lower()
            if low and low not in seen:
                seen.add(low)
                uniq.append(low)
        return sorted(uniq, key=len, reverse=True)

    def phrase_hits(
        self,
        concept: Concept,
        question: str,
        hit_filter: Optional[HitFilter] = None,
    ) -> Tuple[List[PhraseHit], List[str]]:
        """Các cụm khớp dài nhất, không chồng lấn.

        Trả về (hits, rejected) — `rejected` là các cụm bị `hit_filter` loại (ví dụ
        do nằm trong ngữ cảnh phủ định), phục vụ giải thích minh bạch.
        """
        q = question.lower()
        claimed: List[Tuple[int, int]] = []
        hits: List[PhraseHit] = []
        rejected: List[str] = []
        for phrase in self._candidates(concept):
            i = q.find(phrase)
            while i >= 0:
                j = i + len(phrase)
                if any(i < e and s < j for s, e in claimed):
                    i = q.find(phrase, i + 1)
                    continue
                if hit_filter is not None and hit_filter(q, i):
                    rejected.append(phrase)
                    i = q.find(phrase, i + 1)
                    continue
                claimed.append((i, j))
                hits.append(
                    PhraseHit(phrase, i, j, self._phrase_weight(phrase))
                )
                i = q.find(phrase, j)
        hits.sort(key=lambda h: h.start)
        return hits, rejected

    def match(
        self,
        question: str,
        top_k: Optional[int] = None,
        min_score: float = 0.0,
        hit_filter: Optional[HitFilter] = None,
    ) -> List[Tuple[Concept, float]]:
        """Danh sách (concept, score) giảm dần, chỉ giữ concept có cụm khớp."""
        scored: List[Tuple[Concept, float]] = []
        for c in self.store.concepts:
            hits, _ = self.phrase_hits(c, question, hit_filter)
            score = sum(h.weight for h in hits)
            if score > min_score:
                scored.append((c, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k] if top_k else scored
