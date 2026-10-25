import bank_faqs  # noqa: F401 - phải import đầu tiên: nạp fix DLL cho torch trên Windows (xem __init__.py)
import truststore
import re
import unicodedata
import pandas as pd
from dotenv import load_dotenv
from langchain.tools import tool
from typing import Dict, Any
from bank_faqs.vector_db import get_retriever
from bank_faqs.utils.get_conversation_by_id import DATASET
from tavily import TavilyClient
from functools import lru_cache

truststore.inject_into_ssl()
load_dotenv()

tavily_client = TavilyClient()

RATE_FILE = DATASET / 'lai_suat_ngan_hang_23-10-2026.csv'
RATE_DATE = '23/10/2026'
TERMS = ['1T', '3T', '6T', '12T', '18T', '24T', '36T']

# Tên gọi tắt hay gặp -> Mã NH trong file lãi suất (đã chuẩn hóa bằng _norm)
BANK_ALIASES = {
    'vcb': 'vietcombank', 'ngoaithuong': 'vietcombank',
    'dautuvaphattrien': 'bidv',
    'vietin': 'vietinbank', 'ctg': 'vietinbank', 'congthuong': 'vietinbank',
    'nongnghiep': 'agribank',
    'tcb': 'techcombank', 'techcom': 'techcombank',
    'stb': 'sacombank', 'sacom': 'sacombank',
    'vpb': 'vpbank',
    'mb': 'mbbank', 'quandoi': 'mbbank',
    'hdb': 'hdbank',
    'seab': 'seabank',
    'pvcom': 'pvcombank',
    'baca': 'bacabank', 'bab': 'bacabank',
    'baoviet': 'baovietbank', 'bvb': 'baovietbank',
    'nama': 'namabank', 'nab': 'namabank',
    'banviet': 'bvbank',
}

@lru_cache
def _retriever():
    return get_retriever()

def _norm(text: str) -> str:
    text = unicodedata.normalize('NFD', text.lower().replace('đ', 'd'))
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]', '', text)

@lru_cache
def _rates() -> pd.DataFrame:
    df = pd.read_csv(RATE_FILE, encoding='utf-8-sig')
    df['_key'] = df['Mã NH'].map(_norm)
    return df

def _find_bank(df: pd.DataFrame, bank: str) -> pd.DataFrame:
    key = _norm(bank).removeprefix('nganhang')
    key = BANK_ALIASES.get(key, key)
    exact = df[df['_key'] == key]
    if not exact.empty or len(key) < 3:
        return exact
    return df[df['_key'].str.contains(key, regex=False) | df['_key'].map(lambda k: k in key)]

def _fmt(v) -> str:
    return 'không có' if pd.isna(v) else f'{v:g}%'

@tool
def search_faq(query: str) -> str:
    """Tra cứu câu trả lời chăm sóc khách hàng từ dữ liệu nội bộ: thẻ, chuyển tiền, tài khoản, 
    tiết kiệm, vay, lừa đảo, ứng dụng ngân hàng. Dùng cho câu hỏi về thủ tục và cách xử lý sự cố. 
    Không dùng để tra lãi suất (dùng get_interest_rate) hoặc tin tức mới nhất (dùng web_search)."""
    hits = _retriever().invoke(query)
    if not hits:
        return 'Không tìm thấy câu trả lời trong dữ liệu nội bộ.'
    return '\n\n'.join(
        f"Hỏi: {h.page_content}\nĐáp: {h.metadata['answer']}" for h in hits
    )

@tool
def get_interest_rate(bank: str = '') -> str:
    """Tra lãi suất tiết kiệm (%/năm) theo kỳ hạn 1-36 tháng, gửi online và tại quầy, của các ngân hàng
    tại Quy Nhơn. Truyền tên ngân hàng (vd: BIDV, Vietcombank, MB). Để trống để lấy bảng lãi suất
    online của tất cả ngân hàng (dùng khi so sánh, hỏi ngân hàng nào cao nhất).
    Luôn dùng tool này trước web_search cho câu hỏi lãi suất tiết kiệm."""
    df = _rates()
    if not bank.strip():
        cols = [f'Online {t} (%/năm)' for t in TERMS]
        lines = [f"{r['Mã NH']}: " + ', '.join(f'{t} {_fmt(r[c])}' for t, c in zip(TERMS, cols))
                 for _, r in df.iterrows()]
        return f'Lãi suất tiết kiệm online (%/năm), cập nhật {RATE_DATE}:\n' + '\n'.join(lines)

    hits = _find_bank(df, bank)
    if hits.empty:
        return (f"Không có dữ liệu lãi suất của '{bank}'. "
                f"Các ngân hàng có dữ liệu: {', '.join(df['Mã NH'])}.")
    out = []
    for _, r in hits.iterrows():
        online = ', '.join(f"{t} {_fmt(r[f'Online {t} (%/năm)'])}" for t in TERMS)
        counter = ', '.join(f"{t} {_fmt(r[f'Tại quầy {t} (%/năm)'])}" for t in TERMS)
        out.append(f"{r['Mã NH']} (cập nhật {RATE_DATE}, T = tháng):\n- Online: {online}\n- Tại quầy: {counter}")
    return '\n\n'.join(out)

@tool
def web_search(query: str) -> Dict[str, Any]:
    """Tìm kiếm thông tin mới nhất trên web: khuyến mãi, tin tức ngân hàng, lãi suất vay,
    lãi suất của ngân hàng không có trong get_interest_rate.
    Chỉ dùng khi search_faq và get_interest_rate không có câu trả lời.
    Không dùng cho câu hỏi thủ tục, xử lý sự cố (dùng search_faq)."""
    return tavily_client.search(query, max_results=3, timeout=30)

def main():
    res = tavily_client.search('Lãi suất tiết kiệm Vietcombank hôm nay là bao nhiêu?', max_results=3)
    for r in res['results']:
        print(r['title'], '-', r['url'])

if __name__=='__main__':
    main()
