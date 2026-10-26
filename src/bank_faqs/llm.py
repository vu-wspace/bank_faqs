from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI

groq_llm = ChatGroq(
    model='qwen/qwen3.8-27b',
    temperature=0,
    timeout=60,
    max_retries=3,
    reasoning_format='hidden',
    # Câu trả lời thực tế ~15-120 token. Không đặt thì Groq tính mỗi request 2048 token đầu ra,
    # vượt giới hạn gói free (1000 token đầu ra/phút) -> lỗi 429.
    max_tokens=512,
)

google_llm = ChatGoogleGenerativeAI(
    model='gemini-3.1-flash-lite',
    temperature=0,
    timeout=60,
    max_retries=3,
)
