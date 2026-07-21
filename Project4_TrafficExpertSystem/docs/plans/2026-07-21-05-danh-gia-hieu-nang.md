# Plan 5 — Đánh giá hiệu năng (Evaluation)

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans / subagent-driven-development. Steps dùng checkbox `- [ ]`.

**Goal:** Đáp ứng yêu cầu sản phẩm 4c của đề — bộ **testset gán nhãn vàng** + **bộ chỉ số** (độ chính xác trích xuất / kết luận / căn cứ pháp lý; thời gian NLU vs engine) + **báo cáo tự động** (markdown + HTML).

**Architecture:** `eval/testset.jsonl` (gold) → `eval/metrics.py` (hàm đo thuần, TDD) → `eval/runner.py` (chạy `TrafficESService` trên từng case, so với gold, gom số liệu + đo thời gian) → `eval/report.py` (sinh báo cáo). `eval/run_eval.py` là entrypoint tạo file báo cáo.

**Tech Stack:** Python (venv sẵn), pytest. Không phụ thuộc LLM (dùng HeuristicExtractor để số liệu tái lập được).

---

### Task 0: Gói eval + testset gold + loader

**Files:** Create `eval/__init__.py`, `eval/testset.jsonl`, `eval/dataset.py` · Test `tests/test_eval_dataset.py`

Mỗi dòng JSONL: `{"id","text","expected":{"facts":{...},"rule_ids":[...],"tong_tien":N}}`.

- [ ] **Step 1: Viết test thất bại**

```python
# tests/test_eval_dataset.py
from pathlib import Path
from eval.dataset import load_cases

def test_load_cases():
    cases = load_cases(Path("eval/testset.jsonl"))
    assert len(cases) >= 15
    c = cases[0]
    assert c.id and c.text and "rule_ids" in c.expected
```

- [ ] **Step 2: Chạy test (FAIL)**

- [ ] **Step 3a: Cài đặt loader**

```python
# eval/dataset.py
from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

@dataclass
class Case:
    id: str
    text: str
    expected: Dict[str, Any]

def load_cases(path: Path) -> List[Case]:
    out: List[Case] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("//"):
            continue
        d = json.loads(line)
        out.append(Case(d["id"], d["text"], d["expected"]))
    return out
```

- [ ] **Step 3b: Tạo `eval/testset.jsonl`** — tối thiểu 18 case gold trải các nhóm (cồn khí thở/máu, tốc độ ô tô/xe máy, mũ, đèn đỏ, GPLX, đa lỗi, tình tiết tăng nặng, ca không vi phạm). Ví dụ vài dòng (điền đủ ≥18):
```
{"id":"c01","text":"Tôi lái ô tô, thổi nồng độ cồn 0.42 mg/l","expected":{"facts":{"phuongtien.loai":"o_to","chiso.nongDoCon_khiTho":0.42},"rule_ids":["R_CON_OTO_MUC3"],"tong_tien":35000000}}
{"id":"c02","text":"Đi xe máy nồng độ cồn trong máu 60 mg/100ml","expected":{"facts":{"phuongtien.loai":"xe_may"},"rule_ids":["R_CON_XEMAY_MUC2"],"tong_tien":7000000}}
{"id":"c03","text":"Ô tô chạy 75 km/h khu dân cư giới hạn 50","expected":{"facts":{"phuongtien.loai":"o_to"},"rule_ids":["R_TOCDO_OTO_M3"],"tong_tien":7000000}}
{"id":"c04","text":"Chạy xe máy không đội mũ bảo hiểm","expected":{"facts":{"phuongtien.loai":"xe_may","nguoi.khong_mu_bao_hiem":true},"rule_ids":["R_MU_XEMAY"],"tong_tien":500000}}
{"id":"c05","text":"Ô tô vượt đèn đỏ","expected":{"facts":{"phuongtien.loai":"o_to","hanhvi.vuot_den_do":true},"rule_ids":["R_DENDO_OTO"],"tong_tien":19000000}}
{"id":"c06","text":"Tôi lái ô tô, nồng độ cồn 0.42 mg/l, rồi đâm vào một xe máy","expected":{"facts":{"phuongtien.loai":"o_to","tinhtiet.gay_tai_nan":true},"rule_ids":["R_CON_OTO_MUC3"],"tong_tien":40000000}}
{"id":"c07","text":"Lái ô tô bình thường không vi phạm gì","expected":{"facts":{"phuongtien.loai":"o_to"},"rule_ids":[],"tong_tien":0}}
```
(bổ sung tới ≥18 case; với case cần suy tình tiết dùng động từ va chạm; case tốc độ nêu rõ "giới hạn N" để HeuristicExtractor bắt được — nêu hạn chế suy giới hạn trong báo cáo.)

- [ ] **Step 4: Chạy test (PASS)** · **Step 5: Commit**
```bash
git add eval/__init__.py eval/dataset.py eval/testset.jsonl tests/test_eval_dataset.py
git commit -m "feat(eval): Task 0 — testset gold JSONL + loader"
```

---

### Task 1: Hàm đo chỉ số

**Files:** Create `eval/metrics.py` · Test `tests/test_metrics.py`

- [ ] **Step 1: Viết test thất bại**

```python
# tests/test_metrics.py
from eval.metrics import slot_prf, set_match

def test_slot_prf_perfect():
    p, r, f = slot_prf({"a": 1, "b": 2}, {"a": 1, "b": 2})
    assert (p, r, f) == (1.0, 1.0, 1.0)

def test_slot_prf_partial():
    # dự đoán thiếu 1 slot, thừa 1 slot sai
    p, r, f = slot_prf(pred={"a": 1, "c": 9}, gold={"a": 1, "b": 2})
    assert r == 0.5 and p == 0.5

def test_set_match_exact():
    assert set_match(["R1", "R2"], ["R2", "R1"]) == 1.0
    assert set_match([], []) == 1.0
    assert set_match(["R1"], ["R1", "R2"]) == 0.0
```

- [ ] **Step 2: Chạy test (FAIL)**

- [ ] **Step 3: Cài đặt**

```python
# eval/metrics.py
from __future__ import annotations
from typing import Any, Dict, List, Tuple

def slot_prf(pred: Dict[str, Any], gold: Dict[str, Any]) -> Tuple[float, float, float]:
    """Precision/Recall/F1 theo cặp (key,value) đúng."""
    correct = sum(1 for k, v in gold.items() if k in pred and pred[k] == v)
    p = correct / len(pred) if pred else (1.0 if not gold else 0.0)
    r = correct / len(gold) if gold else 1.0
    f = 2 * p * r / (p + r) if (p + r) else 0.0
    return p, r, f

def set_match(pred: List[str], gold: List[str]) -> float:
    """1.0 nếu tập bằng nhau, ngược lại 0.0 (exact-set)."""
    return 1.0 if set(pred) == set(gold) else 0.0
```

- [ ] **Step 4: Chạy test (PASS)** · **Step 5: Commit**
```bash
git add eval/metrics.py tests/test_metrics.py
git commit -m "feat(eval): Task 1 — chỉ số slot P/R/F1 + set-match kết luận"
```

---

### Task 2: Runner đánh giá

**Files:** Create `eval/runner.py` · Test `tests/test_eval_runner.py`

- [ ] **Step 1: Viết test thất bại**

```python
# tests/test_eval_runner.py
from pathlib import Path
from eval.dataset import Case
from eval.runner import evaluate

def test_evaluate_aggregates():
    cases = [Case("c01", "Tôi lái ô tô, thổi nồng độ cồn 0.42 mg/l",
                  {"facts": {"phuongtien.loai": "o_to", "chiso.nongDoCon_khiTho": 0.42},
                   "rule_ids": ["R_CON_OTO_MUC3"], "tong_tien": 35000000})]
    rep = evaluate(cases, Path("traffic_es/knowledge/rules"))
    assert rep["n"] == 1
    assert rep["conclusion_acc"] == 1.0
    assert rep["money_acc"] == 1.0
    assert rep["per_case"][0]["fired"] == ["R_CON_OTO_MUC3"]
```

- [ ] **Step 2: Chạy test (FAIL)**

- [ ] **Step 3: Cài đặt**

```python
# eval/runner.py
from __future__ import annotations
import time
from pathlib import Path
from typing import Any, Dict, List

from traffic_es.service import TrafficESService
from traffic_es.nlu.pipeline import NLUPipeline
from traffic_es.engine.reasoner import Reasoner
from eval.dataset import Case
from eval.metrics import slot_prf, set_match

def evaluate(cases: List[Case], rules_dir: Path) -> Dict[str, Any]:
    svc = TrafficESService(Reasoner.from_rules_dir(rules_dir), NLUPipeline())
    per: List[Dict[str, Any]] = []
    for c in cases:
        t0 = time.perf_counter()
        facts, meta = svc.nlu.run(c.text)
        t1 = time.perf_counter()
        res = svc.reasoner.infer(facts)
        t2 = time.perf_counter()
        fired = [s.data.get("rule_id") for s in res.trace.steps if s.kind == "RULE"]
        p, r, f = slot_prf(facts, c.expected.get("facts", {}))
        per.append({
            "id": c.id, "fired": fired,
            "conclusion": set_match(fired, c.expected.get("rule_ids", [])),
            "money_ok": 1.0 if res.ket_qua.tong_tien == c.expected.get("tong_tien") else 0.0,
            "slot_p": p, "slot_r": r, "slot_f": f,
            "t_nlu_ms": (t1 - t0) * 1000, "t_engine_ms": (t2 - t1) * 1000,
        })
    n = len(per) or 1
    agg = lambda k: sum(x[k] for x in per) / n
    return {
        "n": len(per),
        "conclusion_acc": agg("conclusion"),
        "money_acc": agg("money_ok"),
        "slot_f1": agg("slot_f"),
        "avg_t_nlu_ms": agg("t_nlu_ms"),
        "avg_t_engine_ms": agg("t_engine_ms"),
        "per_case": per,
    }
```

- [ ] **Step 4: Chạy test (PASS)** · **Step 5: Commit**
```bash
git add eval/runner.py tests/test_eval_runner.py
git commit -m "feat(eval): Task 2 — runner chạy service trên testset + gom chỉ số + thời gian"
```

---

### Task 3: Sinh báo cáo (markdown + HTML)

**Files:** Create `eval/report.py` · Test `tests/test_eval_report.py`

- [ ] **Step 1: Viết test thất bại**

```python
# tests/test_eval_report.py
from eval.report import to_markdown

def test_markdown_has_metrics():
    rep = {"n": 10, "conclusion_acc": 0.9, "money_acc": 0.8, "slot_f1": 0.85,
           "avg_t_nlu_ms": 1.2, "avg_t_engine_ms": 0.3, "per_case": []}
    md = to_markdown(rep)
    assert "90.0%" in md and "Kết luận" in md
```

- [ ] **Step 2: Chạy test (FAIL)**

- [ ] **Step 3: Cài đặt**

```python
# eval/report.py
from __future__ import annotations
from typing import Any, Dict

def _pct(x: float) -> str:
    return f"{x * 100:.1f}%"

def to_markdown(rep: Dict[str, Any]) -> str:
    lines = [
        "# Báo cáo đánh giá hiệu năng — Hệ chuyên gia luật giao thông",
        "",
        f"- Số ca kiểm thử: **{rep['n']}**",
        "",
        "| Chỉ số | Giá trị |",
        "|---|---|",
        f"| Độ chính xác **Kết luận** (đúng tập hành vi) | {_pct(rep['conclusion_acc'])} |",
        f"| Độ chính xác **Mức phạt** (đúng tổng tiền) | {_pct(rep['money_acc'])} |",
        f"| **F1 trích xuất Facts** (slot) | {_pct(rep['slot_f1'])} |",
        f"| Thời gian NLU trung bình | {rep['avg_t_nlu_ms']:.2f} ms |",
        f"| Thời gian engine trung bình | {rep['avg_t_engine_ms']:.2f} ms |",
        "",
        "## Chi tiết theo ca",
        "",
        "| Ca | Kết luận | Mức phạt | Slot F1 |",
        "|---|---|---|---|",
    ]
    for c in rep.get("per_case", []):
        lines.append(
            f"| {c['id']} | {'✔' if c['conclusion'] else '�’'} | "
            f"{'✔' if c['money_ok'] else '✗'} | {c['slot_f']*100:.0f}% |"
        )
    return "\n".join(lines)
```

- [ ] **Step 4: Chạy test (PASS)** · **Step 5: Commit**
```bash
git add eval/report.py tests/test_eval_report.py
git commit -m "feat(eval): Task 3 — sinh báo cáo markdown chỉ số hiệu năng"
```

---

### Task 4: Entrypoint chạy đánh giá thật + báo cáo

**Files:** Create `eval/run_eval.py` · Output `docs/bao-cao-hieu-nang.md`

- [ ] **Step 1: Cài đặt entrypoint**

```python
# eval/run_eval.py
from __future__ import annotations
from pathlib import Path
from eval.dataset import load_cases
from eval.runner import evaluate
from eval.report import to_markdown

ROOT = Path(__file__).resolve().parent.parent

def main() -> None:
    cases = load_cases(ROOT / "eval" / "testset.jsonl")
    rep = evaluate(cases, ROOT / "traffic_es" / "knowledge" / "rules")
    md = to_markdown(rep)
    out = ROOT / "docs" / "bao-cao-hieu-nang.md"
    out.write_text(md, encoding="utf-8")
    print(md)
    print(f"\n>> Đã ghi báo cáo: {out}")

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Chạy đánh giá thật**
```bash
.venv/bin/python -m eval.run_eval
```
Quan sát số liệu thật (độ chính xác kết luận/mức phạt/slot F1, thời gian). Nếu ca nào sai do HeuristicExtractor (vd không bắt được giới hạn tốc độ), ghi nhận là **hạn chế đã biết** trong báo cáo (không sửa nhãn gold cho khớp).

- [ ] **Step 3: Chạy toàn bộ suite** — `.venv/bin/python -m pytest -q`
- [ ] **Step 4: Commit báo cáo**
```bash
git add eval/run_eval.py docs/bao-cao-hieu-nang.md
git commit -m "feat(eval): Task 4 — entrypoint chạy đánh giá + báo cáo hiệu năng thật"
```

---

## Kết quả sau Plan 5
Bộ khung đánh giá hoàn chỉnh + báo cáo hiệu năng thật trên testset gold — hoàn tất **yêu cầu sản phẩm 4c**. Cùng với chatbot (4a) và giải thích (4b), đủ 3 yêu cầu sản phẩm của đề. (Tùy chọn nâng cấp: biểu đồ matplotlib, cắm LLMExtractor để so heuristic vs LLM.)
