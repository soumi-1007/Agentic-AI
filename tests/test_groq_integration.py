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
    from backend.agents.ai_service import get_ai_completion
    from backend.agents.triage_router import classify_intent
    from backend.agents.policy_agent import process_policy_query
    from backend.agents.complaint_agent import process_complaint_query
    from backend.graph import run_customer_support_graph
except ImportError:
    from agents.ai_service import get_ai_completion
    from agents.triage_router import classify_intent
    from agents.policy_agent import process_policy_query
    from agents.complaint_agent import process_complaint_query
    from graph import run_customer_support_graph


class TestGroqIntegration(unittest.TestCase):
    """Automated unit test suite for Groq API integration with mocked API calls."""

    def setUp(self):
        self.env_patcher = patch.dict(
            os.environ,
            {
                "AI_PROVIDER": "groq",
                "GROQ_API_KEY": "gsk_mock_test_key_1234567890",
                "GROQ_MODEL": "llama-3.3-70b-versatile",
            },
        )
        self.env_patcher.start()

    def tearDown(self):
        self.env_patcher.stop()

    @patch("groq.Groq")
    def test_groq_triage_classification(self, mock_groq_cls):
        """Verifies intent classification using mocked Groq API."""
        mock_client = MagicMock()
        mock_groq_cls.return_value = mock_client

        mock_choice = MagicMock()
        mock_choice.message.content = "order_tracking"
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response

        intent = classify_intent("Where is my order ORD-1001?")
        self.assertEqual(intent, "order_tracking")
        mock_client.chat.completions.create.assert_called_once()

    @patch("groq.Groq")
    def test_groq_policy_agent_generation(self, mock_groq_cls):
        """Verifies policy answer generation using mocked Groq API."""
        mock_client = MagicMock()
        mock_groq_cls.return_value = mock_client

        mock_choice = MagicMock()
        mock_choice.message.content = "You can return eligible items within 30 days."
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response

        result = process_policy_query("How long do I have to return an item?")
        self.assertTrue(result["found"])
        self.assertIn("30 days", result["response"])

    @patch("groq.Groq")
    def test_groq_complaint_agent_generation(self, mock_groq_cls):
        """Verifies complaint response generation using mocked Groq API."""
        mock_client = MagicMock()
        mock_groq_cls.return_value = mock_client

        mock_choice = MagicMock()
        mock_choice.message.content = "We have received your complaint regarding ORD-1001 and escalated it to our support team."
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response

        result = process_complaint_query("My package arrived damaged for ORD-1001")
        self.assertEqual(result["category"], "Damaged Product")
        self.assertIn("escalated", result["response"])

    @patch("groq.Groq")
    def test_groq_langgraph_workflow_execution(self, mock_groq_cls):
        """Verifies full LangGraph workflow execution with AI_PROVIDER=groq."""
        mock_client = MagicMock()
        mock_groq_cls.return_value = mock_client

        mock_choice = MagicMock()
        mock_choice.message.content = "order_status"
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response

        state = run_customer_support_graph("What is the status of ORD-1005?")
        self.assertEqual(state["intent"], "order_status")
        self.assertEqual(state["order_id"], "ORD-1005")
        self.assertIsNotNone(state["agent_response"])

    def test_groq_missing_api_key_fallback(self):
        """Verifies local fallback when GROQ_API_KEY is empty/missing."""
        with patch.dict(os.environ, {"GROQ_API_KEY": ""}):
            intent = classify_intent("Where is my order ORD-1001?")
            self.assertEqual(intent, "order_tracking")

    @patch("groq.Groq")
    def test_groq_rate_limit_fallback(self, mock_groq_cls):
        """Verifies local fallback when Groq raises RateLimitError."""
        from groq import RateLimitError

        mock_client = MagicMock()
        mock_groq_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_client.chat.completions.create.side_effect = RateLimitError(
            message="Rate limit exceeded",
            response=mock_response,
            body={"error": {"message": "Rate limit exceeded"}},
        )

        intent = classify_intent("Where is my order ORD-1001?")
        self.assertEqual(intent, "order_tracking")


if __name__ == "__main__":
    unittest.main()
