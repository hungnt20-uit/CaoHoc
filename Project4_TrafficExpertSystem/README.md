# Traffic Expert System

Hệ thống chuyên gia tư vấn xử phạt vi phạm giao thông theo **Nghị định 168/2024/NĐ-CP**.

Người dùng mô tả tình huống bằng tiếng Việt → NLU trích facts → suy diễn luật → trả mức phạt, căn cứ pháp lý và chuỗi giải thích. Giao diện: Streamlit.

## Yêu cầu

- Python 3.10+ (khuyến nghị 3.12)
- API key OpenAI / Anthropic (tùy chọn — không có thì dùng **Heuristic offline**)

## Cài đặt

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
python -m pip install -U pip
python -m pip install -r requirements.txt
```

Dùng môi trường `venv` vừa tạo (tránh nhầm `.venv` cũ thiếu package).

## Cấu hình

```bash
cp .env.example .env
```

Chỉnh `.env` (đã gitignore — **không commit key thật**):

```env
# Chọn 1 provider (ưu tiên Anthropic nếu cả hai đều có)
ANTHROPIC_API_KEY=sk-ant-...
# OPENAI_API_KEY=sk-...

# Tùy chọn
# TRAFFIC_ES_LLM_PROVIDER=openai          # anthropic | openai | local
# TRAFFIC_ES_LLM_MODEL=gpt-4o-mini

# LLM local (Colab / vLLM / Ollama…)
# TRAFFIC_ES_LLM_PROVIDER=local
# TRAFFIC_ES_LOCAL_BASE_URL=https://xxx.trycloudflare.com/v1
# TRAFFIC_ES_LOCAL_MODEL=Qwen/Qwen2.5-Coder-7B-Instruct
```

## Chạy ứng dụng

### Local (venv)

```bash
source venv/bin/activate
streamlit run app/streamlit_app.py
```

Mở [http://localhost:8501](http://localhost:8501).

> Không chạy bằng `python app/streamlit_app.py` — phải dùng `streamlit run`.

### Docker Compose

```bash
cp .env.example .env   # nếu chưa có; điền key nếu cần LLM
docker compose up --build
```

App: [http://localhost:8501](http://localhost:8501). Dừng: `docker compose down`.

Sidebar chọn bộ trích xuất: **Tự động** (theo `.env`), OpenAI, Anthropic, Local, hoặc Heuristic.

## Cách dùng nhanh

1. Nhập mô tả tình huống (vd. *“Tôi lái xe máy vượt đèn đỏ”*).
2. Bấm **Phân tích**.
3. Nếu thiếu thông tin, hệ thống **hỏi bổ sung** (radio chọn, không cần gõ lại câu):
   - Thiếu loại xe → chọn Ô tô / Xe máy
   - Câu mơ hồ (*“sai luật”*) → chọn loại lỗi
   - Đã lộ chủ đề cồn/tốc độ nhưng chưa có mức (*“uống rượu”*, *“quá tốc độ”*) → chọn **khung mức** (không nhập số tay)
4. Xem mức phạt, căn cứ, facts, trace suy diễn.

### Ví dụ khung tốc độ

- Vượt 10–20 km/h *(ví dụ: cho phép 50 km/h, chạy 65 km/h)*
- Các khung khác: 5 đến dưới 10, trên 20 đến 35, trên 35 km/h

### Ví dụ khung nồng độ cồn

- Mức 1 / 2 / 3 theo ngưỡng khí thở (hoặc máu) của Nghị định 168

## Phạm vi hỗ trợ (KG + luật)

Căn cứ chính: **Nghị định 168/2024/NĐ-CP**. Ontology / keyphrase nằm trong
`traffic_es/knowledge/concepts.yaml`; luật suy diễn trong `traffic_es/knowledge/rules/`;
câu hỏi bổ sung (khung mức UI) trong `traffic_es/knowledge/clarify.yaml`.

### Concept trong Knowledge Graph

Phạm vi đã mở rộng theo `docs/PLAN_BO_SUNG_ND168.md` (P0–P4). Các nhóm chính:

| Nhóm | Ví dụ concept / fact | File luật |
|------|----------------------|-----------|
| Phương tiện | ô tô, xe máy, **xe đạp** | — |
| Nồng độ cồn / ma túy | `chiso.nongDoCon_*`, `nguoi.co_chat_ma_tuy` | `nong_do_con.yaml`, `chat_kich_thich.yaml` |
| Tốc độ | `chiso.tocDo` + suy `tocDoGioiHan` từ `boicanh.khuVuc` | `toc_do.yaml` + Func `gioi_han_theo_khu_vuc` |
| An toàn & tín hiệu | mũ BH, dây AT, đèn đỏ/vàng, **hiệu lệnh CSGT** | `an_toan_tin_hieu.yaml` |
| Giấy tờ / GPLX | không GPLX, chưa đủ tuổi, GPLX giả, ĐKX, đăng kiểm | `giay_to.yaml` |
| Làn đường / tránh vượt / dừng đỗ | sai làn, quay đầu cấm, vượt cấm, ngược chiều, đỗ sai | `lan_duong.yaml`, `quy_tac_tranh_vuot.yaml`, `dung_do.yaml` |
| Biển số | giả / che / sửa biển | `bien_so.yaml` |
| Vận tải | quá tải, quá khổ, nhồi nhét, đón trả sai | `van_tai.yaml` |
| Hành khách / đi bộ / chủ xe | gây rối, sai phần đường, giao xe không đủ ĐK | `hanh_khach.yaml`, `nguoi_di_bo.yaml`, `chu_xe.yaml` |
| Tình tiết (meta) | gây tai nạn, tái phạm, không chấp hành… | `tinh_tiet.yaml` + meta trong `nong_do_con.yaml` |

> Số liệu khung phạt cần đối chiếu văn bản gốc NĐ 168 khi dùng chính thức. Kế hoạch bổ sung chi tiết: `docs/PLAN_BO_SUNG_ND168.md`.

## Kiểm thử

```bash
source venv/bin/activate
pytest
```

## Cấu trúc chính

```
app/streamlit_app.py          # UI Streamlit
traffic_es/
  service.py                  # API trả lời + hỏi bổ sung
  nlu/                        # normalize, extract, KG, clarify
  engine/                     # forward chaining, penalty, A*
  knowledge/
    concepts.yaml             # Legal-Onto / KG keyphrases
    clarify.yaml              # câu hỏi UI (khung mức, hành vi)
    rules/                    # luật YAML
  llm/                        # OpenAI / Anthropic / local
  explain/                    # sinh giải thích
tests/
scripts/
notebooks/colab_qwen_server.ipynb
```

## Ghi chú bảo mật

- Chỉ commit `.env.example` (placeholder). File `.env` và `venv/` / `.venv/` nằm trong `.gitignore`.
- Không dán API key lên README, issue hay PR.
