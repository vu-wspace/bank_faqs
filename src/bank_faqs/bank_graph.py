from typing import TypedDict
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import tools_condition, ToolNode

# States
class State(TypedDict):
    graph_state: str

# Nodes
def node_1(state: State):
    return {'graph_state': state['graph_state'] + '...'}

def node_2(state: State):
    return {'graph_state': state['graph_state'] + '...'}

def makeTool():
    ...

# Graph
graph = StateGraph(State)

# Define Nodes
graph.add_node('node_1', node_1)
graph.add_node('node_2', node_2)

# graph.add_node('make_tool', makeTool)
# graph.add_node('tools', ToolNode(['tool']))

# Conditional edges
...

# Define Edges
graph.add_edge(START, 'node_1')
# graph.add_conditional_edges(
#     'make_tool',
#     # If the last message (result) from assistant is a tool call     -> tools_condition routes to tools
#     # If the last message (result) from assistant is not a tool call -> tools_condition routes to END
#     tools_condition,
# )
graph.add_edge('node_2', END)

# Add
react_graph = graph.compile()
# react_graph_mem = graph.compile(checkpointer=memory)
