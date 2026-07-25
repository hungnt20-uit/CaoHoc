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
from traffic_es.llm.providers import make_default_llm, default_mode_label

RULES_DIR = Path(__file__).resolve().parent.parent / "traffic_es" / "knowledge" / "rules"


@st.cache_resource
def build():
    llm = make_default_llm()
    extractor = LLMExtractor(llm) if llm is not None else HeuristicExtractor()
    mode = default_mode_label()
    svc = TrafficESService(Reasoner.from_rules_dir(RULES_DIR), NLUPipeline(extractor))
    return svc, mode


st.set_page_config(page_title="Tư vấn xử phạt giao thông", page_icon="⚖️", layout="wide")
svc, mode = build()

st.title("⚖️ Hệ thống chuyên gia tư vấn xử phạt vi phạm giao thông")
st.caption(
    "Mô tả tình huống bằng tiếng Việt — hệ suy diễn ra mức phạt và căn cứ pháp lý "
    "(Nghị định 168/2024)."
)
st.sidebar.markdown(f"**Chế độ trích xuất:** {mode}")
st.sidebar.caption("Đặt biến môi trường `OPENAI_API_KEY` để bật chế độ LLM cho câu phức tạp/khẩu ngữ.")

col1, col2 = st.columns([1, 1])
with col1:
    st.subheader("💬 Tình huống")
    text = st.text_area(
        "Nhập mô tả hiện trường:",
        "Tôi lái ô tô, thổi nồng độ cồn 0.42 mg/l, rồi đâm vào một xe máy.",
        height=140,
    )
    go = st.button("Phân tích", type="primary")

if go and text.strip():
    try:
        ans = svc.answer(text)
    except Exception as exc:  # LLM/mạng lỗi -> báo rõ, không crash
        st.error(f"Lỗi khi phân tích (có thể do LLM/mạng): {exc}")
        st.stop()
    with col1:
        st.markdown(ans.explanation)
    with col2:
        st.subheader("🔎 Hộp kính suy diễn")
        with st.expander("Facts đã trích", expanded=True):
            st.json(ans.facts)
        with st.expander("Chuỗi suy diễn (trace)"):
            st.code(ans.trace.render() or "(không có bước)")
        with st.expander("Tình tiết suy luận / cảnh báo"):
            st.write("Tình tiết:", ans.nlu_meta.get("inferred"))
            st.write("Cảnh báo:", ans.nlu_meta.get("warnings"))
