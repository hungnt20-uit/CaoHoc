from __future__ import annotations

import os
import sys
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

# cho phép chạy `streamlit run app/streamlit_app.py` từ gốc dự án
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from traffic_es.service import TrafficESService
from traffic_es.nlu.pipeline import NLUPipeline
from traffic_es.nlu.clarify import apply_clarification
from traffic_es.engine.reasoner import Reasoner
from traffic_es.nlu.extractor import HeuristicExtractor
from traffic_es.nlu.llm_extractor import LLMExtractor
from traffic_es.nlu.semantic_infer import KeywordInferrer
from traffic_es.nlu.llm_semantic_infer import LLMCircumstanceInferrer
from traffic_es.llm.client import CachingLLM
from traffic_es.llm.providers import (
    make_default_llm,
    default_mode_label,
    OpenAILLM,
    AnthropicLLM,
    LocalOpenAICompatLLM,
    DEFAULT_LOCAL_MODEL,
    DEFAULT_LOCAL_BASE_URL,
)
from traffic_es.knowledge.ontology import ConceptStore
from traffic_es.knowledge.knowledge_graph import KnowledgeGraph
from traffic_es.viz.graph_data import build_legal_onto_graph, build_reasoning_graph
from traffic_es.viz.pyvis_render import try_render_html

ROOT = Path(__file__).resolve().parent.parent
RULES_DIR = ROOT / "traffic_es" / "knowledge" / "rules"
CONCEPTS_PATH = ROOT / "traffic_es" / "knowledge" / "concepts.yaml"

AUTO = "Tự động (theo .env)"
CLAUDE = "Anthropic (Claude)"
OPENAI = "OpenAI (GPT)"
LOCAL = "Local / Colab (Qwen…)"
HEURISTIC = "Heuristic (offline)"


@st.cache_resource
def get_reasoner() -> Reasoner:
    return Reasoner.from_rules_dir(RULES_DIR)


@st.cache_resource
def get_concept_store() -> ConceptStore:
    return ConceptStore.from_yaml(CONCEPTS_PATH)


@st.cache_resource
def get_kg() -> KnowledgeGraph:
    return KnowledgeGraph.from_store(get_concept_store())


def show_graph(graph, *, height: int = 560) -> None:
    """Nhúng đồ thị tương tác; fallback bảng nếu thiếu pyvis."""
    st.caption(graph.summary())
    html = try_render_html(graph, height=f"{height}px")
    if html:
        components.html(html, height=height + 40, scrolling=True)
        return
    st.warning("Chưa có `pyvis`. Chạy: `pip install pyvis networkx` rồi tải lại trang.")
    st.write("**Đỉnh:**", [n.label for n in graph.nodes[:40]], "…" if graph.n_nodes > 40 else "")
    st.write(
        "**Cạnh (mẫu):**",
        [f"{e.source} -[{e.label}]→ {e.target}" for e in graph.edges[:30]],
        "…" if graph.n_edges > 30 else "",
    )


def build_extractor(provider: str, api_key: str, model: str, base_url: str = ""):
    """Trả về (extractor cho BT2, inferrer cho BT1, nhãn chế độ)."""
    key = api_key.strip() or None
    mdl = model.strip() or None

    def _with_llm(llm, label):
        # Cùng một LLM phục vụ cả hai bài toán, có cache để đỡ tốn phí.
        cached = CachingLLM(llm)
        return LLMExtractor(cached), LLMCircumstanceInferrer(cached), label

    try:
        if provider == CLAUDE:
            return _with_llm(
                AnthropicLLM(model=mdl, api_key=key),
                f"LLM · Anthropic · {mdl or 'claude-opus-4-8'}",
            )
        if provider == OPENAI:
            return _with_llm(
                OpenAILLM(model=mdl, api_key=key),
                f"LLM · OpenAI · {mdl or 'gpt-4o-mini'}",
            )
        if provider == LOCAL:
            url = base_url.strip() or DEFAULT_LOCAL_BASE_URL
            llm = LocalOpenAICompatLLM(base_url=url, model=mdl, api_key=key)
            return _with_llm(llm, f"LLM local · {mdl or 'tự dò từ server'}")
        if provider == HEURISTIC:
            return HeuristicExtractor(), KeywordInferrer(), "Heuristic offline"
        # AUTO — theo biến môi trường / .env
        llm = make_default_llm()
        if llm is not None:
            return _with_llm(llm, default_mode_label())
        return HeuristicExtractor(), KeywordInferrer(), "Heuristic offline"
    except Exception as exc:  # thiếu key / lỗi khởi tạo → fallback êm
        st.sidebar.error(f"Không khởi tạo được LLM ({exc}). Đang dùng Heuristic.")
        return HeuristicExtractor(), KeywordInferrer(), "Heuristic offline (fallback)"


st.set_page_config(page_title="Tư vấn xử phạt giao thông", page_icon="⚖️", layout="wide")

# ---- Sidebar cấu hình ----
st.sidebar.header("⚙️ Cấu hình bộ trích xuất")
provider = st.sidebar.selectbox(
    "Bộ trích xuất (NLU)", [AUTO, CLAUDE, OPENAI, LOCAL, HEURISTIC], index=0
)
api_key = ""
model = ""
base_url = ""
if provider in (CLAUDE, OPENAI):
    api_key = st.sidebar.text_input(
        "API key", type="password",
        help="Chỉ lưu trong phiên chạy này, không ghi ra file, không gửi lên chat.",
    )
    ph = "claude-haiku-4-5 (rẻ) / claude-opus-4-8" if provider == CLAUDE else "gpt-4o-mini"
    model = st.sidebar.text_input("Model (tùy chọn)", placeholder=ph)
elif provider == LOCAL:
    base_url = st.sidebar.text_input(
        "Base URL của server LLM",
        value=os.environ.get("TRAFFIC_ES_LOCAL_BASE_URL", ""),
        placeholder="https://xxx.trycloudflare.com  hoặc  http://localhost:8000/v1",
        help="URL do notebook Colab in ra (notebooks/colab_qwen_server.ipynb), "
        "hoặc server tương thích OpenAI chạy máy bạn (vLLM, Ollama, LM Studio).",
    )
    model = st.sidebar.text_input(
        "Model (để trống = tự dò)",
        placeholder="tự lấy từ /v1/models",
        help="Tên model tùy máy chủ đặt: vLLM theo --served-model-name (vd 'coder-7b'), "
        "Ollama theo tag. Để trống thì client tự hỏi server.",
    )
    if st.sidebar.button("Thử kết nối", use_container_width=True):
        try:
            ok, msg = LocalOpenAICompatLLM(
                base_url=base_url.strip() or DEFAULT_LOCAL_BASE_URL,
                model=model.strip() or None,
                timeout=20.0,
            ).health()
        except Exception as exc:
            ok, msg = False, str(exc)
        (st.sidebar.success if ok else st.sidebar.error)(msg)

extractor, inferrer, mode = build_extractor(provider, api_key, model, base_url)
svc = TrafficESService(get_reasoner(), NLUPipeline(extractor, inferrer=inferrer))

st.sidebar.markdown(f"**Chế độ hiện tại:** {mode}")

# ---- Nội dung chính ----
st.title("⚖️ Hệ thống chuyên gia tư vấn xử phạt vi phạm giao thông")
st.caption(
    "Mô tả tình huống bằng tiếng Việt — hệ suy diễn ra mức phạt và căn cứ pháp lý "
    "(Nghị định 168/2024). Có đồ thị Legal-Onto và chuỗi suy diễn dạng nodes/edges."
)

tab_tu_van, tab_kg = st.tabs(["💬 Tư vấn", "🕸️ Nodes graph (Legal-Onto)"])

with tab_kg:
    st.subheader("Knowledge Graph — Legal-Onto")
    st.markdown(
        "KB Legal-Onto vốn là các ngôi sao concept tách rời — UI nối chúng qua "
        "**Legal-Onto → nhóm → concept → keyphrase/fact**. "
        "Cạnh mang nguồn và độ tin (TF-IDF). Sau khi phân tích, concept khớp "
        "được tô đậm với cạnh `EXHIBITS`."
    )
    ans_for_kg = st.session_state.get("answer")
    matched = (ans_for_kg.nlu_meta.get("matched_concepts") if ans_for_kg else None) or []
    onto_graph = build_legal_onto_graph(get_concept_store(), get_kg(), matched)
    show_graph(onto_graph, height=620)
    with st.expander("Chú giải màu / quan hệ"):
        st.markdown(
            """
| Nhóm / cạnh | Ý nghĩa |
|---|---|
| Xanh ngọc / xanh đậm | Concept (theo `nhom`) |
| Cam | Keyphrase |
| Xanh dương | Fact (`MAPS_TO`) |
| `HAS_GROUP` / `HAS_CONCEPT` | Nối ontology → nhóm → concept (tránh cụm rời) |
| `HAS_KEYPHRASE` | Concept sở hữu cụm từ khóa |
| `EXHIBITS` | Concept được kích hoạt bởi câu hỏi (có độ tin) |
| `MAPS_TO` | Concept ánh xạ sang fact trong working memory |
"""
        )

with tab_tu_van:
    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("💬 Tình huống")
        text = st.text_area(
            "Nhập mô tả hiện trường:",
            "Tối qua nhậu xong tôi vẫn cầm lái con xe hơi về nhà, bị thổi ra 0,45 mg/l khí thở, "
            "lại còn quẹt trúng một xe máy.",
            height=140,
        )
        go = st.button("Phân tích", type="primary")

    if go and text.strip():
        with st.spinner("Đang phân tích…"):
            try:
                st.session_state["answer"] = svc.answer(text)
            except Exception as exc:  # LLM/mạng lỗi -> báo rõ, không crash
                st.error(f"Lỗi khi phân tích (có thể do LLM/mạng/hết quota): {exc}")
                st.stop()

    ans = st.session_state.get("answer")
    if ans is not None:
        # Hỏi bổ sung (hành vi / khung mức / loại xe) khi còn thiếu để suy diễn
        if ans.clarifications:
            with col1:
                q = ans.clarifications[0]
                st.info(q.prompt)
                labels = list(q.choices.values())
                values = list(q.choices.keys())
                picked_label = st.radio(
                    "Lựa chọn",
                    labels,
                    horizontal=len(labels) <= 3,
                    key=f"clarify_choice_{q.id}",
                )
                choice = values[labels.index(picked_label)]
                if st.button("Tiếp tục phân tích", type="primary", key=f"clarify_go_{q.id}"):
                    merged = apply_clarification(ans.facts, q, choice)
                    st.session_state["answer"] = svc.continue_with(merged, ans.nlu_meta)
                    st.rerun()

        ans = st.session_state["answer"]
        with col1:
            st.markdown(ans.explanation)
        with col2:
            st.subheader("🔎 Chi tiết phân tích")
            if ans.sample_problem is not None:
                p = ans.sample_problem
                with st.expander(f"🧩 Mẫu bài toán: {p.name}", expanded=True):
                    st.write("**Mục tiêu (Goal):**", p.goal)
                    st.write("**Lời giải mẫu (Sol):**")
                    st.markdown("\n".join(f"{i+1}. {s}" for i, s in enumerate(p.sol)))
            with st.expander("Facts đã trích", expanded=True):
                st.json(ans.facts)
            with st.expander("🕸️ Legal-Onto: concept khớp (question-graph)"):
                mc = ans.nlu_meta.get("matched_concepts") or []
                if mc:
                    for m in mc:
                        st.write(
                            f"- **{m['concept']}** (điểm {m['score']}) "
                            f"— khớp: {', '.join(m['keyphrases'])}"
                        )
                    added = ans.nlu_meta.get("kg_facts_added") or []
                    if added:
                        st.caption("Facts được KG bổ sung: " + ", ".join(added))
                else:
                    st.write("(không có concept nào khớp)")
            with st.expander("Chuỗi suy diễn (trace)"):
                st.code(ans.trace.render() or "(không có bước)")
            with st.expander("Tình tiết suy luận / cảnh báo"):
                st.write("Tình tiết:", ans.nlu_meta.get("inferred"))
                neg = ans.nlu_meta.get("negated_keyphrases") or []
                if neg:
                    st.caption("Cụm bị bỏ vì ở thể phủ định: " + ", ".join(neg))
                for w in ans.nlu_meta.get("warnings") or []:
                    st.warning(w)

        st.divider()
        st.subheader("🕸️ Nodes graph — chuỗi suy diễn tình huống")
        st.markdown(
            "Đồ thị con theo câu hỏi: **INPUT → concept → fact → Working Memory → "
            "RULE → META → kết luận**. Hover cạnh để xem nguồn và độ tin."
        )
        reason_graph = build_reasoning_graph(
            ans.facts,
            ans.trace,
            ans.nlu_meta,
            ket_qua_chi_tiet=ans.ket_qua.chi_tiet,
            store=get_concept_store(),
        )
        show_graph(reason_graph, height=520)
