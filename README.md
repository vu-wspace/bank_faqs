# bank-faqs

Agent chăm sóc khách hàng ngân hàng bằng tiếng Việt, xây dựng với LangChain/LangGraph. Agent trả lời câu hỏi về thẻ, tài khoản, chuyển tiền, tiết kiệm, vay, lừa đảo, ứng dụng ngân hàng và lãi suất tiết kiệm, dựa trên dữ liệu nội bộ, chỉ tìm trên web khi dữ liệu nội bộ không có.

## Cách hoạt động

```
Khách hỏi ──> Agent (Gemini · gemini-3.1-flash-lite)
                 │
                 ├── search_faq         Tìm hội thoại CSKH tương tự trong Qdrant (thủ tục, xử lý sự cố)
                 ├── get_interest_rate  Tra bảng lãi suất tiết kiệm từ file CSV
                 └── web_search         Tavily – chỉ khi 2 tool trên không có câu trả lời
```

Quy tắc hành vi của agent (system prompt trong `utils/agent_prompts.py`):

- Xưng "em", gọi khách là "anh/chị", trả lời ngắn gọn (~80 từ).
- Chỉ trả lời dựa trên kết quả tool, không tự đoán số liệu.
- Khách bị lừa đảo, mất tiền, khóa tài khoản…: hướng dẫn bước khẩn cấp rồi chuyển nhân viên.
- Không bao giờ hỏi OTP, mật khẩu, PIN.
- Từ chối câu hỏi ngoài phạm vi (tư vấn đầu tư vàng, cổ phiếu…).

## Cấu trúc thư mục

```
bank_faqs/
├── dataset/
│   ├── cskh_hoi_thoai_ngan_hang.csv        # Hội thoại gốc, mỗi dòng là 1 lượt nói
│   ├── cskh_gop_theo_id.csv                # Hội thoại đã gộp theo id (đầu vào của vector DB)
│   ├── cskh_hoi_dap_ngan_hang.csv          # Dạng cặp hỏi–đáp kèm ngữ cảnh
│   ├── lai_suat_ngan_hang_23-10-2026.csv   # Lãi suất tiết kiệm 17 ngân hàng
│   └── chi_nhanh_ngan_hang_quy_nhon.csv    # Chi nhánh ngân hàng tại Quy Nhơn (chưa dùng)
├── src/bank_faqs/
│   ├── __init__.py               # Fix lỗi DLL của torch trên Windows
│   ├── llm.py                    # Cấu hình LLM dùng chung: google_llm (Gemini), groq_llm (Groq)
│   ├── bank_agent.py             # Agent dựng bằng create_agent (LangChain), chạy thử 4 câu hỏi mẫu
│   ├── bank_graph.py             # Cùng agent đó nhưng tự dựng bằng StateGraph (LangGraph)
│   ├── tools.py                  # search_faq, get_interest_rate, web_search
│   ├── vector_db.py              # Embedding bkai + Qdrant, nạp dữ liệu
│   ├── api.py                    # Web app FastAPI: trang chat + POST /chat
│   ├── static/index.html         # Giao diện chat
│   └── utils/
│       ├── agent_prompts.py      # System prompt của từng agent
│       ├── mapping.py            # Đăng ký tool và gán tool cho agent
│       ├── history.py            # Cắt bớt lịch sử hội thoại trước khi gửi model
│       └── get_conversation_by_id.py  # Gộp các lượt hội thoại theo id
├── tests/                        # pytest: tool lãi suất, xử lý lỗi, lịch sử, API
├── certs/                        # CA nội bộ (*.crt) cho mạng có SSL inspection, không commit
├── Dockerfile                    # Image cho web app
├── docker-compose.yml            # Qdrant + web app
├── langgraph.json                # Cấu hình cho `langgraph dev`
└── pyproject.toml
```

## Yêu cầu

- Python 3.12.15 và [uv](https://docs.astral.sh/uv/)
- Docker (để chạy Qdrant và web app)
- API key: [Google AI Studio](https://aistudio.google.com/apikey) (Gemini), [Groq](https://console.groq.com), [Tavily](https://tavily.com); LangSmith (tùy chọn, để trace)

## Cài đặt

```bash
uv sync
```

Tạo file `.env` ở thư mục gốc (đã có trong `.gitignore`):

```env
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
| `qdrant` | 6333, 6334 | Vector DB, dữ liệu lưu ở `qdrant_storage/` |
| `bank_faqs_api` | 8000 | Web app FastAPI (uvicorn) |

Khi khởi động, API chờ Qdrant sẵn sàng (thử lại tối đa ~60 giây). Nếu collection còn rỗng, API **tự nạp dữ liệu** từ `dataset/cskh_gop_theo_id.csv`; đặt `AUTO_INGEST: "false"` trong `docker-compose.yml` để tắt. Model embedding được tải sẵn vào image lúc build, nên container không cần tải lại khi chạy. Lần build đầu mất vài phút.

Sau khi chạy:

- **Trang chat:** http://localhost:8000
- **Tài liệu API (Swagger):** http://localhost:8000/docs
- **Kiểm tra trạng thái:** http://localhost:8000/health trả về `{"status": "ok", "documents": 34}`

```bash
docker compose logs -f api     # xem log
docker compose down            # dừng (dữ liệu Qdrant vẫn giữ)
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
| 429 | Gemini/Groq báo vượt giới hạn (theo phút hoặc theo ngày) (xem [Giới hạn của LLM](#giới-hạn-của-llm-gói-free)) |
| 502 | Gemini/Groq lỗi khác |
| 503 | `/health`: không kết nối được Qdrant |

```bash
curl http://localhost:8000/chat -H 'Content-Type: application/json' \
  -d '{"message": "lãi suất 12 tháng BIDV"}'
```

### Mạng công ty có SSL inspection

Nếu log báo `CERTIFICATE_VERIFY_FAILED: self-signed certificate in certificate chain` (ví dụ khi gửi trace lên LangSmith), nghĩa là proxy của công ty đang cấp lại chứng chỉ HTTPS bằng CA nội bộ. Máy Windows đã tin CA này, nhưng container thì không. Cách xử lý: xuất CA từ kho chứng chỉ Windows vào thư mục `certs/` rồi build lại image. Dockerfile sẽ cài mọi file `certs/*.crt` vào container. Các file `.crt` này không được commit.

```powershell
# PowerShell: đổi 'CN=ten-CA*' thành tên CA của công ty (xem issuer của chứng chỉ bị lỗi)
$c = Get-ChildItem Cert:\LocalMachine\Root | Where-Object { $_.Subject -like 'CN=ten-CA*' } | Select-Object -First 1
"-----BEGIN CERTIFICATE-----`n" + [Convert]::ToBase64String($c.RawData, 'InsertLineBreaks') + "`n-----END CERTIFICATE-----" | Set-Content -Encoding ascii certs\company-ca.crt
docker compose up -d --build api
```

**Giới hạn:** lịch sử hội thoại lưu trong RAM của container (`InMemorySaver`), nên mất khi restart. Vì vậy uvicorn chỉ chạy 1 worker. Muốn chạy nhiều worker hoặc nhiều container thì phải đổi sang checkpointer dùng chung, ví dụ Postgres (`langgraph-checkpoint-postgres`).

## Chạy trên máy (không Docker)

**1. Khởi động Qdrant**

```bash
docker compose up -d qdrant
```

Dashboard tại http://localhost:6333/dashboard. Dữ liệu lưu trong `qdrant_storage/`.

**2. Nạp dữ liệu vào vector DB** (chạy lần đầu, hoặc khi dataset thay đổi)

```bash
# Gộp các lượt hội thoại theo id -> dataset/cskh_gop_theo_id.csv
uv run python -m bank_faqs.utils.get_conversation_by_id

# Embedding và nạp vào collection 'cskh_bkai'
uv run python -m bank_faqs.vector_db
```

Lần chạy đầu sẽ tải model `bkai-foundation-models/vietnamese-bi-encoder` từ Hugging Face. ID mỗi điểm được sinh cố định từ `hoi_thoai_id`, nên chạy lại sẽ ghi đè chứ không tạo bản trùng.

**3. Chạy agent**

```bash
uv run python -m bank_faqs.bank_agent
```

Script chạy 4 câu hỏi mẫu (quên mật khẩu, lãi suất, lộ OTP, câu hỏi ngoài phạm vi) và in ra tool đã gọi cùng câu trả lời.

Dùng agent trong code:

```python
from bank_faqs.bank_agent import agent

res = agent.invoke({'messages': [{'role': 'user', 'content': 'thẻ bị nuốt ở cây ATM thì làm sao'}]})
print(res['messages'][-1].text)
```

**4. LangGraph Studio / API server**

```bash
uv run langgraph dev
```

Server chạy tại http://127.0.0.1:2024 với 2 graph khai báo trong `langgraph.json`: `agent_main` (`bank_agent.py`) và `bank_graph` (`bank_graph.py`). Hai graph dùng chung LLM, tool và system prompt, chỉ khác cách dựng. Có thể chat và xem từng bước gọi tool trên LangGraph Studio (link in ra khi khởi động), hoặc gọi qua API:

```bash
curl http://127.0.0.1:2024/runs/wait -H 'Content-Type: application/json' \
  -d '{"assistant_id": "agent_main", "input": {"messages": [{"role": "user", "content": "lãi suất 12 tháng BIDV"}]}}'
```

Trên Windows, cần làm bước trong mục [Lưu ý trên Windows](#lưu-ý-trên-windows) trước.

**5. Web app (không Docker)**

```bash
uv run uvicorn bank_faqs.api:app --port 8000
```

## Test

```bash
uv run pytest
```

Gồm 39 test, chạy khoảng 1 phút và không gọi Groq hay Tavily thật:

- `tests/test_history.py`: cắt lịch sử đúng ranh giới lượt hỏi, rút gọn kết quả tool cũ, không làm thay đổi state.

- `tests/test_tools.py`: nhận diện tên ngân hàng, dữ liệu lãi suất, tool tự bắt lỗi khi Qdrant hoặc Tavily lỗi.
- `tests/test_api.py`: các endpoint (dùng agent giả), validate input, mã lỗi 429/502/503, bộ nhớ theo `thread_id`, tự nạp dữ liệu và thử lại khi Qdrant chưa sẵn sàng.

## Giới hạn của LLM (gói free)

`bank_agent.py` (web app và graph `agent_main`) dùng **Gemini** (`google_llm`); `bank_graph.py` vẫn dùng **Groq** (`groq_llm`). Đổi model bằng cách sửa `llm.py` hoặc tham số `model=` trong `build_agent`.

**Gemini:** giới hạn tính **theo số request mỗi phút cho từng model**. Ví dụ `gemini-3.5-flash` ở gói free chỉ được 5 request/phút, mà mỗi câu hỏi tốn ít nhất 2 request (gọi tool rồi trả lời), nên chỉ được khoảng 2 câu/phút. Model `-lite` có quota riêng. Khi vượt giới hạn, API trả về 429 và ghi `LLM rate limit` vào log.

**Groq:**

Model `qwen/qwen3.8-27b` ở gói free có các giới hạn sau, tính chung cho mọi người dùng của cùng một API key:

| Giới hạn | Mức | Cách dự án xử lý |
|---|---|---|
| Token đầu ra / phút | 1000 | `llm.py` đặt `max_tokens=512`; câu trả lời thực tế khoảng 15–120 token. Không đặt thì mỗi request bị tính 2048 token, nên luôn lỗi. |
| Token đầu vào / phút | 7000 | `utils/history.py` cắt bớt lịch sử khi gửi model: chỉ gửi 4 lượt hỏi gần nhất, và rút kết quả tool của các lượt trước còn 300 ký tự. Nhờ vậy mỗi lần gọi chỉ còn khoảng 1100–2800 token. Trước đây, chat vài lượt là vượt 7000 và Groq trả lỗi 413. |
| Token / ngày | 200.000 | Không xử lý được trong code. Mỗi câu hỏi tốn khoảng 2.500–5.000 token, tức khoảng 50 câu mỗi ngày. Cần nhiều hơn thì nâng gói. |

Khi chạm giới hạn, SDK groq tự chờ rồi thử lại vài lần. Nếu vẫn không được, API trả về **429** và ghi loại giới hạn vào log (`docker compose logs api | grep "rate limit"`). Lịch sử đầy đủ vẫn được giữ trong bộ nhớ; việc cắt bớt chỉ áp dụng cho phần gửi đi model.

## Các tool

| Tool | Nguồn dữ liệu | Dùng khi |
|---|---|---|
| `search_faq(query)` | Qdrant, top 3 hội thoại tương tự | Thủ tục, xử lý sự cố |
| `get_interest_rate(bank='')` | `lai_suat_ngan_hang_23-10-2026.csv` | Lãi suất tiết kiệm online/tại quầy, kỳ hạn 1–36 tháng. Để trống `bank` để lấy bảng so sánh mọi ngân hàng |
| `web_search(query)` | Tavily, 3 kết quả | Khuyến mãi, tin tức, lãi suất vay, ngân hàng không có trong CSV |

`search_faq` và `web_search` tự bắt lỗi (Qdrant sập, Tavily timeout…) và trả thông báo lỗi cho model, thay vì làm hỏng cả lượt hội thoại.

`get_interest_rate` nhận tên ngân hàng không dấu, viết tắt hoặc có tiền tố "ngân hàng" (`vcb`, `Vietin`, `mb bank`, `bac a`, `ngân hàng Techcom`…). Danh sách tên tắt nằm trong `BANK_ALIASES` ở `tools.py`.

**Cập nhật lãi suất:** thay file CSV mới (giữ nguyên tên cột) rồi sửa `RATE_FILE` và `RATE_DATE` trong `tools.py`.

**Thêm tool mới:** viết hàm `@tool` trong `tools.py`, đăng ký vào `TOOLS` và `AGENT_TOOLS` trong `utils/mapping.py`, rồi bổ sung quy tắc dùng tool trong `utils/agent_prompts.py`.

## Lưu ý trên Windows

**Lỗi `OSError: [WinError 1114] ... torch\lib\c10.dll`**

Nguyên nhân: trên máy có antivirus như McAfee, khi Python chạy truy vấn WMI (module `platform` làm việc này, và `pandas`, `truststore`, `langgraph dev` đều gọi `platform`), plugin AMSI của antivirus được nạp vào process kèm một bản `msvcp140.dll` rất cũ (14.00). `torch` cần bản mới hơn nên không khởi tạo được.

Cách xử lý: nạp `msvcp140.dll` của Windows ngay khi Python khởi động, bằng một file `.pth` trong venv. **Chạy lại lệnh này mỗi khi tạo lại `.venv`:**

```bash
uv run python -c "import site, pathlib; pathlib.Path(site.getsitepackages()[-1], '_msvcp140_preload.pth').write_text(\"import sys, ctypes; sys.platform == 'win32' and ctypes.WinDLL('msvcp140.dll')\n\")"
```

Kiểm tra: `uv run python -c "import pandas, torch"` không báo lỗi là được.

Dự phòng khi chưa có file `.pth`: `src/bank_faqs/__init__.py` cũng nạp trước `msvcp140.dll`, và các file chạy được (`vector_db.py`, `tools.py`, `bank_agent.py`, `bank_graph.py`) đều có `import bank_faqs` ở **dòng đầu tiên**, nên `python -m ...` vẫn chạy được. Tuy vậy, chỉ cách này thì không đủ cho `langgraph dev`, vì server import `pandas` trước khi nạp code của dự án.

Nếu chuyển hướng output (pipe, ghi ra file) mà gặp `UnicodeEncodeError` khi in tiếng Việt, đặt biến môi trường `PYTHONUTF8=1`.
