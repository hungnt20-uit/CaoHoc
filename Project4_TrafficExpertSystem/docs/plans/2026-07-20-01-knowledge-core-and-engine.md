# Plan 1 — Nền tảng tri thức + Engine suy diễn ký hiệu

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Xây trái tim ký hiệu của hệ chuyên gia — Legal-Onto (Concept/Rule) + Mạng tính toán `(M,R)` với forward chaining, meta-rule tình tiết, gộp phạt, lưu vết giải thích, và A\* tìm "lời giải tốt" — chạy & test hoàn toàn bằng pytest, không phụ thuộc LLM/UI.

**Architecture:** Facts (dict phẳng key dạng `"chiso.tocDo"`) → WorkingMemory → Deduce_Objects (Funcs tới điểm bất động) → Deduce_Rules (forward chaining khớp điều kiện) → Meta-rule điều chỉnh khung → gộp phạt (tiền cộng dồn, bổ sung lấy nặng nhất) → Trace. Điều kiện luật là chuỗi `"lhs OP rhs"` được đánh giá bằng parser an toàn (KHÔNG dùng `eval`). Luật lưu YAML, nạp qua pydantic.

**Tech Stack:** Python 3.11+, `pydantic` v2, `pyyaml`, `pytest`. (A\* dùng thư viện chuẩn, không cần `networkx` ở Plan này.)

---

### Task 0: Scaffolding dự án

**Files:**
- Create: `requirements.txt`, `pytest.ini`, `traffic_es/__init__.py`, `traffic_es/engine/__init__.py`, `traffic_es/knowledge/__init__.py`, `tests/__init__.py`

- [ ] **Step 1: Tạo requirements.txt**

```
pydantic>=2.6
pyyaml>=6.0
pytest>=8.0
```

- [ ] **Step 2: Tạo pytest.ini**

```ini
[pytest]
testpaths = tests
python_files = test_*.py
addopts = -q
```

- [ ] **Step 3: Tạo các package rỗng**

Tạo 5 file `__init__.py` rỗng ở các đường dẫn trên: `traffic_es/__init__.py`, `traffic_es/engine/__init__.py`, `traffic_es/knowledge/__init__.py`, `tests/__init__.py`. (Package chính là `traffic_es`.)

- [ ] **Step 4: Tạo venv & cài đặt**

Run:
```bash
python3 -m venv .venv && . .venv/bin/activate && pip install -q -r requirements.txt
```
Expected: cài xong không lỗi.

- [ ] **Step 5: Commit**

```bash
git add requirements.txt pytest.ini traffic_es tests
git commit -m "chore: scaffolding package traffic_es + pytest"
```

---

### Task 1: WorkingMemory

**Files:**
- Create: `traffic_es/engine/working_memory.py`
- Test: `tests/test_working_memory.py`

- [ ] **Step 1: Viết test thất bại**

```python
# tests/test_working_memory.py
from traffic_es.engine.working_memory import WorkingMemory

def test_set_get_has():
    wm = WorkingMemory({"chiso.tocDo": 90})
    assert wm.has("chiso.tocDo")
    assert wm.get("chiso.tocDo") == 90
    assert not wm.has("chiso.tocDoGioiHan")

def test_set_records_source():
    wm = WorkingMemory()
    wm.set("chiso.vuot_pct", 80.0, source="FUNC:vuot_toc_do_pct")
    assert wm.get("chiso.vuot_pct") == 80.0
    assert wm.source_of("chiso.vuot_pct") == "FUNC:vuot_toc_do_pct"

def test_as_dict_is_copy():
    wm = WorkingMemory({"a": 1})
    d = wm.as_dict()
    d["a"] = 2
    assert wm.get("a") == 1
```

- [ ] **Step 2: Chạy test để xác nhận FAIL**

Run: `pytest tests/test_working_memory.py -v`
Expected: FAIL — `ModuleNotFoundError: traffic_es.engine.working_memory`

- [ ] **Step 3: Cài đặt tối thiểu**

```python
# traffic_es/engine/working_memory.py
from __future__ import annotations
from typing import Any, Dict, Optional

class WorkingMemory:
    """Bộ nhớ làm việc: map fact-key (dạng 'chiso.tocDo') -> giá trị, kèm nguồn."""

    def __init__(self, facts: Optional[Dict[str, Any]] = None):
        self._facts: Dict[str, Any] = dict(facts or {})
        self._source: Dict[str, str] = {k: "INPUT" for k in self._facts}

    def has(self, key: str) -> bool:
        return key in self._facts

    def get(self, key: str, default: Any = None) -> Any:
        return self._facts.get(key, default)

    def set(self, key: str, value: Any, source: str = "INPUT") -> None:
        self._facts[key] = value
        self._source[key] = source

    def source_of(self, key: str) -> Optional[str]:
        return self._source.get(key)

    def as_dict(self) -> Dict[str, Any]:
        return dict(self._facts)
```

- [ ] **Step 4: Chạy test để xác nhận PASS**

Run: `pytest tests/test_working_memory.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add traffic_es/engine/working_memory.py tests/test_working_memory.py
git commit -m "feat(engine): WorkingMemory với lưu nguồn fact"
```

---

### Task 2: Trace (lưu vết suy diễn)

**Files:**
- Create: `traffic_es/engine/trace.py`
- Test: `tests/test_trace.py`

- [ ] **Step 1: Viết test thất bại**

```python
# tests/test_trace.py
from traffic_es.engine.trace import Trace, TraceStep

def test_add_and_iterate():
    tr = Trace()
    tr.add("FUNC", "tính vượt tốc độ", {"vuot_pct": 80.0})
    tr.add("RULE", "khớp R_TOCDO", {"rule_id": "R1"})
    kinds = [s.kind for s in tr.steps]
    assert kinds == ["FUNC", "RULE"]
    assert tr.steps[0].data["vuot_pct"] == 80.0

def test_render_contains_detail():
    tr = Trace()
    tr.add("META", "áp mức tối đa", {})
    out = tr.render()
    assert "META" in out and "áp mức tối đa" in out
```

- [ ] **Step 2: Chạy test để xác nhận FAIL**

Run: `pytest tests/test_trace.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Cài đặt tối thiểu**

```python
# traffic_es/engine/trace.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List

@dataclass
class TraceStep:
    kind: str          # FUNC | RULE | META | ASTAR | KL
    detail: str
    data: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Trace:
    steps: List[TraceStep] = field(default_factory=list)

    def add(self, kind: str, detail: str, data: Dict[str, Any] | None = None) -> None:
        self.steps.append(TraceStep(kind, detail, dict(data or {})))

    def render(self) -> str:
        return "\n".join(f"[{s.kind:5}] {s.detail}" for s in self.steps)
```

- [ ] **Step 4: Chạy test để xác nhận PASS**

Run: `pytest tests/test_trace.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add traffic_es/engine/trace.py tests/test_trace.py
git commit -m "feat(engine): cấu trúc Trace lưu vết suy diễn"
```

---

### Task 3: Bộ đánh giá điều kiện an toàn (conditions)

**Files:**
- Create: `traffic_es/engine/conditions.py`
- Test: `tests/test_conditions.py`

Điều kiện luật là chuỗi `"<key> <op> <value>"`. `key` tham chiếu WorkingMemory; `value` là số, boolean (`true`/`false`), chuỗi có nháy `"khu_dan_cu"`, hoặc một `key` khác. Toán tử: `>`, `>=`, `<`, `<=`, `==`, `!=`. **Không dùng `eval`.**

- [ ] **Step 1: Viết test thất bại**

```python
# tests/test_conditions.py
import pytest
from traffic_es.engine.working_memory import WorkingMemory
from traffic_es.engine.conditions import eval_condition

def test_numeric_gt_true():
    wm = WorkingMemory({"chiso.nongDoCon_khiTho": 0.42})
    assert eval_condition("chiso.nongDoCon_khiTho > 0.4", wm) is True

def test_numeric_gt_false():
    wm = WorkingMemory({"chiso.nongDoCon_khiTho": 0.2})
    assert eval_condition("chiso.nongDoCon_khiTho > 0.4", wm) is False

def test_bool_eq():
    wm = WorkingMemory({"tinhtiet.gay_tai_nan": True})
    assert eval_condition("tinhtiet.gay_tai_nan == true", wm) is True

def test_string_eq():
    wm = WorkingMemory({"boicanh.khuVuc": "khu_dan_cu"})
    assert eval_condition('boicanh.khuVuc == "khu_dan_cu"', wm) is True

def test_key_vs_key():
    wm = WorkingMemory({"chiso.tocDo": 90, "chiso.tocDoGioiHan": 50})
    assert eval_condition("chiso.tocDo > chiso.tocDoGioiHan", wm) is True

def test_missing_key_is_false():
    wm = WorkingMemory({})
    assert eval_condition("chiso.tocDo > 50", wm) is False

def test_bad_syntax_raises():
    wm = WorkingMemory({})
    with pytest.raises(ValueError):
        eval_condition("chiso.tocDo 50", wm)
```

- [ ] **Step 2: Chạy test để xác nhận FAIL**

Run: `pytest tests/test_conditions.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Cài đặt tối thiểu**

```python
# traffic_es/engine/conditions.py
from __future__ import annotations
import re
from typing import Any
from traffic_es.engine.working_memory import WorkingMemory

_OPS = ["==", "!=", ">=", "<=", ">", "<"]   # thứ tự: khớp toán tử 2 ký tự trước

def _parse_operand(tok: str, wm: WorkingMemory) -> Any:
    tok = tok.strip()
    if tok.startswith('"') and tok.endswith('"'):
        return tok[1:-1]
    low = tok.lower()
    if low == "true":
        return True
    if low == "false":
        return False
    try:
        return float(tok)
    except ValueError:
        pass
    # coi như tham chiếu key trong WorkingMemory
    return wm.get(tok, None)

def eval_condition(cond: str, wm: WorkingMemory) -> bool:
    op = next((o for o in _OPS if o in cond), None)
    if op is None:
        raise ValueError(f"Điều kiện thiếu toán tử: {cond!r}")
    left_raw, right_raw = cond.split(op, 1)
    left = _parse_operand(left_raw, wm)
    right = _parse_operand(right_raw, wm)
    if left is None or right is None:
        return False  # thiếu dữ kiện -> không khớp
    try:
        if op == "==":
            return left == right
        if op == "!=":
            return left != right
        if op == ">":
            return left > right
        if op == "<":
            return left < right
        if op == ">=":
            return left >= right
        if op == "<=":
            return left <= right
    except TypeError:
        return False
    raise ValueError(f"Toán tử không hỗ trợ: {op}")
```

- [ ] **Step 4: Chạy test để xác nhận PASS**

Run: `pytest tests/test_conditions.py -v`
Expected: PASS (7 passed)

- [ ] **Step 5: Commit**

```bash
git add traffic_es/engine/conditions.py tests/test_conditions.py
git commit -m "feat(engine): bộ đánh giá điều kiện luật an toàn (không eval)"
```

---

### Task 4: Mô hình dữ liệu luật (pydantic) + nạp YAML

**Files:**
- Create: `traffic_es/knowledge/rules.py`, `traffic_es/knowledge/kb_loader.py`
- Create (data): `traffic_es/knowledge/rules/nong_do_con.yaml`
- Test: `tests/test_kb_loader.py`

- [ ] **Step 1: Viết test thất bại**

```python
# tests/test_kb_loader.py
from pathlib import Path
from traffic_es.knowledge.kb_loader import load_rules
from traffic_es.knowledge.rules import Rule

RULES_DIR = Path("traffic_es/knowledge/rules")

def test_load_rules_returns_rule_objects():
    rules = load_rules(RULES_DIR)
    assert len(rules) >= 1
    assert all(isinstance(r, Rule) for r in rules)

def test_rule_has_cancu_and_conditions():
    rules = load_rules(RULES_DIR)
    r = next(r for r in rules if r.id == "R_CON_OTO_MUC3")
    assert r.ket_luan.can_cu.nghi_dinh == "168/2024/NĐ-CP"
    assert r.ket_luan.can_cu.dieu == 6
    assert "chiso.nongDoCon_khiTho > 0.4" in r.dieu_kien
    assert r.ket_luan.tien_phat_max == 40000000
```

- [ ] **Step 2: Chạy test để xác nhận FAIL**

Run: `pytest tests/test_kb_loader.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3a: Cài đặt mô hình luật**

```python
# traffic_es/knowledge/rules.py
from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field

class CanCu(BaseModel):
    nghi_dinh: str
    dieu: int
    khoan: Optional[int] = None
    diem: Optional[str] = None

class PhatBoSung(BaseModel):
    tuoc_gplx_thang: Optional[List[int]] = None   # [min, max] tháng
    tru_diem: Optional[int] = None
    tam_giu_xe_ngay: Optional[int] = None

class KetLuan(BaseModel):
    hanh_vi: str
    tien_phat_min: int
    tien_phat_max: int
    phat_bo_sung: PhatBoSung = Field(default_factory=PhatBoSung)
    can_cu: CanCu

class Rule(BaseModel):
    id: str
    nhom: str
    ap_dung_loai_xe: List[str] = Field(default_factory=list)
    dieu_kien: List[str] = Field(default_factory=list)
    ket_luan: KetLuan
    giai_thich_mau: Optional[str] = None

class MetaRule(BaseModel):
    id: str
    loai: str                       # "tinh_tiet"
    dieu_kien: List[str] = Field(default_factory=list)
    chon_muc: Optional[str] = None  # "max" | "min"
    ghi_chu: Optional[str] = None
```

- [ ] **Step 3b: Tạo dữ liệu luật YAML**

```yaml
# traffic_es/knowledge/rules/nong_do_con.yaml
rules:
  - id: R_CON_OTO_MUC3
    nhom: nong_do_con
    ap_dung_loai_xe: [o_to]
    dieu_kien:
      - "chiso.nongDoCon_khiTho > 0.4"
    ket_luan:
      hanh_vi: "Điều khiển ô tô mà trong hơi thở có nồng độ cồn vượt quá 0,4 mg/l"
      tien_phat_min: 30000000
      tien_phat_max: 40000000
      phat_bo_sung: { tuoc_gplx_thang: [22, 24] }
      can_cu: { nghi_dinh: "168/2024/NĐ-CP", dieu: 6, khoan: 11, diem: "a" }
    giai_thich_mau: "Nồng độ cồn vượt 0,4 mg/l → khung phạt cao nhất."
meta_rules:
  - id: M_TANG_NANG_TAI_NAN
    loai: tinh_tiet
    dieu_kien: [ "tinhtiet.gay_tai_nan == true" ]
    chon_muc: max
    ghi_chu: "Tình tiết tăng nặng: áp mức tiền tối đa của khung."
```

> ⚠️ Con số minh họa; thay bằng số chính xác từ văn bản Nghị định khi số hóa (Plan sau).

- [ ] **Step 3c: Cài đặt loader**

```python
# traffic_es/knowledge/kb_loader.py
from __future__ import annotations
from pathlib import Path
from typing import List, Tuple
import yaml
from traffic_es.knowledge.rules import Rule, MetaRule

def _load_yaml_files(rules_dir: Path):
    for path in sorted(Path(rules_dir).glob("*.yaml")):
        with open(path, "r", encoding="utf-8") as f:
            yield yaml.safe_load(f) or {}

def load_rules(rules_dir: Path) -> List[Rule]:
    out: List[Rule] = []
    for doc in _load_yaml_files(rules_dir):
        for raw in doc.get("rules", []):
            out.append(Rule(**raw))
    return out

def load_meta_rules(rules_dir: Path) -> List[MetaRule]:
    out: List[MetaRule] = []
    for doc in _load_yaml_files(rules_dir):
        for raw in doc.get("meta_rules", []):
            out.append(MetaRule(**raw))
    return out

def load_kb(rules_dir: Path) -> Tuple[List[Rule], List[MetaRule]]:
    return load_rules(rules_dir), load_meta_rules(rules_dir)
```

- [ ] **Step 4: Chạy test để xác nhận PASS**

Run: `pytest tests/test_kb_loader.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add traffic_es/knowledge/rules.py traffic_es/knowledge/kb_loader.py traffic_es/knowledge/rules/nong_do_con.yaml tests/test_kb_loader.py
git commit -m "feat(kb): mô hình luật pydantic + nạp YAML + luật nồng độ cồn mẫu"
```

---

### Task 5: Deduce_Objects (Funcs tới điểm bất động)

**Files:**
- Create: `traffic_es/engine/funcs.py`
- Test: `tests/test_funcs.py`

- [ ] **Step 1: Viết test thất bại**

```python
# tests/test_funcs.py
from traffic_es.engine.working_memory import WorkingMemory
from traffic_es.engine.trace import Trace
from traffic_es.engine.funcs import Func, apply_funcs, DEFAULT_FUNCS

def test_vuot_toc_do_pct():
    wm = WorkingMemory({"chiso.tocDo": 90, "chiso.tocDoGioiHan": 50})
    tr = Trace()
    apply_funcs(wm, DEFAULT_FUNCS, tr)
    assert wm.get("chiso.vuot_toc_do_pct") == 80.0
    assert any(s.kind == "FUNC" for s in tr.steps)

def test_func_not_fired_when_inputs_missing():
    wm = WorkingMemory({"chiso.tocDo": 90})   # thiếu tocDoGioiHan
    tr = Trace()
    apply_funcs(wm, DEFAULT_FUNCS, tr)
    assert not wm.has("chiso.vuot_toc_do_pct")

def test_chained_funcs_reach_fixpoint():
    f1 = Func("f_double", ["a"], "b", lambda wm: wm.get("a") * 2)
    f2 = Func("f_inc", ["b"], "c", lambda wm: wm.get("b") + 1)
    wm = WorkingMemory({"a": 3})
    tr = Trace()
    apply_funcs(wm, [f1, f2], tr)
    assert wm.get("b") == 6 and wm.get("c") == 7
```

- [ ] **Step 2: Chạy test để xác nhận FAIL**

Run: `pytest tests/test_funcs.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Cài đặt tối thiểu**

```python
# traffic_es/engine/funcs.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, List
from traffic_es.engine.working_memory import WorkingMemory
from traffic_es.engine.trace import Trace

@dataclass
class Func:
    """Hàm Deduce_Objects: từ inputs (các key) tính ra output (một key)."""
    name: str
    inputs: List[str]
    output: str
    fn: Callable[[WorkingMemory], object]

def apply_funcs(wm: WorkingMemory, funcs: List[Func], trace: Trace) -> None:
    """Chạy các Func lặp tới điểm bất động (fixpoint)."""
    changed = True
    while changed:
        changed = False
        for f in funcs:
            if wm.has(f.output):
                continue
            if all(wm.has(i) for i in f.inputs):
                value = f.fn(wm)
                wm.set(f.output, value, source=f"FUNC:{f.name}")
                trace.add("FUNC", f"{f.output} = {value} (qua {f.name})",
                          {"func": f.name, "output": f.output, "value": value})
                changed = True

def _vuot_toc_do_pct(wm: WorkingMemory) -> float:
    gh = wm.get("chiso.tocDoGioiHan")
    return round((wm.get("chiso.tocDo") - gh) / gh * 100, 2)

DEFAULT_FUNCS: List[Func] = [
    Func("vuot_toc_do_pct", ["chiso.tocDo", "chiso.tocDoGioiHan"],
         "chiso.vuot_toc_do_pct", _vuot_toc_do_pct),
]
```

- [ ] **Step 4: Chạy test để xác nhận PASS**

Run: `pytest tests/test_funcs.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add traffic_es/engine/funcs.py tests/test_funcs.py
git commit -m "feat(engine): Deduce_Objects (Funcs) chạy tới điểm bất động"
```

---

### Task 6: Deduce_Rules + Meta-rule

**Files:**
- Create: `traffic_es/engine/forward_chaining.py`
- Test: `tests/test_forward_chaining.py`

- [ ] **Step 1: Viết test thất bại**

```python
# tests/test_forward_chaining.py
from traffic_es.engine.working_memory import WorkingMemory
from traffic_es.engine.trace import Trace
from traffic_es.engine.forward_chaining import deduce_rules, apply_meta
from traffic_es.knowledge.rules import Rule, KetLuan, CanCu, MetaRule

def _rule():
    return Rule(id="R1", nhom="nong_do_con", ap_dung_loai_xe=["o_to"],
                dieu_kien=["chiso.nongDoCon_khiTho > 0.4"],
                ket_luan=KetLuan(hanh_vi="Nồng độ cồn > 0,4", tien_phat_min=30000000,
                                 tien_phat_max=40000000,
                                 can_cu=CanCu(nghi_dinh="168/2024/NĐ-CP", dieu=6)))

def test_rule_fires_when_condition_met():
    wm = WorkingMemory({"phuongtien.loai": "o_to", "chiso.nongDoCon_khiTho": 0.42})
    tr = Trace()
    fired = deduce_rules(wm, [_rule()], tr)
    assert [r.id for r in fired] == ["R1"]
    assert any(s.kind == "RULE" for s in tr.steps)

def test_rule_skipped_when_vehicle_mismatch():
    wm = WorkingMemory({"phuongtien.loai": "xe_may", "chiso.nongDoCon_khiTho": 0.42})
    fired = deduce_rules(wm, [_rule()], Trace())
    assert fired == []

def test_meta_selects_max():
    wm = WorkingMemory({"tinhtiet.gay_tai_nan": True})
    meta = MetaRule(id="M1", loai="tinh_tiet",
                    dieu_kien=["tinhtiet.gay_tai_nan == true"], chon_muc="max")
    picks = apply_meta(wm, [meta], Trace())
    assert picks == "max"
```

- [ ] **Step 2: Chạy test để xác nhận FAIL**

Run: `pytest tests/test_forward_chaining.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Cài đặt tối thiểu**

```python
# traffic_es/engine/forward_chaining.py
from __future__ import annotations
from typing import List, Optional
from traffic_es.engine.working_memory import WorkingMemory
from traffic_es.engine.trace import Trace
from traffic_es.engine.conditions import eval_condition
from traffic_es.knowledge.rules import Rule, MetaRule

def _vehicle_ok(rule: Rule, wm: WorkingMemory) -> bool:
    if not rule.ap_dung_loai_xe:
        return True
    return wm.get("phuongtien.loai") in rule.ap_dung_loai_xe

def deduce_rules(wm: WorkingMemory, rules: List[Rule], trace: Trace) -> List[Rule]:
    """Forward chaining: trả về các luật vi phạm khớp WorkingMemory."""
    fired: List[Rule] = []
    for r in rules:
        if not _vehicle_ok(r, wm):
            continue
        if all(eval_condition(c, wm) for c in r.dieu_kien):
            fired.append(r)
            cc = r.ket_luan.can_cu
            trace.add("RULE", f"{r.id} khớp → {r.ket_luan.hanh_vi}",
                      {"rule_id": r.id, "can_cu": cc.model_dump(),
                       "tien": [r.ket_luan.tien_phat_min, r.ket_luan.tien_phat_max]})
    return fired

def apply_meta(wm: WorkingMemory, meta_rules: List[MetaRule], trace: Trace) -> Optional[str]:
    """Trả về mức chọn 'max'/'min' nếu có meta-rule tình tiết khớp, ngược lại None."""
    pick: Optional[str] = None
    for m in meta_rules:
        if all(eval_condition(c, wm) for c in m.dieu_kien):
            pick = m.chon_muc or pick
            trace.add("META", f"{m.id}: {m.ghi_chu or ''}".strip(),
                      {"meta_id": m.id, "chon_muc": m.chon_muc})
    return pick
```

- [ ] **Step 4: Chạy test để xác nhận PASS**

Run: `pytest tests/test_forward_chaining.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add traffic_es/engine/forward_chaining.py tests/test_forward_chaining.py
git commit -m "feat(engine): Deduce_Rules (forward chaining) + meta-rule tình tiết"
```

---

### Task 7: Gộp phạt (penalty aggregation)

**Files:**
- Create: `traffic_es/engine/penalty.py`
- Test: `tests/test_penalty.py`

Quy tắc: **tiền phạt cộng dồn** các lỗi; **phạt bổ sung lấy nặng nhất** (tước GPLX dài nhất). Nếu có tình tiết tăng nặng (`pick == "max"`) thì mỗi lỗi lấy `tien_phat_max`, ngược lại lấy trung bình khung.

- [ ] **Step 1: Viết test thất bại**

```python
# tests/test_penalty.py
from traffic_es.engine.penalty import aggregate
from traffic_es.knowledge.rules import Rule, KetLuan, CanCu, PhatBoSung

def _rule(rid, tmin, tmax, tuoc=None):
    return Rule(id=rid, nhom="x", dieu_kien=[],
                ket_luan=KetLuan(hanh_vi=rid, tien_phat_min=tmin, tien_phat_max=tmax,
                                 phat_bo_sung=PhatBoSung(tuoc_gplx_thang=tuoc),
                                 can_cu=CanCu(nghi_dinh="168", dieu=6)))

def test_sum_avg_when_no_aggravation():
    res = aggregate([_rule("A", 10, 20), _rule("B", 30, 50)], pick=None)
    # trung bình khung: 15 + 40 = 55
    assert res.tong_tien == 55
    assert len(res.chi_tiet) == 2

def test_sum_max_when_aggravated():
    res = aggregate([_rule("A", 10, 20), _rule("B", 30, 50)], pick="max")
    assert res.tong_tien == 70   # 20 + 50

def test_supplementary_takes_longest_suspension():
    res = aggregate([_rule("A", 10, 20, tuoc=[10, 12]),
                     _rule("B", 30, 50, tuoc=[22, 24])], pick="max")
    assert res.tuoc_gplx_thang_max == 24
```

- [ ] **Step 2: Chạy test để xác nhận FAIL**

Run: `pytest tests/test_penalty.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Cài đặt tối thiểu**

```python
# traffic_es/engine/penalty.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
from traffic_es.knowledge.rules import Rule

@dataclass
class DongPhat:
    hanh_vi: str
    tien: int
    can_cu: str
    phat_bo_sung: str

@dataclass
class KetQua:
    chi_tiet: List[DongPhat] = field(default_factory=list)
    tong_tien: int = 0
    tuoc_gplx_thang_max: Optional[int] = None

def _tien_cua(rule: Rule, pick: Optional[str]) -> int:
    kl = rule.ket_luan
    if pick == "max":
        return kl.tien_phat_max
    if pick == "min":
        return kl.tien_phat_min
    return (kl.tien_phat_min + kl.tien_phat_max) // 2

def _can_cu_str(rule: Rule) -> str:
    c = rule.ket_luan.can_cu
    parts = [f"Điều {c.dieu}"]
    if c.khoan is not None:
        parts.append(f"Khoản {c.khoan}")
    if c.diem:
        parts.append(f"điểm {c.diem}")
    return f"{', '.join(parts)} — NĐ {c.nghi_dinh}"

def aggregate(rules: List[Rule], pick: Optional[str] = None) -> KetQua:
    res = KetQua()
    for r in rules:
        tien = _tien_cua(r, pick)
        tuoc = r.ket_luan.phat_bo_sung.tuoc_gplx_thang
        bs = f"tước GPLX {tuoc[1]} tháng" if tuoc else "—"
        res.chi_tiet.append(DongPhat(r.ket_luan.hanh_vi, tien, _can_cu_str(r), bs))
        res.tong_tien += tien
        if tuoc:
            res.tuoc_gplx_thang_max = max(res.tuoc_gplx_thang_max or 0, tuoc[1])
    return res
```

- [ ] **Step 4: Chạy test để xác nhận PASS**

Run: `pytest tests/test_penalty.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add traffic_es/engine/penalty.py tests/test_penalty.py
git commit -m "feat(engine): gộp phạt (tiền cộng dồn, bổ sung lấy nặng nhất)"
```

---

### Task 8: Reasoner (điều phối end-to-end)

**Files:**
- Create: `traffic_es/engine/reasoner.py`
- Test: `tests/test_reasoner.py`

- [ ] **Step 1: Viết test thất bại**

```python
# tests/test_reasoner.py
from pathlib import Path
from traffic_es.engine.reasoner import Reasoner

def test_end_to_end_con_oto():
    reasoner = Reasoner.from_rules_dir(Path("traffic_es/knowledge/rules"))
    facts = {"phuongtien.loai": "o_to", "chiso.nongDoCon_khiTho": 0.42,
             "tinhtiet.gay_tai_nan": True}
    res = reasoner.infer(facts)
    assert res.ket_qua.tong_tien == 40000000        # có tăng nặng -> mức max
    assert res.ket_qua.tuoc_gplx_thang_max == 24
    assert any("R_CON_OTO_MUC3" in s.data.get("rule_id", "")
               for s in res.trace.steps if s.kind == "RULE")
    assert any(s.kind == "META" for s in res.trace.steps)

def test_no_violation_returns_empty():
    reasoner = Reasoner.from_rules_dir(Path("traffic_es/knowledge/rules"))
    res = reasoner.infer({"phuongtien.loai": "o_to", "chiso.nongDoCon_khiTho": 0.0})
    assert res.ket_qua.chi_tiet == []
    assert res.ket_qua.tong_tien == 0
```

- [ ] **Step 2: Chạy test để xác nhận FAIL**

Run: `pytest tests/test_reasoner.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Cài đặt tối thiểu**

```python
# traffic_es/engine/reasoner.py
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List
from traffic_es.engine.working_memory import WorkingMemory
from traffic_es.engine.trace import Trace
from traffic_es.engine.funcs import Func, DEFAULT_FUNCS, apply_funcs
from traffic_es.engine.forward_chaining import deduce_rules, apply_meta
from traffic_es.engine.penalty import aggregate, KetQua
from traffic_es.knowledge.rules import Rule, MetaRule
from traffic_es.knowledge.kb_loader import load_kb

@dataclass
class InferResult:
    ket_qua: KetQua
    trace: Trace
    working_memory: Dict[str, Any]

class Reasoner:
    def __init__(self, rules: List[Rule], meta_rules: List[MetaRule],
                 funcs: List[Func] | None = None):
        self.rules = rules
        self.meta_rules = meta_rules
        self.funcs = funcs if funcs is not None else DEFAULT_FUNCS

    @classmethod
    def from_rules_dir(cls, rules_dir: Path) -> "Reasoner":
        rules, meta = load_kb(rules_dir)
        return cls(rules, meta)

    def infer(self, facts: Dict[str, Any]) -> InferResult:
        wm = WorkingMemory(facts)
        trace = Trace()
        apply_funcs(wm, self.funcs, trace)                 # Deduce_Objects
        fired = deduce_rules(wm, self.rules, trace)         # Deduce_Rules
        pick = apply_meta(wm, self.meta_rules, trace)       # Meta-rule
        ket_qua = aggregate(fired, pick)                    # Gộp phạt
        trace.add("KL", f"Tổng {len(fired)} lỗi; tổng tiền {ket_qua.tong_tien}",
                  {"so_loi": len(fired), "tong_tien": ket_qua.tong_tien})
        return InferResult(ket_qua, trace, wm.as_dict())
```

- [ ] **Step 4: Chạy test để xác nhận PASS**

Run: `pytest tests/test_reasoner.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Chạy toàn bộ test**

Run: `pytest -v`
Expected: PASS toàn bộ (tất cả task trước + task này).

- [ ] **Step 6: Commit**

```bash
git add traffic_es/engine/reasoner.py tests/test_reasoner.py
git commit -m "feat(engine): Reasoner điều phối Deduce_Objects→Rules→Meta→gộp phạt"
```

---

### Task 9: A\* tìm "lời giải tốt" trên mạng `(M,R)` (mức gọn)

**Files:**
- Create: `traffic_es/engine/astar.py`
- Test: `tests/test_astar.py`

Mô hình `(M, R)`: mỗi luật `r` có `inputs` (tập key cần có) → `output` (một key), trọng số `w`. Bài toán `(H, Goal)`: từ H (tập key đã biết) tìm **danh sách luật tối tiểu tổng trọng số nhỏ nhất** để suy ra tất cả key trong Goal. Heuristic `h(state)` = số key mục tiêu còn thiếu.

- [ ] **Step 1: Viết test thất bại**

```python
# tests/test_astar.py
from traffic_es.engine.astar import DedRule, astar_solve

def test_finds_minimal_chain():
    rules = [
        DedRule("r1", {"U", "I"}, "S", w=1),
        DedRule("r2", {"S", "cos"}, "P", w=1),
        DedRule("r3", {"U", "I", "cos"}, "P", w=5),  # đường tắt nhưng đắt
    ]
    sol = astar_solve(H={"U", "I", "cos"}, goal={"P"}, rules=rules)
    assert [r.id for r in sol] == ["r1", "r2"]   # tổng w=2 < 5

def test_unsolvable_returns_none():
    rules = [DedRule("r1", {"A"}, "B", w=1)]
    assert astar_solve(H={"X"}, goal={"B"}, rules=rules) is None

def test_goal_already_known_returns_empty():
    assert astar_solve(H={"P"}, goal={"P"}, rules=[]) == []
```

- [ ] **Step 2: Chạy test để xác nhận FAIL**

Run: `pytest tests/test_astar.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Cài đặt tối thiểu**

```python
# traffic_es/engine/astar.py
from __future__ import annotations
import heapq
from dataclasses import dataclass, field
from typing import List, Optional, Set

@dataclass(frozen=True)
class DedRule:
    id: str
    inputs: frozenset
    output: str
    w: float = 1.0
    def __init__(self, id, inputs, output, w=1.0):
        object.__setattr__(self, "id", id)
        object.__setattr__(self, "inputs", frozenset(inputs))
        object.__setattr__(self, "output", output)
        object.__setattr__(self, "w", w)

def _h(state: Set[str], goal: Set[str]) -> int:
    return len(goal - state)

def astar_solve(H: Set[str], goal: Set[str], rules: List[DedRule]) -> Optional[List[DedRule]]:
    """Trả về danh sách luật (lời giải tốt theo tổng trọng số nhỏ nhất), [] nếu Goal⊆H, None nếu vô nghiệm."""
    start = frozenset(H)
    goal = set(goal)
    if goal <= start:
        return []
    counter = 0
    # (f, g, counter, state, path)
    frontier = [(_h(set(start), goal), 0.0, counter, start, [])]
    best_g = {start: 0.0}
    while frontier:
        f, g, _, state, path = heapq.heappop(frontier)
        sset = set(state)
        if goal <= sset:
            return path
        for r in rules:
            if r.output in sset:
                continue
            if r.inputs <= sset:
                nstate = frozenset(sset | {r.output})
                ng = g + r.w
                if ng < best_g.get(nstate, float("inf")):
                    best_g[nstate] = ng
                    counter += 1
                    heapq.heappush(frontier, (ng + _h(set(nstate), goal), ng, counter, nstate, path + [r]))
    return None
```

- [ ] **Step 4: Chạy test để xác nhận PASS**

Run: `pytest tests/test_astar.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Chạy toàn bộ & commit**

Run: `pytest -q`
Expected: toàn bộ PASS.

```bash
git add traffic_es/engine/astar.py tests/test_astar.py
git commit -m "feat(engine): A* tìm lời giải tốt trên mạng (M,R)"
```

---

## Kết quả sau Plan 1
Một engine ký hiệu hoàn chỉnh, test bằng `pytest -q` (khoảng 25 test), demo được: `Reasoner.from_rules_dir(...).infer(facts)` trả về kết quả phạt + căn cứ + trace. Sẵn sàng cho Plan 2 (NLU/LLM) cắm Facts vào `infer()`.

## Ghi chú spec-coverage
- Legal-Onto Concept 5 thành phần: cấu trúc `Concept` đầy đủ sẽ thêm ở **Plan 2** (khi cần cho grounding/KG); Plan 1 tập trung Rules/Funcs của engine — đủ để suy diễn & test.
- Knowledge Graph + TF-IDF + đồ thị câu hỏi + LLM: **Plan 2**.
- Explanation generator (văn tiếng Việt) & UI: **Plan 3**. Trace ở Plan 1 là đầu vào cho generator đó.
