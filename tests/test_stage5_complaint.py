import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Ensure backend directory is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "backend"))
sys.path.insert(0, BACKEND_DIR)

from agents.triage_router import classify_intent, INTENT_CUSTOMER_COMPLAINT
from agents.complaint_agent import (
    categorize_complaint,
    extract_order_id,
    process_complaint_query,
    generate_handoff_summary,
)
from database.seed_data import create_and_seed_db, DB_PATH


class TestStage5ComplaintAgentAndHumanHandoff(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Seed DB once for tests."""
        create_and_seed_db(DB_PATH)

    def test_complaint_categorization(self):
        """Verify complaint categorization logic for various categories."""
        self.assertEqual(categorize_complaint("My package arrived damaged and cracked"), "Damaged Product")
        self.assertEqual(categorize_complaint("The item is missing from my package"), "Missing Item")
        self.assertEqual(categorize_complaint("My delivery is late and overdue"), "Late Delivery")
        self.assertEqual(categorize_complaint("I received the wrong item in my box"), "Incorrect Order")
        self.assertEqual(categorize_complaint("I want a chargeback for a refund dispute"), "Refund Dispute")

    def test_complaint_triage_routing(self):
        """Verify Triage Router classifies complaint messages correctly."""
        intent = classify_intent("My package arrived damaged for ORD-1001")
        self.assertEqual(intent, INTENT_CUSTOMER_COMPLAINT)

        intent2 = classify_intent("I received the wrong product in my delivery")
        self.assertEqual(intent2, INTENT_CUSTOMER_COMPLAINT)

    def test_complaint_agent_valid_order_id(self):
        """Verify Complaint Agent handles valid Order IDs with database verification."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "", "GROQ_API_KEY": ""}):
            res = process_complaint_query("My package arrived damaged for ORD-1001")
            self.assertTrue(res["escalated"])
            self.assertTrue(res["order_found"])
            self.assertEqual(res["order_id"], "ORD-1001")
            self.assertEqual(res["category"], "Damaged Product")
            self.assertIn("ORD-1001", res["response"])
            self.assertIn("Wireless Noise-Canceling Headphones", res["response"])

        # Check handoff summary contents
        summary = res["handoff_summary"]
        self.assertIn("HUMAN HANDOFF ESCALATION", summary)
        self.assertIn("Order ID          : ORD-1001 (Verified in Database)", summary)
        self.assertIn("Customer ID       : CUST-5002", summary)

    def test_complaint_agent_invalid_order_id(self):
        """Verify Complaint Agent handles non-existent Order IDs gracefully."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "", "GROQ_API_KEY": ""}):
            res = process_complaint_query("My delivery is overdue for ORD-9999")
            self.assertTrue(res["escalated"])
            self.assertFalse(res["order_found"])
            self.assertEqual(res["order_id"], "ORD-9999")
            self.assertIn("could not locate this Order ID", res["response"])

        summary = res["handoff_summary"]
        self.assertIn("Order ID          : ORD-9999 (Unverified / Not Found in DB)", summary)

    def test_complaint_agent_missing_order_id(self):
        """Verify Complaint Agent handles queries without an Order ID."""
        res = process_complaint_query("I received the wrong item in my delivery")
        self.assertTrue(res["escalated"])
        self.assertIsNone(res["order_id"])
        self.assertEqual(res["category"], "Incorrect Order")

        summary = res["handoff_summary"]
        self.assertIn("Order ID          : Not Provided", summary)

    def test_no_false_refund_approval_claims(self):
        """Verify Complaint Agent does not falsely claim a refund/replacement is approved."""
        res = process_complaint_query("I demand a refund for my damaged item ORD-1001")
        # Response should indicate escalation for review, not approved refund
        self.assertNotIn("refund has been approved", res["response"].lower())
        self.assertNotIn("replacement has been approved", res["response"].lower())

    @patch("openai.OpenAI")
    def test_complaint_agent_openai_integration_mock(self, mock_openai_cls):
        """Verify Complaint Agent with mocked OpenAI LLM response."""
        mock_client = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "We apologize for the damaged item. Your ticket has been escalated."
        mock_resp = MagicMock()
        mock_resp.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_resp
        mock_openai_cls.return_value = mock_client

        with patch.dict(os.environ, {"OPENAI_API_KEY": "mock_key"}):
            res = process_complaint_query("My package arrived damaged for ORD-1001")
            self.assertTrue(res["escalated"])
            self.assertEqual(res["category"], "Damaged Product")
            self.assertEqual(res["response"], "We apologize for the damaged item. Your ticket has been escalated.")


if __name__ == "__main__":
    unittest.main()
