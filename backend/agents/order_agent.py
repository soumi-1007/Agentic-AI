import re
import os
import sys

# Ensure backend directory is in path to import DB connection tools
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from database.order_service import get_order_by_id, format_order_details

ORDER_ID_PATTERN = re.compile(r"\bORD-\d+\b", re.IGNORECASE)


def extract_order_id(message: str) -> str:
    """Extracts an Order ID matching pattern ORD-XXXX from user message."""
    if not message:
        return None
    match = ORDER_ID_PATTERN.search(message)
    return match.group(0).upper() if match else None


def process_order_query(message: str, intent: str) -> dict:
    """Processes an order query by extracting Order ID, fetching DB details,

    and generating a natural-language response.
    """
    order_id = extract_order_id(message)

    if not order_id:
        return {
            "order_id": None,
            "order": None,
            "intent": intent,
            "response": (
                "I noticed your inquiry is related to an order, but I couldn't find a valid "
                "Order ID (e.g., ORD-1001) in your message. Please include your Order ID!"
            ),
            "formatted_details": None,
        }

    order = get_order_by_id(order_id)

    if not order:
        return {
            "order_id": order_id,
            "order": None,
            "intent": intent,
            "response": f"Order '{order_id}' was not found in our database. Please check your Order ID.",
            "formatted_details": None,
        }

    # Generate natural language response based on intent
    product = order["product_name"]
    status = order["status"]
    shipment = order["shipment_status"]
    delivery = order["delivery_date"]
    return_elig = "Yes" if order["return_eligible"] == 1 else "No"

    if intent == "order_tracking":
        nl_response = (
            f"Your order {order_id} ({product}) is currently '{status}'. "
            f"Shipment Status: {shipment}. Delivery Date: {delivery}."
        )
    elif intent == "order_status":
        nl_response = (
            f"The status of order {order_id} ({product}) is '{status}' "
            f"with shipment status '{shipment}'."
        )
    elif intent == "order_details":
        nl_response = (
            f"Here are the details for order {order_id}: Purchased {product} on {order['order_date']}. "
            f"Status: {status} | Shipment: {shipment} | Return Eligible: {return_elig}."
        )
    else:  # Fallback
        nl_response = (
            f"Order {order_id} ({product}) is '{status}'. Shipment status: {shipment}."
        )

    formatted_details = format_order_details(order)

    return {
        "order_id": order_id,
        "order": order,
        "intent": intent,
        "response": nl_response,
        "formatted_details": formatted_details,
    }
