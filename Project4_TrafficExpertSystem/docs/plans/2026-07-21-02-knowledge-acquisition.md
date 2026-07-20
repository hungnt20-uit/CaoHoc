# Plan 2 — Số hóa Nghị định → Knowledge Base (Legal-Onto)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Chuyển 3 văn bản Nghị định (100/2019, 123/2021, 168/2024) thành Knowledge Base có cấu trúc — luật YAML (đúng schema Plan 1) + khái niệm Legal-Onto — có kiểm chứng, để engine Plan 1 suy diễn trên dữ liệu luật thật.

**Architecture:** `.doc → text` (textutil) → **segmenter** tách Chương/Điều/Khoản/Điểm → **extractor** (LLM có inject, test bằng mock) biến mỗi mệnh đề phạt thành `Rule` (dieu_kien, ket_luan, can_cu) → **validate** bằng pydantic schema Plan 1 + kiểm tra toàn vẹn → ghi `knowledge/rules/*.yaml`. Các hàm thuần (parse tiền, tách cấu trúc) được TDD chặt; phần gọi LLM test bằng `FakeLLM`. Việc chạy trích thật trên toàn văn bản là bước thực thi/data (script `scripts/build_kb.py`), có human-review.

**Tech Stack:** Python 3.11+ (đã có venv Plan 1), `pydantic`, `pyyaml`, `pytest`. LLM provider thật (openai/anthropic/google) nạp tùy chọn qua biến môi trường; **không bắt buộc để chạy test**.

**Phụ thuộc dữ liệu:** 3 file `.doc` tại `.../Project4/data/` (đang là placeholder iCloud — cần tải nội dung về máy trước khi chạy Task 1 & Task 6; các task khác không cần).

---

### Task 0: Scaffolding module acquisition + LLM client dùng chung

**Files:**
- Create: `traffic_es/llm/__init__.py`, `traffic_es/acquisition/__init__.py`
- Create: `traffic_es/llm/client.py`
- Test: `tests/test_llm_client.py`

`LLMClient` là giao diện trừu tượng; `FakeLLM` trả lời theo kịch bản (cho test); `CachingLLM` bọc cache theo hash prompt. Provider thật thêm ở Task 6 (không cần cho test).

- [ ] **Step 1: Viết test thất bại**

```python
# tests/test_llm_client.py
from traffic_es.llm.client import FakeLLM, CachingLLM

def test_fake_llm_returns_scripted():
    llm = FakeLLM(responses={"xin chào": "chào bạn"})
    assert llm.complete(system="s", user="xin chào") == "chào bạn"

def test_fake_llm_json():
    llm = FakeLLM(responses={"trích": '{"a": 1}'})
    assert llm.complete_json(system="s", user="trích") == {"a": 1}

def test_caching_llm_calls_once():
    calls = {"n": 0}
    class Counting(FakeLLM):
        def complete(self, system, user, **kw):
            calls["n"] += 1
            return "x"
    llm = CachingLLM(Counting(responses={}))
    llm.complete(system="s", user="u")
    llm.complete(system="s", user="u")
    assert calls["n"] == 1     # lần 2 lấy từ cache
```

- [ ] **Step 2: Chạy test để xác nhận FAIL**

Run: `.venv/bin/python -m pytest tests/test_llm_client.py -q`
Expected: FAIL — `ModuleNotFoundError: traffic_es.llm.client`

- [ ] **Step 3: Cài đặt**

Tạo `traffic_es/llm/__init__.py` và `traffic_es/acquisition/__init__.py` (rỗng), rồi:

```python
# traffic_es/llm/client.py
from __future__ import annotations
import json, hashlib
from typing import Any, Dict, Optional


class LLMClient:
    """Giao diện LLM tối thiểu. Provider thật kế thừa và override complete()."""

    def complete(self, system: str, user: str, **kw: Any) -> str:
        raise NotImplementedError

    def complete_json(self, system: str, user: str, **kw: Any) -> Dict[str, Any]:
        raw = self.complete(system=system, user=user, **kw)
        return json.loads(raw)


class FakeLLM(LLMClient):
    """LLM giả cho test: khớp 'user' với substring trong responses."""

    def __init__(self, responses: Optional[Dict[str, str]] = None):
        self.responses = responses or {}

    def complete(self, system: str, user: str, **kw: Any) -> str:
        for key, val in self.responses.items():
            if key in user:
                return val
        return ""


class CachingLLM(LLMClient):
    """Bọc một LLMClient, cache theo hash (system,user)."""

    def __init__(self, inner: LLMClient):
        self.inner = inner
        self._cache: Dict[str, str] = {}

    def _key(self, system: str, user: str) -> str:
        return hashlib.sha256((system + "\x00" + user).encode("utf-8")).hexdigest()

    def complete(self, system: str, user: str, **kw: Any) -> str:
        k = self._key(system, user)
        if k not in self._cache:
            self._cache[k] = self.inner.complete(system=system, user=user, **kw)
        return self._cache[k]
```

- [ ] **Step 4: Chạy test để xác nhận PASS**

Run: `.venv/bin/python -m pytest tests/test_llm_client.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add traffic_es/llm tests/test_llm_client.py traffic_es/acquisition/__init__.py
git commit -m "feat(llm): Task 0 — LLMClient trừu tượng + FakeLLM + CachingLLM"
```

---

### Task 1: Chuyển .doc → text

**Files:**
- Create: `traffic_es/acquisition/doc_to_text.py`
- Test: `tests/test_doc_to_text.py`
- Fixture: `tests/fixtures/sample_clause.txt`

Dùng `textutil` (macOS). Hàm nhận đường dẫn, trả text; nếu đã là `.txt` thì đọc thẳng (giúp test không phụ thuộc `.doc`).

- [ ] **Step 1: Tạo fixture text**

```
# tests/fixtures/sample_clause.txt
Điều 6. Xử phạt người điều khiển xe ô tô vi phạm quy tắc giao thông đường bộ
11. Phạt tiền từ 30.000.000 đồng đến 40.000.000 đồng đối với người điều khiển xe thực hiện một trong các hành vi vi phạm sau đây:
a) Điều khiển xe trên đường mà trong hơi thở có nồng độ cồn vượt quá 0,4 miligam/1 lít khí thở.
```

- [ ] **Step 2: Viết test thất bại**

```python
# tests/test_doc_to_text.py
from pathlib import Path
from traffic_es.acquisition.doc_to_text import to_text

def test_reads_txt_directly():
    txt = to_text(Path("tests/fixtures/sample_clause.txt"))
    assert "Điều 6." in txt
    assert "nồng độ cồn vượt quá 0,4" in txt
```

- [ ] **Step 3: Chạy test để xác nhận FAIL**

Run: `.venv/bin/python -m pytest tests/test_doc_to_text.py -q`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 4: Cài đặt**

```python
# traffic_es/acquisition/doc_to_text.py
from __future__ import annotations
import subprocess, tempfile, os
from pathlib import Path


def to_text(path: Path) -> str:
    path = Path(path)
    if path.suffix.lower() == ".txt":
        return path.read_text(encoding="utf-8", errors="replace")
    # .doc/.docx: dùng textutil của macOS
    with tempfile.TemporaryDirectory() as td:
        out = os.path.join(td, "out.txt")
        subprocess.run(
            ["textutil", "-convert", "txt", "-encoding", "UTF-8", "-output", out, str(path)],
            check=True, timeout=300,
        )
        return Path(out).read_text(encoding="utf-8", errors="replace")
```

- [ ] **Step 5: Chạy test để xác nhận PASS**

Run: `.venv/bin/python -m pytest tests/test_doc_to_text.py -q`
Expected: PASS (1 passed)

- [ ] **Step 6: Commit**

```bash
git add traffic_es/acquisition/doc_to_text.py tests/test_doc_to_text.py tests/fixtures/sample_clause.txt
git commit -m "feat(acq): Task 1 — chuyển .doc→text (textutil), đọc .txt trực tiếp"
```

---

### Task 2: Parser tiền phạt tiếng Việt

**Files:**
- Create: `traffic_es/acquisition/money.py`
- Test: `tests/test_money.py`

Tiếng Việt dùng dấu `.` ngăn nghìn: "30.000.000 đồng" = 30000000. Cần: `parse_money("30.000.000 đồng") -> 30000000`; `money_range("Phạt tiền từ 30.000.000 đồng đến 40.000.000 đồng ...") -> (30000000, 40000000)`.

- [ ] **Step 1: Viết test thất bại**

```python
# tests/test_money.py
import pytest
from traffic_es.acquisition.money import parse_money, money_range

def test_parse_money():
    assert parse_money("30.000.000 đồng") == 30000000
    assert parse_money("500.000") == 500000

def test_money_range():
    text = "Phạt tiền từ 30.000.000 đồng đến 40.000.000 đồng đối với người điều khiển xe"
    assert money_range(text) == (30000000, 40000000)

def test_money_range_single_returns_same():
    assert money_range("Phạt tiền 800.000 đồng") == (800000, 800000)

def test_money_range_none_when_absent():
    assert money_range("Không có mức tiền ở đây") is None
```

- [ ] **Step 2: Chạy test để xác nhận FAIL**

Run: `.venv/bin/python -m pytest tests/test_money.py -q`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Cài đặt**

```python
# traffic_es/acquisition/money.py
from __future__ import annotations
import re
from typing import Optional, Tuple

_NUM = re.compile(r"\d{1,3}(?:\.\d{3})+|\d+")

def parse_money(s: str) -> int:
    m = _NUM.search(s)
    if not m:
        raise ValueError(f"Không tìm thấy số tiền trong: {s!r}")
    return int(m.group(0).replace(".", ""))

def money_range(text: str) -> Optional[Tuple[int, int]]:
    nums = [int(x.replace(".", "")) for x in _NUM.findall(text)]
    # chỉ giữ số lớn (>= 10.000) để tránh dính "1 lít", "0,4", số điều/khoản
    money = [n for n in nums if n >= 10000]
    if not money:
        return None
    if len(money) == 1:
        return (money[0], money[0])
    return (money[0], money[1])
```

- [ ] **Step 4: Chạy test để xác nhận PASS**

Run: `.venv/bin/python -m pytest tests/test_money.py -q`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add traffic_es/acquisition/money.py tests/test_money.py
git commit -m "feat(acq): Task 2 — parser tiền phạt tiếng Việt (khoảng từ..đến..)"
```

---

### Task 3: Segmenter cấu trúc pháp lý (Điều / Khoản / Điểm)

**Files:**
- Create: `traffic_es/acquisition/segmenter.py`
- Test: `tests/test_segmenter.py`

Trả về danh sách `Clause(dieu, dieu_title, khoan, diem, text)`. Điều: dòng `Điều <n>.`; Khoản: dòng bắt đầu `<n>.`; Điểm: dòng bắt đầu `<chữ>)`.

- [ ] **Step 1: Viết test thất bại**

```python
# tests/test_segmenter.py
from traffic_es.acquisition.segmenter import segment, Clause

TEXT = """Điều 6. Xử phạt người điều khiển xe ô tô
11. Phạt tiền từ 30.000.000 đồng đến 40.000.000 đồng đối với người điều khiển xe thực hiện hành vi:
a) Điều khiển xe trên đường mà trong hơi thở có nồng độ cồn vượt quá 0,4 miligam/1 lít khí thở.
b) Không chấp hành yêu cầu kiểm tra về nồng độ cồn.
12. Phạt tiền từ 2.000.000 đồng đến 3.000.000 đồng đối với hành vi khác.
Điều 7. Xử phạt người điều khiển xe mô tô
1. Phạt tiền từ 200.000 đồng đến 300.000 đồng.
"""

def test_segment_counts_dieu():
    clauses = segment(TEXT)
    dieus = sorted({c.dieu for c in clauses})
    assert dieus == [6, 7]

def test_diem_carries_dieu_khoan_context():
    clauses = segment(TEXT)
    a = next(c for c in clauses if c.diem == "a")
    assert a.dieu == 6 and a.khoan == 11
    assert "nồng độ cồn vượt quá 0,4" in a.text

def test_khoan_without_diem_is_a_clause():
    clauses = segment(TEXT)
    k12 = next(c for c in clauses if c.dieu == 6 and c.khoan == 12 and c.diem is None)
    assert "2.000.000" in k12.text
```

- [ ] **Step 2: Chạy test để xác nhận FAIL**

Run: `.venv/bin/python -m pytest tests/test_segmenter.py -q`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Cài đặt**

```python
# traffic_es/acquisition/segmenter.py
from __future__ import annotations
import re
from dataclasses import dataclass
from typing import List, Optional

_RE_DIEU = re.compile(r"^Điều\s+(\d+)\.\s*(.*)$")
_RE_KHOAN = re.compile(r"^(\d+)\.\s+(.*)$")
_RE_DIEM = re.compile(r"^([a-zđ])\)\s+(.*)$")


@dataclass
class Clause:
    dieu: Optional[int]
    dieu_title: str
    khoan: Optional[int]
    diem: Optional[str]
    text: str


def segment(text: str) -> List[Clause]:
    clauses: List[Clause] = []
    dieu: Optional[int] = None
    dieu_title = ""
    khoan: Optional[int] = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        m = _RE_DIEU.match(line)
        if m:
            dieu = int(m.group(1))
            dieu_title = m.group(2).strip()
            khoan = None
            continue
        m = _RE_DIEM.match(line)
        if m:  # điểm phải kiểm tra trước khoản? Không: 'a)' khác '11.'
            clauses.append(Clause(dieu, dieu_title, khoan, m.group(1), m.group(2).strip()))
            continue
        m = _RE_KHOAN.match(line)
        if m:
            khoan = int(m.group(1))
            clauses.append(Clause(dieu, dieu_title, khoan, None, m.group(2).strip()))
            continue
        # dòng nối tiếp: gắn vào clause cuối cùng
        if clauses:
            clauses[-1].text += " " + line
    return clauses
```

- [ ] **Step 4: Chạy test để xác nhận PASS**

Run: `.venv/bin/python -m pytest tests/test_segmenter.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add traffic_es/acquisition/segmenter.py tests/test_segmenter.py
git commit -m "feat(acq): Task 3 — segmenter cấu trúc Điều/Khoản/Điểm"
```

---

### Task 4: Mô hình khái niệm Legal-Onto (Concept 5 thành phần)

**Files:**
- Create: `traffic_es/knowledge/ontology.py`
- Create (data): `traffic_es/knowledge/concepts.yaml`
- Test: `tests/test_ontology.py`

Concept = `(Name, Content, InnerRul, Attrs, Keyphrases)` đúng mô hình của thầy. Seed vài concept phương tiện.

- [ ] **Step 1: Viết test thất bại**

```python
# tests/test_ontology.py
from pathlib import Path
from traffic_es.knowledge.ontology import Concept, ConceptStore

def test_concept_fields():
    c = Concept(name="xe mô tô", content="Phương tiện cơ giới hai bánh",
                inner_rul="Điều 3.39 QCVN 41:2016/BGTVT",
                attrs={"loai": "xe_may"}, keyphrases=["xe máy", "mô tô", "xe gắn máy"])
    assert c.name == "xe mô tô"
    assert "mô tô" in c.keyphrases

def test_store_lookup_by_keyphrase():
    store = ConceptStore.from_yaml(Path("traffic_es/knowledge/concepts.yaml"))
    c = store.find_by_keyphrase("xe gắn máy")
    assert c is not None and c.attrs.get("loai") == "xe_may"
```

- [ ] **Step 2: Chạy test để xác nhận FAIL**

Run: `.venv/bin/python -m pytest tests/test_ontology.py -q`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3a: Cài đặt model**

```python
# traffic_es/knowledge/ontology.py
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
import yaml


@dataclass
class Concept:
    name: str
    content: str = ""
    inner_rul: str = ""
    attrs: Dict[str, str] = field(default_factory=dict)
    keyphrases: List[str] = field(default_factory=list)


@dataclass
class ConceptStore:
    concepts: List[Concept] = field(default_factory=list)

    @classmethod
    def from_yaml(cls, path: Path) -> "ConceptStore":
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        items = [Concept(**c) for c in raw.get("concepts", [])]
        return cls(items)

    def find_by_keyphrase(self, phrase: str) -> Optional[Concept]:
        p = phrase.strip().lower()
        for c in self.concepts:
            if p == c.name.lower() or any(p == k.lower() for k in c.keyphrases):
                return c
        return None
```

- [ ] **Step 3b: Tạo dữ liệu concept seed**

```yaml
# traffic_es/knowledge/concepts.yaml
concepts:
  - name: "xe ô tô"
    content: "Phương tiện giao thông cơ giới đường bộ chở người/hàng có từ 4 bánh."
    inner_rul: "Luật Trật tự, an toàn giao thông đường bộ 2024"
    attrs: { loai: "o_to" }
    keyphrases: ["ô tô", "oto", "xe hơi", "xe con"]
  - name: "xe mô tô"
    content: "Phương tiện cơ giới đường bộ hai hoặc ba bánh."
    inner_rul: "Điều 3.39 QCVN 41:2016/BGTVT"
    attrs: { loai: "xe_may" }
    keyphrases: ["xe máy", "mô tô", "xe gắn máy", "xe mô tô"]
```

- [ ] **Step 4: Chạy test để xác nhận PASS**

Run: `.venv/bin/python -m pytest tests/test_ontology.py -q`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add traffic_es/knowledge/ontology.py traffic_es/knowledge/concepts.yaml tests/test_ontology.py
git commit -m "feat(kb): Task 4 — Legal-Onto Concept (Name,Content,InnerRul,Attrs,Keyphrases) + seed"
```

---

### Task 5: Trích Rule từ mệnh đề phạt (LLM inject, test bằng mock)

**Files:**
- Create: `traffic_es/acquisition/rule_extractor.py`
- Test: `tests/test_rule_extractor.py`

`extract_rules(clause, nghi_dinh, llm) -> list[Rule]`: dựng prompt từ `clause`, gọi `llm.complete_json`, hợp lệ hóa vào `Rule` (Plan 1). Điền `can_cu` từ ngữ cảnh clause; tiền phạt lấy từ chính clause bằng `money_range` (không tin LLM cho con số — chống ảo giác).

- [ ] **Step 1: Viết test thất bại**

```python
# tests/test_rule_extractor.py
import json
from traffic_es.llm.client import FakeLLM
from traffic_es.acquisition.segmenter import Clause
from traffic_es.acquisition.rule_extractor import extract_rules
from traffic_es.knowledge.rules import Rule

def _clause():
    return Clause(dieu=6, dieu_title="Xử phạt người điều khiển xe ô tô", khoan=11, diem="a",
                  text="Điều khiển xe trên đường mà trong hơi thở có nồng độ cồn vượt quá 0,4 miligam/1 lít khí thở.")

def test_extract_builds_valid_rule():
    # LLM chỉ trả phần ngữ nghĩa: nhóm, loại xe, điều kiện, mô tả
    llm = FakeLLM(responses={"nồng độ cồn": json.dumps({
        "nhom": "nong_do_con",
        "ap_dung_loai_xe": ["o_to"],
        "dieu_kien": ["chiso.nongDoCon_khiTho > 0.4"],
        "hanh_vi": "Điều khiển ô tô mà trong hơi thở có nồng độ cồn vượt quá 0,4 mg/l",
    })})
    # tiền phạt truyền kèm từ khoản (đã parse ngoài LLM)
    rules = extract_rules(_clause(), nghi_dinh="168/2024/NĐ-CP", llm=llm,
                          tien_min=30000000, tien_max=40000000)
    assert len(rules) == 1
    r = rules[0]
    assert isinstance(r, Rule)
    assert r.ket_luan.tien_phat_max == 40000000       # từ clause, KHÔNG từ LLM
    assert r.ket_luan.can_cu.dieu == 6 and r.ket_luan.can_cu.khoan == 11
    assert r.ket_luan.can_cu.diem == "a"
    assert r.nhom == "nong_do_con"

def test_extract_returns_empty_on_blank_llm():
    llm = FakeLLM(responses={})   # trả "" -> không phải hành vi phạt
    rules = extract_rules(_clause(), nghi_dinh="168/2024/NĐ-CP", llm=llm,
                          tien_min=0, tien_max=0)
    assert rules == []
```

- [ ] **Step 2: Chạy test để xác nhận FAIL**

Run: `.venv/bin/python -m pytest tests/test_rule_extractor.py -q`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Cài đặt**

```python
# traffic_es/acquisition/rule_extractor.py
from __future__ import annotations
import json
from typing import List
from traffic_es.acquisition.segmenter import Clause
from traffic_es.llm.client import LLMClient
from traffic_es.knowledge.rules import Rule, KetLuan, CanCu

SYSTEM = (
    "Bạn là trợ lý pháp lý. Cho một mệnh đề trong nghị định xử phạt giao thông, "
    "hãy trích thành JSON với các khóa: nhom, ap_dung_loai_xe (mảng), "
    "dieu_kien (mảng biểu thức dạng 'chiso.x > 0.4' hoặc 'boicanh.khuVuc == \"khu_dan_cu\"'), "
    "hanh_vi (mô tả ngắn). Nếu mệnh đề KHÔNG mô tả hành vi bị phạt, trả về chuỗi rỗng. "
    "TUYỆT ĐỐI không bịa số tiền phạt."
)


def _rule_id(nghi_dinh: str, clause: Clause, nhom: str) -> str:
    nd = nghi_dinh.split("/")[0]
    return f"R_{nd}_D{clause.dieu}_K{clause.khoan}_{clause.diem or 'x'}_{nhom}".upper()


def extract_rules(
    clause: Clause, nghi_dinh: str, llm: LLMClient, tien_min: int, tien_max: int
) -> List[Rule]:
    user = f"Điều {clause.dieu} ({clause.dieu_title}), Khoản {clause.khoan}: {clause.text}"
    raw = llm.complete(system=SYSTEM, user=user)
    if not raw or not raw.strip():
        return []
    data = json.loads(raw)
    if not data or not data.get("hanh_vi"):
        return []
    ket_luan = KetLuan(
        hanh_vi=data["hanh_vi"],
        tien_phat_min=tien_min,     # số tiền LẤY TỪ CLAUSE, không từ LLM
        tien_phat_max=tien_max,
        can_cu=CanCu(nghi_dinh=nghi_dinh, dieu=clause.dieu, khoan=clause.khoan,
                     diem=clause.diem),
    )
    rule = Rule(
        id=_rule_id(nghi_dinh, clause, data.get("nhom", "khac")),
        nhom=data.get("nhom", "khac"),
        ap_dung_loai_xe=data.get("ap_dung_loai_xe", []),
        dieu_kien=data.get("dieu_kien", []),
        ket_luan=ket_luan,
    )
    return [rule]
```

- [ ] **Step 4: Chạy test để xác nhận PASS**

Run: `.venv/bin/python -m pytest tests/test_rule_extractor.py -q`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add traffic_es/acquisition/rule_extractor.py tests/test_rule_extractor.py
git commit -m "feat(acq): Task 5 — trích Rule từ mệnh đề (LLM ngữ nghĩa, tiền từ clause)"
```

---

### Task 6: Pipeline build_kb + smoke test + chạy trên văn bản thật

**Files:**
- Create: `traffic_es/acquisition/build_kb.py`
- Create: `scripts/build_kb.py`
- Test: `tests/test_build_kb.py`

`build_kb_from_text(text, nghi_dinh, llm) -> list[Rule]`: segment → với clause có `money_range` → `extract_rules`. `write_rules_yaml(rules, path)` gộp theo nhóm. Provider thật gắn ở `scripts/build_kb.py` (chỉ chạy khi có API key & file đã tải).

- [ ] **Step 1: Viết test thất bại**

```python
# tests/test_build_kb.py
import json
from pathlib import Path
from traffic_es.llm.client import FakeLLM
from traffic_es.acquisition.build_kb import build_kb_from_text, write_rules_yaml
from traffic_es.knowledge.kb_loader import load_rules

TEXT = ("Điều 6. Xử phạt người điều khiển xe ô tô\n"
        "11. Phạt tiền từ 30.000.000 đồng đến 40.000.000 đồng đối với người điều khiển xe:\n"
        "a) Điều khiển xe trên đường mà trong hơi thở có nồng độ cồn vượt quá 0,4 miligam/1 lít khí thở.\n")

def _llm():
    return FakeLLM(responses={"nồng độ cồn": json.dumps({
        "nhom": "nong_do_con", "ap_dung_loai_xe": ["o_to"],
        "dieu_kien": ["chiso.nongDoCon_khiTho > 0.4"],
        "hanh_vi": "Điều khiển ô tô nồng độ cồn > 0,4 mg/l"})})

def test_build_extracts_rule_with_money_from_text():
    rules = build_kb_from_text(TEXT, nghi_dinh="168/2024/NĐ-CP", llm=_llm())
    assert len(rules) == 1
    assert rules[0].ket_luan.tien_phat_min == 30000000
    assert rules[0].ket_luan.tien_phat_max == 40000000

def test_write_and_reload_roundtrip(tmp_path):
    rules = build_kb_from_text(TEXT, nghi_dinh="168/2024/NĐ-CP", llm=_llm())
    out = tmp_path / "generated.yaml"
    write_rules_yaml(rules, out)
    reloaded = load_rules(tmp_path)
    assert [r.id for r in reloaded] == [r.id for r in rules]
```

- [ ] **Step 2: Chạy test để xác nhận FAIL**

Run: `.venv/bin/python -m pytest tests/test_build_kb.py -q`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3a: Cài đặt pipeline**

```python
# traffic_es/acquisition/build_kb.py
from __future__ import annotations
from pathlib import Path
from typing import List
import yaml
from traffic_es.acquisition.segmenter import segment
from traffic_es.acquisition.money import money_range
from traffic_es.acquisition.rule_extractor import extract_rules
from traffic_es.llm.client import LLMClient
from traffic_es.knowledge.rules import Rule


def build_kb_from_text(text: str, nghi_dinh: str, llm: LLMClient) -> List[Rule]:
    rules: List[Rule] = []
    last_range = None
    for clause in segment(text):
        mr = money_range(clause.text)
        if mr:
            last_range = mr           # khoản mẹ mang mức tiền, áp cho các điểm con
        if last_range is None:
            continue
        tien_min, tien_max = last_range
        rules.extend(extract_rules(clause, nghi_dinh, llm, tien_min, tien_max))
    return rules


def write_rules_yaml(rules: List[Rule], path: Path) -> None:
    data = {"rules": [r.model_dump(exclude_none=True) for r in rules]}
    Path(path).write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
```

- [ ] **Step 3b: Script chạy thật (không chạy trong test)**

```python
# scripts/build_kb.py
"""Chạy trích KB thật từ các Nghị định. Cần API key + file .doc đã tải về máy.
Ví dụ: OPENAI_API_KEY=... .venv/bin/python scripts/build_kb.py \
    --doc "/path/168_2024_ND-CP.doc" --nghi-dinh "168/2024/NĐ-CP" \
    --dieu 6 --out traffic_es/knowledge/rules/168_dieu6.yaml
Provider thật: cài đặt lớp con LLMClient dùng openai/anthropic tại đây.
"""
from __future__ import annotations
import argparse, os
from pathlib import Path
from traffic_es.acquisition.doc_to_text import to_text
from traffic_es.acquisition.build_kb import build_kb_from_text, write_rules_yaml
from traffic_es.acquisition.segmenter import segment
from traffic_es.llm.client import LLMClient, CachingLLM


class OpenAILLM(LLMClient):
    def __init__(self, model: str = "gpt-4o-mini"):
        from openai import OpenAI  # import trễ để test không cần openai
        self.client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        self.model = model

    def complete(self, system: str, user: str, **kw) -> str:
        r = self.client.chat.completions.create(
            model=self.model, temperature=0,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
            response_format={"type": "json_object"},
        )
        return r.choices[0].message.content or ""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--doc", required=True)
    ap.add_argument("--nghi-dinh", required=True)
    ap.add_argument("--dieu", type=int, default=None, help="chỉ trích 1 Điều để tiết kiệm token")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    text = to_text(Path(args.doc))
    if args.dieu is not None:
        clauses = [c for c in segment(text) if c.dieu == args.dieu]
        text = "\n".join(
            [f"Điều {args.dieu}. {clauses[0].dieu_title}"]
            + [f"{c.khoan}. {c.text}" if c.diem is None else f"{c.diem}) {c.text}"
               for c in clauses]
        )
    llm = CachingLLM(OpenAILLM())
    rules = build_kb_from_text(text, args.nghi_dinh, llm)
    write_rules_yaml(rules, Path(args.out))
    print(f"Đã ghi {len(rules)} luật -> {args.out}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Chạy test để xác nhận PASS**

Run: `.venv/bin/python -m pytest tests/test_build_kb.py -q`
Expected: PASS (2 passed). (Script `scripts/build_kb.py` KHÔNG chạy trong test.)

- [ ] **Step 5: Commit**

```bash
git add traffic_es/acquisition/build_kb.py scripts/build_kb.py tests/test_build_kb.py
git commit -m "feat(acq): Task 6 — pipeline build_kb (mock-tested) + script trích thật"
```

- [ ] **Step 6: (Thực thi/data — sau khi tải file & có API key) Chạy trích thật, có review**

Chạy (ví dụ Điều 6 của NĐ 168 — nhóm hành vi ô tô):
```bash
OPENAI_API_KEY=... .venv/bin/python scripts/build_kb.py \
  --doc "/Users/.../Project4/data/168_2024_ND-CP_m_619502.doc" \
  --nghi-dinh "168/2024/NĐ-CP" --dieu 6 \
  --out traffic_es/knowledge/rules/168_dieu6.yaml
```
**Bắt buộc human review** file YAML sinh ra: đối chiếu `dieu_kien`, `can_cu`, tiền phạt với văn bản gốc; sửa tay biểu thức điều kiện cho khớp ngưỡng. Sau đó commit dữ liệu:
```bash
git add traffic_es/knowledge/rules/168_dieu6.yaml
git commit -m "data(kb): trích luật Điều 6 NĐ 168/2024 (đã review)"
```

---

### Task 7: Kiểm tra toàn vẹn Knowledge Base

**Files:**
- Test: `tests/test_kb_integrity.py`

- [ ] **Step 1: Viết test**

```python
# tests/test_kb_integrity.py
from pathlib import Path
from traffic_es.knowledge.kb_loader import load_rules

RULES_DIR = Path("traffic_es/knowledge/rules")

def test_rule_ids_unique():
    rules = load_rules(RULES_DIR)
    ids = [r.id for r in rules]
    assert len(ids) == len(set(ids)), "Có id luật trùng nhau"

def test_every_rule_has_valid_penalty_and_cancu():
    for r in load_rules(RULES_DIR):
        assert r.ket_luan.tien_phat_min <= r.ket_luan.tien_phat_max, r.id
        assert r.ket_luan.can_cu.nghi_dinh, r.id
        assert r.ket_luan.can_cu.dieu > 0, r.id

def test_conditions_reference_known_namespaces():
    ok = ("phuongtien.", "nguoi.", "chiso.", "boicanh.", "tinhtiet.")
    for r in load_rules(RULES_DIR):
        for cond in r.dieu_kien:
            assert cond.startswith(ok), f"{r.id}: điều kiện lạ {cond!r}"
```

- [ ] **Step 2: Chạy test để xác nhận PASS**

Run: `.venv/bin/python -m pytest tests/test_kb_integrity.py -q`
Expected: PASS (3 passed) — với KB hiện có (nồng độ cồn mẫu + dữ liệu đã trích).

- [ ] **Step 3: Chạy toàn bộ & commit**

Run: `.venv/bin/python -m pytest -q`
Expected: toàn bộ PASS.

```bash
git add tests/test_kb_integrity.py
git commit -m "test(kb): Task 7 — kiểm tra toàn vẹn KB (id duy nhất, phạt/căn cứ hợp lệ)"
```

---

## Kết quả sau Plan 2
- Pipeline số hóa Nghị định hoàn chỉnh, test bằng mock (không tốn API).
- Legal-Onto Concept model + seed concepts.
- KB mở rộng bằng dữ liệu trích thật (Điều/nhóm chọn lọc), có human-review + test toàn vẹn.
- Engine Plan 1 chạy được trên luật thật.

## Spec-coverage & ghi chú
- Spec §3 (số hóa tri thức, Text Mining): Task 1–6.
- Legal-Onto Concept 5 thành phần: Task 4.
- Chống ảo giác số tiền: tiền phạt lấy từ clause (`money_range`), không từ LLM (Task 5).
- **Chưa** làm trong Plan 2 (để Plan 3): NLU câu hỏi người dùng, đồ thị câu hỏi, subgraph matching, semantic_infer (Bài toán 1), grounding — dùng lại `LLMClient` và `ConceptStore` của Plan 2.
- **Phụ thuộc:** Task 1 & Task 6-Step6 cần 3 file `.doc` đã tải nội dung về máy (hiện là placeholder iCloud).
