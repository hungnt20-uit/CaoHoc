# Đặc tả thiết kế (Design Spec)
# Project 4 — Hệ thống Chuyên gia Tư vấn Hành vi Vi phạm Luật Giao thông dựa trên Reasoning

- **Môn học:** Chuyên đề Tri thức và Ứng dụng (Cao học — UIT)
- **Ngày:** 2026-07-20
- **Khung lý thuyết áp dụng:** Legal-Onto (`𝒦 = (Conc, Rel, Rules) ⊕ (Keyphrases, Rela)`) + Mạng tính toán `(M, R)` với mô hình bài toán `(H, Goal)` + Pipeline đồ thị câu hỏi (Question-Graph / Subgraph Matching) — theo trường phái PGS.TS. Nguyễn Đình Hiển.
- **Kiến trúc:** Neuro-symbolic (Hybrid) — LLM lo ngôn ngữ, engine ký hiệu lo pháp lý + giải thích.

---

## 1. Mục tiêu & Phạm vi

### 1.1. Mục tiêu
Xây dựng Hệ chuyên gia có khả năng **suy luận ngữ nghĩa tự động**: nhận mô tả hiện trường bằng **ngôn ngữ tự nhiên tiếng Việt (kể cả câu phức tạp)** → tự động tổng hợp **tình tiết tăng nặng/giảm nhẹ** → đưa ra **quyết định xử phạt** kèm **căn cứ pháp lý (Điều/Khoản/Điểm của Nghị định)** và **chuỗi giải thích minh bạch**.

### 1.2. Sản phẩm bắt buộc (theo đề)
1. Giao diện chatbot xử lý ngôn ngữ tự nhiên tiếng Việt phức tạp.
2. Cơ chế giải thích chuỗi suy luận (Explainable AI): chỉ rõ *tại sao* quy ra lỗi đó và *áp dụng điều khoản nào*.
3. Báo cáo thử nghiệm hiệu năng.

### 1.3. Nguyên tắc kiến trúc (bất biến)
- **Mọi quyết định phạt do engine ký hiệu quyết định**, không để LLM tự sinh con số/căn cứ.
- **Truy xuất nguồn 100%**: mỗi kết luận gắn đúng Điều/Khoản/Điểm văn bản gốc.
- **Chống "ảo giác" pháp lý**: LLM đề xuất → validator ontology phê duyệt.
- **Ánh xạ thuật ngữ**: ngôn ngữ đời thường của dân → thuật ngữ chuẩn trong luật.

### 1.4. Quyết định đã chốt
- Sản phẩm: **hệ thống chạy thật đầy đủ**.
- Ngôn ngữ lập trình: **Python**.
- LLM: **API trả phí** (OpenAI/Claude/Gemini), có lớp trừu tượng để đổi provider.
- Nguồn luật: **người dùng cung cấp** văn bản Nghị định 100/2019, 123/2021, 168/2024.
- Giao tiếp: **tiếng Việt là chính**, xử lý tốt tiếng Việt phức tạp.
- A\*: **hiện thực ở mức gọn**; gộp phạt trình bày **rõ ràng, dễ hiểu**.

---

## 2. Nền tảng tri thức: Mô hình Legal-Onto

Mô hình tri thức tuân theo Legal-Onto:

```
𝒦 = (Conc, Rel, Rules) ⊕ (Keyphrases, Rela)
     └──── Rela-model ────┘   └── Knowledge Graph ──┘
```

### 2.1. Concept (khái niệm) — cấu trúc 5 thành phần
Mỗi concept: **`(Name, Content, InnerRul, Attrs, Keyphrases)`**

| Thành phần | Ý nghĩa | Ví dụ (concept "Xe mô tô") |
|---|---|---|
| `Name` | Tên khái niệm | "xe mô tô" |
| `Content` | Định nghĩa/nội dung | "Phương tiện giao thông cơ giới đường bộ hai/ba bánh…" |
| `InnerRul` | Căn cứ pháp lý gắn trong concept | Điều 3.39, QCVN 41:2016/BGTVT |
| `Attrs` | Thuộc tính/khái niệm con | dung tích xi-lanh, trọng lượng |
| `Keyphrases` | Cụm từ khóa (cho KG & so khớp) | ["xe máy", "mô tô", "xe gắn máy"] |

**Danh mục Concept của miền giao thông:**
`PhuongTien`, `NguoiDieuKhien`, `HanhVi`, `ChiSo` (đo lường), `BoiCanh`, `TinhTiet`, `HinhPhat`.

**Thuộc tính chính (Attrs) theo Concept:**
- `PhuongTien`: loai {ô tô, xe máy, xe máy chuyên dùng, xe đạp…}, taiTrong, soChoNgoi.
- `NguoiDieuKhien`: coGPLX, hangGPLX, tuoi, diemGPLX_conLai.
- `HanhVi`: ma, moTa, nhom {nồng độ cồn, tốc độ, tín hiệu, làn, giấy tờ…}.
- `ChiSo`: nongDoCon_khiTho (mg/l), nongDoCon_mau (mg/100ml), tocDo (km/h), tocDoGioiHan.
- `BoiCanh`: khuVuc {khu dân cư, cao tốc, đô thị…}, thoiDiem, thoiTiet, bienBao.
- `TinhTiet`: loai {tăng nặng / giảm nhẹ}, ma, moTa.
- `HinhPhat`: tienPhat_min, tienPhat_max, phatBoSung {tước GPLX, trừ điểm, tạm giữ xe}, canCu {nghiDinh, dieu, khoan, diem}.

### 2.2. Relation (quan hệ) — 3 nhóm
- `R_hier`: quan hệ phân cấp `is-a`, `has-a` (vd: *xe máy* is-a *phương tiện*).
- `R_con`: quan hệ kết nối `a-part-of` và quan hệ nhị phân khác.
- `R_Phrases`: quan hệ giữa keyphrase và concept (vd: "điều khiển" relates-to "xe máy").
- Quan hệ nghiệp vụ: `viPham`, `dieuKhien`, `apDungCho`, `dan_den`, `quyDinhBoi`, `dieuChinh`.

### 2.3. Knowledge Graph (Keyphrases, Rela)
- Node = concept/thực thể; cạnh = quan hệ.
- Mỗi keyphrase gán **trọng số TF-IDF** để đo tầm quan trọng, phục vụ so khớp câu hỏi.
- Tối ưu đồ thị: loại bộ ba vô nghĩa (TF-IDF thấp), gộp bộ ba tương đương (cosine embedding PhoBERT ≥ α, α≈0.6–0.8).

### 2.4. Rules — định dạng luật (YAML)
Mỗi hành vi vi phạm = 1 rule, ánh xạ 1–1 tới Điều/Khoản/Điểm:

```yaml
- id: R_CON_OTO_MUC3
  nhom: nong_do_con
  ap_dung_loai_xe: [o_to]
  dieu_kien:                         # LHS
    - chiso.nongDoCon_khiTho > 0.4     # hoặc nongDoCon_mau > 80
  ket_luan:                          # RHS
    hanh_vi: "Điều khiển ô tô mà trong hơi thở có nồng độ cồn vượt quá 0,4 mg/l"
    tien_phat_min: 30000000
    tien_phat_max: 40000000
    phat_bo_sung: { tuoc_gplx_thang: [22, 24], tru_diem: null }
    can_cu: { nghi_dinh: "168/2024/NĐ-CP", dieu: 6, khoan: 11, diem: "a" }
  giai_thich_mau: "Nồng độ cồn {gt} mg/l > 0,4 mg/l → khung phạt cao nhất."

# Meta-rule điều chỉnh khung phạt theo tình tiết
- id: M_TANG_NANG_TAI_NAN
  loai: tinh_tiet
  dieu_kien: [ "tinhtiet.gay_tai_nan == true" ]
  hieu_ung: { chon_muc: "max", ghi_chu: "Tình tiết tăng nặng: áp mức tiền tối đa của khung" }
```

> ⚠️ Con số ví dụ là minh họa; **thay bằng số chính xác từ văn bản Nghị định** khi số hóa.

---

## 3. Số hóa tri thức (Knowledge Acquisition) — Quy trình Text Mining

Xây KB từ văn bản Nghị định theo quy trình khai thác văn bản 5 bước:
1. **Tiền xử lý:** tách câu/từ (tokenization), POS tagging, chunking. Công cụ tiếng Việt: `underthesea` / `VnCoreNLP` / **PhoBERT**.
2. **Trích xuất bộ ba/keyphrase:** dependency parsing → (Chủ thể, Quan hệ, Đối tượng); trích keyphrase pháp lý. **LLM hỗ trợ** trích luật (điều kiện → hình phạt → căn cứ).
3. **Chọn lọc:** loại từ dừng, tính TF-IDF, gộp keyphrase đồng nghĩa.
4. **Xây KB:** đổ vào Concept/Relation/Rules + Knowledge Graph; **chuyên gia rà soát** (human-in-the-loop) để đảm bảo chính xác pháp lý.
5. **Xuất artifact:** `rules/*.yaml`, `ontology.owl` (owlready2/rdflib — mở bằng Protégé), đồ thị KG.

**Phạm vi ban đầu:** ưu tiên các nhóm hành vi phổ biến/nhiều tình tiết (nồng độ cồn, tốc độ, tín hiệu đèn, làn đường, giấy tờ, mũ bảo hiểm/dây an toàn), mở rộng dần.

---

## 4. Engine suy diễn — Mạng tính toán `(M, R)`

### 4.1. Hình thức luận (đúng môn học)
- **Mạng:** `(M, R)` — `M` = tập biến/thuộc tính (M = M_num ∪ M_func), `R` = tập luật. Mỗi luật `r`: đẳng thức giữa biến, hoặc luật dẫn `u(r) → v(r)`.
- **Mô hình bài toán:** `(H, Goal)` — `H` = giả thiết (Facts hiện trường), `Goal = ("KEYWORD", ListObj)` với KEYWORD ∈ {"Tìm", "Tính", "Chứng minh"}.
- **Lời giải:** danh sách luật `S = [r₁, …, r_k]` sao cho `S(H) = r_k(…r₁(H)…) ⊨ Goal`. **"Lời giải tốt"** = không có tập con nào của `S` cũng là lời giải (tối tiểu).
- **Mẫu bài toán `(Mp, Goal, Sol)`:** lưu các tình huống phạt điển hình làm case-based reasoning.

### 4.2. Chu trình suy diễn (Deduce_Objects + Deduce_Rules)
```
INFER(H=Facts, KB):
  WM ← H ; Trace ← []
  # (1) DEDUCE_OBJECTS — chạy Funcs tính thuộc tính dẫn xuất tới điểm bất động
  #     vd: vuot_toc_do_% = (tocDo - tocDoGioiHan)/tocDoGioiHan; đổi nồng độ cồn máu↔khí thở
  repeat: for f in KB.Funcs: if f.inputs⊆WM and f.output∉WM: WM∪={f.out}; Trace+=FUNC
  until fixpoint
  # (2) DEDUCE_RULES — forward chaining, so khớp ngưỡng số/logic
  ViPham ← [ r for r in KB.Rules if MATCH(r.dieu_kien, WM) ] ; Trace += RULE_FIRED
  # (3) Meta-rule tình tiết tăng nặng/giảm nhẹ
  for vp in ViPham: for m in KB.MetaRules: if MATCH(m,WM): vp.hp=ADJUST(vp.hp,m); Trace+=META
  # (4) Tổng hợp
  return KETLUAN(ViPham, Trace)
```
- Bước (1) = **Deduce_Objects** (tính nội tại đối tượng); Bước (2) = **Deduce_Rules** (áp luật). Vòng lặp tới **điểm bất động** ⇒ đảm bảo tính dừng & đầy đủ trên tập luật hữu hạn.

### 4.3. A\* tìm "lời giải tốt" (mức gọn) — liên hệ BT3
- Mạng suy diễn có trọng số `(A, D, w)`: `A`=thuộc tính đã biết, `D`=luật/hàm, `w(r)`=chi phí (luật trực tiếp w=1; suy luận LLM w cao hơn).
- **A\*** với heuristic `h(N)` = số thuộc tính mục tiêu còn thiếu → chuỗi suy diễn **tổng trọng số nhỏ nhất** (dùng cho suy luận gián tiếp: sự kiện thô → tình tiết → điều chỉnh khung).

### 4.4. Gộp phạt (rõ ràng, dễ hiểu)
- Nhiều hành vi → **liệt kê từng lỗi độc lập** (mỗi lỗi: hành vi | Điều/Khoản/Điểm | tiền phạt | phạt bổ sung).
- **Tiền phạt: cộng dồn** các lỗi; **hình phạt bổ sung: lấy mức nặng nhất** (tước GPLX dài nhất…).
- Bảng tổng hợp cuối luôn hiển thị dòng "TỔNG" minh bạch.
- Hai luật mâu thuẫn → gắn cờ *"cần xác nhận"*.

### 4.5. Cấu trúc Trace (phục vụ giải thích)
Mỗi bước lưu bản ghi `[FUNC|RULE|META|ASTAR|KL]` với: dữ kiện vào, luật áp dụng, kết luận, căn cứ. Explanation generator duyệt tuần tự → sinh văn tiếng Việt *"Vì … nên … chiếu Điều X Khoản Y…"*. Con số & căn cứ **bất biến từ engine**; LLM chỉ diễn đạt lại cho mượt.

---

## 5. Tích hợp LLM (Bài toán 1 & 2) + Pipeline đồ thị câu hỏi

### 5.1. Bài toán 2 — Trích xuất tri thức sự kiện (NL → Ontology)
Pipeline theo module QA của môn học, kết hợp LLM:
1. **Tiền xử lý câu hỏi:** chuẩn hóa ký tự/viết tắt ("nđc"→nồng độ cồn, "kdc"→khu dân cư), sửa lỗi chính tả, chuẩn hóa số+đơn vị.
2. **Câu hỏi → đồ thị bộ ba** `(Chủ thể, Quan hệ, Đối tượng)`: LLM đóng vai **entity recognition** + structured output (JSON), ánh xạ vào node ontology (kèm `evidence`).
3. **Phân rã đồ thị sao** (Star Graph Partitioning): tách đồ thị câu hỏi phức tạp thành các sao con quanh mỗi chủ thể.
4. **So khớp đồ thị con** (Subgraph Matching) với Knowledge Graph của KB (so khớp keyphrase, dùng embedding PhoBERT + TF-IDF).
5. **Validator ontology (grounding):** kiểm tra tên node/kiểu/đơn vị/miền giá trị hợp lệ → loại fact sai, hỏi lại người dùng. *LLM đề xuất, ontology phê duyệt.*

Ví dụ JSON Facts đã ánh xạ:
```json
{ "phuongtien": {"loai":"o_to","evidence":"lái ô tô"},
  "chiso": {"nongDoCon_khiTho":{"value":0.42,"unit":"mg/l","evidence":"thổi nồng độ cồn 0.42"},
            "tocDo":{"value":90,"unit":"km/h","evidence":"chạy 90"}},
  "boicanh": {"khuVuc":"khu_dan_cu","thoiDiem":"ban_dem"},
  "raw_events": ["quẹt trúng một xe máy"] }
```

### 5.2. Bài toán 1 — Suy luận ngữ nghĩa (tình tiết/hành vi gián tiếp)
- LLM suy diễn từ `raw_events`, **chỉ chọn trong danh mục tình tiết đã định nghĩa (closed vocabulary)**, kèm `confidence` + `ly_do` + `nguon`.
- Ví dụ: `"quẹt trúng một xe máy"` → `tinhtiet.gay_tai_nan=true (0.9)`.
- Fact suy luận **quay lại làm đầu vào engine §4** (A\* nối "sự kiện thô → tình tiết → điều chỉnh khung"). `confidence` thấp → engine đánh dấu *"cần xác nhận"*.

### 5.3. Luồng dữ liệu tổng thể
```
Người dùng (NL)
  │ §5.1 Bài toán 2: tiền xử lý → đồ thị câu hỏi → phân rã sao → subgraph matching (LLM + KG)
  ▼
Facts thô ─► Validator ontology (grounding)
  │ §5.2 Bài toán 1: LLM suy luận tình tiết gián tiếp (closed-vocab)
  ▼
Facts đầy đủ ─► ENGINE §4 (Deduce_Objects → A*/forward chaining → Deduce_Rules → meta-rule → gộp phạt)
  ▼
Trace + Kết luận ─► Explanation generator (LLM diễn đạt lại; số & căn cứ bất biến)
  ▼
Chatbot: hành vi + căn cứ Điều/Khoản/Điểm + tiền phạt + phạt bổ sung + giải thích
```

### 5.4. Trừu tượng hóa provider
Interface `LLMClient` chung → cắm OpenAI/Claude/Gemini bằng config; API key qua biến môi trường (không hard-code); có **cache** để chạy test lặp đỡ tốn phí.

---

## 6. Giao diện Chatbot (Streamlit)

Bố cục 2 cột "glass-box":
- **Cột trái — Hội thoại:** người dùng nhập tình huống; bot hỏi bổ sung khi thiếu dữ kiện hoặc confidence thấp (slot-filling, đa lượt).
- **Cột phải — 3 tab:**
  1. **Facts đã trích** (Bài toán 2) — kèm `evidence`, cho sửa tay.
  2. **Chuỗi suy diễn** (trace §4) — FUNC/RULE/META/A\*.
  3. **Kết luận & Căn cứ** — bảng mỗi hành vi | Điều/Khoản/Điểm | tiền phạt | phạt bổ sung + dòng TỔNG.

**Xử lý tiếng Việt phức tạp:** chuẩn hóa dấu/viết tắt/số-đơn vị; tách đa vi phạm trong một câu; giữ ngữ cảnh hội thoại nhiều lượt.

---

## 7. Đánh giá hiệu năng

Bộ **test set 30–50 tình huống** (dễ→phức tạp, có bẫy tình tiết gián tiếp), gán nhãn vàng (gold). Chỉ số:

| Chỉ số | Cách đo |
|---|---|
| Độ chính xác trích xuất (BT2) | Facts máy vs gold — precision/recall theo slot |
| Độ chính xác kết luận | hành vi vi phạm đúng/đủ |
| Độ chính xác căn cứ pháp lý | Điều/Khoản/Điểm & khung tiền khớp Nghị định |
| Độ chính xác tình tiết gián tiếp (BT1) | tăng nặng/giảm nhẹ đúng |
| Thời gian phản hồi | tách LLM vs engine ký hiệu |
| Chi phí token | trung bình mỗi truy vấn |

Xuất **báo cáo tự động** (bảng số + biểu đồ `matplotlib`) đưa thẳng vào bài nộp. Đối sánh tham chiếu với kết quả Legal-Onto của thầy (~82.6% trên Luật giao thông VN).

---

## 8. Cấu trúc dự án

```
Project4_TrafficExpertSystem/
├── knowledge/
│   ├── ontology.py            # Legal-Onto: Concept(Name,Content,InnerRul,Attrs,Keyphrases), Relations
│   ├── knowledge_graph.py     # (Keyphrases, Rela) + TF-IDF
│   ├── rules/                 # luật YAML trích từ NĐ 100/123/168
│   ├── export_owl.py          # xuất ontology.owl (owlready2)
│   └── kb_loader.py
├── engine/
│   ├── working_memory.py
│   ├── funcs.py               # Deduce_Objects
│   ├── forward_chaining.py    # Deduce_Rules + meta-rule + gộp phạt
│   ├── astar_network.py       # Mạng (M,R), bài toán (H,Goal), A* "lời giải tốt"
│   ├── sample_problems.py     # Mẫu bài toán (Mp, Goal, Sol)
│   └── trace.py
├── nlu/
│   ├── llm_client.py          # trừu tượng OpenAI/Claude/Gemini + cache
│   ├── question_graph.py      # câu hỏi → đồ thị bộ ba → phân rã sao
│   ├── subgraph_matching.py   # so khớp KG (PhoBERT + TF-IDF)
│   ├── extract_facts.py       # Bài toán 2
│   ├── semantic_infer.py      # Bài toán 1
│   └── grounding.py           # validator theo ontology
├── explain/generator.py       # trace → văn tiếng Việt
├── app/streamlit_app.py       # chatbot UI
├── eval/
│   ├── testset.jsonl          # 30–50 case gold
│   └── run_eval.py            # sinh báo cáo hiệu năng
├── docs/                      # spec (file này), báo cáo, slide
├── requirements.txt · .env.example · README.md
```
**Phụ thuộc chính:** `owlready2`/`rdflib`, `pyyaml`, `pydantic`, `openai`/`anthropic`/`google-genai`, `underthesea`/`py_vncorenlp`, `transformers` (PhoBERT), `streamlit`, `matplotlib`, `networkx` (đồ thị/A\*).

---

## 9. Bám sát học thuật & Tài liệu tham khảo

- **Legal-Onto** `𝒦 = (Conc, Rel, Rules) ⊕ (Keyphrases, Rela)` — mô hình lõi.
- **Mạng tính toán** `(M, R)`, bài toán `(H, Goal)`, "lời giải tốt", Mẫu bài toán `(Mp, Goal, Sol)`.
- **Pipeline QA:** Question→Graph → Star Decomposition → Subgraph Matching.
- Paper nền (trích trong slide của thầy): Vuong T. Pham — *Ontology-based Knowledge Graph Approach for Legal Queries*; *Building Knowledge Graphs from Legal Documents with LLM-based Entity Recognition*; *Knowledge Graph-based Legal Query System with LLM and RAG* (ACIIDS 2025).
- **Hướng phát triển nâng cao (tùy chọn):** logic programming trong không gian vector / partial evaluation (không bắt buộc cho bản chạy).

---

## 10. Rủi ro & Giả định
- **Độ chính xác pháp lý** phụ thuộc chất lượng số hóa luật → cần chuyên gia/human-in-the-loop rà soát.
- **NĐ 168/2024** hiệu lực 01/2025 thay phần lớn NĐ 100 cho đường bộ → ưu tiên 168, đối chiếu chéo.
- **Chi phí LLM** → cache + giới hạn phạm vi test.
- **Tiếng Việt phức tạp** → kết hợp NLP tiếng Việt (PhoBERT) + LLM; slot-filling khi thiếu dữ kiện.
- Giả định: người dùng cấp đủ văn bản Nghị định; có API key khi chạy.
