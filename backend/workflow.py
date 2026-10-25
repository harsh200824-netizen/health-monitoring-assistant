
from typing import TypedDict, Any

from langgraph.graph import StateGraph, START, END


class HealthWorkflowState(TypedDict, total=False):
    question: str
    validated: bool
    result: dict[str, Any]
    error: str


def validate_input(state: HealthWorkflowState):
    question = state.get("question", "")

    if not isinstance(question, str) or not question.strip():
        return {
            "validated": False,
            "error": "Question cannot be empty."
        }

    return {"validated": True}


def run_health_agent(state: HealthWorkflowState):
    from backend.agent import run_agent

    answer = run_agent(state["question"])

    return {
        "result": {
            "question": state["question"],
            "answer": answer
        }
    }


def handle_invalid_input(state: HealthWorkflowState):
    return {
        "result": {
            "question": state.get("question", ""),
            "answer": state.get("error", "Invalid input.")
        }
    }


def choose_next_step(state: HealthWorkflowState):
    if state.get("validated"):
        return "agent"

    return "error"


builder = StateGraph(HealthWorkflowState)

builder.add_node("validate", validate_input)
builder.add_node("agent", run_health_agent)
builder.add_node("error", handle_invalid_input)

builder.add_edge(START, "validate")

builder.add_conditional_edges(
    "validate",
    choose_next_step,
    {
        "agent": "agent",
        "error": "error"
    }
)

builder.add_edge("agent", END)
builder.add_edge("error", END)

health_workflow = builder.compile()
