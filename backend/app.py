import os
import sys
from dotenv import load_dotenv

# Ensure backend path is present
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from database.order_service import (
    get_order_by_id,
    format_order_details,
    display_sample_orders,
)
try:
    from graph import run_customer_support_graph
except ImportError:
    from backend.graph import run_customer_support_graph

# Load environment variables
load_dotenv()


def handle_user_message(user_message: str):
    """Routes customer message through the LangGraph Multi-Agent Orchestrator."""
    print(f"\nUser Message: \"{user_message}\"")

    # Invoke LangGraph Workflow
    state = run_customer_support_graph(user_message)
    intent = state.get("intent")
    agent_response = state.get("agent_response")
    formatted_details = state.get("formatted_details")
    policy_section = state.get("policy_section")
    handoff_summary = state.get("handoff_summary")

    print(f"\nIntent detected: {intent}\n")

    # Display results based on intent / agent type
    if intent in ["order_tracking", "order_status", "order_details"]:
        print("Order Agent:")
        print(agent_response)
        if formatted_details:
            print(formatted_details)
    elif intent == "policy_inquiry":
        print("Policy Agent:")
        print(agent_response)
        if policy_section:
            print(f"\n[Policy Section Retrieved: {policy_section}]")
    elif intent == "customer_complaint":
        print("Complaint Agent:")
        print(agent_response)
        if handoff_summary:
            print(handoff_summary)
    else:
        print("Support Agent:")
        print(agent_response)


def main():
    """Main CLI entrypoint for Customer Support Agent."""
    print("----------------------------------------")
    print("   E-Commerce Customer Support Agent")
    print("----------------------------------------")

    # If message passed via command line argument
    if len(sys.argv) > 1:
        user_message = " ".join(sys.argv[1:])
        handle_user_message(user_message)
        return

    # Interactive CLI loop if no argument provided
    display_sample_orders(limit=5)
    print("\nTry typing queries like:")
    print(" - 'Where is my order ORD-1001?'")
    print(" - 'What is the status of ORD-1005?'")
    print(" - 'Tell me about your return policy'")
    print(" - 'My package arrived damaged for ORD-1001'")
    print(" - 'I received the wrong item in my order ORD-1002'")

    while True:
        try:
            user_input = input("\nEnter customer message (or 'exit' to quit): ").strip()
            if not user_input or user_input.lower() in ["exit", "quit", "q"]:
                print("Exiting support agent. Goodbye!")
                break
            handle_user_message(user_input)
        except (KeyboardInterrupt, EOFError):
            print("\nExiting support agent. Goodbye!")
            break


if __name__ == "__main__":
    main()
