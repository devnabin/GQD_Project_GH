import os

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_openai import AzureChatOpenAI
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

load_dotenv() 


# Tool


# LLM with bound tool
llm = AzureChatOpenAI(
    model = os.getenv('AZURE_OPENAI_MODEL'),
    # model_provider="azure_openai",
    azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
    api_version="2024-02-01",
)


def multiply(a: int, b: int) -> int:
    """Multiply a and b.

    Args:
        a: first int
        b: second int
    """
    return a * b


llm_with_tools = llm.bind_tools([multiply])

# Node
def tool_calling_llm(state: MessagesState):
    return {"messages": [llm_with_tools.invoke(state["messages"])]}

# Build graph
builder = StateGraph(MessagesState)
builder.add_node("call_the_process", tool_calling_llm)
builder.add_node("tools", ToolNode([multiply]))

builder.add_edge(START, "call_the_process")
builder.add_conditional_edges(
    "call_the_process",
    # If the latest message (result) from assistant is a tool call -> tools_condition routes to tools
    # If the latest message (result) from assistant is a not a tool call -> tools_condition routes to END
    tools_condition,
)
builder.add_edge("tools", END)

# Compile graph
graph = builder.compile()