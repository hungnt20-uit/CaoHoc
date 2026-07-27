from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

# cho phép chạy `streamlit run app/streamlit_app.py` từ gốc dự án
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from traffic_es.service import TrafficESService
from traffic_es.nlu.pipeline import NLUPipeline
from traffic_es.engine.reasoner import Reasoner
from traffic_es.nlu.extractor import HeuristicExtractor
from traffic_es.nlu.llm_extractor import LLMExtractor
from traffic_es.llm.providers import (
    make_default_llm,
    default_mode_label,
    OpenAILLM,
    AnthropicLLM,
)

RULES_DIR = Path(__file__).resolve().parent.parent / "traffic_es" / "knowledge" / "rules"

AUTO = "Tự động (theo .env)"
CLAUDE = "Anthropic (Claude)"
OPENAI = "OpenAI (GPT)"
HEURISTIC = "Heuristic (offline)"


@st.cache_resource
def get_reasoner() -> Reasoner:
    return Reasoner.from_rules_dir(RULES_DIR)


def build_extractor(provider: str, api_key: str, model: str):
    key = api_key.strip() or None
    mdl = model.strip() or None
    try:
        if provider == CLAUDE:
            return LLMExtractor(AnthropicLLM(model=mdl, api_key=key)), f"LLM · Anthropic · {mdl or 'claude-opus-4-8'}"
        if provider == OPENAI:
            return LLMExtractor(OpenAILLM(model=mdl, api_key=key)), f"LLM · OpenAI · {mdl or 'gpt-4o-mini'}"
        if provider == HEURISTIC:
            return HeuristicExtractor(), "Heuristic offline"
        # AUTO — theo biến môi trường / .env
        llm = make_default_llm()
        if llm is not None:
            return LLMExtractor(llm), default_mode_label()
        return HeuristicExtractor(), "Heuristic offline"
    except Exception as exc:  # thiếu key / lỗi khởi tạo → fallback êm
        st.sidebar.error(f"Không khởi tạo được LLM ({exc}). Đang dùng Heuristic.")
        return HeuristicExtractor(), "Heuristic offline (fallback)"


st.set_page_config(page_title="Tư vấn xử phạt giao thông", page_icon="⚖️", layout="wide")

# ---- Sidebar cấu hình ----
st.sidebar.header("⚙️ Cấu hình bộ trích xuất")
provider = st.sidebar.selectbox(
    "Bộ trích xuất (NLU)", [AUTO, CLAUDE, OPENAI, HEURISTIC], index=0
)
api_key = ""
model = ""
if provider in (CLAUDE, OPENAI):
    api_key = st.sidebar.text_input(
        "API key", type="password",
        help="Chỉ lưu trong phiên chạy này, không ghi ra file, không gửi lên chat.",
    )
    ph = "claude-haiku-4-5 (rẻ) / claude-opus-4-8" if provider == CLAUDE else "gpt-4o-mini"
    model = st.sidebar.text_input("Model (tùy chọn)", placeholder=ph)

extractor, mode = build_extractor(provider, api_key, model)
svc = TrafficESService(get_reasoner(), NLUPipeline(extractor))

st.sidebar.markdown(f"**Chế độ hiện tại:** {mode}")
st.sidebar.caption(
    "LLM hiểu câu phức tạp/khẩu ngữ tốt hơn; Heuristic chạy offline, miễn phí. "
    "Có thể đặt key trong `.env` để dùng chế độ Tự động."
)

# ---- Nội dung chính ----
st.title("⚖️ Hệ thống chuyên gia tư vấn xử phạt vi phạm giao thông")
st.caption(
    "Mô tả tình huống bằng tiếng Việt — hệ suy diễn ra mức phạt và căn cứ pháp lý "
    "(Nghị định 168/2024)."
)

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
            ans = svc.answer(text)
        except Exception as exc:  # LLM/mạng lỗi -> báo rõ, không crash
            st.error(f"Lỗi khi phân tích (có thể do LLM/mạng/hết quota): {exc}")
            st.stop()
    with col1:
        st.markdown(ans.explanation)
    with col2:
        st.subheader("🔎 Hộp kính suy diễn")
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
            st.write("Cảnh báo:", ans.nlu_meta.get("warnings"))
