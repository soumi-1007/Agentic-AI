import os
import re
from pathlib import Path
from dotenv import load_dotenv

# Ensure backend path is present
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
if BACKEND_DIR not in sys.path if "sys" in globals() else True:
    import sys
    sys.path.insert(0, BACKEND_DIR)

from database.order_service import get_order_by_id

# Reliably load .env from project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

ORDER_ID_PATTERN = re.compile(r"\bORD-?\d+\b", re.IGNORECASE)

# Complaint Category Keyword Maps
COMPLAINT_CATEGORIES = {
    "Damaged Product": ["damaged", "broken", "cracked", "defective", "shattered", "scratched", "faulty"],
    "Missing Item": ["missing", "never received", "empty box", "stolen", "didn't arrive", "did not arrive", "not delivered", "lost"],
    "Late Delivery": ["late", "delayed", "overdue", "taking too long", "delay"],
    "Incorrect Order": ["wrong item", "incorrect item", "wrong size", "different product", "wrong color", "incorrect order"],
    "Refund Dispute": ["refund dispute", "refund denied", "want my money back", "chargeback", "refund issue", "dispute"],
}

HUMAN_KEYWORDS = [
    "human", "real person", "real human", "talk to someone", "speak to someone",
    "support agent", "human agent", "human support", "manager", "transfer me", "connect me",
    "customer support", "representative"
]


def extract_order_id(message: str) -> str:
    """Extracts an Order ID matching pattern ORD-XXXX from user message."""
    if not message:
        return None
    match = ORDER_ID_PATTERN.search(message)
    return match.group(0).upper() if match else None


def categorize_complaint(message: str) -> str:
    """Categorizes the customer complaint or human support request based on keywords."""
    msg_lower = message.lower()
    for cat_name, keywords in COMPLAINT_CATEGORIES.items():
        if any(kw in msg_lower for kw in keywords):
            return cat_name
    if any(kw in msg_lower for kw in HUMAN_KEYWORDS):
        return "Human Support Request"
    return "General Complaint"


def generate_handoff_summary(user_message: str, category: str, order_id: str, order: dict) -> str:
    """Generates a structured human handoff escalation summary."""
    lines = [
        "\n========================================",
        "        HUMAN HANDOFF ESCALATION",
        "========================================",
        "  Escalation Status : Pending Human Agent Review",
        f"  Complaint Category: {category}",
    ]

    if order:
        lines.extend([
            f"  Order ID          : {order['order_id']} (Verified in Database)",
            f"  Customer ID       : {order['customer_id']}",
            f"  Product Name      : {order['product_name']}",
            f"  Order Status      : {order['status']}",
            f"  Shipment Status   : {order['shipment_status']}",
            f"  Refund Status     : {order['refund_status']}",
        ])
    elif order_id:
        lines.append(f"  Order ID          : {order_id} (Unverified / Not Found in DB)")
    else:
        lines.append("  Order ID          : Not Provided")

    lines.extend([
        f"  Customer Message  : \"{user_message.strip()}\"",
        "  Actions Taken     : Complaint categorized, Order validated in SQLite DB." if order or order_id else "  Actions Taken     : Request categorized, routed to Human Handoff.",
        f"  Escalation Reason : Customer reporting {category.lower()} needing human support review.",
        "========================================\n",
    ])

    return "\n".join(lines)


def process_complaint_query(user_message: str) -> dict:
    """Processes customer complaints and human support requests, validates order IDs, and creates a human handoff summary.

    Does NOT promise or approve refunds/replacements unless confirmed in DB.
    """
    order_id = extract_order_id(user_message)
    category = categorize_complaint(user_message)
    order = get_order_by_id(order_id) if order_id else None

    # Direct response for explicit human support requests
    msg_lower = user_message.lower()
    is_direct_human_request = any(kw in msg_lower for kw in [
        "speak with a human", "speak to a human", "talk to a human", "connect me to a human",
        "speak with an agent", "speak to an agent", "talk to an agent", "connect me to an agent",
        "real person", "human agent", "human support", "speak to a manager", "talk to a manager",
        "transfer me", "need a human", "want a human", "want a real person"
    ])

    customer_response = None

    if is_direct_human_request and not any(kw in msg_lower for kw in ["damaged", "broken", "missing", "wrong"]):
        customer_response = "Certainly. I'll connect you with a human support specialist."

    if not customer_response:
        try:
            from .ai_service import get_ai_completion
        except ImportError:
            from backend.agents.ai_service import get_ai_completion

        prompt = (
            f"A customer has submitted a request under category [{category}].\n"
            f"Order ID: {order_id if order_id else 'Not provided'}.\n"
            f"Order Details from DB: {dict(order) if order else 'N/A'}.\n\n"
            f"Customer Message: \"{user_message}\"\n\n"
            f"Write a concise, polite customer response reassuring them that their request has been logged "
            f"and escalated to a human support agent for review.\n"
            f"CRITICAL RULE: Do NOT state or claim that a refund, return, or replacement has been approved. "
            f"Inform them that a human support specialist will review their request."
        )
        system_prompt = "You are an empathetic customer support complaint and human handoff agent."

        customer_response = get_ai_completion(
            messages=[{"role": "user", "content": prompt}],
            system_prompt=system_prompt,
            max_tokens=150,
            temperature=0.0,
        )

    # Fallback customer response adhering strictly to Rule 6 (no false approval claims)
    if not customer_response:
        if is_direct_human_request:
            customer_response = "Certainly. I'll connect you with a human support specialist."
        elif order:
            customer_response = (
                f"I sincerely apologize for the issue with your order {order['order_id']} ({order['product_name']}). "
                f"I have logged your complaint under '{category}' and escalated this issue to a human support specialist. "
                f"Our team will review your order details and follow up with you shortly."
            )
        elif order_id:
            customer_response = (
                f"I apologize for the trouble with order '{order_id}'. We could not locate this Order ID in our records, "
                f"but I have categorized your complaint under '{category}' and created a human handoff ticket for our support team."
            )
        else:
            customer_response = (
                f"I am very sorry to hear about your experience. I have categorized your issue under '{category}' "
                f"and escalated your message to our human support team for immediate review."
            )

    handoff_summary = generate_handoff_summary(user_message, category, order_id, order)

    return {
        "query": user_message,
        "category": category,
        "order_id": order_id,
        "order_found": bool(order),
        "order": order,
        "response": customer_response,
        "handoff_summary": handoff_summary,
        "escalated": True,
    }
