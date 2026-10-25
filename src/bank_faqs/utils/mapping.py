from bank_faqs.tools import search_faq, get_interest_rate, web_search

TOOLS = {
    'search_faq': {
        'func': search_faq,
        'description': (
            'Tra cứu câu trả lời chăm sóc khách hàng từ dữ liệu nội bộ: thẻ, chuyển tiền, tài khoản, '
            'tiết kiệm, vay, lừa đảo, ứng dụng ngân hàng. Dùng cho câu hỏi về thủ tục và cách xử lý sự cố. '
            'Không dùng để tra lãi suất (dùng get_interest_rate) hoặc tin tức mới nhất (dùng web_search).'
        ),
        'args': {'query': 'string - câu hỏi của khách hàng'},
    },
    'get_interest_rate': {
        'func': get_interest_rate,
        'description': (
            'Tra lãi suất tiết kiệm (%/năm) theo kỳ hạn 1-36 tháng, online và tại quầy, của các ngân hàng tại Quy Nhơn. '
            'Để trống bank để lấy bảng lãi suất online của tất cả ngân hàng (khi cần so sánh). '
            'Luôn dùng trước web_search cho câu hỏi lãi suất tiết kiệm.'
        ),
        'args': {'bank': 'string - tên ngân hàng (vd: BIDV, Vietcombank), có thể để trống'},
    },
    'web_search': {
        'func': web_search,
        'description': (
            'Tìm kiếm thông tin mới nhất trên web: khuyến mãi, tin tức ngân hàng, lãi suất vay, '
            'lãi suất của ngân hàng không có trong get_interest_rate. '
            'Chỉ dùng khi search_faq và get_interest_rate không có câu trả lời. '
            'Không dùng cho câu hỏi thủ tục, xử lý sự cố (dùng search_faq).'
        ),
        'args': {'query': 'string - từ khóa tìm kiếm'},
    },
}

AGENT_TOOLS = {
    'agent_main': ['search_faq', 'get_interest_rate', 'web_search'],
}

def get_tool(name: str):
    if name not in TOOLS:
        raise ValueError(f'Tool không tồn tại: {name}')
    return TOOLS[name]['func']

def get_agent_tools(agent: str) -> list:
    return [get_tool(name) for name in AGENT_TOOLS[agent]]

def tools_prompt(agent: str) -> str:
    lines = []
    for name in AGENT_TOOLS[agent]:
        t = TOOLS[name]
        args = ', '.join(f'{k}: {v}' for k, v in t['args'].items())
        lines.append(f"- {name}({args}): {t['description']}")
    return '\n'.join(lines)

if __name__ == '__main__':
    print(tools_prompt('agent_main'))
