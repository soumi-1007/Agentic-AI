import os
import sys
import unittest
import sqlite3

# Add backend directory to sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "backend"))
sys.path.insert(0, BACKEND_DIR)

from database.seed_data import create_and_seed_db, DB_PATH
from database.order_service import get_order_by_id, format_order_details


class TestOrderDatabase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Ensure database is seeded before running tests."""
        create_and_seed_db(DB_PATH)

    def test_database_record_count(self):
        """Verify that exactly 50 mock orders were inserted into the database."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM orders")
        count = cursor.fetchone()[0]
        conn.close()
        self.assertEqual(count, 50, "Database should contain exactly 50 orders.")

    def test_order_lookup_valid(self):
        """Verify looking up a known order ID returns correct details."""
        order = get_order_by_id("ORD-1001")
        self.assertIsNotNone(order, "Order ORD-1001 should be found.")
        self.assertEqual(order["order_id"], "ORD-1001")
        self.assertIn("customer_id", order)
        self.assertIn("product_name", order)
        self.assertIn("status", order)

    def test_order_lookup_case_insensitive(self):
        """Verify order lookup works regardless of casing."""
        order = get_order_by_id("ord-1001")
        self.assertIsNotNone(order, "Order lookup should be case-insensitive.")
        self.assertEqual(order["order_id"], "ORD-1001")

    def test_order_lookup_invalid(self):
        """Verify looking up a non-existent order ID returns None."""
        order = get_order_by_id("ORD-99999")
        self.assertIsNone(order, "Order ORD-99999 should return None.")

    def test_formatted_output(self):
        """Verify order formatting string contains expected labels."""
        order = get_order_by_id("ORD-1001")
        formatted = format_order_details(order)
        self.assertIn("ORDER DETAILS: ORD-1001", formatted)
        self.assertIn("Product Name", formatted)
        self.assertIn("Order Status", formatted)


if __name__ == "__main__":
    unittest.main()
