# Plan 6 — Hoàn thiện LLMExtractor (LLM thật)

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Steps dùng checkbox `- [ ]`.

**Goal:** Cho chatbot hiểu câu tiếng Việt phức tạp/khẩu ngữ qua **LLM thật** (OpenAI, mở rộng Claude/Gemini), thay bộ trích heuristic khi có API key — kèm parse bền vững, grounding chống ảo giác, và fallback êm khi không có key/lỗi mạng.

**Architecture:** `traffic_es/llm/providers.py` (OpenAILLM + `make_default_llm()` chọn theo env) → `LLMExtractor` (Plan 3) được làm bền: bóc code-fence, parse lỗi → rỗng, **grounding** output, ép kiểu số. `app/streamlit_app.py` dùng `make_default_llm()` + hiển thị chế độ rõ + fallback. `scripts/build_kb.py` tái dùng provider (DRY). Test bằng `FakeLLM`, không tốn API.

**Tech Stack:** thêm `openai>=1.0` vào requirements. pytest với FakeLLM.

---

### Task 0: Provider LLM dùng chung + chọn theo môi trường

**Files:** Modify `requirements.txt` · Create `traffic_es/llm/providers.py` · Test `tests/test_llm_providers.py`

- [ ] **Step 1: Thêm `openai>=1.0` vào requirements.txt** và cài: `.venv/bin/pip install "openai>=1.0"`

- [ ] **Step 2: Viết test thất bại**

```python
# tests/test_llm_providers.py
import traffic_es.llm.providers as prov

def test_make_default_none_without_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert prov.make_default_llm() is None

def test_make_default_returns_client_with_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    # không gọi API thật: chỉ kiểm tra tạo được đối tượng có .complete
    llm = prov.make_default_llm()
    assert llm is not None and hasattr(llm, "complete")
```

- [ ] **Step 3: Cài đặt**

```python
# traffic_es/llm/providers.py
from __future__ import annotations
import os
from typing import Optional
from traffic_es.llm.client import LLMClient


class OpenAILLM(LLMClient):
    def __init__(self, model: Optional[str] = None, api_key: Optional[str] = None):
        from openai import OpenAI  # import trễ để test/heuristic không cần openai
        self.model = model or os.environ.get("TRAFFIC_ES_LLM_MODEL", "gpt-4o-mini")
        self.client = OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"))

    def complete(self, system: str, user: str, **kw) -> str:
        r = self.client.chat.completions.create(
            model=self.model, temperature=0,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
            response_format={"type": "json_object"},
        )
        return r.choices[0].message.content or ""


def make_default_llm() -> Optional[LLMClient]:
    """LLMClient theo môi trường; None nếu không có key (→ dùng heuristic)."""
    if not os.environ.get("OPENAI_API_KEY"):
        return None
    try:
        return OpenAILLM()
    except Exception:
        return None
```

> Ghi chú: `test_make_default_returns_client_with_key` cần `openai` đã cài (Step 1). `OpenAI(api_key=...)` không gọi mạng khi khởi tạo.

- [ ] **Step 4: Chạy test (PASS)** · **Step 5: Commit**
```bash
git add requirements.txt traffic_es/llm/providers.py tests/test_llm_providers.py
git commit -m "feat(llm): Task 0 — provider OpenAI dùng chung + make_default_llm theo env"
```

---

### Task 1: Làm bền LLMExtractor (fence, grounding, ép kiểu)

**Files:** Modify `traffic_es/nlu/llm_extractor.py` · Test `tests/test_llm_extractor_robust.py`

- [ ] **Step 1: Viết test thất bại**

```python
# tests/test_llm_extractor_robust.py
from traffic_es.llm.client import FakeLLM
from traffic_es.nlu.llm_extractor import LLMExtractor

def test_strips_code_fence_and_grounds():
    raw = '```json\n{"facts": {"phuongtien.loai": "o_to", "chiso.nongDoCon_khiTho": "0.42", "foo.bar": 1}, "raw_events": ["đâm xe"]}\n```'
    llm = FakeLLM(responses={"cồn": raw})
    facts, ev, events = LLMExtractor(llm).extract("lái ô tô cồn 0.42")
    assert facts["phuongtien.loai"] == "o_to"
    assert facts["chiso.nongDoCon_khiTho"] == 0.42   # ép chuỗi -> số
    assert "foo.bar" not in facts                     # grounding loại node lạ
    assert "đâm xe" in events

def test_invalid_json_returns_empty():
    llm = FakeLLM(responses={"x": "không phải JSON gì cả"})
    facts, ev, events = LLMExtractor(llm).extract("x")
    assert facts == {} and events == []
```

- [ ] **Step 2: Chạy test (FAIL)**

- [ ] **Step 3: Viết lại `llm_extractor.py`**

```python
# traffic_es/nlu/llm_extractor.py
from __future__ import annotations
import json
import re
from typing import Dict, List, Tuple

from traffic_es.llm.client import LLMClient
from traffic_es.nlu.grounding import ground

SYSTEM = (
    "Bạn trích thông tin hiện trường giao thông từ câu tiếng Việt thành JSON gồm 2 khóa: "
    "'facts' (map node ontology hợp lệ) và 'raw_events' (mảng câu sự kiện thô). "
    "Node hợp lệ: phuongtien.loai ('o_to'|'xe_may'); chiso.nongDoCon_khiTho (mg/l); "
    "chiso.nongDoCon_mau (mg/100ml); chiso.tocDo; chiso.tocDoGioiHan (km/h); "
    "boicanh.khuVuc ('khu_dan_cu'); nguoi.khong_mu_bao_hiem/khong_day_an_toan (bool); "
    "nguoi.coGPLX (bool); hanhvi.vuot_den_do (bool). "
    "Sự kiện va chạm/tái phạm/bỏ chạy để trong raw_events. TUYỆT ĐỐI không bịa số. "
    "Chỉ trả JSON."
)

_FENCE = re.compile(r"^```[a-zA-Z]*\n?|\n?```$")


def _parse(raw: str) -> dict:
    s = raw.strip()
    s = _FENCE.sub("", s).strip()
    try:
        return json.loads(s)
    except (json.JSONDecodeError, TypeError):
        return {}


def _coerce(facts: Dict[str, object]) -> Dict[str, object]:
    out: Dict[str, object] = {}
    for k, v in facts.items():
        if isinstance(v, str):
            low = v.strip().lower()
            if low in ("true", "false"):
                out[k] = low == "true"
                continue
            try:
                out[k] = float(v)
                continue
            except ValueError:
                pass
        out[k] = v
    return out


class LLMExtractor:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    def extract(self, text: str) -> Tuple[Dict[str, object], Dict[str, str], List[str]]:
        data = _parse(self.llm.complete(system=SYSTEM, user=text))
        if not data:
            return {}, {}, []
        facts = _coerce(data.get("facts", {}) or {})
        facts, _warns = ground(facts)      # grounding chống ảo giác/node lạ
        return facts, {}, list(data.get("raw_events", []) or [])
```

- [ ] **Step 4: Chạy test (PASS) + toàn bộ suite** · **Step 5: Commit**
```bash
git add traffic_es/nlu/llm_extractor.py tests/test_llm_extractor_robust.py
git commit -m "feat(nlu): Task 1 — LLMExtractor bền (bóc fence, grounding, ép kiểu số/bool)"
```

---

### Task 2: Nối provider vào Streamlit + build_kb (DRY) + fallback êm

**Files:** Modify `app/streamlit_app.py`, `scripts/build_kb.py`

- [ ] **Step 1: Cập nhật `scripts/build_kb.py`** — xóa lớp `OpenAILLM` nội bộ, import từ provider chung:
Thay `class OpenAILLM(...): ...` và import cũ bằng:
```python
from traffic_es.llm.providers import OpenAILLM
```
(giữ nguyên phần dùng `CachingLLM(OpenAILLM())`.)

- [ ] **Step 2: Viết lại `app/streamlit_app.py`** — dùng `make_default_llm`, chế độ rõ, fallback êm, bỏ print debug:

```python
from __future__ import annotations
import sys
from pathlib import Path
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from traffic_es.service import TrafficESService
from traffic_es.nlu.pipeline import NLUPipeline
from traffic_es.engine.reasoner import Reasoner
from traffic_es.nlu.extractor import HeuristicExtractor
from traffic_es.nlu.llm_extractor import LLMExtractor
from traffic_es.llm.providers import make_default_llm

RULES_DIR = Path(__file__).resolve().parent.parent / "traffic_es" / "knowledge" / "rules"


@st.cache_resource
def build():
    llm = make_default_llm()
    if llm is not None:
        extractor, mode = LLMExtractor(llm), "LLM (OpenAI)"
    else:
        extractor, mode = HeuristicExtractor(), "Heuristic offline"
    svc = TrafficESService(Reasoner.from_rules_dir(RULES_DIR), NLUPipeline(extractor))
    return svc, mode


st.set_page_config(page_title="Tư vấn xử phạt giao thông", page_icon="⚖️", layout="wide")
svc, mode = build()

st.title("⚖️ Hệ thống chuyên gia tư vấn xử phạt vi phạm giao thông")
st.caption(f"Mô tả tình huống bằng tiếng Việt — suy diễn mức phạt & căn cứ pháp lý (NĐ 168/2024).")
st.sidebar.markdown(f"**Chế độ trích xuất:** {mode}")
st.sidebar.caption("Đặt biến môi trường `OPENAI_API_KEY` để bật chế độ LLM cho câu phức tạp.")

col1, col2 = st.columns([1, 1])
with col1:
    st.subheader("💬 Tình huống")
    text = st.text_area("Nhập mô tả hiện trường:",
                        "Tôi lái ô tô, thổi nồng độ cồn 0.42 mg/l, rồi đâm vào một xe máy.",
                        height=140)
    go = st.button("Phân tích", type="primary")

if go and text.strip():
    try:
        ans = svc.answer(text)
    except Exception as exc:
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
```

- [ ] **Step 3: Chạy toàn bộ suite (PASS)** + smoke import app:
`.venv/bin/python -c "import ast; ast.parse(open('app/streamlit_app.py').read()); print('app OK')"`

- [ ] **Step 4: Commit**
```bash
git add app/streamlit_app.py scripts/build_kb.py
git commit -m "feat(app): Task 2 — Streamlit dùng provider chung + chế độ rõ + fallback êm"
```

---

## Kết quả sau Plan 6
Chatbot tự dùng **LLM thật** khi có `OPENAI_API_KEY` (hiểu câu phức tạp/khẩu ngữ), có parse bền + grounding chống ảo giác, fallback heuristic khi không có key — provider dùng chung cho app lẫn build_kb. Test đầy đủ bằng FakeLLM (không tốn API).
