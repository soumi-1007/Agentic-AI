import os
import re
from pathlib import Path
from dotenv import load_dotenv

# Reliably load .env from project root regardless of working directory
PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

# Intent Constants
INTENT_ORDER_TRACKING = "order_tracking"
INTENT_ORDER_STATUS = "order_status"
INTENT_ORDER_DETAILS = "order_details"
INTENT_POLICY_INQUIRY = "policy_inquiry"
INTENT_CUSTOMER_COMPLAINT = "customer_complaint"
INTENT_HUMAN_HANDOFF = "human_handoff"
INTENT_UNKNOWN = "unknown"

VALID_INTENTS = {
    INTENT_ORDER_TRACKING,
    INTENT_ORDER_STATUS,
    INTENT_ORDER_DETAILS,
    INTENT_POLICY_INQUIRY,
    INTENT_CUSTOMER_COMPLAINT,
    INTENT_HUMAN_HANDOFF,
    INTENT_UNKNOWN,
}

SYSTEM_PROMPT = (
    "You are an intent classification triage router for an e-commerce customer support system.\n"
    "Classify the customer message into EXACTLY one of these seven intent labels:\n"
    "- order_tracking     : Asking where a package/order is, tracking info, delivery date, or shipment location.\n"
    "- order_status       : Asking about order status, progress, condition, or state.\n"
    "- order_details      : Asking to view order details, items purchased, summary, or receipt.\n"
    "- policy_inquiry     : Asking about return policy, refund processing time, shipping fees, exchanges, or store policies.\n"
    "- customer_complaint : Reporting damaged items, broken products, missing packages, late delivery complaints, wrong items/products received, or refund disputes.\n"
    "- human_handoff      : Explicitly requesting to speak with a human agent, real person, manager, customer support representative, transfer, or escalation.\n"
    "- unknown            : General greetings, chit-chat, or queries completely unrelated to orders, policies, complaints, or human support.\n\n"
    "Examples:\n"
    "\"Where is my order ORD-1001?\" -> order_tracking\n"
    "\"What is the status of ORD-1005?\" -> order_status\n"
    "\"Show me details for ORD-1010\" -> order_details\n"
    "\"Tell me about your return policy\" -> policy_inquiry\n"
    "\"My package arrived with damaged headphones ORD-1001\" -> customer_complaint\n"
    "\"I want to speak with a human support agent\" -> human_handoff\n"
    "\"I need a real person\" -> human_handoff\n"
    "\"My order is late and I want to speak with a human\" -> human_handoff\n"
    "\"I want to speak to a manager\" -> human_handoff\n"
    "\"Hello how are you\" -> unknown\n\n"
    "Respond with ONLY the single intent label (order_tracking, order_status, order_details, policy_inquiry, customer_complaint, human_handoff, or unknown). "
    "Do NOT include extra text, punctuation, explanations, or quotes."
)

# Rule-based fallback keywords
HUMAN_KEYWORDS = [
    "human", "real person", "real human", "talk to someone", "speak to someone",
    "talk with someone", "speak with someone", "support agent", "human agent",
    "human support", "manager", "transfer me", "connect me", "customer support",
    "talk to a manager", "speak to a manager", "speak with a manager",
    "talk to an agent", "speak to an agent", "speak with an agent", "connect to an agent",
    "talk to a human", "speak to a human", "speak with a human", "connect to a human",
    "talk to a real person", "speak to a real person", "speak with a real person",
    "escalate to a human", "escalate this to a human", "need customer support",
    "need a human", "want a human", "want a real person", "want to talk to someone",
    "connect me to a support agent", "connect me to a human", "connect me to an agent"
]

HUMAN_PATTERN = re.compile(
    r"\b("
    r"speak\s+(with|to)\s+(a\s+)?(human|agent|person|manager|representative|someone)|"
    r"talk\s+(with|to)\s+(a\s+)?(human|agent|person|manager|representative|someone|real\s+person)|"
    r"connect\s+me\s+to\s+(a\s+)?(human|agent|person|manager|support)|"
    r"transfer\s+me\s+to\s+(a\s+)?(human|agent|person|manager)|"
    r"need\s+(a\s+)?(human|real\s+person|support\s+agent)|"
    r"want\s+(a\s+)?(human|real\s+person)|"
    r"escalate\s+to\s+(a\s+)?(human|manager)|"
    r"human\s+(support|agent|person|representative)|"
    r"real\s+(person|human)|"
    r"customer\s+support"
    r")\b",
    re.IGNORECASE,
)

COMPLAINT_KEYWORDS = [
    "damaged", "broken", "cracked", "defective", "shattered", "scratched", "faulty",
    "missing", "never received", "empty box", "stolen", "didn't arrive", "did not arrive",
    "wrong item", "wrong product", "wrong order", "incorrect item", "incorrect product", "wrong size", "different product",
    "dispute", "disputed", "complaint", "complain", "terrible", "horrible", "unacceptable", "issue with",
]
TRACKING_KEYWORDS = ["where is", "where's", "track", "tracking", "shipment", "shipping", "delivery date", "package location", "when will it arrive"]
STATUS_KEYWORDS = ["status", "state", "progress", "condition", "stage"]
DETAILS_KEYWORDS = ["details", "detail", "info", "information", "show me", "summary", "receipt", "items", "item"]
POLICY_KEYWORDS = ["policy", "return", "refund", "exchange", "fees", "fee", "cost to return", "days", "rules"]
ORDER_ID_PATTERN = re.compile(r"\bORD-?\d+\b", re.IGNORECASE)


def is_explicit_human_request(message: str) -> bool:
    """Checks if message contains an explicit request for human support."""
    if not message:
        return False
    msg_lower = message.lower().strip()
    if any(kw in msg_lower for kw in HUMAN_KEYWORDS):
        return True
    if HUMAN_PATTERN.search(msg_lower):
        return True
    return False


def classify_intent_rule_based(message: str) -> str:
    """Local rule-based classifier used as deliberate fallback when OpenAI API is unavailable."""
    if not message or not message.strip():
        return INTENT_UNKNOWN

    msg_lower = message.lower().strip()

    # Rule 1 (HIGHEST PRIORITY): Check explicit human support request first
    if is_explicit_human_request(msg_lower):
        return INTENT_HUMAN_HANDOFF

    # Rule 2: Check complaint indicators
    if any(kw in msg_lower for kw in COMPLAINT_KEYWORDS):
        return INTENT_CUSTOMER_COMPLAINT

    # Rule 3: Check policy indicators
    if any(kw in msg_lower for kw in POLICY_KEYWORDS) and not ORDER_ID_PATTERN.search(msg_lower):
        return INTENT_POLICY_INQUIRY

    # Rule 4: Check order tracking indicators
    if any(kw in msg_lower for kw in TRACKING_KEYWORDS):
        return INTENT_ORDER_TRACKING

    # Rule 5: Check order status indicators
    if any(kw in msg_lower for kw in STATUS_KEYWORDS):
        return INTENT_ORDER_STATUS

    # Rule 6: Check order details indicators
    if any(kw in msg_lower for kw in DETAILS_KEYWORDS):
        return INTENT_ORDER_DETAILS

    # Rule 7: If message contains Order ID
    if ORDER_ID_PATTERN.search(msg_lower):
        return INTENT_ORDER_DETAILS

    return INTENT_UNKNOWN


def classify_intent_with_ai(message: str) -> str:
    """Classifies a customer message using the configured AI provider (Groq or OpenAI).

    Provides high-priority override for explicit human support requests.
    """
    if not message or not message.strip():
        return INTENT_UNKNOWN

    # High-priority override for explicit human support requests
    if is_explicit_human_request(message):
        return INTENT_HUMAN_HANDOFF

    try:
        from .ai_service import get_ai_completion
    except ImportError:
        from backend.agents.ai_service import get_ai_completion

    raw_response = get_ai_completion(
        messages=[{"role": "user", "content": message.strip()}],
        system_prompt=SYSTEM_PROMPT,
        max_tokens=20,
        temperature=0.0,
    )

    if raw_response:
        cleaned = raw_response.strip().lower()
        cleaned = re.sub(r"[^\w_]", "", cleaned)
        if cleaned in VALID_INTENTS:
            return cleaned

    return classify_intent_rule_based(message)


def classify_intent_with_openai(message: str) -> str:
    """Legacy alias preserved for backwards compatibility."""
    return classify_intent_with_ai(message)


def classify_intent(message: str) -> str:
    """Primary intent classification router entrypoint."""
    return classify_intent_with_ai(message)
