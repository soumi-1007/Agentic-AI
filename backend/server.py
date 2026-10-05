import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

# Ensure backend directory and project root are in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Load environment variables
load_dotenv(PROJECT_ROOT / ".env")

try:
    from graph import run_customer_support_graph
    from database.order_service import get_order_by_id
except ImportError:
    from backend.graph import run_customer_support_graph
    from backend.database.order_service import get_order_by_id

# Initialize FastAPI app
app = FastAPI(
    title="E-Commerce Customer Support API",
    description="Multi-Agent Customer Support Backend powered by LangGraph and Groq/OpenAI",
    version="1.0.0",
)


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    """Silence browser favicon 404 logs cleanly."""
    return Response(status_code=204)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    message: str
    intent: Optional[str] = None
    order_id: Optional[str] = None
    agent_response: Optional[str] = None
    formatted_details: Optional[str] = None
    policy_section: Optional[str] = None
    handoff_summary: Optional[str] = None
    escalation_details: Optional[Dict[str, Any]] = None
    raw_agent_result: Optional[Dict[str, Any]] = None
    status: str = "success"


@app.get("/api/health")
def health_check():
    """Health check endpoint for customer support backend."""
    return {
        "status": "ok",
        "service": "E-Commerce Customer Support API",
        "version": "1.0.0",
        "ai_provider": os.getenv("AI_PROVIDER", "groq"),
    }


@app.post("/api/chat", response_model=ChatResponse)
def handle_chat_message(request: ChatRequest):
    """Processes customer messages through the LangGraph Multi-Agent workflow."""
    user_message = request.message.strip() if request.message else ""
    if not user_message:
        raise HTTPException(status_code=400, detail="Customer message cannot be empty.")

    try:
        # Invoke LangGraph Workflow
        state = run_customer_support_graph(user_message)

        return ChatResponse(
            message=user_message,
            intent=state.get("intent"),
            order_id=state.get("order_id"),
            agent_response=state.get("agent_response"),
            formatted_details=state.get("formatted_details"),
            policy_section=state.get("policy_section"),
            handoff_summary=state.get("handoff_summary"),
            escalation_details=state.get("escalation_details"),
            raw_agent_result=state.get("raw_agent_result"),
            status="success",
        )
    except Exception as e:
        err_type = type(e).__name__
        print(f"[SERVER ERROR] Failure during LangGraph processing ({err_type}): {str(e)}")
        return ChatResponse(
            message=user_message,
            intent="unknown",
            agent_response="I'm sorry, an unexpected error occurred while processing your request. Please try again or contact human support.",
            status="error",
        )


@app.get("/api/orders/{order_id}")
def get_order_details(order_id: str):
    """Direct lookup endpoint for SQLite order records."""
    clean_id = order_id.strip().upper()
    order = get_order_by_id(clean_id)
    if not order:
        raise HTTPException(status_code=404, detail=f"Order '{clean_id}' was not found in database.")
    return {"order_id": clean_id, "order": order}


# Mount Frontend Static Files if frontend directory exists
frontend_dir = PROJECT_ROOT / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    print("\n=========================================")
    print("   Starting Customer Support API Server")
    print("   URL: http://127.0.0.1:8000")
    print("=========================================\n")
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
