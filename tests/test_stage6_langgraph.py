import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Ensure project root and backend are in path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from graph import run_customer_support_graph, create_support_graph, route_intent
    from graph.state import GraphState
except ImportError:
    from backend.graph import run_customer_support_graph, create_support_graph, route_intent
    from backend.graph.state import GraphState


class TestStage6LangGraph(unittest.TestCase):
    """Automated unit test suite for Stage 6: LangGraph Multi-Agent Orchestration & Human Handoff Routing."""

    def test_state_structure_integrity(self):
        """Verifies that run_customer_support_graph returns a complete GraphState dictionary."""
        with patch("backend.agents.triage_router.classify_intent", return_value="order_tracking"):
            state = run_customer_support_graph("Where is my order ORD-1001?")
            self.assertIn("customer_message", state)
            self.assertIn("intent", state)
            self.assertIn("order_id", state)
            self.assertIn("agent_response", state)
            self.assertIn("formatted_details", state)
            self.assertIn("policy_section", state)
            self.assertIn("handoff_summary", state)
            self.assertIn("escalation_details", state)
            self.assertIn("raw_agent_result", state)
            self.assertEqual(state["intent"], "order_tracking")
            self.assertEqual(state["order_id"], "ORD-1001")

    def test_order_tracking_routing(self):
        """Verifies routing and response propagation for order_tracking intent."""
        state = run_customer_support_graph("Where is my order ORD-1001?")
        self.assertEqual(state["intent"], "order_tracking")
        self.assertEqual(state["order_id"], "ORD-1001")
        self.assertIsNotNone(state["agent_response"])
        self.assertIsNotNone(state["raw_agent_result"])

    def test_order_status_routing(self):
        """Verifies routing and response propagation for order_status intent."""
        state = run_customer_support_graph("What is the status of ORD-1005?")
        self.assertEqual(state["intent"], "order_status")
        self.assertEqual(state["order_id"], "ORD-1005")
        self.assertIsNotNone(state["agent_response"])

    def test_order_details_routing(self):
        """Verifies routing and response propagation for order_details intent."""
        state = run_customer_support_graph("Show me details for ORD-1010")
        self.assertEqual(state["intent"], "order_details")
        self.assertEqual(state["order_id"], "ORD-1010")
        self.assertIsNotNone(state["agent_response"])

    def test_missing_order_id_in_graph(self):
        """Verifies handling when an order query is missing a valid Order ID."""
        with patch("backend.agents.triage_router.classify_intent", return_value="order_status"):
            state = run_customer_support_graph("What is the status of my order?")
            self.assertEqual(state["intent"], "order_status")
            self.assertIsNone(state["order_id"])
            self.assertIn("couldn't find a valid Order ID", state["agent_response"])

    def test_policy_inquiry_routing(self):
        """Verifies routing and response propagation for policy_inquiry intent."""
        state = run_customer_support_graph("Tell me about your return policy")
        self.assertEqual(state["intent"], "policy_inquiry")
        self.assertIsNotNone(state["agent_response"])
        self.assertIsNotNone(state["policy_section"])

    def test_customer_complaint_routing(self):
        """Verifies routing and response propagation for customer_complaint intent."""
        state = run_customer_support_graph("My package arrived with damaged headphones ORD-1001")
        self.assertEqual(state["intent"], "customer_complaint")
        self.assertEqual(state["order_id"], "ORD-1001")
        self.assertIsNotNone(state["agent_response"])
        self.assertIsNotNone(state["handoff_summary"])
        self.assertIsNotNone(state["escalation_details"])
        self.assertTrue(state["escalation_details"]["escalated"])
        self.assertIn("Pending Human Agent Review", state["handoff_summary"])

    def test_explicit_human_request_speak_with_human(self):
        """TEST 4: 'I want to speak with a human support agent' -> Human Handoff."""
        state = run_customer_support_graph("I want to speak with a human support agent")
        self.assertEqual(state["intent"], "human_handoff")
        self.assertIsNone(state["order_id"])
        self.assertIsNotNone(state["agent_response"])
        self.assertIn("connect you with a human support specialist", state["agent_response"])
        self.assertIsNotNone(state["handoff_summary"])
        self.assertIn("Order ID          : Not Provided", state["handoff_summary"])

    def test_explicit_human_request_real_person(self):
        """TEST 5: 'I need a real person' -> Human Handoff."""
        state = run_customer_support_graph("I need a real person")
        self.assertEqual(state["intent"], "human_handoff")
        self.assertIsNotNone(state["handoff_summary"])

    def test_explicit_human_request_combined_late_order(self):
        """TEST 6: 'My order is late and I want to speak with a human.' -> Human Handoff with summary."""
        state = run_customer_support_graph("My order is late and I want to speak with a human.")
        self.assertEqual(state["intent"], "human_handoff")
        self.assertIsNotNone(state["handoff_summary"])
        self.assertIn("Late Delivery", state["handoff_summary"])

    def test_explicit_human_request_combined_refund(self):
        """TEST 7: 'My refund hasn't arrived. Connect me to an agent.' -> Human Handoff."""
        state = run_customer_support_graph("My refund hasn't arrived. Connect me to an agent.")
        self.assertEqual(state["intent"], "human_handoff")
        self.assertIsNotNone(state["handoff_summary"])

    def test_explicit_human_request_speak_to_manager(self):
        """TEST 8: 'I want to speak to a manager.' -> Human Handoff."""
        state = run_customer_support_graph("I want to speak to a manager.")
        self.assertEqual(state["intent"], "human_handoff")
        self.assertIsNotNone(state["handoff_summary"])

    def test_unknown_intent_routing(self):
        """Verifies safe routing to unknown_intent_node when intent is unhandled."""
        state = run_customer_support_graph("Can you recommend a good sci-fi movie?")
        self.assertEqual(state["intent"], "unknown")
        self.assertIn("couldn't identify an order, policy, or complaint request", state["agent_response"])
        self.assertIn("human support", state["agent_response"])

    def test_route_intent_helper(self):
        """Direct unit test for route_intent conditional mapping logic."""
        self.assertEqual(route_intent({"intent": "order_tracking"}), "order_agent")
        self.assertEqual(route_intent({"intent": "order_status"}), "order_agent")
        self.assertEqual(route_intent({"intent": "order_details"}), "order_agent")
        self.assertEqual(route_intent({"intent": "policy_inquiry"}), "policy_agent")
        self.assertEqual(route_intent({"intent": "customer_complaint"}), "complaint_agent")
        self.assertEqual(route_intent({"intent": "human_handoff"}), "complaint_agent")
        self.assertEqual(route_intent({"intent": "unknown"}), "unknown_intent")
        self.assertEqual(route_intent({"intent": None}), "unknown_intent")

    def test_offline_local_fallback_in_graph(self):
        """Verifies that graph functions operational offline using local fallback when OpenAI is unconfigured/fails."""
        with patch("os.getenv", return_value=None):
            state = run_customer_support_graph("Where is my order ORD-1001?")
            self.assertEqual(state["intent"], "order_tracking")
            self.assertEqual(state["order_id"], "ORD-1001")
            self.assertIsNotNone(state["agent_response"])


if __name__ == "__main__":
    unittest.main()
