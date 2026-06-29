from langgraph.graph import StateGraph, END
from app.workflow.context import GraphState
from app.workflow.agents.context_loader import context_loader_node
from app.workflow.agents.quality_inspector import quality_inspector_node
from app.workflow.agents.security_auditor import security_auditor_node
from app.workflow.agents.performance_analyzer import performance_analyzer_node
from app.workflow.agents.review_synthesizer import review_synthesizer_node


def build_review_graph():
    """
    Constructs and returns the LangGraph execution flow for the code review process.
    
    The architecture relies on a parallel processing model:
    - Initially, the `fetch_pr` node retrieves metadata and diffs from the repository.
    - The execution branches concurrently to `agent_quality`, `agent_security`, and `agent_performance`.
    - These specialized nodes perform independent evaluations of the pulled code.
    - Finally, execution converges at `agent_reviewer`, which synthesizes the analyses into a unified review.
    
    Returns:
        CompiledGraph: The compiled state graph ready for execution.
    """
    graph = StateGraph(GraphState)

    # Initialize the state graph with the unified GraphState schema.
    graph.add_node("fetch_pr", context_loader_node)
    graph.add_node("agent_quality", quality_inspector_node)
    graph.add_node("agent_security", security_auditor_node)
    graph.add_node("agent_performance", performance_analyzer_node)
    graph.add_node("agent_reviewer", review_synthesizer_node)

    # Define the initial entry point of the execution graph.
    graph.set_entry_point("fetch_pr")

    # Configure parallel outward routing from the data fetching node to the specialized analysis agents.
    graph.add_edge("fetch_pr", "agent_quality")
    graph.add_edge("fetch_pr", "agent_security")
    graph.add_edge("fetch_pr", "agent_performance")

    # Aggregate the parallel streams into the final synthesis node.
    graph.add_edge("agent_quality", "agent_reviewer")
    graph.add_edge("agent_security", "agent_reviewer")
    graph.add_edge("agent_performance", "agent_reviewer")

    # Terminate the execution pathway following the final review synthesis.
    graph.add_edge("agent_reviewer", END)

    return graph.compile()


# Instantiate a compiled graph singleton to optimize performance by avoiding repeated compilations during runtime.
review_graph = build_review_graph()