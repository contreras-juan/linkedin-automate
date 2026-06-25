from src.graph import build_workflow_graph, run_workflow
from src.state import WorkflowState


def test_build_workflow_graph_runs_agents_in_expected_order() -> None:
    graph = build_workflow_graph(
        researcher=_event_node("researcher", "research done"),
        curator=_event_node("curator", "curation done"),
        writer=_event_node("writer", "writing done"),
        reviewer=_event_node("reviewer", "review done"),
    )

    result = graph.invoke(WorkflowState().model_dump(mode="python"))
    final_state = WorkflowState.model_validate(result)

    assert [event.agent for event in final_state.events] == [
        "researcher",
        "curator",
        "writer",
        "reviewer",
    ]
    assert [event.message for event in final_state.events] == [
        "research done",
        "curation done",
        "writing done",
        "review done",
    ]


def test_run_workflow_returns_valid_workflow_state(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.graph.build_workflow_graph",
        lambda **_: _FakeCompiledGraph(),
    )

    final_state = run_workflow(max_results=1)

    assert isinstance(final_state, WorkflowState)
    assert final_state.events[-1].agent == "reviewer"


def _event_node(agent: str, message: str):
    def node(state: WorkflowState) -> WorkflowState:
        return state.with_event(agent=agent, message=message)

    return node


class _FakeCompiledGraph:
    def invoke(self, state_payload):
        state = WorkflowState.model_validate(state_payload)
        return state.with_event(agent="reviewer", message="fake graph complete").model_dump(
            mode="python"
        )
