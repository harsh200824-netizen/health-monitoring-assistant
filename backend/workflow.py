"""Validated orchestration for the health assistant chat flow."""
from typing import TypedDict, Any
import re

from langgraph.graph import StateGraph, START, END


MAX_QUESTION_LENGTH = 500


class HealthWorkflowState(TypedDict, total=False):
    question: str
    user_id: str
    validated: bool
    result: dict[str, Any]
    error: str


def validate_input(state: HealthWorkflowState):
    question = state.get("question", "")
    if not isinstance(question, str) or not question.strip():
        return {"validated": False, "error": "Please enter a question."}
    question = question.strip()
    if len(question) > MAX_QUESTION_LENGTH:
        return {
            "validated": False,
            "error": f"Question must be {MAX_QUESTION_LENGTH} characters or fewer.",
        }
    if any(ord(char) < 32 and char not in "\\n\\r\\t" for char in question):
        return {"validated": False, "error": "Question contains unsupported control characters."}
    return {"question": question, "validated": True}


def run_health_agent(state: HealthWorkflowState):
    from backend.agent import run_agent

    try:
        answer = run_agent(
            state["question"],
            user_id=state.get("user_id"),
        )
        if not isinstance(answer, str) or not answer.strip():
            answer = "I couldn't generate a response right now. Please try again."
    except Exception:
        # Keep internal provider details and secrets out of the API response.
        answer = "The health assistant is temporarily unavailable. Please try again shortly."

    return {"result": {"question": state["question"], "answer": answer}}


def handle_invalid_input(state: HealthWorkflowState):
    return {
        "result": {
            "question": state.get("question", ""),
            "answer": state.get("error", "Invalid input."),
        }
    }


def choose_next_step(state: HealthWorkflowState):
    return "agent" if state.get("validated") else "error"


builder = StateGraph(HealthWorkflowState)
builder.add_node("validate", validate_input)
builder.add_node("agent", run_health_agent)
builder.add_node("error", handle_invalid_input)
builder.add_edge(START, "validate")
builder.add_conditional_edges("validate", choose_next_step, {"agent": "agent", "error": "error"})
builder.add_edge("agent", END)
builder.add_edge("error", END)
health_workflow = builder.compile()
