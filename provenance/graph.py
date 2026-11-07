"""LangGraph execution with explicit model, tool, and answer boundaries.

Checkpoint/resume is deliberately not enabled: budget reservations and evidence
read permissions must be persisted together before resuming can be safe.
"""

from typing import TypedDict


class ResearchState(TypedDict, total=False):
    messages: list
    response: dict
    answer: dict


def execute_graph(messages, model_step, tool_step, finish_step, max_model_calls):
    try:
        from langgraph.graph import END, START, StateGraph
    except ImportError:
        raise ValueError("Install project dependencies: uv sync") from None

    def model_node(state):
        response = model_step(state["messages"])
        return {"response": response, "messages": state["messages"] + response["output"]}

    def route(state):
        return (
            "tools"
            if any(item.get("type") == "function_call" for item in state["response"]["output"])
            else "finalize"
        )

    def tool_node(state):
        return {"messages": tool_step(state["messages"], state["response"]["output"])}

    def answer_node(state):
        return {"answer": finish_step(state["response"]["output"])}

    graph = StateGraph(ResearchState)
    graph.add_node("model", model_node)
    graph.add_node("tools", tool_node)
    graph.add_node("finalize", answer_node)
    graph.add_edge(START, "model")
    graph.add_conditional_edges("model", route, {"tools": "tools", "finalize": "finalize"})
    graph.add_edge("tools", "model")
    graph.add_edge("finalize", END)
    compiled = graph.compile()
    result = compiled.invoke({"messages": messages}, {"recursion_limit": 2 * max_model_calls + 4})
    return result["answer"]
