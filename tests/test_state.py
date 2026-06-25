from src.state import AgentEvent, WorkflowState


def test_workflow_state_is_updated_by_returning_a_new_copy() -> None:
    initial_state = WorkflowState()

    next_state = initial_state.with_event(
        agent="researcher",
        message="Fetched recent papers.",
        metadata={"count": 3},
    )

    assert initial_state.events == []
    assert next_state.events == [
        AgentEvent(
            agent="researcher",
            message="Fetched recent papers.",
            metadata={"count": 3},
            created_at=next_state.events[0].created_at,
        )
    ]


def test_workflow_state_collects_errors_without_mutating_original() -> None:
    initial_state = WorkflowState()

    next_state = initial_state.with_error("LMStudio is unavailable.")

    assert initial_state.errors == []
    assert next_state.errors == ["LMStudio is unavailable."]
