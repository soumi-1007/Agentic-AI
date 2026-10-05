import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

# Ensure project root and backend are in path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.server import app


class TestServerAPI(unittest.TestCase):
    """Automated unit test suite for FastAPI Customer Support Server endpoints."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_health_endpoint(self):
        """Verifies GET /api/health returns status ok."""
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertIn("service", data)

    def test_chat_order_tracking(self):
        """Verifies POST /api/chat handles order tracking inquiries."""
        response = self.client.post("/api/chat", json={"message": "Where is my order ORD-1001?"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["intent"], "order_tracking")
        self.assertEqual(data["order_id"], "ORD-1001")
        self.assertIsNotNone(data["agent_response"])

    def test_chat_policy_inquiry(self):
        """Verifies POST /api/chat handles policy inquiries."""
        response = self.client.post("/api/chat", json={"message": "Tell me about your return policy"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["intent"], "policy_inquiry")
        self.assertIsNotNone(data["agent_response"])
        self.assertIsNotNone(data["policy_section"])

    def test_chat_complaint_submission(self):
        """Verifies POST /api/chat handles complaint submission."""
        response = self.client.post("/api/chat", json={"message": "My package arrived damaged for ORD-1001"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["intent"], "customer_complaint")
        self.assertEqual(data["order_id"], "ORD-1001")
        self.assertIsNotNone(data["handoff_summary"])

    def test_chat_empty_message_error(self):
        """Verifies POST /api/chat returns HTTP 400 on empty message."""
        response = self.client.post("/api/chat", json={"message": ""})
        self.assertEqual(response.status_code, 400)

    def test_direct_order_lookup_valid(self):
        """Verifies GET /api/orders/{order_id} returns valid order details."""
        response = self.client.get("/api/orders/ORD-1001")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["order_id"], "ORD-1001")
        self.assertIsNotNone(data["order"])
        self.assertEqual(data["order"]["customer_id"], "CUST-5002")

    def test_direct_order_lookup_invalid(self):
        """Verifies GET /api/orders/{order_id} returns HTTP 404 for non-existent order."""
        response = self.client.get("/api/orders/ORD-9999")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
