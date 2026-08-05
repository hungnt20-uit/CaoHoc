"""Dựng nodes/edges từ Legal-Onto KG và từ Answer (chuỗi suy diễn).

Cạnh mang nhãn quan hệ (HAS_KEYPHRASE / EXHIBITS / MAPS_TO / FIRES / …),
nguồn gốc và độ tin cậy — khớp yêu cầu giải thích đồ thị tri thức trong đề bài.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional, Set

from traffic_es.engine.trace import Trace
from traffic_es.knowledge.knowledge_graph import KnowledgeGraph
from traffic_es.knowledge.ontology import ConceptStore

# Màu theo nhóm concept (Legal-Onto)
_NHOM_COLOR = {
    "phuong_tien": "#2A9D8F",
    "nong_do_con": "#264653",
    "toc_do": "#1D3557",
    "mu_bao_hiem": "#E9C46A",
    "day_an_toan": "#F4A261",
    "tin_hieu": "#E76F51",
    "giay_to": "#457B9D",
    "tinh_tiet": "#D62828",
}

_GROUP_COLOR = {
    "concept": "#2A9D8F",
    "keyphrase": "#F4A261",
    "fact": "#457B9D",
    "rule": "#E9C46A",
    "meta": "#E76F51",
    "conclusion": "#D62828",
    "input": "#6C757D",
    "inferred": "#9B5DE5",
    "root": "#1B263B",
    "nhom": "#415A77",
}

_NHOM_LABEL = {
    "phuong_tien": "Phương tiện",
    "nong_do_con": "Nồng độ cồn",
    "toc_do": "Tốc độ",
    "mu_bao_hiem": "Mũ bảo hiểm",
    "day_an_toan": "Dây an toàn",
    "tin_hieu": "Tín hiệu",
    "giay_to": "Giấy tờ",
    "tinh_tiet": "Tình tiết",
}


@dataclass
class GNode:
    id: str
    label: str
    group: str
    title: str = ""
    color: str = "#888888"
    size: int = 18
    highlight: bool = False


@dataclass
class GEdge:
    source: str
    target: str
    label: str
    title: str = ""
    color: str = "#AAAAAA"
    width: float = 1.5


@dataclass
class GraphData:
    nodes: List[GNode] = field(default_factory=list)
    edges: List[GEdge] = field(default_factory=list)

    @property
    def n_nodes(self) -> int:
        return len(self.nodes)

    @property
    def n_edges(self) -> int:
        return len(self.edges)

    def summary(self) -> str:
        return (
            f"{self.n_nodes} đỉnh, {self.n_edges} cạnh. "
            "Mọi cạnh đều mang nguồn gốc và độ tin cậy."
        )


def _nid(*parts: str) -> str:
    return "|".join(parts)


def _edge_title(rel: str, source: str, confidence: float) -> str:
    return (
        f"<b>{rel}</b><br>"
        f"nguồn: <code>{source}</code><br>"
        f"độ tin: <b>{confidence:.2f}</b>"
    )


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def build_legal_onto_graph(
    store: ConceptStore,
    kg: Optional[KnowledgeGraph] = None,
    matched_concepts: Optional[Iterable[Mapping[str, Any]]] = None,
) -> GraphData:
    """Đồ thị Legal-Onto: root → nhóm → concept ↔ keyphrase + MAPS_TO fact.

    KB gốc là các ngôi sao concept tách rời; ta nối qua hub ``Legal-Onto`` và
    node ``nhom`` để thành một đồ thị liên thông (tránh cụm "rời rạc" trên UI).

    Nếu có `matched_concepts`, concept/keyphrase khớp được highlight với cạnh
    ``EXHIBITS`` (điểm TF-IDF → độ tin).
    """
    matched_map: Dict[str, Mapping[str, Any]] = {}
    matched_phrases: Set[str] = set()
    for m in matched_concepts or []:
        name = str(m.get("concept") or "")
        if name:
            matched_map[name.lower()] = m
        for kp in m.get("keyphrases") or []:
            matched_phrases.add(str(kp).lower())

    g = GraphData()
    seen_nodes: Set[str] = set()
    max_w = 1.0
    if kg is not None:
        weights = [
            kg._phrase_weight(p)
            for c in store.concepts
            for p in list(c.keyphrases) + [c.name]
        ]
        max_w = max(weights) if weights else 1.0

    # Hub gốc — gom mọi nhóm concept thành 1 thành phần liên thông
    root_id = "ROOT"
    g.nodes.append(
        GNode(
            id=root_id,
            label="Legal-Onto",
            group="root",
            title="<b>Legal-Onto</b><br>Ontology khái niệm Nghị định 168/2024",
            color=_GROUP_COLOR["root"],
            size=36,
            highlight=True,
        )
    )
    seen_nodes.add(root_id)

    for c in store.concepts:
        nhom = (c.attrs or {}).get("nhom", "") or "khac"
        nhom_id = _nid("N", nhom)
        if nhom_id not in seen_nodes:
            g.nodes.append(
                GNode(
                    id=nhom_id,
                    label=_NHOM_LABEL.get(nhom, nhom),
                    group="nhom",
                    title=f"<b>Nhóm</b> <code>{nhom}</code>",
                    color=_NHOM_COLOR.get(nhom, _GROUP_COLOR["nhom"]),
                    size=22,
                )
            )
            seen_nodes.add(nhom_id)
            g.edges.append(
                GEdge(
                    source=root_id,
                    target=nhom_id,
                    label="HAS_GROUP",
                    title=_edge_title("HAS_GROUP", "concepts.yaml#attrs.nhom", 1.0),
                    color="#778DA9",
                    width=1.5,
                )
            )

        cid = _nid("C", c.name)
        is_hit = c.name.lower() in matched_map
        score = float(matched_map[c.name.lower()]["score"]) if is_hit else 0.0
        color = _NHOM_COLOR.get(nhom, _GROUP_COLOR["concept"])
        title = (
            f"<b>{c.name}</b> <i>(concept)</i><br>"
            f"nhóm: {nhom}<br>"
            f"{c.content}<br>"
            f"<i>{c.inner_rul}</i>"
        )
        if is_hit:
            title += f"<br><b>khớp câu hỏi · điểm {score:.3f}</b>"
        g.nodes.append(
            GNode(
                id=cid,
                label=c.name,
                group="concept",
                title=title,
                color=color,
                size=32 if is_hit else 26,
                highlight=is_hit,
            )
        )
        seen_nodes.add(cid)
        g.edges.append(
            GEdge(
                source=nhom_id,
                target=cid,
                label="HAS_CONCEPT",
                title=_edge_title("HAS_CONCEPT", "concepts.yaml", 1.0),
                color="#778DA9",
                width=1.4,
            )
        )

        # MAPS_TO fact — id gồm cả value để ô tô / mô tô không dính chung 1 đỉnh
        fact_key = (c.attrs or {}).get("fact")
        fact_val = (c.attrs or {}).get("value")
        if fact_key:
            fid = _nid("F", fact_key, str(fact_val or ""))
            if fid not in seen_nodes:
                g.nodes.append(
                    GNode(
                        id=fid,
                        label=f"{fact_key}={fact_val}" if fact_val else fact_key,
                        group="fact",
                        title=f"<b>{fact_key}</b><br>value: {fact_val}",
                        color=_GROUP_COLOR["fact"],
                        size=16,
                    )
                )
                seen_nodes.add(fid)
            g.edges.append(
                GEdge(
                    source=cid,
                    target=fid,
                    label="MAPS_TO",
                    title=_edge_title("MAPS_TO", "concepts.yaml#attrs", 1.0),
                    color="#457B9D",
                    width=1.2,
                )
            )

        phrases = list(dict.fromkeys(list(c.keyphrases) + [c.name]))
        for phrase in phrases:
            kid = _nid("K", c.name, phrase.lower())
            phrase_hit = phrase.lower() in matched_phrases and is_hit
            w = kg._phrase_weight(phrase) if kg is not None else 1.0
            conf = _clamp01(w / max_w) if max_w else 0.5
            if kid not in seen_nodes:
                g.nodes.append(
                    GNode(
                        id=kid,
                        label=phrase,
                        group="keyphrase",
                        title=f"<b>{phrase}</b> <i>(keyphrase)</i><br>concept: {c.name}",
                        color="#E76F51" if phrase_hit else _GROUP_COLOR["keyphrase"],
                        size=14 if phrase_hit else 10,
                        highlight=phrase_hit,
                    )
                )
                seen_nodes.add(kid)

            if phrase_hit:
                rel_conf = _clamp01(score / 10.0) if score else conf
                g.edges.append(
                    GEdge(
                        source=cid,
                        target=kid,
                        label="EXHIBITS",
                        title=_edge_title("EXHIBITS", "question_graph", max(rel_conf, 0.55)),
                        color="#D62828",
                        width=3.0,
                    )
                )
            else:
                g.edges.append(
                    GEdge(
                        source=cid,
                        target=kid,
                        label="HAS_KEYPHRASE",
                        title=_edge_title("HAS_KEYPHRASE", "concepts.yaml", conf),
                        color="#CFCFCF",
                        width=1.0,
                    )
                )

    return g


def build_reasoning_graph(
    facts: Mapping[str, Any],
    trace: Trace,
    nlu_meta: Mapping[str, Any],
    ket_qua_chi_tiet: Optional[Iterable[Any]] = None,
    store: Optional[ConceptStore] = None,
) -> GraphData:
    """Đồ thị suy diễn: INPUT → concept → fact → RULE/META → kết luận."""
    g = GraphData()
    seen: Set[str] = set()
    fact_ids: Dict[str, str] = {}  # fact_key -> node id
    concept_by_name: Dict[str, Any] = {}
    if store is not None:
        concept_by_name = {c.name.lower(): c for c in store.concepts}

    def add_node(node: GNode) -> None:
        if node.id not in seen:
            g.nodes.append(node)
            seen.add(node.id)

    add_node(
        GNode(
            id="INPUT",
            label="Tình huống",
            group="input",
            title="Đầu vào ngôn ngữ tự nhiên",
            color=_GROUP_COLOR["input"],
            size=30,
            highlight=True,
        )
    )

    # Concept khớp Legal-Onto
    matched_concept_ids: List[str] = []
    for m in nlu_meta.get("matched_concepts") or []:
        name = str(m.get("concept") or "")
        if not name:
            continue
        cid = _nid("C", name)
        matched_concept_ids.append(cid)
        score = float(m.get("score") or 0.0)
        add_node(
            GNode(
                id=cid,
                label=name,
                group="concept",
                title=(
                    f"<b>{name}</b><br>nhóm: {m.get('nhom') or '—'}<br>"
                    f"điểm khớp: {score:.3f}<br>"
                    f"keyphrases: {', '.join(m.get('keyphrases') or [])}"
                ),
                color=_NHOM_COLOR.get(str(m.get("nhom") or ""), _GROUP_COLOR["concept"]),
                size=28,
                highlight=True,
            )
        )
        conf = _clamp01(score / 10.0) if score else 0.7
        g.edges.append(
            GEdge(
                source="INPUT",
                target=cid,
                label="MATCHES",
                title=_edge_title("MATCHES", "question_graph", max(conf, 0.55)),
                color="#2A9D8F",
                width=2.5,
            )
        )
        for kp in m.get("keyphrases") or []:
            kid = _nid("K", name, str(kp).lower())
            add_node(
                GNode(
                    id=kid,
                    label=str(kp),
                    group="keyphrase",
                    title=f"<b>{kp}</b> · EXHIBITS từ {name}",
                    color=_GROUP_COLOR["keyphrase"],
                    size=12,
                    highlight=True,
                )
            )
            g.edges.append(
                GEdge(
                    source=cid,
                    target=kid,
                    label="EXHIBITS",
                    title=_edge_title("EXHIBITS", "pattern_detector", max(conf, 0.7)),
                    color="#E76F51",
                    width=2.0,
                )
            )

    # Facts trong working memory
    kg_added = set(nlu_meta.get("kg_facts_added") or [])
    skip_prefixes = ("clarify.",)
    for key, val in facts.items():
        if any(key.startswith(p) for p in skip_prefixes):
            continue
        fid = _nid("F", key)
        fact_ids[key] = fid
        add_node(
            GNode(
                id=fid,
                label=f"{key}={val}",
                group="fact",
                title=f"<b>fact</b><br>{key} = {val}",
                color=_GROUP_COLOR["fact"],
                size=16,
            )
        )
        # Ưu tiên nối concept → fact (MAPS_TO); nếu không có thì từ INPUT
        linked_from_concept = False
        for m in nlu_meta.get("matched_concepts") or []:
            c = concept_by_name.get(str(m.get("concept") or "").lower())
            if c is None:
                continue
            if (c.attrs or {}).get("fact") != key:
                continue
            g.edges.append(
                GEdge(
                    source=_nid("C", c.name),
                    target=fid,
                    label="MAPS_TO",
                    title=_edge_title("MAPS_TO", "concepts.yaml#attrs", 1.0),
                    color="#457B9D",
                    width=2.0,
                )
            )
            linked_from_concept = True
        if not linked_from_concept:
            src_label = "knowledge_graph" if key in kg_added else "nlu.extractor"
            g.edges.append(
                GEdge(
                    source="INPUT",
                    target=fid,
                    label="EXTRACTS",
                    title=_edge_title("EXTRACTS", src_label, 0.9),
                    color="#457B9D",
                    width=1.2,
                )
            )

    # Tình tiết suy luận gián tiếp (bỏ trùng với fact đã có)
    for i, inf in enumerate(nlu_meta.get("inferred") or []):
        fact = str(inf.get("fact") or f"inferred_{i}")
        if fact in fact_ids:
            # Fact đã hiện — chỉ gắn cạnh INFERS từ INPUT → fact (nếu chưa có MAPS_TO)
            continue
        conf = _clamp01(float(inf.get("confidence") or 0.5))
        iid = _nid("I", fact)
        add_node(
            GNode(
                id=iid,
                label=f"{fact}={inf.get('value')}",
                group="inferred",
                title=(
                    f"<b>tình tiết suy luận</b><br>{fact}<br>"
                    f"evidence: {inf.get('evidence') or '—'}"
                ),
                color=_GROUP_COLOR["inferred"],
                size=18,
                highlight=True,
            )
        )
        g.edges.append(
            GEdge(
                source="INPUT",
                target=iid,
                label="INFERS",
                title=_edge_title("INFERS", str(inf.get("source") or "semantic_infer"), conf),
                color="#9B5DE5",
                width=2.0,
            )
        )
        fact_ids[fact] = iid

    # Hub Working Memory — gom fact trước khi kích hoạt luật (tránh cạnh rời / quạt rối)
    wm_id = "WM"
    add_node(
        GNode(
            id=wm_id,
            label="Working Memory",
            group="fact",
            title="<b>Working Memory</b><br>Tập fact dùng để suy diễn",
            color="#1D3557",
            size=26,
            highlight=True,
        )
    )
    if fact_ids:
        for fid in fact_ids.values():
            g.edges.append(
                GEdge(
                    source=fid,
                    target=wm_id,
                    label="GROUNDS",
                    title=_edge_title("GROUNDS", "working_memory", 1.0),
                    color="#1D3557",
                    width=1.5,
                )
            )
    else:
        g.edges.append(
            GEdge(
                source="INPUT",
                target=wm_id,
                label="GROUNDS",
                title=_edge_title("GROUNDS", "working_memory", 0.5),
                color="#1D3557",
                width=1.2,
            )
        )

    # Trace: RULE / META / FUNC / ASTAR / KL
    prev_rule_ids: List[str] = []
    for step in trace.steps:
        kind = step.kind.upper()
        data = step.data or {}
        if kind == "RULE":
            rid = str(data.get("rule_id") or step.detail[:40])
            nid = _nid("R", rid)
            add_node(
                GNode(
                    id=nid,
                    label=rid,
                    group="rule",
                    title=f"<b>RULE</b> {rid}<br>{step.detail}",
                    color=_GROUP_COLOR["rule"],
                    size=24,
                    highlight=True,
                )
            )
            g.edges.append(
                GEdge(
                    source=wm_id,
                    target=nid,
                    label="FIRES",
                    title=_edge_title("FIRES", "forward_chaining", 0.95),
                    color="#E9C46A",
                    width=2.2,
                )
            )
            prev_rule_ids.append(nid)
        elif kind == "META":
            mid = _nid("M", step.detail[:48] or "meta")
            add_node(
                GNode(
                    id=mid,
                    label="META",
                    group="meta",
                    title=f"<b>META</b><br>{step.detail}",
                    color=_GROUP_COLOR["meta"],
                    size=22,
                    highlight=True,
                )
            )
            src = prev_rule_ids[-1] if prev_rule_ids else "INPUT"
            g.edges.append(
                GEdge(
                    source=src,
                    target=mid,
                    label="APPLIES",
                    title=_edge_title("APPLIES", "meta_rules", 0.9),
                    color="#E76F51",
                    width=2.0,
                )
            )
            prev_rule_ids.append(mid)
        elif kind in ("FUNC", "ASTAR"):
            nid = _nid(kind, step.detail[:40])
            add_node(
                GNode(
                    id=nid,
                    label=kind,
                    group="rule",
                    title=f"<b>{kind}</b><br>{step.detail}",
                    color="#A8DADC",
                    size=18,
                )
            )
            g.edges.append(
                GEdge(
                    source="INPUT",
                    target=nid,
                    label=kind,
                    title=_edge_title(kind, "deduction_network", 0.85),
                    color="#A8DADC",
                    width=1.5,
                )
            )
        elif kind == "KL":
            kid = "KL"
            add_node(
                GNode(
                    id=kid,
                    label="Kết luận",
                    group="conclusion",
                    title=f"<b>Kết luận</b><br>{step.detail}",
                    color=_GROUP_COLOR["conclusion"],
                    size=30,
                    highlight=True,
                )
            )
            src = prev_rule_ids[-1] if prev_rule_ids else "INPUT"
            g.edges.append(
                GEdge(
                    source=src,
                    target=kid,
                    label="CONCLUDES",
                    title=_edge_title("CONCLUDES", "aggregate", 1.0),
                    color="#D62828",
                    width=3.0,
                )
            )

    # Chi tiết mức phạt (nếu có)
    for i, dong in enumerate(ket_qua_chi_tiet or []):
        label = str(getattr(dong, "hanh_vi", None) or dong)
        can_cu = getattr(dong, "can_cu", "") or ""
        tien = getattr(dong, "tien", None)
        pid = _nid("P", str(i), label[:32])
        short = (label[:42] + "…") if len(label) > 42 else label
        money = f"tiền: {tien:,} đ<br>" if isinstance(tien, int) else ""
        add_node(
            GNode(
                id=pid,
                label=short,
                group="conclusion",
                title=f"<b>{label}</b><br>{money}căn cứ: {can_cu}",
                color="#9D0208",
                size=20,
            )
        )
        g.edges.append(
            GEdge(
                source="KL" if "KL" in seen else (prev_rule_ids[-1] if prev_rule_ids else "INPUT"),
                target=pid,
                label="PENALTY",
                title=_edge_title("PENALTY", "NĐ 168/2024", 1.0),
                color="#9D0208",
                width=2.0,
            )
        )

    return g
