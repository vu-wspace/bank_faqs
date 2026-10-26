# bank-faqs

Agent chăm sóc khách hàng ngân hàng bằng tiếng Việt, xây dựng với LangChain/LangGraph. Agent trả lời câu hỏi về thẻ, tài khoản, chuyển tiền, tiết kiệm, vay, lừa đảo, ứng dụng ngân hàng, lãi suất tiết kiệm và địa chỉ chi nhánh tại Quy Nhơn. Câu trả lời dựa trên dữ liệu nội bộ; agent chỉ tìm trên web khi dữ liệu nội bộ không có. Có kèm web chat (FastAPI) chạy bằng Docker.

## Cách hoạt động

```
Khách hỏi ──> Agent (Gemini · gemini-3.1-flash-lite)
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
- `get_branch_info` trả về cho từng chi nhánh: địa chỉ theo nguồn, phường mới (sau sáp nhập 1/7/2025), điện thoại, giờ làm việc, **độ tin cậy** và **URL nguồn**. Ô ghi "Chưa có nguồn" trong CSV được trả về là "chưa có thông tin", để model không tự bịa. Trong câu trả lời, agent ghi link nguồn cạnh từng chi nhánh, và trang chat hiển thị link bấm được.
- `search_faq` và `web_search` tự bắt lỗi (Qdrant sập, Tavily timeout…) và trả thông báo lỗi cho model, thay vì làm hỏng cả lượt hội thoại.

**Cập nhật dữ liệu:**
- **Lãi suất:** đặt file CSV mới vào `data/raw/` (giữ nguyên tên cột), rồi sửa `RATE_FILE` và `RATE_DATE` trong `config.py`.
- **Chi nhánh:** sửa trực tiếp `data/raw/chi_nhanh_ngan_hang_quy_nhon.csv` (giữ nguyên tên cột). Cột `Nguồn` có thể chứa nhiều URL, phân cách bằng `;`.
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
│   ├── processed/
│   │   └── cskh_gop_theo_id.csv              # Hội thoại đã gộp theo id, sinh bởi data_prep.py, nạp vào Qdrant
│   └── unused/                               # Chưa dùng trong code, không đưa vào image Docker
│       └── cskh_hoi_dap_ngan_hang.csv        # Cùng dữ liệu hội thoại, dạng cặp hỏi–đáp kèm ngữ cảnh
├── src/bank_faqs/
│   ├── __init__.py       # Khởi tạo chung: fix DLL torch (Windows), dùng kho chứng chỉ hệ thống, nạp .env
│   ├── config.py         # Đường dẫn dữ liệu, cấu hình Qdrant/embedding, biến môi trường
│   ├── llm.py            # Cấu hình LLM: google_llm (Gemini), groq_llm (Groq)
│   ├── prompts.py        # System prompt của từng agent
│   ├── tools.py          # 4 tool + gán tool cho từng agent
│   ├── history.py        # Cắt bớt lịch sử hội thoại trước khi gửi model
│   ├── agent.py          # Agent dựng bằng create_agent (LangChain), chạy thử 4 câu hỏi mẫu
│   ├── graph.py          # Cùng agent đó nhưng tự dựng bằng StateGraph (LangGraph)
│   ├── data_prep.py      # Gộp các lượt hội thoại theo id -> data/processed/
│   ├── vector_db.py      # Embedding bkai + Qdrant, nạp dữ liệu
│   ├── api.py            # Web app FastAPI: trang chat + POST /chat + /health
│   └── static/index.html # Giao diện chat
├── tests/                # pytest (51 test)
├── certs/                # CA nội bộ (*.crt) cho mạng có SSL inspection, không commit
├── Dockerfile            # Image cho web app
├── docker-compose.yml    # Qdrant + web app
├── langgraph.json        # Cấu hình cho `langgraph dev`
├── pyproject.toml        # Thư viện (nguồn chính, cùng uv.lock)
└── requirements.txt      # Danh sách thư viện cho pip, khớp với pyproject.toml
```

## Yêu cầu

- Python 3.12.15 và [uv](https://docs.astral.sh/uv/)
- Docker (để chạy Qdrant và web app)
- API key: [Google AI Studio](https://aistudio.google.com/apikey) (Gemini), [Groq](https://console.groq.com), [Tavily](https://tavily.com); LangSmith (tùy chọn, để trace)

## Cài đặt

```bash
uv sync            # cài thư viện + nhóm dev (pytest, langgraph-cli, jupyter)
```

Nếu dùng pip thay cho uv: `pip install -r requirements.txt`. File này đã có sẵn index của torch bản CPU. Thư viện dev cài riêng theo hướng dẫn ở cuối file.

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
| `qdrant` | 6333, 6334 | Vector DB (v1.20.0), dữ liệu lưu ở Docker volume `qdrant_data` |
| `bank_faqs_api` | 8000 | Web app FastAPI (uvicorn) |

- Khi khởi động, API chờ Qdrant sẵn sàng (thử lại tối đa ~60 giây).
- Nếu collection còn rỗng, API **tự nạp dữ liệu** từ `data/processed/cskh_gop_theo_id.csv`. Đặt `AUTO_INGEST: "false"` trong `docker-compose.yml` để tắt.
- Model embedding được tải sẵn vào image lúc build, nên container không cần mạng tới Hugging Face.
- Lần build đầu mất vài phút. Các lần sau, nếu chỉ sửa `src/` hoặc `data/`, Docker dùng lại cache của bước cài thư viện và tải model.
- Image chỉ chứa thứ cần để chạy: không có `tests/`, `data/unused/`, `.env` (key được truyền qua `env_file` lúc chạy), hay thư viện dev.

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
| 429 | Gemini/Groq báo vượt giới hạn (theo phút hoặc theo ngày); xem [Giới hạn của LLM](#giới-hạn-của-llm-gói-free) |
| 502 | Gemini/Groq lỗi khác |
| 503 | `/health`: không kết nối được Qdrant |

```bash
curl http://localhost:8000/chat -H 'Content-Type: application/json' \
  -d '{"message": "chi nhánh BIDV ở Quy Nhơn"}'
```

**Giới hạn:** lịch sử hội thoại lưu trong RAM của container (`InMemorySaver`), nên mất khi restart. Vì vậy uvicorn chỉ chạy 1 worker. Muốn chạy nhiều worker hoặc nhiều container thì phải đổi sang checkpointer dùng chung, ví dụ Postgres (`langgraph-checkpoint-postgres`).

### Mạng công ty có SSL inspection

Nếu log báo `CERTIFICATE_VERIFY_FAILED: self-signed certificate in certificate chain` (ví dụ khi gọi Gemini hoặc gửi trace lên LangSmith), nghĩa là proxy của công ty đang cấp lại chứng chỉ HTTPS bằng CA nội bộ. Khi chạy trên máy, `bank_faqs/__init__.py` đã cho Python dùng kho chứng chỉ Windows (qua `truststore`), vốn đã tin CA này. Container thì không có CA đó. Cách xử lý: xuất CA từ kho chứng chỉ Windows vào thư mục `certs/` rồi build lại image. Dockerfile sẽ cài mọi file `certs/*.crt` vào container. Các file `.crt` này không được commit.

```powershell
# PowerShell: đổi 'CN=ten-CA*' thành tên CA của công ty (xem issuer của chứng chỉ bị lỗi)
$c = Get-ChildItem Cert:\LocalMachine\Root | Where-Object { $_.Subject -like 'CN=ten-CA*' } | Select-Object -First 1
"-----BEGIN CERTIFICATE-----`n" + [Convert]::ToBase64String($c.RawData, 'InsertLineBreaks') + "`n-----END CERTIFICATE-----" | Set-Content -Encoding ascii certs\company-ca.crt
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

Server chạy tại http://127.0.0.1:2024 với 2 graph khai báo trong `langgraph.json`: `agent_main` (`agent.py`) và `bank_graph` (`graph.py`). Hai graph dùng chung tool và system prompt, chỉ khác cách dựng và LLM (xem [Giới hạn của LLM](#giới-hạn-của-llm-gói-free)). Có thể chat và xem từng bước gọi tool trên LangGraph Studio (link in ra khi khởi động), hoặc gọi qua API:

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

Gồm 51 test, chạy dưới 1 phút và không gọi LLM hay Tavily thật:

- `tests/test_tools.py`:
  - nhận diện tên ngân hàng và dữ liệu lãi suất;
  - tool chi nhánh: lọc theo ngân hàng/đường, có nguồn và độ tin cậy, tách nhiều URL nguồn, ẩn ô "Chưa có nguồn";
  - tool tự bắt lỗi khi Qdrant hoặc Tavily lỗi.
- `tests/test_history.py`: cắt lịch sử đúng ranh giới lượt hỏi, rút gọn kết quả tool cũ, không làm thay đổi state.
- `tests/test_api.py`:
  - các endpoint (dùng agent giả) và validate input;
  - mã lỗi 429/502/503, của cả Gemini và Groq;
  - bộ nhớ theo `thread_id`;
  - tự nạp dữ liệu, thử lại khi Qdrant chưa sẵn sàng, và dùng chung một Qdrant client.

## Giới hạn của LLM (gói free)

`agent.py` (web app và graph `agent_main`) dùng **Gemini** (`google_llm`), còn `graph.py` dùng **Groq** (`groq_llm`). Đổi model bằng cách sửa `llm.py`, hoặc tham số `model=` trong `build_agent`.

**Gemini:** giới hạn tính **theo số request mỗi phút cho từng model**. Ví dụ `gemini-3.5-flash` ở gói free chỉ được 5 request/phút, mà mỗi câu hỏi tốn ít nhất 2 request (gọi tool rồi trả lời), nên chỉ được khoảng 2 câu/phút. Model `-lite` có quota riêng. Khi vượt giới hạn, API trả về 429 và ghi `LLM rate limit` vào log.

**Groq:** model `qwen/qwen3.8-27b` ở gói free có các giới hạn sau, tính chung cho mọi người dùng của cùng một API key:

| Giới hạn | Mức | Cách dự án xử lý |
|---|---|---|
| Token đầu ra / phút | 1000 | `llm.py` đặt `max_tokens=512`; câu trả lời thực tế khoảng 15–120 token. Không đặt thì mỗi request bị tính 2048 token, nên luôn lỗi. |
| Token đầu vào / phút | 7000 | `history.py` cắt bớt lịch sử khi gửi model: chỉ gửi 4 lượt hỏi gần nhất, và rút kết quả tool của các lượt trước còn 300 ký tự. Nhờ vậy mỗi lần gọi chỉ còn khoảng 1100–2800 token. Trước đây, chat vài lượt là vượt 7000 và Groq trả lỗi 413. |
| Token / ngày | 200.000 | Không xử lý được trong code. Mỗi câu hỏi tốn khoảng 2.500–5.000 token, tức khoảng 50 câu mỗi ngày. Cần nhiều hơn thì nâng gói. |

Khi chạm giới hạn, SDK tự chờ rồi thử lại vài lần. Nếu vẫn không được, API trả về **429** và ghi loại giới hạn vào log (`docker compose logs api | grep "rate limit"`). Lịch sử đầy đủ vẫn được giữ trong bộ nhớ; việc cắt bớt chỉ áp dụng cho phần gửi đi model. Việc cắt bớt này áp dụng cho cả hai model.

## Lưu ý về dữ liệu chi nhánh

- Dữ liệu được tổng hợp từ nguồn công khai, chủ yếu là trang đăng ký thuế (infodoanhnghiep.com). Cột `Ghi chú / độ tin cậy` cho biết mỗi thông tin lấy từ đâu.
- Địa chỉ là địa chỉ **theo nguồn**, nhiều chỗ còn theo địa giới hành chính trước khi sáp nhập phường ngày 1/7/2025. Cột `Phường mới` ghi phường sau sáp nhập nếu đối chiếu được.
- 19/23 chi nhánh chưa có số điện thoại, và chưa chi nhánh nào có giờ làm việc.
- Chi nhánh "BIDV CN Quy Nhơn" có URL nguồn mang chữ `Chi-Nhanh-Tay-Son`. Nên kiểm tra lại dòng này.

## Lưu ý trên Windows

**Lỗi `OSError: [WinError 1114] ... torch\lib\c10.dll`**

Nguyên nhân: trên máy có antivirus như McAfee, khi Python chạy truy vấn WMI (module `platform` làm việc này, và `pandas`, `truststore`, `langgraph dev` đều gọi `platform`), plugin AMSI của antivirus được nạp vào process kèm một bản `msvcp140.dll` rất cũ (14.00). `torch` cần bản mới hơn nên không khởi tạo được.

Cách xử lý: nạp `msvcp140.dll` của Windows ngay khi Python khởi động, bằng một file `.pth` trong venv. **Chạy lại lệnh này mỗi khi tạo lại `.venv`:**

```bash
uv run python -c "import site, pathlib; pathlib.Path(site.getsitepackages()[-1], '_msvcp140_preload.pth').write_text(\"import sys, ctypes; sys.platform == 'win32' and ctypes.WinDLL('msvcp140.dll')\n\")"
```

Kiểm tra: `uv run python -c "import pandas, torch"` không báo lỗi là được.

Dự phòng khi chưa có file `.pth`: `src/bank_faqs/__init__.py` cũng nạp trước `msvcp140.dll`, và các file chạy được (`vector_db.py`, `agent.py`, `graph.py`) đều có `import bank_faqs` ở **dòng đầu tiên**, nên `python -m ...` vẫn chạy được. Tuy vậy, chỉ cách này thì không đủ cho `langgraph dev`, vì server import `pandas` trước khi nạp code của dự án.

Nếu chuyển hướng output (pipe, ghi ra file) mà gặp `UnicodeEncodeError` khi in tiếng Việt, đặt biến môi trường `PYTHONUTF8=1`.
