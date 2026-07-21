# Plan 4 — Mở rộng tri thức (KB đầy đủ hơn + OR + liên kết Nghị định)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development hoặc superpowers:executing-plans. Steps dùng checkbox `- [ ]`.

**Goal:** Nâng độ phủ KB của NĐ 168 (thêm tốc độ, mũ bảo hiểm, dây đai an toàn, vượt đèn đỏ, không GPLX), nâng độ trung thực (nồng độ cồn **máu HOẶC khí thở** qua điều kiện **OR**, trừ điểm GPLX trong kết quả), và thêm **lớp liên kết Nghị định** 168↔100↔123 + đường sắt. (Ưu tiên 1+2+3 người dùng duyệt; đánh giá hiệu năng dời sang Plan 5.)

**Architecture:** Mở rộng `engine.conditions` để hỗ trợ node điều kiện lồng `{any:[...]}` / `{all:[...]}` (đệ quy); `Rule.dieu_kien` nhận `str | dict`. Thêm Func `vuot_toc_do_kmh`. `penalty` bổ sung `tru_diem_max`. Data luật số hóa & kiểm chứng từ NĐ 168 thật. `knowledge/nghi_dinh_links.py` mô tả quan hệ hiệu lực giữa các NĐ.

**Tech Stack:** Python (venv sẵn), pydantic, pytest. Không phụ thuộc LLM.

---

### Task 0: Engine — điều kiện OR/AND lồng nhau + trừ điểm trong kết quả

**Files:** Modify `traffic_es/engine/conditions.py`, `traffic_es/knowledge/rules.py`, `traffic_es/engine/forward_chaining.py`, `traffic_es/engine/penalty.py` · Test `tests/test_conditions_nested.py`, `tests/test_penalty_trudiem.py`

- [ ] **Step 1: Viết test thất bại (điều kiện lồng)**

```python
# tests/test_conditions_nested.py
from traffic_es.engine.working_memory import WorkingMemory
from traffic_es.engine.conditions import eval_cond_node

def test_any_group():
    wm = WorkingMemory({"chiso.nongDoCon_mau": 90})
    node = {"any": ["chiso.nongDoCon_khiTho > 0.4", "chiso.nongDoCon_mau > 80"]}
    assert eval_cond_node(node, wm) is True

def test_all_group_nested_in_any():
    wm = WorkingMemory({"chiso.nongDoCon_mau": 60})
    node = {"any": [
        {"all": ["chiso.nongDoCon_khiTho > 0.25", "chiso.nongDoCon_khiTho <= 0.4"]},
        {"all": ["chiso.nongDoCon_mau > 50", "chiso.nongDoCon_mau <= 80"]},
    ]}
    assert eval_cond_node(node, wm) is True

def test_plain_string_still_works():
    wm = WorkingMemory({"chiso.tocDo": 90})
    assert eval_cond_node("chiso.tocDo > 50", wm) is True
```

- [ ] **Step 2: Chạy test (FAIL)** — `.venv/bin/python -m pytest tests/test_conditions_nested.py -q`

- [ ] **Step 3a: Bổ sung `eval_cond_node` vào conditions.py** (thêm cuối file, giữ `eval_condition` cũ)

```python
def eval_cond_node(node, wm) -> bool:
    """Đánh giá node điều kiện: str | {'any':[...]} | {'all':[...]} (đệ quy)."""
    if isinstance(node, str):
        return eval_condition(node, wm)
    if isinstance(node, dict):
        if "any" in node:
            return any(eval_cond_node(c, wm) for c in node["any"])
        if "all" in node:
            return all(eval_cond_node(c, wm) for c in node["all"])
    raise ValueError(f"Node điều kiện không hợp lệ: {node!r}")
```

- [ ] **Step 3b: Nới kiểu `Rule.dieu_kien`** trong `rules.py`
Đổi `from typing import List, Optional` → thêm `Union, Dict, Any`; đổi
`dieu_kien: List[str] = Field(default_factory=list)` →
`dieu_kien: List[Union[str, Dict[str, Any]]] = Field(default_factory=list)`
(MetaRule giữ `List[str]`.)

- [ ] **Step 3c: forward_chaining dùng eval_cond_node**
Trong `forward_chaining.py`: đổi import `from traffic_es.engine.conditions import eval_condition` → `eval_cond_node`; trong `deduce_rules` đổi `all(eval_condition(c, wm) ...)` → `all(eval_cond_node(c, wm) ...)`. (MetaRule vẫn dùng `eval_condition` cho chuỗi — sửa `apply_meta` giữ `eval_condition`; thêm import cả hai.)

- [ ] **Step 4: Viết test trừ điểm + cài đặt penalty**

```python
# tests/test_penalty_trudiem.py
from traffic_es.engine.penalty import aggregate
from traffic_es.knowledge.rules import Rule, KetLuan, CanCu, PhatBoSung

def _r(rid, diem):
    return Rule(id=rid, nhom="x", dieu_kien=[],
        ket_luan=KetLuan(hanh_vi=rid, tien_phat_min=1, tien_phat_max=2,
            phat_bo_sung=PhatBoSung(tru_diem=diem), can_cu=CanCu(nghi_dinh="168", dieu=6)))

def test_tru_diem_max():
    res = aggregate([_r("A", 4), _r("B", 10)], pick=None)
    assert res.tru_diem_max == 10
```

Trong `penalty.py`: thêm field `tru_diem_max: Optional[int] = None` vào `KetQua`; trong vòng lặp `aggregate`, sau xử lý `tuoc`:
```python
        if r.ket_luan.phat_bo_sung.tru_diem:
            res.tru_diem_max = max(res.tru_diem_max or 0, r.ket_luan.phat_bo_sung.tru_diem)
```
và trong `DongPhat.phat_bo_sung` ghép thêm trừ điểm khi có:
```python
        bs_parts = []
        if tuoc: bs_parts.append(f"tước GPLX {tuoc[1]} tháng")
        if r.ket_luan.phat_bo_sung.tru_diem: bs_parts.append(f"trừ {r.ket_luan.phat_bo_sung.tru_diem} điểm")
        bs = " · ".join(bs_parts) if bs_parts else "—"
```
(thay dòng `bs = ...` cũ.)

- [ ] **Step 5: Chạy 2 test mới + toàn bộ suite (PASS)**
`.venv/bin/python -m pytest -q`  (mọi test cũ vẫn xanh — thay đổi tương thích ngược)

- [ ] **Step 6: Commit**
```bash
git add traffic_es/engine/conditions.py traffic_es/knowledge/rules.py traffic_es/engine/forward_chaining.py traffic_es/engine/penalty.py tests/test_conditions_nested.py tests/test_penalty_trudiem.py
git commit -m "feat(engine): Task 0 — điều kiện OR/AND lồng nhau + trừ điểm trong kết quả"
```

---

### Task 1: Nồng độ cồn — hỗ trợ máu HOẶC khí thở (OR)

**Files:** Modify `traffic_es/knowledge/rules/nong_do_con.yaml`, `traffic_es/nlu/grounding.py` · Test `tests/test_con_mau.py`

Cập nhật 6 luật: mỗi mức dùng `dieu_kien` với **một node `any`** gồm nhánh khí thở và nhánh máu. Ngưỡng máu (mg/100ml): mức1 ≤50, mức2 50–80, mức3 >80 (đối chiếu văn bản).

- [ ] **Step 1: Viết test thất bại**

```python
# tests/test_con_mau.py
from pathlib import Path
from traffic_es.engine.reasoner import Reasoner

def test_con_mau_only():
    r = Reasoner.from_rules_dir(Path("traffic_es/knowledge/rules"))
    # chỉ có nồng độ cồn trong MÁU (không có khí thở)
    res = r.infer({"phuongtien.loai": "o_to", "chiso.nongDoCon_mau": 90})
    assert res.ket_qua.tong_tien == 35000000   # (30+40)/2 khung mức 3
    assert any(s.data.get("rule_id") == "R_CON_OTO_MUC3" for s in res.trace.steps if s.kind=="RULE")

def test_con_khiTho_still_works():
    r = Reasoner.from_rules_dir(Path("traffic_es/knowledge/rules"))
    res = r.infer({"phuongtien.loai": "o_to", "chiso.nongDoCon_khiTho": 0.42})
    assert res.ket_qua.chi_tiet[0].can_cu.startswith("Điều 6, Khoản 11")
```

- [ ] **Step 2: Chạy test (FAIL — vì mức 3 chưa khớp máu)**

- [ ] **Step 3a: Cập nhật `nong_do_con.yaml`** — đổi `dieu_kien` mỗi luật thành node `any` (khí thở OR máu). Ví dụ mức 3 ô tô:
```yaml
    dieu_kien:
      - any:
          - "chiso.nongDoCon_khiTho > 0.4"
          - "chiso.nongDoCon_mau > 80"
```
Mức 1 (ô tô & xe máy):
```yaml
    dieu_kien:
      - any:
          - all: ["chiso.nongDoCon_khiTho > 0", "chiso.nongDoCon_khiTho <= 0.25"]
          - all: ["chiso.nongDoCon_mau > 0", "chiso.nongDoCon_mau <= 50"]
```
Mức 2:
```yaml
    dieu_kien:
      - any:
          - all: ["chiso.nongDoCon_khiTho > 0.25", "chiso.nongDoCon_khiTho <= 0.4"]
          - all: ["chiso.nongDoCon_mau > 50", "chiso.nongDoCon_mau <= 80"]
```
(giữ nguyên `ket_luan`, `can_cu`, `id`, `ap_dung_loai_xe` của 6 luật.)

- [ ] **Step 3b: grounding.py** — thêm `"chiso.nongDoCon_mau": (0.0, 500.0)` vào `_RANGES`.

- [ ] **Step 4: Chạy test + suite (PASS)** · **Step 5: Commit**
```bash
git add traffic_es/knowledge/rules/nong_do_con.yaml traffic_es/nlu/grounding.py tests/test_con_mau.py
git commit -m "feat(kb): Task 1 — nồng độ cồn hỗ trợ máu HOẶC khí thở (điều kiện OR)"
```

---

### Task 2: Func vượt tốc độ (km/h) + nhóm TỐC ĐỘ (NĐ 168)

**Files:** Modify `traffic_es/engine/funcs.py` · Create `traffic_es/knowledge/rules/toc_do.yaml` · Test `tests/test_toc_do.py`

Số liệu kiểm chứng NĐ168: ô tô Đ6 (5–<10:800k–1tr K3a; 10–20:4–6tr K5đ; >20–35:6–8tr K6a; >35:12–14tr K7a); xe máy Đ7 (5–<10:400–600k K2b; 10–20:800k–1tr K4a; >20:6–8tr K8a).

- [ ] **Step 1: Thêm Func `vuot_toc_do_kmh` vào funcs.py**
```python
def _vuot_toc_do_kmh(wm):
    return wm.get("chiso.tocDo") - wm.get("chiso.tocDoGioiHan")
```
và thêm vào `DEFAULT_FUNCS`:
```python
    Func("vuot_toc_do_kmh", ["chiso.tocDo", "chiso.tocDoGioiHan"],
         "chiso.vuot_toc_do_kmh", _vuot_toc_do_kmh),
```

- [ ] **Step 2: Viết test thất bại**
```python
# tests/test_toc_do.py
from pathlib import Path
from traffic_es.engine.reasoner import Reasoner

def _infer(loai, tocDo, gh=50):
    r = Reasoner.from_rules_dir(Path("traffic_es/knowledge/rules"))
    return r.infer({"phuongtien.loai": loai, "chiso.tocDo": tocDo, "chiso.tocDoGioiHan": gh})

def test_oto_vuot_25kmh():
    res = _infer("o_to", 75)          # vượt 25 km/h -> mức >20-35
    assert res.ket_qua.tong_tien == 7000000    # (6+8)/2
def test_xemay_vuot_15kmh():
    res = _infer("xe_may", 65)        # vượt 15 -> mức 10-20
    assert res.ket_qua.chi_tiet[0].can_cu.startswith("Điều 7")
def test_khong_vuot():
    res = _infer("o_to", 52)          # vượt 2 km/h -> không thuộc mức phạt
    assert res.ket_qua.tong_tien == 0
```

- [ ] **Step 3: Chạy test (FAIL)** · Tạo `toc_do.yaml` với 7 luật (ô tô 4 mức + xe máy 3 mức), điều kiện dùng `chiso.vuot_toc_do_kmh` với khoảng `>=`/`<`; mỗi luật `can_cu` đúng Điều/Khoản/Điểm ở trên; ví dụ ô tô mức >20–35:
```yaml
  - id: R_TOCDO_OTO_M3
    nhom: toc_do
    ap_dung_loai_xe: [o_to]
    dieu_kien:
      - all: ["chiso.vuot_toc_do_kmh > 20", "chiso.vuot_toc_do_kmh <= 35"]
    ket_luan:
      hanh_vi: "Điều khiển ô tô chạy quá tốc độ quy định trên 20 km/h đến 35 km/h"
      tien_phat_min: 6000000
      tien_phat_max: 8000000
      phat_bo_sung: { tru_diem: 4 }
      can_cu: { nghi_dinh: "168/2024/NĐ-CP", dieu: 6, khoan: 6, diem: "a" }
```
(các luật còn lại theo bảng số liệu trên; mức thấp nhất dùng `>= 5` và `< 10`.)

- [ ] **Step 4: Chạy test + suite (PASS)** · **Step 5: Commit**
```bash
git add traffic_es/engine/funcs.py traffic_es/knowledge/rules/toc_do.yaml tests/test_toc_do.py
git commit -m "feat(kb): Task 2 — Func vượt tốc độ km/h + nhóm tốc độ NĐ168 (ô tô, xe máy)"
```

---

### Task 3: Các nhóm còn lại — mũ bảo hiểm, dây đai an toàn, vượt đèn đỏ, không GPLX

**Files:** Create `traffic_es/knowledge/rules/an_toan_tin_hieu.yaml` · Test `tests/test_nhom_khac.py`

Số liệu NĐ168: mũ bảo hiểm xe máy Đ7 K2h 400–600k; dây đai an toàn ô tô Đ6 K3k 800k–1tr; vượt đèn đỏ ô tô Đ6 K9b 18–20tr, xe máy Đ7 K7c 4–6tr; không GPLX ô tô Đ18 K9b 18–20tr, xe máy Đ18 K5a 2–4tr. Dùng Fact boolean: `nguoi.khong_mu_bao_hiem`, `nguoi.khong_day_an_toan`, `hanhvi.vuot_den_do`, `nguoi.coGPLX`.

- [ ] **Step 1: Viết test thất bại**
```python
# tests/test_nhom_khac.py
from pathlib import Path
from traffic_es.engine.reasoner import Reasoner
R = lambda: Reasoner.from_rules_dir(Path("traffic_es/knowledge/rules"))

def test_mu_bao_hiem():
    res = R().infer({"phuongtien.loai": "xe_may", "nguoi.khong_mu_bao_hiem": True})
    assert res.ket_qua.chi_tiet[0].can_cu.startswith("Điều 7")
def test_vuot_den_do_oto():
    res = R().infer({"phuongtien.loai": "o_to", "hanhvi.vuot_den_do": True})
    assert res.ket_qua.tong_tien == 19000000     # (18+20)/2
def test_khong_gplx_xemay():
    res = R().infer({"phuongtien.loai": "xe_may", "nguoi.coGPLX": False})
    assert res.ket_qua.tong_tien == 3000000      # (2+4)/2
```

- [ ] **Step 2: Chạy test (FAIL)** · Tạo `an_toan_tin_hieu.yaml` với các luật:
  - `R_MU_XEMAY` (xe_may, `nguoi.khong_mu_bao_hiem == true`, 400–600k, trừ điểm nếu có, Đ7 K2 đ.h)
  - `R_DAY_OTO` (o_to, `nguoi.khong_day_an_toan == true`, 800k–1tr, Đ6 K3 đ.k)
  - `R_DENDO_OTO` (o_to, `hanhvi.vuot_den_do == true`, 18–20tr, trừ điểm, Đ6 K9 đ.b)
  - `R_DENDO_XEMAY` (xe_may, `hanhvi.vuot_den_do == true`, 4–6tr, Đ7 K7 đ.c)
  - `R_NOGPLX_OTO` (o_to, `nguoi.coGPLX == false`, 18–20tr, Đ18 K9 đ.b)
  - `R_NOGPLX_XEMAY` (xe_may, `nguoi.coGPLX == false`, 2–4tr, Đ18 K5 đ.a)

- [ ] **Step 3: Chạy test + suite (PASS)** · **Step 4: Cập nhật grounding** thêm namespace `hanhvi.` vào `_KNOWN_PREFIX` (grounding.py) và integrity test namespaces. · **Step 5: Commit**
```bash
git add traffic_es/knowledge/rules/an_toan_tin_hieu.yaml traffic_es/nlu/grounding.py tests/test_nhom_khac.py tests/test_kb_integrity.py
git commit -m "feat(kb): Task 3 — mũ bảo hiểm, dây an toàn, vượt đèn đỏ, không GPLX (NĐ168)"
```

---

### Task 4: Lớp liên kết Nghị định (168 ↔ 100 ↔ 123)

**Files:** Create `traffic_es/knowledge/nghi_dinh_links.py`, `traffic_es/knowledge/nghi_dinh_links.yaml` · Test `tests/test_nd_links.py`

- [ ] **Step 1: Viết test thất bại**
```python
# tests/test_nd_links.py
from pathlib import Path
from traffic_es.knowledge.nghi_dinh_links import NghiDinhLinks

def test_168_supersedes_100_duongbo():
    links = NghiDinhLinks.load(Path("traffic_es/knowledge/nghi_dinh_links.yaml"))
    assert links.hieu_luc_hien_hanh("duong_bo") == "168/2024/NĐ-CP"
    assert "100/2019/NĐ-CP" in links.bi_thay_the_boi("168/2024/NĐ-CP")

def test_100_con_hieu_luc_duongsat():
    links = NghiDinhLinks.load(Path("traffic_es/knowledge/nghi_dinh_links.yaml"))
    assert links.hieu_luc_hien_hanh("duong_sat") == "100/2019/NĐ-CP"
```

- [ ] **Step 2: Chạy test (FAIL)** · Tạo data + module:

```yaml
# traffic_es/knowledge/nghi_dinh_links.yaml
nghi_dinh:
  - id: "100/2019/NĐ-CP"
    ten: "Xử phạt VPHC lĩnh vực giao thông đường bộ và đường sắt"
    linh_vuc: [duong_bo, duong_sat]
    hieu_luc: "một phần"   # đường bộ đã bị thay thế
  - id: "123/2021/NĐ-CP"
    ten: "Sửa đổi, bổ sung NĐ 100/2019"
    sua_doi: "100/2019/NĐ-CP"
    hieu_luc: "một phần"
  - id: "168/2024/NĐ-CP"
    ten: "Xử phạt VPHC về TTATGT đường bộ; trừ điểm GPLX"
    linh_vuc: [duong_bo]
    hieu_luc: "hiện hành"
    thay_the: ["100/2019/NĐ-CP", "123/2021/NĐ-CP"]   # phần đường bộ, từ 01/01/2025
hieu_luc_theo_linh_vuc:
  duong_bo: "168/2024/NĐ-CP"
  duong_sat: "100/2019/NĐ-CP"
```

```python
# traffic_es/knowledge/nghi_dinh_links.py
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List
import yaml

@dataclass
class NghiDinhLinks:
    items: List[dict]
    hieu_luc_map: Dict[str, str]

    @classmethod
    def load(cls, path: Path) -> "NghiDinhLinks":
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        return cls(raw.get("nghi_dinh", []), raw.get("hieu_luc_theo_linh_vuc", {}))

    def hieu_luc_hien_hanh(self, linh_vuc: str) -> str:
        return self.hieu_luc_map.get(linh_vuc, "")

    def bi_thay_the_boi(self, nghi_dinh_id: str) -> List[str]:
        for it in self.items:
            if it["id"] == nghi_dinh_id:
                return it.get("thay_the", [])
        return []
```

- [ ] **Step 3: Chạy test + suite (PASS)** · **Step 4: Commit**
```bash
git add traffic_es/knowledge/nghi_dinh_links.py traffic_es/knowledge/nghi_dinh_links.yaml tests/test_nd_links.py
git commit -m "feat(kb): Task 4 — lớp liên kết Nghị định 168↔100↔123 + đường sắt"
```

---

### Task 5: Kiểm tra tổng + demo mở rộng

- [ ] **Step 1: Chạy toàn bộ suite** — `.venv/bin/python -m pytest -q` (mọi test xanh)
- [ ] **Step 2: Đếm coverage KB** — script in tổng số luật theo nhóm.
- [ ] **Step 3: Demo đa nhóm** — vài tình huống (cồn máu, tốc độ, vượt đèn đỏ + không mũ) → in kết quả gộp phạt.
- [ ] **Step 4: Commit** (nếu có script demo/eval nhỏ)

---

## Kết quả sau Plan 4
KB phủ **nhiều nhóm hành vi chính của NĐ 168** (nồng độ cồn máu/khí thở, tốc độ 4/3 mức, mũ bảo hiểm, dây an toàn, vượt đèn đỏ, không GPLX), engine hỗ trợ **điều kiện OR** + **trừ điểm**, và có **lớp liên kết Nghị định**. Sẵn sàng cho Plan 5 (đánh giá hiệu năng) trên KB phong phú.

## Spec-coverage
- Ưu tiên (1) mở rộng NĐ168: Task 2, 3. · (2) OR + cồn máu: Task 0, 1. · (3) liên kết NĐ: Task 4.
- Còn lại (Plan 5): bộ testset + metrics + báo cáo hiệu năng.
