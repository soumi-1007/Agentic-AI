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
    INTENT_POLICY_INQUIRY,
    INTENT_UNKNOWN,
)


class TestStage3OpenAITriageRouter(unittest.TestCase):

    @patch("openai.OpenAI")
    def test_openai_order_tracking(self, mock_openai_cls):
        """Test OpenAI classification for order_tracking intent."""
        mock_client = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "order_tracking"
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_cls.return_value = mock_client

        with patch.dict(os.environ, {"OPENAI_API_KEY": "mock_key"}):
            intent = classify_intent("Where is my order ORD-1001?")
            self.assertEqual(intent, INTENT_ORDER_TRACKING)

    @patch("openai.OpenAI")
    def test_openai_order_status(self, mock_openai_cls):
        """Test OpenAI classification for order_status intent."""
        mock_client = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "order_status"
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_cls.return_value = mock_client

        with patch.dict(os.environ, {"OPENAI_API_KEY": "mock_key"}):
            intent = classify_intent("What is the status of ORD-1005?")
            self.assertEqual(intent, INTENT_ORDER_STATUS)

    @patch("openai.OpenAI")
    def test_openai_order_details(self, mock_openai_cls):
        """Test OpenAI classification for order_details intent."""
        mock_client = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "order_details"
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_cls.return_value = mock_client

        with patch.dict(os.environ, {"OPENAI_API_KEY": "mock_key"}):
            intent = classify_intent("Show me details for ORD-1010")
            self.assertEqual(intent, INTENT_ORDER_DETAILS)

    @patch("openai.OpenAI")
    def test_openai_unknown(self, mock_openai_cls):
        """Test OpenAI classification for unknown intent."""
        mock_client = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "unknown"
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_cls.return_value = mock_client

        with patch.dict(os.environ, {"OPENAI_API_KEY": "mock_key"}):
            intent = classify_intent("Hello how are you")
            self.assertEqual(intent, INTENT_UNKNOWN)

    @patch("openai.OpenAI")
    def test_openai_response_cleaning(self, mock_openai_cls):
        """Test cleaning of raw OpenAI response text with newline and punctuation."""
        mock_client = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "  order_tracking. \n"
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_cls.return_value = mock_client

        with patch.dict(os.environ, {"OPENAI_API_KEY": "mock_key"}):
            intent = classify_intent("Where is my order ORD-1001?")
            self.assertEqual(intent, INTENT_ORDER_TRACKING)

    @patch("openai.OpenAI")
    def test_openai_api_failure_fallback_handling(self, mock_openai_cls):
        """Verify that OpenAI API exceptions fall back safely without crashing."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API connection error")
        mock_openai_cls.return_value = mock_client

        with patch.dict(os.environ, {"OPENAI_API_KEY": "mock_key"}):
            intent = classify_intent("Where is my order ORD-1001?")
            self.assertEqual(intent, INTENT_ORDER_TRACKING)

            unknown_intent = classify_intent("Hello how are you")
            self.assertEqual(unknown_intent, INTENT_UNKNOWN)

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_api_key_handling(self):
        """Verify that missing API key falls back safely."""
        intent = classify_intent("Where is my order ORD-1001?")
        self.assertEqual(intent, INTENT_ORDER_TRACKING)

        unknown_intent = classify_intent("Hello how are you")
        self.assertEqual(unknown_intent, INTENT_UNKNOWN)


if __name__ == "__main__":
    unittest.main()
