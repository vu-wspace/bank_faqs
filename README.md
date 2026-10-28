# bank-faqs

Agent chăm sóc khách hàng ngân hàng bằng tiếng Việt, xây dựng với LangChain/LangGraph. Agent trả lời câu hỏi về thẻ, tài khoản, chuyển tiền, tiết kiệm, vay, lừa đảo, ứng dụng ngân hàng, lãi suất tiết kiệm và địa chỉ chi nhánh tại Quy Nhơn. Câu trả lời dựa trên dữ liệu nội bộ; agent chỉ tìm trên web khi dữ liệu nội bộ không có. Có kèm web chat (FastAPI) chạy bằng Docker.

## Cách hoạt động

```
Khách hỏi ──> Agent (OpenRouter · nvidia/nemotron-3-ultra-550b-a55b:free; lỗi/hết quota thì dùng Gemini)
                 │
                 ├── search_faq         Tìm hội thoại CSKH tương tự trong Qdrant (thủ tục, xử lý sự cố)
                 ├── get_interest_rate  Tra bảng lãi suất tiết kiệm (CSV)
                 ├── get_branch_info    Tra địa chỉ, số điện thoại chi nhánh tại Quy Nhơn (CSV), kèm nguồn
                 └── web_search         Tavily – chỉ khi các tool trên không có câu trả lời
```

Quy tắc hành vi của agent (system prompt trong `prompts.py`):

- Xưng "em", gọi khách là "anh/chị", trả lời ngắn gọn (~80 từ, không tính phần nguồn).
- Chỉ trả lời dựa trên kết quả tool, không tự đoán số liệu (phí, lãi suất, số điện thoại, giờ làm việc…).
- Thông tin chi nhánh: mỗi chi nhánh được nhắc tới phải kèm link nguồn.
- Khách bị lừa đảo, mất tiền, khóa tài khoản…: hướng dẫn bước khẩn cấp rồi chuyển nhân viên.
- Không bao giờ hỏi OTP, mật khẩu, PIN.
- Từ chối câu hỏi ngoài phạm vi (tư vấn đầu tư vàng, cổ phiếu…).

## Các tool

| Tool | Nguồn dữ liệu | Dùng khi |
|---|---|---|
| `search_faq(query)` | Qdrant, top 3 hội thoại tương tự | Thủ tục, xử lý sự cố |
| `get_interest_rate(bank='')` | `data/raw/lai_suat_ngan_hang_23-10-2026.csv` | Lãi suất tiết kiệm online/tại quầy, kỳ hạn 1–36 tháng. Để trống `bank` để lấy bảng so sánh mọi ngân hàng |
| `get_branch_info(bank='', street='')` | `data/raw/chi_nhanh_ngan_hang_quy_nhon.csv` | Địa chỉ, số điện thoại của 23 chi nhánh (18 ngân hàng) tại Quy Nhơn. Lọc theo ngân hàng và/hoặc tên đường; để trống cả hai để lấy toàn bộ |
| `web_search(query)` | Tavily, 3 kết quả | Khuyến mãi, tin tức, lãi suất vay, ngân hàng không có trong dữ liệu |

- `get_interest_rate` và `get_branch_info` nhận tên ngân hàng không dấu, viết tắt, tên cũ hoặc có tiền tố "ngân hàng" (`vcb`, `Vietin`, `mb bank`, `bac a`, `ngân hàng Techcom`, `oceanbank`…). Danh sách tên tắt nằm trong `BANK_ALIASES` ở `tools.py`. Tên đường cũng so khớp không dấu (`le duan` khớp "Lê Duẩn").
- `get_branch_info` trả về cho từng chi nhánh: địa chỉ theo nguồn, phường mới (sau sáp nhập 1/7/2025), điện thoại, giờ làm việc, **độ tin cậy** và **URL nguồn**. Ô ghi "Chưa có nguồn" hoặc bỏ trống trong CSV được trả về là "chưa có thông tin", để model không tự bịa. Trong câu trả lời, agent ghi link nguồn cạnh từng chi nhánh, và trang chat hiển thị link bấm được.
- `search_faq` và `web_search` tự bắt lỗi (Qdrant sập, Tavily timeout…) và trả thông báo lỗi cho model, thay vì làm hỏng cả lượt hội thoại.

**Cập nhật dữ liệu:**
- **Lãi suất:** đặt file CSV mới vào `data/raw/` (giữ nguyên tên cột), rồi sửa `RATE_FILE` và `RATE_DATE` trong `config.py`.
- **Chi nhánh:** sửa trực tiếp `data/raw/chi_nhanh_ngan_hang_quy_nhon.csv` (giữ nguyên tên cột). Cột `Nguồn` có thể chứa nhiều URL, phân cách bằng `;`. Ô chưa có dữ liệu thì ghi "Chưa có nguồn" hoặc để trống; cả hai đều được trả về là "chưa có thông tin".
- **Hội thoại CSKH:** sửa `data/raw/cskh_hoi_thoai_ngan_hang.csv`, rồi chạy lại bước [nạp dữ liệu](#chạy-trên-máy-không-docker).

**Thêm tool mới:** viết hàm `@tool` trong `tools.py`; docstring của hàm chính là mô tả mà model đọc để quyết định khi nào gọi tool. Sau đó thêm vào `TOOLS` và `AGENT_TOOLS` ở cuối `tools.py`, rồi bổ sung quy tắc dùng tool trong `prompts.py`.

## Cấu trúc thư mục

```
bank_faqs/
├── data/
│   ├── raw/                                  # Dữ liệu gốc
│   │   ├── cskh_hoi_thoai_ngan_hang.csv      # Hội thoại CSKH, mỗi dòng là 1 lượt nói
│   │   ├── lai_suat_ngan_hang_23-10-2026.csv # Lãi suất tiết kiệm 17 ngân hàng (get_interest_rate)
│   │   └── chi_nhanh_ngan_hang_quy_nhon.csv  # 23 chi nhánh tại Quy Nhơn, có nguồn (get_branch_info)
│   └── processed/
│       └── cskh_gop_theo_id.csv              # Hội thoại đã gộp theo id, sinh bởi data_prep.py, nạp vào Qdrant
├── src/bank_faqs/
│   ├── __init__.py       # Khởi tạo chung: fix DLL torch (Windows), dùng kho chứng chỉ hệ thống, nạp .env
│   ├── config.py         # Đường dẫn dữ liệu, cấu hình Qdrant/embedding, biến môi trường
│   ├── llm.py            # Cấu hình LLM: open_llm (OpenRouter, đang dùng), google_llm (Gemini, judge của eval), groq_llm (Groq)
│   ├── prompts.py        # System prompt của từng agent
│   ├── tools.py          # 4 tool + gán tool cho từng agent
│   ├── history.py        # Cắt bớt lịch sử hội thoại trước khi gửi model
│   ├── agent.py          # Agent dựng bằng create_agent (LangChain), chạy thử 4 câu hỏi mẫu
│   ├── graph.py          # Cùng agent đó nhưng tự dựng bằng StateGraph (LangGraph)
│   ├── data_prep.py      # Gộp các lượt hội thoại theo id -> data/processed/
│   ├── vector_db.py      # Embedding bkai + Qdrant, nạp dữ liệu
│   ├── api.py            # Web app FastAPI: trang chat + POST /chat + /health
│   └── static/index.html # Giao diện chat
├── tests/                # pytest (65 test, không gọi API thật)
├── evals/                # Đánh giá chất lượng agent
│   ├── dataset.jsonl     # 37 câu hỏi kèm tool mong đợi, từ khóa, tiêu chí chấm
│   ├── run_eval.py       # Script chấm truy xuất + agent
│   └── results/          # Kết quả từng lần chạy (JSON), không commit
├── certs/                # CA nội bộ (*.crt) cho mạng có SSL inspection, không commit
├── .env                  # API key, không commit (xem Cài đặt)
├── Dockerfile            # Image cho web app
├── docker-compose.yml    # Qdrant + web app
├── langgraph.json        # Cấu hình cho `langgraph dev`
├── pyproject.toml        # Thư viện (nguồn chính, cùng uv.lock)
└── requirements.txt      # Danh sách thư viện cho pip, phải khớp pyproject.toml (có test kiểm tra)
```

## Yêu cầu

- Python 3.12.15 và [uv](https://docs.astral.sh/uv/)
- Docker (để chạy Qdrant và web app)
- API key: [OpenRouter](https://openrouter.ai/keys) (agent), [Google AI Studio](https://aistudio.google.com/apikey) (Gemini, judge của eval), [Groq](https://console.groq.com), [Tavily](https://tavily.com); LangSmith (tùy chọn, để trace). `llm.py` khởi tạo cả 3 client LLM ngay khi import nên cần đủ cả 3 key, kể cả model không dùng

## Cài đặt

```bash
uv sync            # cài thư viện + nhóm dev (pytest, langgraph-cli)
```

Nếu dùng pip thay cho uv: `pip install -r requirements.txt`. File này đã có sẵn index của torch bản CPU. Thư viện dev cài riêng theo hướng dẫn ở cuối file. Khi thêm hoặc bớt thư viện, sửa `pyproject.toml` (`uv add …`) rồi sửa `requirements.txt` cho khớp; `tests/test_requirements.py` sẽ báo nếu hai file lệch nhau.

Tạo file `.env` ở thư mục gốc (đã có trong `.gitignore`):

```env
OPENROUTER_API_KEY=...
GOOGLE_API_KEY=...
GROQ_API_KEY=...
TAVILY_API_KEY=...
QDRANT_URL=http://localhost:6333

# Tùy chọn
LANGSMITH_API_KEY=...
LANGSMITH_TRACING=true
LANGSMITH_PROJECT=bank-faqs
```

## Deploy bằng Docker (web app)

Cách nhanh nhất để chạy cả hệ thống, chỉ cần Docker và file `.env`:

```bash
docker compose up -d --build
```

Lệnh này chạy 2 container:

| Container | Cổng | Vai trò |
|---|---|---|
| `qdrant` | 6333, 6334 | Vector DB (v1.20.0), dữ liệu lưu ở Docker volume `qdrant_data` |
| `bank_faqs_api` | 8000 | Web app FastAPI (uvicorn) |

- Khi khởi động, API chờ Qdrant sẵn sàng (thử lại tối đa ~60 giây).
- Nếu collection còn rỗng, API **tự nạp dữ liệu** từ `data/processed/cskh_gop_theo_id.csv`. Đặt `AUTO_INGEST: "false"` trong `docker-compose.yml` để tắt.
- Model embedding được tải sẵn vào image lúc build, nên container không cần mạng tới Hugging Face.
- Lần build đầu mất vài phút. Các lần sau, nếu chỉ sửa `src/` hoặc `data/`, Docker dùng lại cache của bước cài thư viện và tải model.
- Image chỉ chứa thứ cần để chạy (`src/`, `data/`, thư viện, model embedding): không có `tests/`, `evals/`, `.env` (key được truyền qua `env_file` lúc chạy), hay thư viện dev.
- Sau khi sửa code, dữ liệu hoặc thư viện: chạy lại `docker compose up -d --build api` để build lại image.

Sau khi chạy:

- **Trang chat:** http://localhost:8000
- **Tài liệu API (Swagger):** http://localhost:8000/docs
- **Kiểm tra trạng thái:** http://localhost:8000/health trả về `{"status": "ok", "documents": 34}`

```bash
docker compose logs -f api     # xem log
docker compose down            # dừng (dữ liệu Qdrant vẫn giữ trong volume)
docker compose down -v         # dừng và xóa luôn dữ liệu Qdrant (lần chạy sau API tự nạp lại)
```

### API

`POST /chat`

```json
// request: bỏ trống thread_id để bắt đầu hội thoại mới
{"message": "lãi suất 12 tháng BIDV", "thread_id": null}

// response
{"thread_id": "5f0c…", "answer": "Lãi suất tiết kiệm BIDV kỳ hạn 12 tháng…", "tools": ["get_interest_rate"]}
```

Gửi lại `thread_id` ở các lượt sau để agent nhớ ngữ cảnh. Ví dụ: hỏi "lãi suất BIDV" rồi hỏi tiếp "còn Vietcombank thì sao". `tools` chỉ liệt kê các tool được gọi trong lượt đó.

| Mã lỗi | Khi nào |
|---|---|
| 422 | `message` rỗng hoặc dài quá 1000 ký tự |
| 429 | Cả OpenRouter lẫn Gemini dự phòng đều báo vượt giới hạn (theo phút hoặc theo ngày); xem [Giới hạn của LLM](#giới-hạn-của-llm-gói-free) |
| 502 | Cả OpenRouter lẫn Gemini dự phòng đều lỗi (lỗi khác, mất kết nối…) |
| 503 | `/health`: không kết nối được Qdrant |

```bash
curl http://localhost:8000/chat -H 'Content-Type: application/json' \
  -d '{"message": "chi nhánh BIDV ở Quy Nhơn"}'
```

**Giới hạn:** lịch sử hội thoại lưu trong RAM của container (`InMemorySaver`), nên mất khi restart. Vì vậy uvicorn chỉ chạy 1 worker. Muốn chạy nhiều worker hoặc nhiều container thì phải đổi sang checkpointer dùng chung, ví dụ Postgres (`langgraph-checkpoint-postgres`).

### Mạng có SSL inspection

Nếu log báo `CERTIFICATE_VERIFY_FAILED: self-signed certificate in certificate chain` (ví dụ khi gọi Gemini hoặc gửi trace lên LangSmith), nghĩa là proxy của mạng đang cấp lại chứng chỉ HTTPS bằng một CA nội bộ. Khi chạy trên máy, `bank_faqs/__init__.py` đã cho Python dùng kho chứng chỉ Windows (qua `truststore`), vốn đã tin CA này. Container thì không có CA đó. Cách xử lý: xuất CA từ kho chứng chỉ Windows vào thư mục `certs/` rồi build lại image. Dockerfile sẽ cài mọi file `certs/*.crt` vào container. Các file `.crt` này không được commit.

```powershell
# PowerShell: đổi 'CN=ten-CA*' thành tên CA nội bộ (xem issuer của chứng chỉ bị lỗi)
$c = Get-ChildItem Cert:\LocalMachine\Root | Where-Object { $_.Subject -like 'CN=ten-CA*' } | Select-Object -First 1
"-----BEGIN CERTIFICATE-----`n" + [Convert]::ToBase64String($c.RawData, 'InsertLineBreaks') + "`n-----END CERTIFICATE-----" | Set-Content -Encoding ascii certs\internal-ca.crt
docker compose up -d --build api
```

## Chạy trên máy (không Docker)

**1. Khởi động Qdrant**

```bash
docker compose up -d qdrant
```

Dashboard tại http://localhost:6333/dashboard.

**2. Nạp dữ liệu vào vector DB** (chạy lần đầu, hoặc khi dữ liệu hội thoại thay đổi)

```bash
# Gộp các lượt hội thoại theo id -> data/processed/cskh_gop_theo_id.csv
uv run python -m bank_faqs.data_prep

# Embedding và nạp vào collection 'cskh_bkai'
uv run python -m bank_faqs.vector_db
```

Lần chạy đầu sẽ tải model `bkai-foundation-models/vietnamese-bi-encoder` từ Hugging Face. ID mỗi điểm được sinh cố định từ `hoi_thoai_id`, nên chạy lại sẽ ghi đè chứ không tạo bản trùng.

**3. Chạy agent**

```bash
uv run python -m bank_faqs.agent
```

Script chạy 4 câu hỏi mẫu (quên mật khẩu, lãi suất, lộ OTP, câu hỏi ngoài phạm vi) và in ra tool đã gọi cùng câu trả lời.

Dùng agent trong code:

```python
from bank_faqs.agent import agent

res = agent.invoke({'messages': [{'role': 'user', 'content': 'thẻ bị nuốt ở cây ATM thì làm sao'}]})
print(res['messages'][-1].text)
```

**4. LangGraph Studio / API server**

```bash
uv run langgraph dev
```

Server chạy tại http://127.0.0.1:2024 với 2 graph khai báo trong `langgraph.json`: `agent_main` (`agent.py`) và `bank_graph` (`graph.py`). Hai graph dùng chung LLM, tool và system prompt, chỉ khác cách dựng. Có thể chat và xem từng bước gọi tool trên LangGraph Studio (link in ra khi khởi động), hoặc gọi qua API:

```bash
curl http://127.0.0.1:2024/runs/wait -H 'Content-Type: application/json' \
  -d '{"assistant_id": "agent_main", "input": {"messages": [{"role": "user", "content": "lãi suất 12 tháng BIDV"}]}}'
```

`langgraph dev` thuộc nhóm thư viện dev (`langgraph-cli[inmem]`), nên không được cài vào image Docker. Trên Windows, cần làm bước trong mục [Lưu ý trên Windows](#lưu-ý-trên-windows) trước.

**5. Web app (không Docker)**

```bash
uv run uvicorn bank_faqs.api:app --port 8000
```

## Test

```bash
uv run pytest
```

Gồm 65 test, chạy dưới 1 phút và không gọi LLM hay Tavily thật (trace LangSmith được tắt trong `conftest.py`):

- `tests/test_tools.py`:
  - nhận diện tên ngân hàng và dữ liệu lãi suất;
  - tool chi nhánh: lọc theo ngân hàng/đường, có nguồn và độ tin cậy, tách nhiều URL nguồn, ẩn ô "Chưa có nguồn" và ô bỏ trống;
  - tool tự bắt lỗi khi Qdrant hoặc Tavily lỗi.
- `tests/test_history.py`: cắt lịch sử đúng ranh giới lượt hỏi, rút gọn kết quả tool cũ, không làm thay đổi state.
- `tests/test_api.py`:
  - các endpoint (dùng agent giả) và validate input;
  - mã lỗi 429/502/503, của OpenRouter, Gemini và Groq;
  - bộ nhớ theo `thread_id`;
  - tự nạp dữ liệu, thử lại khi Qdrant chưa sẵn sàng, và dùng chung một Qdrant client.
- `tests/test_agent.py`: model chính lỗi thì agent trả lời bằng model dự phòng; tắt dự phòng (`fallback=False`) thì lỗi được báo ra.
- `tests/test_llm.py`: `timeout` của từng LLM đúng đơn vị (OpenRouter tính bằng mili giây, xem [Giới hạn của LLM](#giới-hạn-của-llm-gói-free)).
- `tests/test_requirements.py`: `requirements.txt` có đúng các thư viện trong `pyproject.toml`.
- `tests/test_eval_dataset.py`: `evals/dataset.jsonl` hợp lệ (đúng tên trường, id không trùng, tool và `faq_id` có tồn tại, câu hỏi không chép nguyên văn từ dữ liệu). Nhờ vậy khi đổi tên tool hay sửa dữ liệu mà quên cập nhật eval thì test sẽ báo.

## Đánh giá (eval)

Khác với test, eval gọi **LLM, Qdrant và Tavily thật** để đo chất lượng câu trả lời. Eval chạy trên máy (không có trong image Docker), cần Qdrant đã có dữ liệu và key trong `.env`:

```bash
docker compose up -d qdrant                        # nếu chưa chạy
uv run python evals/run_eval.py                    # chạy tất cả (~10-15 phút; gói free OpenRouter không đủ quota, xem bên dưới)
uv run python evals/run_eval.py --only rate,branch # lọc theo category hoặc id (vd: faq-01)
uv run python evals/run_eval.py --retrieval-only   # chỉ chấm truy xuất, không gọi LLM
uv run python evals/run_eval.py --target graph     # chấm graph.py (StateGraph) thay cho agent.py (create_agent)
```

Bộ câu hỏi `evals/dataset.jsonl` gồm 37 câu, được **diễn đạt lại** khác câu gốc trong CSV (để retriever không tìm thấy chính nó): 21 FAQ, 4 chuyển nhân viên, 1 bảo mật OTP, 4 lãi suất, 3 chi nhánh, 1 tìm web, 3 ngoài phạm vi. Mỗi dòng là một JSON:

| Trường | Ý nghĩa |
|---|---|
| `id`, `category`, `question` | Mã câu, nhóm, câu hỏi |
| `tools` | Tool đầu tiên agent nên gọi (một trong danh sách). `[]` = không được gọi tool. `tools_optional: true` = không chấm |
| `faq_id` | Hội thoại đúng trong `cskh_gop_theo_id.csv` (dùng chấm truy xuất và làm câu trả lời tham khảo cho judge) |
| `must_contain` | Danh sách nhóm từ khóa; câu trả lời phải chứa ít nhất 1 từ của **mỗi** nhóm. Không phân biệt hoa thường, `7,4` khớp `7.4` |
| `escalate`, `refuse` | Agent phải báo chuyển nhân viên / phải từ chối |
| `criteria` | Tiêu chí cho LLM judge |

Các chỉ số:

- **Truy xuất:** đưa câu hỏi thẳng vào retriever (top 3), tính hit@1, hit@3, MRR theo `faq_id`.
- **routing:** tool gọi đầu tiên có đúng `tools` không.
- **keyword:** có đủ `must_contain` không.
- **behavior:** có chuyển nhân viên / từ chối đúng như `escalate` / `refuse` không (do judge nhận định).
- **judge:** Gemini (`google_llm`) chấm 1-5 theo `criteria`, kèm `grounded` (chỉ dùng thông tin từ kết quả tool). Judge là LLM nên vẫn có thể chấm sai; `routing` và `keyword` là kiểm tra cứng, tin cậy hơn.
- Kèm độ trễ trung bình và số câu trả lời dài quá 80 từ (đếm cả link nguồn).

Script in bảng tổng hợp theo nhóm, liệt kê câu chưa đạt và lưu chi tiết từng câu (câu trả lời, tool đã gọi, nhận xét của judge) vào `evals/results/<thời gian>-<target>.json`. Eval tự tắt trace LangSmith, nghỉ 4 giây giữa các câu (`--delay`), và khi OpenRouter/Gemini/Groq báo vượt giới hạn theo phút (429) thì chờ 60 giây rồi thử lại (tối đa 2 lần, cho cả agent lẫn judge). Câu nào vẫn lỗi (hết quota, sai key…) được ghi là lỗi và bỏ khỏi thống kê, không làm dừng cả lần chạy. Nhấn Ctrl+C giữa chừng thì vẫn in và lưu kết quả các câu đã chạy. Trước khi chạy, script kiểm tra Qdrant đã có dữ liệu chưa; collection rỗng thì báo lỗi luôn, thay vì cho ra điểm truy xuất 0%.

Kết quả gần nhất:

| Model của agent | Số câu chấm được | Kết quả |
|---|---|---|
| `nvidia/nemotron-3-ultra-550b-a55b:free` (OpenRouter, 27–28/10/2026, chạy 2 phần vì quota) | 37/37 | routing 36/36, keyword 9/9, behavior 8/8, grounded 37/37, judge TB 4.97/5, độ trễ TB ~13 giây, 19/37 câu dài quá 80 từ. Câu duy nhất dưới 5 điểm: `branch-01` (4 điểm, chưa xưng "em"). Câu chi nhánh và tìm web chậm nhất (~30 giây) |
| `gemini-3.1-flash-lite` (model cũ, 27/10/2026) | 37/37 | routing 35/36, keyword 9/9, behavior 8/8, judge 5/5, độ trễ TB ~11 giây, hơn nửa số câu dài quá 80 từ; không gọi `search_faq` với câu "bị lừa đọc OTP" (`esc-01`) |

Truy xuất không phụ thuộc LLM: hit@1 96% (24/25, trượt `faq-14`).

Với gói free của OpenRouter (~50 request/ngày), một ngày không chạy hết 37 câu (cần khoảng 90 request). Chạy từng phần qua `--only`, mỗi ngày một phần, ví dụ `--only faq` rồi hôm sau `--only escalation,security,rate,branch,web,out_of_scope`. Lưu ý: quota dùng chung với web app, nên trong ngày chạy eval thì web app chủ yếu trả lời bằng Gemini dự phòng.

**Thêm câu hỏi:** thêm một dòng vào `dataset.jsonl`. Nên diễn đạt khác câu trong dữ liệu, và với câu có số liệu thì thêm `must_contain` để kiểm tra cứng.

## Giới hạn của LLM (gói free)

| LLM trong `llm.py` | Model | Dùng cho |
|---|---|---|
| `open_llm` (OpenRouter) | `nvidia/nemotron-3-ultra-550b-a55b:free` | Agent: `agent.py` (web app, graph `agent_main`) và `graph.py` (graph `bank_graph`) |
| `google_llm` (Gemini) | `gemini-3.1-flash-lite` | Dự phòng của `agent.py` khi OpenRouter lỗi; judge của eval |
| `groq_llm` (Groq) | `qwen/qwen3.8-27b` | Dự phòng, hiện không dùng |

Đổi model của agent bằng cách sửa `llm.py`, hoặc truyền `model=` khác trong `build_agent` (`agent.py`) và `bind_tools` (`graph.py`). Cả 3 client được tạo ngay khi import `llm.py`, nên `.env` phải có đủ cả 3 key.

**Dự phòng:** `build_agent()` gắn `ModelFallbackMiddleware(google_llm)`: lượt nào OpenRouter lỗi (hết quota ngày, quá tải, mất kết nối…) thì lượt đó Gemini trả lời thay, nên web app vẫn chạy được khi OpenRouter hết quota. OpenRouter hết quota thì báo lỗi sau khoảng 1 giây nên khách gần như không phải chờ thêm. Việc chuyển sang Gemini không ghi log; muốn biết model chính có đang lỗi không thì kiểm tra quota (lệnh bên dưới). Chỉ `agent.py` có dự phòng, `graph.py` thì không. Eval gọi `build_agent(fallback=False)` để điểm số phản ánh đúng model chính.

**OpenRouter:** model có hậu tố `:free` bị giới hạn khoảng **20 request/phút** và **50 request/ngày** nếu tài khoản chưa từng nạp đủ 10 USD credit (nạp rồi thì 1000 request/ngày). Mỗi câu hỏi tốn 2–3 request, nên gói free chỉ đủ khoảng 20 câu mỗi ngày, **tính chung cho web app và eval**. Hết quota ngày thì agent chuyển sang Gemini cho tới khi quota reset (00:00 UTC, tức 7:00 sáng giờ Việt Nam). Kiểm tra quota của key: `curl https://openrouter.ai/api/v1/key -H "Authorization: Bearer $OPENROUTER_API_KEY"`.

> **Chú ý:** `ChatOpenRouter` tính `timeout` bằng **mili giây** (`timeout=60_000` là 60 giây), khác `ChatGroq`/`ChatGoogleGenerativeAI` tính bằng giây. Nếu đặt `timeout=60` thì mọi request bị hủy sau 60ms, SDK thử lại liên tục và agent treo vài phút mà không báo lỗi. `tests/test_llm.py` kiểm tra lỗi này.

**Gemini** (judge): giới hạn theo số request mỗi phút cho từng model (vd `gemini-3.1-flash-lite` ở gói free: 15 request/phút). Eval tự chờ và thử lại khi bị 429.

**Groq** (dự phòng): gói free giới hạn 1000 token đầu ra/phút, 7000 token đầu vào/phút và 200.000 token/ngày (khoảng 50 câu hỏi). `llm.py` đặt `max_tokens=512`, vì nếu không đặt thì Groq tính mỗi request 2048 token đầu ra và luôn vượt giới hạn.

**Cắt bớt lịch sử (mọi model):** gửi lại toàn bộ lịch sử thì số token đầu vào tăng mãi, chat vài lượt là vượt giới hạn (Groq trả 413) và chậm dần. `history.py` chỉ gửi model 4 lượt hỏi gần nhất, và rút kết quả tool của các lượt trước còn 300 ký tự; mỗi lần gọi còn khoảng 1100–2800 token. Lịch sử đầy đủ vẫn giữ trong bộ nhớ, chỉ phần gửi đi model bị cắt.

Khi chạm giới hạn, SDK tự chờ rồi thử lại vài lần. Nếu vẫn không được, API trả về **429** và ghi loại giới hạn vào log (`docker compose logs api | grep "rate limit"`).

## Lưu ý về dữ liệu chi nhánh

- Dữ liệu được tổng hợp từ nguồn công khai, chủ yếu là trang đăng ký thuế (infodoanhnghiep.com). Cột `Ghi chú / độ tin cậy` cho biết mỗi thông tin lấy từ đâu.
- Địa chỉ là địa chỉ **theo nguồn**, nhiều chỗ còn theo địa giới hành chính trước khi sáp nhập phường ngày 1/7/2025. Cột `Phường mới` ghi phường sau sáp nhập nếu đối chiếu được.
- 19/23 chi nhánh chưa có số điện thoại, và chưa chi nhánh nào có giờ làm việc.
- Chi nhánh "BIDV CN Quy Nhơn" có URL nguồn mang chữ `Chi-Nhanh-Tay-Son`. Nên kiểm tra lại dòng này.

## Lưu ý trên Windows

- **Lỗi `OSError: [WinError 1114] ... torch\lib\c10.dll`**
  - Nguyên nhân: antivirus (vd McAfee) nạp một bản `msvcp140.dll` cũ (14.00) vào process Python, khi Python chạy truy vấn WMI qua module `platform`. `pandas`, `truststore` và `langgraph dev` đều gọi `platform`. `torch` cần bản mới hơn nên không khởi tạo được.
  - Cách xử lý: tạo file `.pth` trong venv để nạp `msvcp140.dll` của Windows ngay khi Python khởi động. **Chạy lại mỗi khi tạo lại `.venv`:**

    ```bash
    uv run python -c "import site, pathlib; pathlib.Path(site.getsitepackages()[-1], '_msvcp140_preload.pth').write_text(\"import sys, ctypes; sys.platform == 'win32' and ctypes.WinDLL('msvcp140.dll')\n\")"
    ```

  - Kiểm tra: `uv run python -c "import pandas, torch"` không báo lỗi.
  - Dự phòng khi chưa có file `.pth`: `src/bank_faqs/__init__.py` cũng nạp trước `msvcp140.dll`. Các file chạy được (`vector_db.py`, `agent.py`, `graph.py`) có `import bank_faqs` ở **dòng đầu tiên**, nên `python -m ...` vẫn chạy được. Cách này không đủ cho `langgraph dev`, vì server import `pandas` trước khi nạp code của dự án.
- **Lỗi `UnicodeEncodeError` khi in tiếng Việt** (lúc chuyển hướng output sang pipe hoặc file): đặt biến môi trường `PYTHONUTF8=1`.
