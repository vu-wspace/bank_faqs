from bank_faqs.tools import search_faq, web_search

TOOLS = {
    'search_faq': {
        'func': search_faq,
        'description': (
            'Tra cứu câu trả lời chăm sóc khách hàng từ dữ liệu nội bộ: thẻ, chuyển tiền, tài khoản, '
            'tiết kiệm, vay, lừa đảo, ứng dụng ngân hàng. Dùng cho câu hỏi về thủ tục và cách xử lý sự cố. '
            'Không dùng để tra lãi suất hoặc tin tức mới nhất (dùng web_search).'
        ),
        'args': {'query': 'string - câu hỏi của khách hàng'},
    },
    'web_search': {
        'func': web_search,
        'description': (
            'Tìm kiếm thông tin mới nhất trên web: lãi suất hiện hành, khuyến mãi, tin tức ngân hàng. '
            'Chỉ dùng khi search_faq không có câu trả lời hoặc khi cần số liệu cập nhật. '
            'Không dùng cho câu hỏi thủ tục, xử lý sự cố (dùng search_faq).'
        ),
        'args': {'query': 'string - từ khóa tìm kiếm'},
    },
}

AGENT_TOOLS = {
    'agent_main': ['search_faq', 'web_search'],
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
