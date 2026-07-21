# Plan 3 — NLU + Chatbot (sản phẩm chạy đầu-cuối)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Từ mô tả tiếng Việt tự nhiên → trích Facts (ánh xạ ontology) → suy luận tình tiết gián tiếp (Bài toán 1) → engine Plan 1 → giải thích tiếng Việt → **chatbot Streamlit chạy đầu-cuối**. Chạy được **offline** (bộ trích heuristic) và cắm LLM thật khi có API key.

**Architecture:** `nlu/` (normalize → extractor → grounding → semantic_infer → pipeline) sinh Facts phẳng cho `Reasoner` (Plan 1); `explain/generator.py` biến Trace thành văn tiếng Việt; `service.py` nối NLU + engine + explain; `app/streamlit_app.py` là UI. Extractor có 2 hiện thực: `HeuristicExtractor` (regex, offline) và `LLMExtractor` (dùng `LLMClient` Plan 2). Tất cả test bằng heuristic/mock — không cần API.

**Tech Stack:** Python (venv sẵn), `pydantic`, `pytest`, `streamlit` (thêm mới). Tái dùng `traffic_es.engine`, `traffic_es.llm`, `traffic_es.knowledge`.

---

### Task 0: Chuẩn hóa văn bản tiếng Việt

**Files:** Create `traffic_es/nlu/__init__.py`, `traffic_es/nlu/normalize.py` · Test `tests/test_normalize.py`

- [ ] **Step 1: Viết test thất bại**

```python
# tests/test_normalize.py
from traffic_es.nlu.normalize import normalize

def test_decimal_comma_to_dot():
    assert "0.42" in normalize("nồng độ cồn 0,42 mg/l")

def test_expand_abbreviations():
    out = normalize("nđc 0.3 trong kdc")
    assert "nồng độ cồn" in out and "khu dân cư" in out

def test_lowercase_preserved_content():
    assert "ô tô" in normalize("Tôi lái Ô Tô").lower()
```

- [ ] **Step 2: Chạy test (FAIL)** — `.venv/bin/python -m pytest tests/test_normalize.py -q`

- [ ] **Step 3: Cài đặt**

```python
# traffic_es/nlu/normalize.py
from __future__ import annotations
import re

_ABBR = {
    r"\bnđc\b": "nồng độ cồn",
    r"\bkdc\b": "khu dân cư",
    r"\bgplx\b": "giấy phép lái xe",
    r"\btncgt\b": "tai nạn giao thông",
}

def normalize(text: str) -> str:
    t = text.strip()
    # 0,42 -> 0.42 (số thập phân), giữ nguyên dấu phẩy ngăn cách khác
    t = re.sub(r"(?<=\d),(?=\d)", ".", t)
    low = t.lower()
    for pat, full in _ABBR.items():
        low = re.sub(pat, full, low)
    return low
```

- [ ] **Step 4: Chạy test (PASS)** · **Step 5: Commit**
```bash
git add traffic_es/nlu/__init__.py traffic_es/nlu/normalize.py tests/test_normalize.py
git commit -m "feat(nlu): Task 0 — chuẩn hóa văn bản tiếng Việt (số, viết tắt)"
```

---

### Task 1: Bộ trích Facts — HeuristicExtractor (offline)

**Files:** Create `traffic_es/nlu/extractor.py` · Test `tests/test_extractor.py`

Trả về `(facts: dict, evidences: dict, raw_events: list)`. Nhận diện: loại xe, nồng độ cồn (mg/l khí thở), tốc độ & giới hạn, khu vực; câu sự kiện thô cho Bài toán 1.

- [ ] **Step 1: Viết test thất bại**

```python
# tests/test_extractor.py
from traffic_es.nlu.extractor import HeuristicExtractor

def test_extract_oto_con():
    ex = HeuristicExtractor()
    facts, ev, raw = ex.extract("tôi lái ô tô, thổi nồng độ cồn 0.42 mg/l")
    assert facts["phuongtien.loai"] == "o_to"
    assert facts["chiso.nongDoCon_khiTho"] == 0.42

def test_extract_xemay_and_event():
    ex = HeuristicExtractor()
    facts, ev, raw = ex.extract("chạy xe máy sau khi uống rượu rồi đâm vào người đi bộ")
    assert facts["phuongtien.loai"] == "xe_may"
    assert any("đâm" in r for r in raw)
```

- [ ] **Step 2: Chạy test (FAIL)**

- [ ] **Step 3: Cài đặt**

```python
# traffic_es/nlu/extractor.py
from __future__ import annotations
import re
from typing import Dict, List, Protocol, Tuple

Facts = Dict[str, object]


class Extractor(Protocol):
    def extract(self, text: str) -> Tuple[Facts, Dict[str, str], List[str]]: ...


_XE = [
    ("o_to", [r"ô ?tô", r"oto", r"xe hơi", r"xe con"]),
    ("xe_may", [r"xe máy", r"mô ?tô", r"xe gắn máy"]),
]
_EVENT_KW = ["đâm", "va chạm", "quẹt", "tông", "tai nạn", "tái phạm", "bỏ chạy", "không chấp hành"]


class HeuristicExtractor:
    """Trích Facts bằng regex — chạy offline, không cần LLM."""

    def extract(self, text: str) -> Tuple[Facts, Dict[str, str], List[str]]:
        t = text.lower()
        facts: Facts = {}
        ev: Dict[str, str] = {}
        # loại xe
        for loai, pats in _XE:
            for p in pats:
                m = re.search(p, t)
                if m:
                    facts["phuongtien.loai"] = loai
                    ev["phuongtien.loai"] = m.group(0)
                    break
            if "phuongtien.loai" in facts:
                break
        # nồng độ cồn (mg/l khí thở)
        m = re.search(r"(?:nồng độ cồn|cồn)[^0-9]{0,20}(\d+(?:\.\d+)?)", t)
        if m:
            facts["chiso.nongDoCon_khiTho"] = float(m.group(1))
            ev["chiso.nongDoCon_khiTho"] = m.group(0)
        # tốc độ
        m = re.search(r"(?:chạy|tốc độ)[^0-9]{0,10}(\d+)\s*(?:km|km/h)", t)
        if m:
            facts["chiso.tocDo"] = float(m.group(1))
            ev["chiso.tocDo"] = m.group(0)
        m = re.search(r"(?:giới hạn|cho phép)[^0-9]{0,10}(\d+)", t)
        if m:
            facts["chiso.tocDoGioiHan"] = float(m.group(1))
        # khu vực
        if "khu dân cư" in t:
            facts["boicanh.khuVuc"] = "khu_dan_cu"
            ev["boicanh.khuVuc"] = "khu dân cư"
        # sự kiện thô cho Bài toán 1
        raw = [seg.strip() for seg in re.split(r"[.,;]| rồi | và ", text)
               if any(kw in seg.lower() for kw in _EVENT_KW)]
        return facts, ev, raw
```

- [ ] **Step 4: Chạy test (PASS)** · **Step 5: Commit**
```bash
git add traffic_es/nlu/extractor.py tests/test_extractor.py
git commit -m "feat(nlu): Task 1 — HeuristicExtractor trích Facts offline (Bài toán 2)"
```

---

### Task 2: Grounding — kiểm chứng Facts theo ontology

**Files:** Create `traffic_es/nlu/grounding.py` · Test `tests/test_grounding.py`

- [ ] **Step 1: Viết test thất bại**

```python
# tests/test_grounding.py
from traffic_es.nlu.grounding import ground

def test_keeps_known_and_drops_unknown():
    facts = {"phuongtien.loai": "o_to", "chiso.nongDoCon_khiTho": 0.4, "foo.bar": 1}
    clean, warns = ground(facts)
    assert "phuongtien.loai" in clean and "foo.bar" not in clean
    assert any("foo.bar" in w for w in warns)

def test_flags_out_of_range():
    clean, warns = ground({"chiso.nongDoCon_khiTho": 99})
    assert "chiso.nongDoCon_khiTho" not in clean
    assert any("miền" in w for w in warns)
```

- [ ] **Step 2: Chạy test (FAIL)**

- [ ] **Step 3: Cài đặt**

```python
# traffic_es/nlu/grounding.py
from __future__ import annotations
from typing import Dict, List, Tuple

_KNOWN_PREFIX = ("phuongtien.", "nguoi.", "chiso.", "boicanh.", "tinhtiet.")
_RANGES = {
    "chiso.nongDoCon_khiTho": (0.0, 5.0),
    "chiso.tocDo": (0.0, 300.0),
    "chiso.tocDoGioiHan": (0.0, 150.0),
}

def ground(facts: Dict[str, object]) -> Tuple[Dict[str, object], List[str]]:
    clean: Dict[str, object] = {}
    warns: List[str] = []
    for k, v in facts.items():
        if not k.startswith(_KNOWN_PREFIX):
            warns.append(f"Bỏ node lạ ngoài ontology: {k}")
            continue
        if k in _RANGES and isinstance(v, (int, float)):
            lo, hi = _RANGES[k]
            if not (lo <= v <= hi):
                warns.append(f"{k}={v} ngoài miền [{lo},{hi}] → loại")
                continue
        clean[k] = v
    return clean, warns
```

- [ ] **Step 4: Chạy test (PASS)** · **Step 5: Commit**
```bash
git add traffic_es/nlu/grounding.py tests/test_grounding.py
git commit -m "feat(nlu): Task 2 — grounding kiểm chứng Facts theo ontology"
```

---

### Task 3: Bài toán 1 — Suy luận tình tiết gián tiếp

**Files:** Create `traffic_es/nlu/semantic_infer.py` · Test `tests/test_semantic_infer.py`

- [ ] **Step 1: Viết test thất bại**

```python
# tests/test_semantic_infer.py
from traffic_es.nlu.semantic_infer import infer_circumstances

def test_infer_tai_nan():
    inf = infer_circumstances(["đâm vào người đi bộ"])
    assert any(i["fact"] == "tinhtiet.gay_tai_nan" and i["value"] is True for i in inf)

def test_infer_tai_pham():
    inf = infer_circumstances(["đây là lần tái phạm"])
    assert any(i["fact"] == "tinhtiet.tai_pham" for i in inf)

def test_no_event_no_infer():
    assert infer_circumstances(["trời mưa nhẹ"]) == []
```

- [ ] **Step 2: Chạy test (FAIL)**

- [ ] **Step 3: Cài đặt**

```python
# traffic_es/nlu/semantic_infer.py
from __future__ import annotations
from typing import Dict, List

# closed-vocabulary: chỉ suy ra tình tiết đã định nghĩa
_RULES = [
    ("tinhtiet.gay_tai_nan", ["đâm", "va chạm", "quẹt", "tông", "tai nạn"],
     "va chạm/gây thiệt hại cho người hoặc phương tiện khác"),
    ("tinhtiet.tai_pham", ["tái phạm", "nhiều lần", "lần thứ hai"],
     "hành vi lặp lại"),
    ("tinhtiet.khong_chap_hanh", ["bỏ chạy", "không chấp hành", "chống đối"],
     "không chấp hành yêu cầu của người thi hành công vụ"),
]

def infer_circumstances(raw_events: List[str]) -> List[Dict[str, object]]:
    joined = " ".join(raw_events).lower()
    out: List[Dict[str, object]] = []
    for fact, kws, ly_do in _RULES:
        hit = next((kw for kw in kws if kw in joined), None)
        if hit:
            out.append({"fact": fact, "value": True, "confidence": 0.9,
                        "ly_do": ly_do, "nguon": hit})
    return out
```

- [ ] **Step 4: Chạy test (PASS)** · **Step 5: Commit**
```bash
git add traffic_es/nlu/semantic_infer.py tests/test_semantic_infer.py
git commit -m "feat(nlu): Task 3 — suy luận tình tiết gián tiếp (Bài toán 1, closed-vocab)"
```

---

### Task 4: NLU pipeline (điều phối)

**Files:** Create `traffic_es/nlu/pipeline.py` · Test `tests/test_nlu_pipeline.py`

- [ ] **Step 1: Viết test thất bại**

```python
# tests/test_nlu_pipeline.py
from traffic_es.nlu.pipeline import NLUPipeline

def test_pipeline_end_to_end_facts():
    facts, meta = NLUPipeline().run("Lái ô tô, nồng độ cồn 0.42, rồi đâm vào xe máy")
    assert facts["phuongtien.loai"] == "o_to"
    assert facts["chiso.nongDoCon_khiTho"] == 0.42
    assert facts["tinhtiet.gay_tai_nan"] is True
    assert "evidences" in meta and "inferred" in meta
```

- [ ] **Step 2: Chạy test (FAIL)**

- [ ] **Step 3: Cài đặt**

```python
# traffic_es/nlu/pipeline.py
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
        meta = {"normalized": norm, "evidences": ev, "raw_events": raw,
                "inferred": inferred, "warnings": warns}
        return clean, meta
```

- [ ] **Step 4: Chạy test (PASS)** · **Step 5: Commit**
```bash
git add traffic_es/nlu/pipeline.py tests/test_nlu_pipeline.py
git commit -m "feat(nlu): Task 4 — NLU pipeline (normalize→extract→infer→ground)"
```

---

### Task 5: Explanation generator (Trace → văn tiếng Việt)

**Files:** Create `traffic_es/explain/__init__.py`, `traffic_es/explain/generator.py` · Test `tests/test_explain.py`

- [ ] **Step 1: Viết test thất bại**

```python
# tests/test_explain.py
from pathlib import Path
from traffic_es.engine.reasoner import Reasoner
from traffic_es.explain.generator import render_explanation

def test_explanation_mentions_cancu_and_total():
    r = Reasoner.from_rules_dir(Path("traffic_es/knowledge/rules"))
    res = r.infer({"phuongtien.loai": "o_to", "chiso.nongDoCon_khiTho": 0.42,
                   "tinhtiet.gay_tai_nan": True})
    text = render_explanation(res.trace, res.ket_qua)
    assert "Điều 6" in text
    assert "40.000.000" in text
    assert "tước" in text.lower()
```

- [ ] **Step 2: Chạy test (FAIL)**

- [ ] **Step 3: Cài đặt**

```python
# traffic_es/explain/generator.py
from __future__ import annotations
from traffic_es.engine.trace import Trace
from traffic_es.engine.penalty import KetQua


def _tien(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def render_explanation(trace: Trace, ket_qua: KetQua) -> str:
    lines = ["**Phân tích hành vi & căn cứ pháp lý:**"]
    if not ket_qua.chi_tiet:
        return "Không phát hiện hành vi vi phạm từ thông tin cung cấp."
    has_meta = any(s.kind == "META" for s in trace.steps)
    for i, d in enumerate(ket_qua.chi_tiet, 1):
        lines.append(
            f"{i}. **{d.hanh_vi}**\n"
            f"   - Căn cứ: {d.can_cu}\n"
            f"   - Tiền phạt: {_tien(d.tien)}đ · Hình phạt bổ sung: {d.phat_bo_sung}"
        )
    if has_meta:
        lines.append("> Có **tình tiết tăng nặng** → áp mức tiền tối đa của khung.")
    tong = f"\n**Tổng hợp:** {len(ket_qua.chi_tiet)} lỗi · tổng tiền **{_tien(ket_qua.tong_tien)}đ**"
    if ket_qua.tuoc_gplx_thang_max:
        tong += f" · tước GPLX tối đa **{ket_qua.tuoc_gplx_thang_max} tháng**"
    lines.append(tong)
    return "\n".join(lines)
```

- [ ] **Step 4: Chạy test (PASS)** · **Step 5: Commit**
```bash
git add traffic_es/explain tests/test_explain.py
git commit -m "feat(explain): Task 5 — sinh giải thích tiếng Việt từ Trace"
```

---

### Task 6: Service end-to-end (NL → kết quả + giải thích)

**Files:** Create `traffic_es/service.py` · Test `tests/test_service.py`

- [ ] **Step 1: Viết test thất bại**

```python
# tests/test_service.py
from pathlib import Path
from traffic_es.service import TrafficESService

def test_service_answers_full():
    svc = TrafficESService.default(Path("traffic_es/knowledge/rules"))
    ans = svc.answer("Tôi lái ô tô, nồng độ cồn 0.42 mg/l, rồi đâm vào một xe máy")
    assert ans.ket_qua.tong_tien == 40000000     # tai nạn -> max khung 30-40
    assert "Điều 6" in ans.explanation
    assert ans.facts["tinhtiet.gay_tai_nan"] is True

def test_service_no_violation():
    svc = TrafficESService.default(Path("traffic_es/knowledge/rules"))
    ans = svc.answer("Tôi lái ô tô bình thường, không uống rượu")
    assert ans.ket_qua.tong_tien == 0
```

- [ ] **Step 2: Chạy test (FAIL)**

- [ ] **Step 3: Cài đặt**

```python
# traffic_es/service.py
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

from traffic_es.engine.reasoner import Reasoner, InferResult
from traffic_es.nlu.pipeline import NLUPipeline
from traffic_es.explain.generator import render_explanation
from traffic_es.engine.penalty import KetQua
from traffic_es.engine.trace import Trace


@dataclass
class Answer:
    ket_qua: KetQua
    trace: Trace
    explanation: str
    facts: Dict[str, Any]
    nlu_meta: Dict[str, Any]


class TrafficESService:
    def __init__(self, reasoner: Reasoner, nlu: NLUPipeline):
        self.reasoner = reasoner
        self.nlu = nlu

    @classmethod
    def default(cls, rules_dir: Path) -> "TrafficESService":
        return cls(Reasoner.from_rules_dir(rules_dir), NLUPipeline())

    def answer(self, text: str) -> Answer:
        facts, meta = self.nlu.run(text)
        res: InferResult = self.reasoner.infer(facts)
        explanation = render_explanation(res.trace, res.ket_qua)
        return Answer(res.ket_qua, res.trace, explanation, facts, meta)
```

- [ ] **Step 4: Chạy test (PASS) + toàn bộ suite** · **Step 5: Commit**
```bash
git add traffic_es/service.py tests/test_service.py
git commit -m "feat: Task 6 — TrafficESService nối NLU + engine + giải thích (end-to-end)"
```

---

### Task 7: Chatbot Streamlit + provider LLM tùy chọn

**Files:** Create `app/streamlit_app.py`, `traffic_es/nlu/llm_extractor.py` · Update `requirements.txt` (thêm `streamlit`) · Test `tests/test_llm_extractor.py`

`LLMExtractor` dùng `LLMClient` (Plan 2) để trích Facts JSON; test bằng `FakeLLM`. App mặc định `HeuristicExtractor` (offline); nếu có `OPENAI_API_KEY` thì dùng LLM.

- [ ] **Step 1: Viết test thất bại (LLMExtractor)**

```python
# tests/test_llm_extractor.py
import json
from traffic_es.llm.client import FakeLLM
from traffic_es.nlu.llm_extractor import LLMExtractor

def test_llm_extractor_maps_facts():
    llm = FakeLLM(responses={"ô tô": json.dumps({
        "facts": {"phuongtien.loai": "o_to", "chiso.nongDoCon_khiTho": 0.42},
        "raw_events": ["đâm vào xe máy"]})})
    facts, ev, raw = LLMExtractor(llm).extract("lái ô tô cồn 0.42 đâm vào xe máy")
    assert facts["phuongtien.loai"] == "o_to"
    assert "đâm vào xe máy" in raw
```

- [ ] **Step 2: Chạy test (FAIL)**

- [ ] **Step 3a: Cài đặt LLMExtractor**

```python
# traffic_es/nlu/llm_extractor.py
from __future__ import annotations
import json
from typing import Dict, List, Tuple

from traffic_es.llm.client import LLMClient

SYSTEM = (
    "Trích thông tin hiện trường giao thông thành JSON gồm 'facts' (ánh xạ node ontology: "
    "phuongtien.loai [o_to|xe_may], chiso.nongDoCon_khiTho, chiso.tocDo, chiso.tocDoGioiHan, "
    "boicanh.khuVuc) và 'raw_events' (danh sách câu sự kiện thô như va chạm/tái phạm). "
    "Chỉ dùng node hợp lệ, không bịa số."
)


class LLMExtractor:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    def extract(self, text: str) -> Tuple[Dict[str, object], Dict[str, str], List[str]]:
        raw = self.llm.complete(system=SYSTEM, user=text)
        if not raw.strip():
            return {}, {}, []
        data = json.loads(raw)
        return data.get("facts", {}), {}, data.get("raw_events", [])
```

- [ ] **Step 3b: Cập nhật requirements.txt** — thêm dòng `streamlit>=1.36`

- [ ] **Step 3c: Cài đặt app Streamlit**

```python
# app/streamlit_app.py
from __future__ import annotations
import os
from pathlib import Path
import streamlit as st

from traffic_es.service import TrafficESService
from traffic_es.nlu.pipeline import NLUPipeline
from traffic_es.engine.reasoner import Reasoner
from traffic_es.nlu.extractor import HeuristicExtractor

RULES_DIR = Path(__file__).resolve().parent.parent / "traffic_es" / "knowledge" / "rules"


@st.cache_resource
def get_service() -> TrafficESService:
    extractor = HeuristicExtractor()
    if os.environ.get("OPENAI_API_KEY"):
        try:
            from traffic_es.nlu.llm_extractor import LLMExtractor
            from scripts.build_kb import OpenAILLM  # tái dùng provider
            extractor = LLMExtractor(OpenAILLM())
        except Exception:
            extractor = HeuristicExtractor()
    return TrafficESService(Reasoner.from_rules_dir(RULES_DIR), NLUPipeline(extractor))


st.set_page_config(page_title="Tư vấn xử phạt giao thông", page_icon="⚖️", layout="wide")
st.title("⚖️ Hệ chuyên gia tư vấn xử phạt vi phạm giao thông")
st.caption("Mô tả tình huống bằng tiếng Việt — hệ suy diễn ra mức phạt và căn cứ pháp lý.")

svc = get_service()
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("💬 Tình huống")
    text = st.text_area("Nhập mô tả hiện trường:",
                        "Tôi lái ô tô, thổi nồng độ cồn 0.42 mg/l, rồi đâm vào một xe máy.",
                        height=140)
    go = st.button("Phân tích", type="primary")

if go and text.strip():
    ans = svc.answer(text)
    with col1:
        st.markdown(ans.explanation)
    with col2:
        st.subheader("🔎 Hộp kính suy diễn")
        with st.expander("Facts đã trích", expanded=True):
            st.json(ans.facts)
        with st.expander("Chuỗi suy diễn (trace)"):
            st.code(ans.trace.render() or "(không có bước)")
        with st.expander("Tình tiết suy luận / cảnh báo"):
            st.write(ans.nlu_meta.get("inferred"))
            st.write(ans.nlu_meta.get("warnings"))
```

- [ ] **Step 4: Chạy test (PASS) + toàn bộ suite** — `.venv/bin/python -m pytest -q`

- [ ] **Step 5: Chạy thử app (thủ công, xác minh end-to-end)**
```bash
.venv/bin/python -m streamlit run app/streamlit_app.py
```
Kiểm tra: nhập tình huống → hiện giải thích + facts + trace. (Không chạy trong test tự động.)

- [ ] **Step 6: Commit**
```bash
git add app/streamlit_app.py traffic_es/nlu/llm_extractor.py tests/test_llm_extractor.py requirements.txt
git commit -m "feat: Task 7 — chatbot Streamlit + LLMExtractor (offline heuristic mặc định)"
```

---

## Kết quả sau Plan 3
Sản phẩm chạy đầu-cuối: gõ tình huống tiếng Việt → chatbot Streamlit trả mức phạt + căn cứ Điều/Khoản + giải thích + hộp kính (facts/trace/tình tiết). Chạy offline bằng heuristic; cắm LLM thật khi có API key. Sẵn sàng cho Plan 4 (đánh giá hiệu năng trên bộ test).

## Spec-coverage
- Yêu cầu SP 4a (chatbot tiếng Việt): Task 7. · 4b (giải thích chuỗi suy luận): Task 5.
- Bài toán 2 (NL→ontology): Task 1 (+Task 7 LLM). · Bài toán 1 (suy luận gián tiếp): Task 3.
- Grounding chống ảo giác: Task 2. · Còn lại cho Plan 4: đánh giá hiệu năng (testset + metrics).
