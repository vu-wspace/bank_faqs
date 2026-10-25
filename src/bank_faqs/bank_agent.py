import truststore
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain.agents import create_agent
from bank_faqs.utils.mapping import get_agent_tools
from bank_faqs.utils.agent_prompts import get_system_prompt

truststore.inject_into_ssl()
load_dotenv()

groq_llm = ChatGroq(
    model='qwen/qwen3.8-27b',
    temperature=0,
    timeout=60,
    max_retries=3
)

agent = create_agent(
    model=groq_llm,
    tools=get_agent_tools('agent_main'),
    system_prompt=get_system_prompt('agent_main')
)

if __name__ == "__main__":
    tests = [
        'quên mk app rồi, lấy lại sao vậy',             # nên gọi search_faq
        'lãi suất gửi 12 tháng ở BIDV bao nhiêu',       # nên gọi web_search
        'em lỡ đưa otp cho người ta, mất hết tiền rồi', # nên báo chuyển nhân viên
        'nên mua vàng hay cổ phiếu',                    # nên từ chối
    ]
    for q in tests:
        res = agent.invoke({'messages': [{'role': 'user', 'content': q}]})
        called = [tc['name'] for m in res['messages'] for tc in (getattr(m, 'tool_calls', None) or [])]
        print(f"\nKhách: {q}\nTool đã gọi: {called}\nTrả lời: {res['messages'][-1].text}")
