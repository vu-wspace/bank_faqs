import bank_faqs  # noqa: F401 - phải import đầu tiên: nạp fix DLL cho torch trên Windows (xem __init__.py)
import truststore
from dotenv import load_dotenv
from typing import Annotated, TypedDict
from langchain_core.messages import AnyMessage, SystemMessage
from langgraph.graph.message import add_messages
from bank_faqs.llm import groq_llm
from bank_faqs.utils.mapping import get_agent_tools
from bank_faqs.utils.agent_prompts import get_system_prompt
from bank_faqs.utils.history import trim_history
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import tools_condition, ToolNode

truststore.inject_into_ssl()
load_dotenv()

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
bank_graph = StateGraph(State)

# Define Nodes
bank_graph.add_node('model', call_model)
bank_graph.add_node('tools', tool_node)

# Define Edges
bank_graph.add_edge(START, 'model')

bank_graph.add_conditional_edges(
    'model',
    # If the last message (result) from assistant is a tool call     -> tools_condition routes to tools
    # If the last message (result) from assistant is not a tool call -> tools_condition routes to END
    tools_condition,
)

bank_graph.add_edge('tools', 'model')

# Add
bank_agent = bank_graph.compile()
# bank_agent_mem = graph.compile(checkpointer=memory)

if __name__ == "__main__":
    res = bank_agent.invoke(
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
