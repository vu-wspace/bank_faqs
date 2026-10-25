# bank-faqs

Agent chăm sóc khách hàng ngân hàng bằng tiếng Việt, xây dựng với LangChain/LangGraph. Agent trả lời câu hỏi về thẻ, tài khoản, chuyển tiền, tiết kiệm, vay, lừa đảo, ứng dụng ngân hàng và lãi suất tiết kiệm, dựa trên dữ liệu nội bộ, chỉ tìm trên web khi dữ liệu nội bộ không có.

## Cách hoạt động

```
Khách hỏi ──> Agent (Groq · qwen/qwen3.8-27b)
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
│   ├── bank_agent.py             # Khởi tạo LLM + agent, chạy thử 4 câu hỏi mẫu
│   ├── tools.py                  # search_faq, get_interest_rate, web_search
│   ├── vector_db.py              # Embedding bkai + Qdrant, nạp dữ liệu
│   └── utils/
│       ├── agent_prompts.py      # System prompt của từng agent
│       ├── mapping.py            # Đăng ký tool và gán tool cho agent
│       └── get_conversation_by_id.py  # Gộp các lượt hội thoại theo id
├── docker-compose.yml            # Qdrant
└── pyproject.toml
```

## Yêu cầu

- Python 3.12.15 và [uv](https://docs.astral.sh/uv/)
- Docker (để chạy Qdrant)
- API key: [Groq](https://console.groq.com), [Tavily](https://tavily.com); LangSmith (tùy chọn, để trace)

## Cài đặt

```bash
uv sync
```

Tạo file `.env` ở thư mục gốc (đã có trong `.gitignore`):

```env
GROQ_API_KEY=...
TAVILY_API_KEY=...
QDRANT_URL=http://localhost:6333

# Tùy chọn
LANGSMITH_API_KEY=...
LANGSMITH_TRACING=true
LANGSMITH_PROJECT=bank-faqs
```

## Chạy

**1. Khởi động Qdrant**

```bash
docker compose up -d
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

## Các tool

| Tool | Nguồn dữ liệu | Dùng khi |
|---|---|---|
| `search_faq(query)` | Qdrant, top 3 hội thoại tương tự | Thủ tục, xử lý sự cố |
| `get_interest_rate(bank='')` | `lai_suat_ngan_hang_23-10-2026.csv` | Lãi suất tiết kiệm online/tại quầy, kỳ hạn 1–36 tháng. Để trống `bank` để lấy bảng so sánh mọi ngân hàng |
| `web_search(query)` | Tavily, 3 kết quả | Khuyến mãi, tin tức, lãi suất vay, ngân hàng không có trong CSV |

`get_interest_rate` nhận tên ngân hàng không dấu, viết tắt hoặc có tiền tố "ngân hàng" (`vcb`, `Vietin`, `mb bank`, `bac a`, `ngân hàng Techcom`…). Danh sách tên tắt nằm trong `BANK_ALIASES` ở `tools.py`.

**Cập nhật lãi suất:** thay file CSV mới (giữ nguyên tên cột) rồi sửa `RATE_FILE` và `RATE_DATE` trong `tools.py`.

**Thêm tool mới:** viết hàm `@tool` trong `tools.py`, đăng ký vào `TOOLS` và `AGENT_TOOLS` trong `utils/mapping.py`, rồi bổ sung quy tắc dùng tool trong `utils/agent_prompts.py`.

## Lưu ý trên Windows

Trên một số máy Windows, `torch` báo lỗi `WinError 1114 ... c10.dll` nếu `pandas` hoặc `truststore` được import trước nó (xung đột MSVC runtime). `src/bank_faqs/__init__.py` xử lý bằng cách nạp trước `msvcp140.dll` của hệ thống. Vì vậy các file chạy được (`vector_db.py`, `tools.py`, `bank_agent.py`) đều có `import bank_faqs` ở **dòng đầu tiên**. Khi tạo file chạy mới, hãy giữ quy ước này.

Nếu chuyển hướng output (pipe, ghi ra file) mà gặp `UnicodeEncodeError` khi in tiếng Việt, đặt biến môi trường `PYTHONUTF8=1`.
