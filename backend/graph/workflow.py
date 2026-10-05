import os
import sys
from pathlib import Path

# Ensure backend directory is in path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from langgraph.graph import StateGraph, START, END
from .state import GraphState
from .nodes import (
    triage_node,
    order_agent_node,
    policy_agent_node,
    complaint_agent_node,
    unknown_intent_node,
)


def route_intent(state: GraphState) -> str:
    """Conditional edge routing function mapping intent to target node."""
    intent = state.get("intent")
    if intent in ["order_tracking", "order_status", "order_details"]:
        return "order_agent"
    elif intent == "policy_inquiry":
        return "policy_agent"
    elif intent in ["customer_complaint", "human_handoff"]:
        return "complaint_agent"
    else:
        return "unknown_intent"


def create_support_graph():
    """Builds and compiles the LangGraph StateGraph workflow for Customer Support."""
    workflow = StateGraph(GraphState)

    # Add Nodes
    workflow.add_node("triage", triage_node)
    workflow.add_node("order_agent", order_agent_node)
    workflow.add_node("policy_agent", policy_agent_node)
    workflow.add_node("complaint_agent", complaint_agent_node)
    workflow.add_node("unknown_intent", unknown_intent_node)

    # Add Entry Edge
    workflow.add_edge(START, "triage")

    # Add Conditional Routing Edge from Triage
    workflow.add_conditional_edges(
        "triage",
        route_intent,
        {
            "order_agent": "order_agent",
            "policy_agent": "policy_agent",
            "complaint_agent": "complaint_agent",
            "unknown_intent": "unknown_intent",
        },
    )

    # Add Terminal Edges to END
    workflow.add_edge("order_agent", END)
    workflow.add_edge("policy_agent", END)
    workflow.add_edge("complaint_agent", END)
    workflow.add_edge("unknown_intent", END)

    return workflow.compile()


# Compile global graph instance
graph = create_support_graph()


def run_customer_support_graph(customer_message: str) -> GraphState:
    """Graph entry point that accepts a customer message and executes the LangGraph workflow."""
    initial_state: GraphState = {
        "customer_message": customer_message,
        "intent": None,
        "order_id": None,
        "agent_response": None,
        "formatted_details": None,
        "policy_section": None,
        "handoff_summary": None,
        "escalation_details": None,
        "raw_agent_result": None,
    }
    return graph.invoke(initial_state)
