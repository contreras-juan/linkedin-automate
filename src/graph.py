from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from src.agents import curator_node, researcher_node, reviewer_node, writer_node
from src.state import WorkflowState
from src.tools.arxiv_tool import DEFAULT_RESEARCH_CATEGORIES
from src.tools.curator_tool import DEFAULT_FILTER_PROFILE_PATH


StateNode = Callable[[WorkflowState], WorkflowState]


def build_workflow_graph(
    categories: Sequence[str] = DEFAULT_RESEARCH_CATEGORIES,
    max_results: int = 10,
    profile_path: str = DEFAULT_FILTER_PROFILE_PATH,
    researcher: StateNode | None = None,
    curator: StateNode | None = None,
    writer: StateNode | None = None,
    reviewer: StateNode | None = None,
) -> CompiledStateGraph:
    workflow = StateGraph(WorkflowState)
    workflow.add_node(
        "researcher",
        _wrap_node(
            researcher
            or (lambda state: researcher_node(state, categories=categories, max_results=max_results))
        ),
    )
    workflow.add_node(
        "curator",
        _wrap_node(curator or (lambda state: curator_node(state, profile_path=profile_path))),
    )
    workflow.add_node("writer", _wrap_node(writer or writer_node))
    workflow.add_node("reviewer", _wrap_node(reviewer or reviewer_node))

    workflow.add_edge(START, "researcher")
    workflow.add_edge("researcher", "curator")
    workflow.add_edge("curator", "writer")
    workflow.add_edge("writer", "reviewer")
    workflow.add_edge("reviewer", END)

    return workflow.compile()


def run_workflow(
    initial_state: WorkflowState | None = None,
    categories: Sequence[str] = DEFAULT_RESEARCH_CATEGORIES,
    max_results: int = 10,
    profile_path: str = DEFAULT_FILTER_PROFILE_PATH,
) -> WorkflowState:
    graph = build_workflow_graph(
        categories=categories,
        max_results=max_results,
        profile_path=profile_path,
    )
    result = graph.invoke(_to_graph_payload(initial_state or WorkflowState()))
    return WorkflowState.model_validate(result)


def _wrap_node(node: StateNode) -> Callable[[dict[str, Any] | WorkflowState], dict[str, Any]]:
    def wrapped(state: dict[str, Any] | WorkflowState) -> dict[str, Any]:
        current_state = _coerce_state(state)
        next_state = node(current_state)
        return _to_graph_payload(next_state)

    return wrapped


def _coerce_state(state: dict[str, Any] | WorkflowState) -> WorkflowState:
    if isinstance(state, WorkflowState):
        return state

    return WorkflowState.model_validate(state)


def _to_graph_payload(state: WorkflowState) -> dict[str, Any]:
    return state.model_dump(mode="python")
