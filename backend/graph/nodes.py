import os
import sys
from pathlib import Path

# Ensure backend path is present
PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    from agents.triage_router import classify_intent
    from agents.order_agent import process_order_query
    from agents.policy_agent import process_policy_query
    from agents.complaint_agent import process_complaint_query
except ImportError:
    from backend.agents.triage_router import classify_intent
    from backend.agents.order_agent import process_order_query
    from backend.agents.policy_agent import process_policy_query
    from backend.agents.complaint_agent import process_complaint_query

from .state import GraphState


def triage_node(state: GraphState) -> dict:
    """Triage Node: Classifies the customer message using the Triage Router."""
    customer_message = state.get("customer_message", "")
    intent = classify_intent(customer_message)
    return {"intent": intent}


def order_agent_node(state: GraphState) -> dict:
    """Order Agent Node: Processes order queries without duplicating business logic."""
    customer_message = state.get("customer_message", "")
    intent = state.get("intent", "order_details")
    result = process_order_query(customer_message, intent)

    return {
        "order_id": result.get("order_id"),
        "agent_response": result.get("response"),
        "formatted_details": result.get("formatted_details"),
        "raw_agent_result": result,
    }


def policy_agent_node(state: GraphState) -> dict:
    """Policy Agent Node: Processes policy inquiries using RAG."""
    customer_message = state.get("customer_message", "")
    result = process_policy_query(customer_message)

    return {
        "agent_response": result.get("response"),
        "policy_section": result.get("section"),
        "raw_agent_result": result,
    }


def complaint_agent_node(state: GraphState) -> dict:
    """Complaint Agent Node: Processes customer complaints and creates human handoff summary."""
    customer_message = state.get("customer_message", "")
    result = process_complaint_query(customer_message)

    return {
        "order_id": result.get("order_id"),
        "agent_response": result.get("response"),
        "handoff_summary": result.get("handoff_summary"),
        "escalation_details": {
            "category": result.get("category"),
            "escalated": result.get("escalated", True),
            "order_id": result.get("order_id"),
            "order_found": result.get("order_found", False),
            "handoff_summary": result.get("handoff_summary"),
        },
        "raw_agent_result": result,
    }


def unknown_intent_node(state: GraphState) -> dict:
    """Unknown Intent Node: Handles unhandled queries safely with clarification or human support options."""
    clarification_message = (
        "I'm sorry, I couldn't identify an order, policy, or complaint request in your message. "
        "Currently, I can assist with order tracking ('Where is my order ORD-1001?'), "
        "store policies ('Tell me about your return policy'), and complaints ('My package arrived damaged for ORD-1001'). "
        "If you need further assistance, please rephrase your query or request human support."
    )
    return {
        "agent_response": clarification_message,
        "raw_agent_result": {"status": "unknown_intent", "response": clarification_message},
    }
