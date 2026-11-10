"""Week 7 workflow validation and failure-handling tests."""
from backend.workflow import validate_input, handle_invalid_input


def test_workflow_rejects_blank_question():
    state = validate_input({"question": "   "})
    assert state["validated"] is False
    assert "enter a question" in state["error"].lower()


def test_workflow_rejects_oversized_question():
    state = validate_input({"question": "x" * 501})
    assert state["validated"] is False
    assert "500" in state["error"]


def test_workflow_accepts_valid_question_and_trims_it():
    state = validate_input({"question": "  How many steps did I record?  "})
    assert state["validated"] is True
    assert state["question"] == "How many steps did I record?"


def test_invalid_input_has_safe_fallback_result():
    result = handle_invalid_input({"question": "", "error": "Please enter a question."})
    assert result["result"]["answer"] == "Please enter a question."
