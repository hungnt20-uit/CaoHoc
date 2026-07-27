# Plan 7 — Đóng gap #1 (Mạng tính toán + A*) & gap #2 (Legal-Onto KG + subgraph matching)

> REQUIRED SUB-SKILL: superpowers:executing-plans. TDD, commit từng task.

**Goal:** Đưa 2 phương pháp lõi của môn vào luồng chạy thật:
- **Gap #1:** Mạng tính toán `(M,R)`, mô hình bài toán `(H, Goal)`, A* tìm "lời giải tốt" — dùng để **suy diễn có hướng** các thuộc tính dẫn xuất (Deduce_Objects) thay cho fixpoint mù; + **Mẫu bài toán `(Mp, Goal, Sol)`**.
- **Gap #2:** **Legal-Onto Knowledge Graph** (keyphrases + **TF-IDF**) + **question-graph → subgraph matching** cho Bài toán 2 (ánh xạ câu hỏi vào node ontology).

**Nguyên tắc:** thay đổi tương thích ngược — KG/question-graph **chỉ bổ sung** fact còn thiếu, không ghi đè; A* thay `apply_funcs` nhưng cho cùng kết quả + thêm vết `[ASTAR]`.

---

### Task 0: `conditions.referenced_keys` — trích khóa thuộc tính từ điều kiện lồng
`engine/conditions.py`: hàm trả tập lhs-key từ node `str | {any|all:[...]}`. Test.

### Task 1: `engine/deduction_network.py` — (M,R) + A* dẫn xuất có hướng
- `funcs_to_network(funcs) -> [DedRule]`; `goal_attrs(rules, funcs, wm) -> set` (thuộc tính dẫn xuất mà luật cần & chưa có); `solve_and_apply(wm, funcs, rules, trace)`: A* tìm chuỗi func tối thiểu → áp theo thứ tự (vết `[ASTAR] lời giải S=…` + `[FUNC]`), fixpoint phần còn lại. Test: input tốc độ → chuỗi `[vuot_toc_do_kmh]`.

### Task 2: Tích hợp vào `reasoner.py`
Thay `apply_funcs` bằng `solve_and_apply`. Suite xanh; test trace chứa `ASTAR` cho ca tốc độ.

### Task 3: `knowledge/sample_problems.py` — Mẫu bài toán (Mp, Goal, Sol)
`SampleProblem(name, Mp:set, goal:(kw,target), sol:[str])` + `match(facts)`; seed mẫu tốc độ & cồn. Test.

### Task 4: Mở rộng `concepts.yaml`
Thêm concept hành vi: nong_do_con, toc_do, mu_bao_hiem, day_an_toan, tin_hieu, giay_to (+keyphrases, attrs{nhom}). Giữ 2 concept phương tiện.

### Task 5: `knowledge/knowledge_graph.py` — TF-IDF keyphrase
`KnowledgeGraph.from_store(store)` tính IDF trên keyphrase (mỗi concept = 1 "tài liệu"); `match(question)->[(concept,score)]`. Test.

### Task 6: `nlu/question_graph.py` — câu hỏi → bộ ba → subgraph matching
`to_nodes(question)->set` (keyphrase khớp); `subgraph_match(question, kg)->[(concept,score)]` (star quanh mỗi concept); `map_to_facts(concepts)->facts` (loai xe + boolean hành vi). Test.

### Task 7: Tích hợp KG vào `nlu/pipeline.py` (bổ sung, không ghi đè) + demo
Pipeline chạy question-graph → subgraph matching → điền fact còn thiếu; ghi `matched_concepts` vào meta. Suite xanh + demo.

## Kết quả
A*/mạng tính toán chạy thật trong engine (có vết lời giải), có Mẫu bài toán; Legal-Onto có Knowledge Graph TF-IDF + subgraph matching cho Bài toán 2 → **sát phương pháp môn học**.
