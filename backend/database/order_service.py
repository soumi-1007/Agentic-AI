import os
import sqlite3
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Determine database file path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB_PATH = os.path.join(BASE_DIR, "orders.db")
DB_PATH = os.getenv("DATABASE_PATH", DEFAULT_DB_PATH)

# Make sure relative paths resolve relative to workspace root if needed
if not os.path.isabs(DB_PATH):
    WORKSPACE_ROOT = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))
    DB_PATH = os.path.join(WORKSPACE_ROOT, DB_PATH)


def get_db_connection(db_path=DB_PATH):
    """Establishes and returns a database connection with Row factory enabled."""
    if not os.path.exists(db_path):
        raise FileNotFoundError(
            f"Database file not found at '{db_path}'. Please run seed_data.py first."
        )
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def get_order_by_id(order_id, db_path=DB_PATH):
    """Queries the database for a specific order ID."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM orders WHERE LOWER(order_id) = LOWER(?)", (order_id.strip(),)
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def format_order_details(order):
    """Formats order dictionary into a clean human-readable output."""
    if not order:
        return "Order not found."

    return (
        f"\n========================================\n"
        f"        ORDER DETAILS: {order['order_id']}\n"
        f"========================================\n"
        f"  Customer ID     : {order['customer_id']}\n"
        f"  Product Name    : {order['product_name']}\n"
        f"  Order Date      : {order['order_date']}\n"
        f"  Order Status    : {order['status']}\n"
        f"  Shipment Status : {order['shipment_status']}\n"
        f"  Delivery Date   : {order['delivery_date']}\n"
        f"  Return Eligible : {'Yes' if order['return_eligible'] == 1 else 'No'}\n"
        f"  Refund Status   : {order['refund_status']}\n"
        f"========================================\n"
    )


def display_sample_orders(limit=5, db_path=DB_PATH):
    """Retrieves a list of sample order IDs from the database."""
    try:
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT order_id, product_name, status FROM orders LIMIT ?", (limit,))
        rows = cursor.fetchall()
        conn.close()
        print("\nAvailable Sample Orders:")
        for row in rows:
            print(f" - {row['order_id']} ({row['product_name']} | {row['status']})")
    except Exception:
        pass
