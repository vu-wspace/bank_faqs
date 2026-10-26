import bank_faqs  # noqa: F401 - phải import đầu tiên khi chạy file trực tiếp (xem __init__.py)
from typing import Annotated, TypedDict
from langchain_core.messages import AnyMessage, SystemMessage
from langgraph.graph.message import add_messages
from bank_faqs.llm import groq_llm
from bank_faqs.tools import get_agent_tools
from bank_faqs.prompts import get_system_prompt
from bank_faqs.history import trim_history
from langgraph.graph import START, StateGraph
from langgraph.prebuilt import tools_condition, ToolNode

TOOLS = get_agent_tools('agent_main')
SYSTEM_PROMPT = get_system_prompt('agent_main')

llm_with_tools = groq_llm.bind_tools(TOOLS, parallel_tool_calls=False)

# States
class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]

# Nodes
def call_model(state: State) -> dict:
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + trim_history(state['messages'])
    response = llm_with_tools.invoke(messages)
    return {'messages': [response]}

tool_node = ToolNode(TOOLS)

# Graph
builder = StateGraph(State)

# Define Nodes
builder.add_node('model', call_model)
builder.add_node('tools', tool_node)

# Define Edges
builder.add_edge(START, 'model')

builder.add_conditional_edges(
    'model',
    # If the last message (result) from assistant is a tool call     -> tools_condition routes to tools
    # If the last message (result) from assistant is not a tool call -> tools_condition routes to END
    tools_condition,
)

builder.add_edge('tools', 'model')

graph = builder.compile()

if __name__ == "__main__":
    res = graph.invoke(
        {
            'messages': [
                {
                    'role': 'user',
                    'content': 'quên mk app rồi, lấy lại sao vậy',
                },
            ]
        }
    )

    for m in res['messages']:
        m.pretty_print()
