import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Ensure backend directory is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "backend"))
sys.path.insert(0, BACKEND_DIR)

from agents.triage_router import (
    classify_intent,
    INTENT_ORDER_TRACKING,
    INTENT_ORDER_STATUS,
    INTENT_ORDER_DETAILS,
    INTENT_UNKNOWN,
)
from agents.order_agent import process_order_query, extract_order_id
from database.seed_data import create_and_seed_db, DB_PATH


class TestStage2TriageAndOrderAgent(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Seed DB once for tests."""
        create_and_seed_db(DB_PATH)

    @patch("openai.OpenAI")
    def test_triage_router_intents(self, mock_openai_cls):
        """Verify Triage Router correctly classifies intents using mocked OpenAI API."""
        mock_client = MagicMock()

        def side_effect(model, messages, **kwargs):
            user_msg = ""
            for m in messages:
                if m.get("role") == "user":
                    user_msg = m.get("content", "")

            resp = MagicMock()
            choice = MagicMock()

            if "Where is my order" in user_msg:
                choice.message.content = "order_tracking"
            elif "What is the status" in user_msg:
                choice.message.content = "order_status"
            elif "Show me details" in user_msg:
                choice.message.content = "order_details"
            else:
                choice.message.content = "unknown"

            resp.choices = [choice]
            return resp

        mock_client.chat.completions.create.side_effect = side_effect
        mock_openai_cls.return_value = mock_client

        with patch.dict(os.environ, {"OPENAI_API_KEY": "mock_key"}):
            self.assertEqual(
                classify_intent("Where is my order ORD-1001?"), INTENT_ORDER_TRACKING
            )
            self.assertEqual(
                classify_intent("What is the status of ORD-1005?"), INTENT_ORDER_STATUS
            )
            self.assertEqual(
                classify_intent("Show me details for ORD-1010"), INTENT_ORDER_DETAILS
            )
            self.assertEqual(
                classify_intent("Tell me about your return policy"), INTENT_UNKNOWN
            )

    def test_order_id_extraction(self):
        """Verify order ID pattern matching."""
        self.assertEqual(extract_order_id("Where is my order ORD-1001?"), "ORD-1001")
        self.assertEqual(extract_order_id("Status of ord-1005 please"), "ORD-1005")
        self.assertIsNone(extract_order_id("Tell me about returns"))

    def test_order_agent_processing_valid_order(self):
        """Verify order agent fetches DB record and returns natural language response."""
        res = process_order_query("Where is my order ORD-1001?", INTENT_ORDER_TRACKING)
        self.assertEqual(res["order_id"], "ORD-1001")
        self.assertIsNotNone(res["order"])
        self.assertIn("Wireless Noise-Canceling Headphones", res["response"])
        self.assertIsNotNone(res["formatted_details"])

    def test_order_agent_non_existent_order(self):
        """Verify order agent handles invalid order IDs gracefully."""
        res = process_order_query("What is the status of ORD-9999?", INTENT_ORDER_STATUS)
        self.assertEqual(res["order_id"], "ORD-9999")
        self.assertIsNone(res["order"])
        self.assertIn("was not found", res["response"])

    def test_order_agent_missing_order_id(self):
        """Verify order agent prompts user for order ID if missing from message."""
        res = process_order_query("Where is my shipment?", INTENT_ORDER_TRACKING)
        self.assertIsNone(res["order_id"])
        self.assertIn("couldn't find a valid Order ID", res["response"])


if __name__ == "__main__":
    unittest.main()
