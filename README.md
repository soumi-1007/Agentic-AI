# E-Commerce Customer Support Agent

An AI-driven customer support system for e-commerce applications.

---

## 📌 Project Progress

- **Stage 1**: Foundation & Order Database Setup (SQLite `orders.db`, 50 mock orders, `seed_data.py`).
- **Stage 2**: Triage Router & Order Agent integration (`triage_router.py`, `order_agent.py`, regex Order ID extraction, DB querying).
- **Stage 3**: OpenAI LLM integration for Triage Router (`openai` SDK, `gpt-4o-mini` model, strict intent classification, robust error handling, mocked unit tests).
- **Stage 4**: Policy Agent with Retrieval-Augmented Generation (RAG over `sample_policy.txt`, text chunking, grounded answer generation, handles supported/unsupported questions and local fallbacks).
- **Stage 5**: Complaint Agent & Human Handoff Escalation (recognizes complaints: damaged products, missing items, late deliveries, wrong orders, refund disputes; validates SQLite order IDs; generates structured human handoff escalation summaries).
- **Stage 6**: LangGraph Multi-Agent Orchestration (`StateGraph` workflow, shared `GraphState`, conditional intent routing, nodes for Order Agent, Policy Agent RAG, Complaint Escalation Agent, and Unknown Intent clarification, 9 graph workflow tests).
- **Stage 7**: Groq API Integration (`AI_PROVIDER=groq`, `GROQ_API_KEY`, `GROQ_MODEL`, `ai_service.py` provider abstraction, model fallback to `openai/gpt-oss-20b`, 6 new unit tests).
- **Future Stages**: MCP tools, Chatbot UI.

---

## 📁 Directory Structure

```text
customer-support-agent/
├── backend/
│   ├── agents/
│   │   ├── __init__.py         # Package initialization
│   │   ├── ai_service.py       # Multi-provider LLM helper (Groq & OpenAI API calls & fallbacks)
│   │   ├── triage_router.py    # AI intent classification (order_tracking, order_status, order_details, policy_inquiry, customer_complaint, unknown)
│   │   ├── order_agent.py      # Extracts Order ID, fetches DB records & generates order responses
│   │   ├── policy_agent.py     # RAG Policy Agent querying sample_policy.txt
│   │   └── complaint_agent.py  # Complaint Agent & Human Handoff Escalation summary generator
│   ├── graph/
│   │   ├── __init__.py         # Graph package exports
│   │   ├── state.py            # GraphState TypedDict state definition
│   │   ├── nodes.py            # LangGraph node functions (triage, order, policy, complaint, unknown)
│   │   └── workflow.py         # StateGraph builder, conditional edge routing, graph execution entrypoint
│   ├── data/
│   │   └── sample_policy.txt   # Mock Return & Refund policy document
│   ├── database/
│   │   ├── order_service.py    # DB connection & query services
│   │   ├── seed_data.py        # Database creation and 50 mock order generator
│   │   └── orders.db           # SQLite database
│   └── app.py                  # CLI support agent routing messages through LangGraph
├── frontend/                   # Directory reserved for future Chatbot UI
├── tests/                      # Automated test suite
│   ├── test_database.py        # Stage 1 unit tests
│   ├── test_stage2.py          # Stage 2 Order Agent unit tests
│   ├── test_stage3.py          # Stage 3 OpenAI Triage Router unit tests
│   ├── test_stage4_policy.py   # Stage 4 Policy Agent RAG unit tests
│   ├── test_stage5_complaint.py# Stage 5 Complaint Agent & Human Handoff unit tests
│   ├── test_stage6_langgraph.py# Stage 6 LangGraph Multi-Agent workflow unit tests
│   └── test_groq_integration.py# Stage 7 Groq API integration unit tests
├── .env                        # Environment variable configuration
├── .gitignore                  # Git ignore rules
├── requirements.txt            # Python dependencies
└── README.md                   # Project documentation
```

---

## ⚡ AI Provider Configuration (Groq & OpenAI)

The system dynamically switches AI providers based on the `AI_PROVIDER` setting in `.env`:

1. **Configuring Groq API (`AI_PROVIDER=groq`)**:
   ```env
   AI_PROVIDER=groq
   GROQ_API_KEY=gsk_your_actual_groq_api_key_here
   GROQ_MODEL=llama-3.3-70b-versatile
   ```

2. **Configuring OpenAI API (`AI_PROVIDER=openai`)**:
   ```env
   AI_PROVIDER=openai
   OPENAI_API_KEY=sk-proj-your-actual-openai_api_key_here
   ```

3. **Error Handling & Model Fallbacks**:
   - `ai_service.py` intercepts `AuthenticationError` (401), `RateLimitError` (429), and connection failures gracefully.
   - If a requested Groq model returns `404 Not Found`, the system automatically attempts fallback models (e.g., `openai/gpt-oss-20b` or `qwen/qwen3.8-27b`) before falling back to local offline logic.
   - **Key Privacy**: API keys are loaded securely from `.env` and are never printed, logged, or exposed.

---

## 🕸️ LangGraph Multi-Agent Architecture

The Customer Support Agent orchestrates inquiries using a **LangGraph `StateGraph`** workflow.

### Workflow Routing Graph
```text
                  +---------------------------+
                  |  Customer Message Input   |
                  +-------------+-------------+
                                |
                                v
                      +-------------------+
                      |   Triage Node     |
                      | (classify_intent) |
                      +---------+---------+
                                |
                   [Conditional Edge: route_intent]
                                |
      +-------------------------+-------------------------+-------------------------+
      | (order_*)               | (policy_inquiry)        | (customer_complaint)    | (unknown)
      v                         v                         v                         v
+------------------+  +-------------------+  +----------------------+  +---------------------+
| Order Agent Node |  | Policy Agent Node |  | Complaint Agent Node |  | Unknown Intent Node |
+--------+---------+  +---------+---------+  +----------+-----------+  +----------+----------+
         |                      |                       |                         |
         +----------------------+-----------+-----------+-------------------------+
                                            |
                                            v
                              +---------------------------+
                              |   Common Workflow Output  |
                              +---------------------------+
```

### Shared Workflow State (`GraphState`)
All nodes share a single state structure defined in `backend/graph/state.py`:
- `customer_message` (str): Raw user query string.
- `intent` (str): Intent classified by Triage Router.
- `order_id` (str): Extracted Order ID (if applicable).
- `agent_response` (str): Final natural language answer generated by handling agent.
- `formatted_details` (str): Formatted order summary table (if applicable).
- `policy_section` (str): Retrieved policy document section name (if applicable).
- `handoff_summary` (str): Human handoff escalation summary string (if applicable).
- `raw_agent_result` (dict): Complete dictionary returned by the underlying agent.

---

## 🗄️ Database Schema (`orders` Table)

| Column | Type | Description |
|---|---|---|
| `order_id` | TEXT (PK) | Unique Order Identifier (e.g. `ORD-1001`) |
| `customer_id` | TEXT | Customer ID (e.g. `CUST-5001`) |
| `product_name` | TEXT | E-commerce product description |
| `order_date` | TEXT | Date order was placed (`YYYY-MM-DD`) |
| `status` | TEXT | Order Status (`Processing`, `Shipped`, `In Transit`, `Delivered`, `Delayed`, `Cancelled`) |
| `shipment_status` | TEXT | Detailed tracking description |
| `delivery_date` | TEXT | Actual or estimated delivery date |
| `return_eligible` | INTEGER | `1` (True) or `0` (False) |
| `refund_status` | TEXT | Refund state (`N/A`, `Refund Requested`, `Refunded`, etc.) |

---

## 📜 Complaint Agent & Human Handoff Escalation

Recognizes and categorizes complaints into:
- **Damaged Product**
- **Missing Item**
- **Late Delivery**
- **Incorrect Order**
- **Refund Dispute**

When a complaint is received, it extracts and validates any Order ID using the SQLite database (`orders.db`), generates an empathetic response (without making false unapproved refund claims), and produces a structured **HUMAN HANDOFF ESCALATION SUMMARY**.

---

## 🚀 Setup & Usage Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Seed Database
```bash
python backend/database/seed_data.py
```

### 3. Run Customer Support Agent via LangGraph CLI
```bash
# Order Inquiries
python backend/app.py "Where is my order ORD-1001?"
python backend/app.py "What is the status of ORD-1005?"

# Policy Inquiries (RAG Agent)
python backend/app.py "How long do I have to return an item?"

# Complaint & Human Handoff Escalation
python backend/app.py "My package arrived with damaged headphones ORD-1001"

# Unhandled / Unknown Inquiries
python backend/app.py "Can you recommend a good book?"

# Interactive CLI Mode
python backend/app.py
```

---

## 🧪 Running Tests & API Diagnostics

### 1. Unit Test Suite (Offline / Mocked)
Run the full automated unit test suite (47 tests covering DB, Order Agent, OpenAI & Groq Triage Router, Policy Agent RAG, Complaint Agent Handoff, and LangGraph workflow):
```bash
python -m unittest discover tests
```

### 2. Live OpenAI API Diagnostic Test
To test live API connectivity, key validity, and credit quota status against OpenAI servers:
```bash
python tests/test_live_api_diagnostic.py
```
*(Or enable live execution in unittest discover via `RUN_LIVE_API_TESTS=1 python -m unittest discover tests`)*

---

## 🔑 AI Provider Fallback Mechanics

When Groq or OpenAI APIs are unavailable, rate-limited, or unconfigured, the system automatically uses the local keyword/pattern rule-based classifier (`classify_intent_rule_based`), local RAG retriever, and local complaint templates, preserving 100% offline functionality across the LangGraph workflow.

