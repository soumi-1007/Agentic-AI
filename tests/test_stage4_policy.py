import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Ensure backend directory is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "backend"))
sys.path.insert(0, BACKEND_DIR)

from agents.policy_agent import (
    load_and_chunk_policy,
    retrieve_relevant_chunk,
    process_policy_query,
)


class TestStage4PolicyAgentRAG(unittest.TestCase):

    def test_load_and_chunk_policy(self):
        """Verify policy document is loaded and chunked into sections."""
        chunks = load_and_chunk_policy()
        self.assertGreater(len(chunks), 0, "Policy document should contain chunks.")
        sections = [c["section"] for c in chunks]
        self.assertIn("Return Window", sections)
        self.assertIn("Return Shipping Fees", sections)

    def test_retrieval_supported_questions(self):
        """Verify retrieval matches correct policy sections for supported queries."""
        chunks = load_and_chunk_policy()

        # Query 1: Return Window
        chunk1, score1 = retrieve_relevant_chunk("How many days do I have to return an item?", chunks)
        self.assertIsNotNone(chunk1)
        self.assertEqual(chunk1["section"], "Return Window")

        # Query 2: Return Shipping Fees
        chunk2, score2 = retrieve_relevant_chunk("Who pays for return shipping?", chunks)
        self.assertIsNotNone(chunk2)
        self.assertEqual(chunk2["section"], "Return Shipping Fees")

        # Query 3: Refund Timeframe
        chunk3, score3 = retrieve_relevant_chunk("How long does refund processing take?", chunks)
        self.assertIsNotNone(chunk3)
        self.assertEqual(chunk3["section"], "Refund Processing Time")

    def test_retrieval_unsupported_questions(self):
        """Verify retrieval returns None for unsupported queries not in policy."""
        chunks = load_and_chunk_policy()
        chunk, score = retrieve_relevant_chunk("What is your pet policy in retail stores?", chunks)
        self.assertIsNone(chunk, "Pet policy should not match any return policy chunk.")

    def test_policy_agent_supported_query_fallback(self):
        """Verify policy agent returns grounded response for supported questions using fallback."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "", "GROQ_API_KEY": ""}):
            res = process_policy_query("What is the return shipping fee?")
            self.assertTrue(res["found"])
            self.assertEqual(res["section"], "Return Shipping Fees")
            self.assertIn("$5.99", res["response"])

    def test_policy_agent_unsupported_query(self):
        """Verify policy agent explicitly states when document does not contain the answer."""
        res = process_policy_query("Do you offer a lifetime warranty on electronics?")
        self.assertFalse(res["found"])
        self.assertIsNone(res["section"])
        self.assertIn("does not contain information", res["response"])

    @patch("openai.OpenAI")
    def test_policy_agent_openai_integration_mock(self, mock_openai_cls):
        """Verify policy agent with mocked OpenAI LLM response."""
        mock_client = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "Items can be returned within 30 days of delivery date."
        mock_resp = MagicMock()
        mock_resp.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_resp
        mock_openai_cls.return_value = mock_client

        with patch.dict(os.environ, {"OPENAI_API_KEY": "mock_key"}):
            res = process_policy_query("How long do I have to return an item?")
            self.assertTrue(res["found"])
            self.assertEqual(res["section"], "Return Window")
            self.assertEqual(res["response"], "Items can be returned within 30 days of delivery date.")


if __name__ == "__main__":
    unittest.main()
