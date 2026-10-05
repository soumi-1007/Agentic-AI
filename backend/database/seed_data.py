import os
import sqlite3
from datetime import datetime, timedelta
import random

# Determine database file path relative to this script directory
DB_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DB_DIR, "orders.db")


def create_and_seed_db(db_path=DB_PATH):
    """Creates the orders table and seeds it with 50 realistic mock e-commerce orders."""
    print(f"Connecting to database at: {db_path}")

    # Ensure parent directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Drop table if exists to allow fresh seeding
    cursor.execute("DROP TABLE IF EXISTS orders")

    # Create orders table schema
    cursor.execute(
        """
        CREATE TABLE orders (
            order_id TEXT PRIMARY KEY,
            customer_id TEXT NOT NULL,
            product_name TEXT NOT NULL,
            order_date TEXT NOT NULL,
            status TEXT NOT NULL,
            shipment_status TEXT NOT NULL,
            delivery_date TEXT,
            return_eligible INTEGER NOT NULL DEFAULT 0,
            refund_status TEXT NOT NULL DEFAULT 'N/A'
        )
    """
    )

    # List of realistic e-commerce products
    products = [
        "Wireless Noise-Canceling Headphones",
        "Ergonomic Office Chair",
        "Mechanical Gaming Keyboard",
        "Smart Watch Series 5",
        "4K Ultra HD Monitor 27-inch",
        "USB-C Dual Docking Station",
        "Portable Bluetooth Speaker",
        "Stainless Steel Insulated Water Bottle",
        "Organic Cotton Unisex Hoodie",
        "Trail Running Shoes",
        "High-Speed Wi-Fi 6 Router",
        "Compact Espresso Machine",
        "Noise-Isolating Earbuds",
        "1080p HD Webcam with Microphone",
        "Adjustable Standing Desk",
        "Wireless Vertical Ergonomic Mouse",
        "External SSD Storage 1TB",
        "Smart Home Security Camera",
        "Electric Stand Mixer 5-Quart",
        "Air Purifier with HEPA Filter",
    ]

    statuses_distribution = [
        ("Processing", "Order Received", None, 0, "N/A"),
        ("Processing", "Preparing for Shipment", None, 0, "N/A"),
        ("Shipped", "In Transit", None, 0, "N/A"),
        ("In Transit", "Out for Delivery", None, 0, "N/A"),
        ("In Transit", "Arrived at Regional Hub", None, 0, "N/A"),
        ("Delivered", "Delivered to Front Door", None, 1, "N/A"),
        ("Delivered", "Delivered to Parcel Locker", None, 1, "N/A"),
        ("Delivered", "Delivered - Signed by Resident", None, 0, "N/A"),  # Past 30-day window
        ("Delayed", "Delayed in Transit due to Weather", None, 0, "N/A"),
        ("Delayed", "Customs Clearance Delay", None, 0, "N/A"),
        ("Cancelled", "Cancelled by Customer", None, 0, "Refunded"),
        ("Cancelled", "Cancelled due to Out of Stock", None, 0, "Refunded"),
        ("Delivered", "Delivered", None, 1, "Refund Requested"),
    ]

    mock_orders = []
    base_date = datetime(2026, 9, 27)

    for i in range(1, 51):
        order_id = f"ORD-{1000 + i}"
        customer_id = f"CUST-{5000 + (i % 20) + 1}"  # ~20 unique customers
        product_name = products[(i - 1) % len(products)]

        # Pick status blueprint
        status, shipment_status, _, return_elig, refund_stat = statuses_distribution[
            (i - 1) % len(statuses_distribution)
        ]

        # Calculate dates logically
        days_ago = (i * 2) % 35 + 1
        order_dt = base_date - timedelta(days=days_ago)
        order_date_str = order_dt.strftime("%Y-%m-%d")

        if status == "Delivered":
            delivery_dt = order_dt + timedelta(days=random.randint(2, 5))
            delivery_date_str = delivery_dt.strftime("%Y-%m-%d")

            # Return eligible if delivered within 30 days of today
            days_since_delivery = (base_date - delivery_dt).days
            return_eligible = 1 if days_since_delivery <= 30 else 0
        elif status in ["Shipped", "In Transit", "Delayed"]:
            est_delivery_dt = base_date + timedelta(days=random.randint(1, 4))
            delivery_date_str = f"Estimated {est_delivery_dt.strftime('%Y-%m-%d')}"
            return_eligible = 0
        else:
            delivery_date_str = "N/A"
            return_eligible = 0

        # Override refund status if explicitly set in blueprint
        refund_status = refund_stat

        mock_orders.append(
            (
                order_id,
                customer_id,
                product_name,
                order_date_str,
                status,
                shipment_status,
                delivery_date_str,
                return_eligible,
                refund_status,
            )
        )

    cursor.executemany(
        """
        INSERT INTO orders (
            order_id, customer_id, product_name, order_date,
            status, shipment_status, delivery_date, return_eligible, refund_status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        mock_orders,
    )

    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM orders")
    count = cursor.fetchone()[0]
    print(f"Successfully created and seeded 'orders' table with {count} mock records.")

    conn.close()


if __name__ == "__main__":
    create_and_seed_db()
