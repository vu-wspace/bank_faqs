import truststore
from dotenv import load_dotenv
from langchain.tools import tool
from typing import Dict, Any
from bank_faqs.vector_db import get_retriever
from tavily import TavilyClient
from functools import lru_cache

truststore.inject_into_ssl()
load_dotenv()

tavily_client = TavilyClient()

@lru_cache
def _retriever():
    return get_retriever()

@tool
def search_faq(query: str) -> str:
    """Tra cứu câu trả lời chăm sóc khách hàng từ dữ liệu nội bộ: thẻ, chuyển tiền, tài khoản, 
    tiết kiệm, vay, lừa đảo, ứng dụng ngân hàng. Dùng cho câu hỏi về thủ tục và cách xử lý sự cố. 
    Không dùng để tra lãi suất hoặc tin tức mới nhất (dùng web_search)."""
    hits = _retriever().invoke(query)
    if not hits:
        return 'Không tìm thấy câu trả lời trong dữ liệu nội bộ.'
    return '\n\n'.join(
        f"Hỏi: {h.page_content}\nĐáp: {h.metadata['answer']}" for h in hits
    )

@tool
def web_search(query: str) -> Dict[str, Any]:
    """Tìm kiếm thông tin mới nhất trên web: lãi suất hiện hành, khuyến mãi, tin tức ngân hàng. 
    Chỉ dùng khi search_faq không có câu trả lời hoặc khi cần số liệu cập nhật. 
    Không dùng cho câu hỏi thủ tục, xử lý sự cố (dùng search_faq)."""
    return tavily_client.search(query, max_results=3, timeout=30)

def main():
    res = tavily_client.search('Lãi suất tiết kiệm Vietcombank hôm nay là bao nhiêu?', max_results=3)
    for r in res['results']:
        print(r['title'], '-', r['url'])

if __name__=='__main__':
    main()
