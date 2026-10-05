import os
import re
from pathlib import Path
from dotenv import load_dotenv

# Reliably load .env from project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

POLICY_FILE_PATH = PROJECT_ROOT / "backend" / "data" / "sample_policy.txt"


def load_and_chunk_policy(file_path=POLICY_FILE_PATH):
    """Loads the policy document and splits it into logical section chunks."""
    if not os.path.exists(file_path):
        return []

    with open(file_path, "r", encoding="utf-8") as f:
        raw_text = f.read()

    chunks = []
    # Split by section headers [SECTION: ...]
    sections = re.split(r"\[SECTION:\s*([^\]]+)\]", raw_text)

    # First part is header comments
    for i in range(1, len(sections), 2):
        sec_title = sections[i].strip()
        sec_content = sections[i + 1].strip() if i + 1 < len(sections) else ""
        if sec_content:
            chunks.append({"section": sec_title, "content": sec_content})

    return chunks


def retrieve_relevant_chunk(query: str, chunks: list):
    """Retrieves the most relevant policy chunk using term overlap and section key phrase matching.

    Returns (best_chunk, best_score) or (None, 0.0) if no matching section meets relevance threshold.
    """
    if not query or not chunks:
        return None, 0.0

    query_lower = query.lower()
    stopwords = {"a", "an", "the", "is", "are", "do", "does", "what", "how", "where", "can", "i", "my", "your", "to", "for", "of", "in", "about", "tell", "me", "our", "have"}
    query_words = set(re.findall(r"\b[a-z]{2,}\b", query_lower)) - stopwords

    if not query_words:
        return None, 0.0

    best_chunk = None
    best_score = 0.0

    for chunk in chunks:
        sec_title = chunk["section"].lower()
        chunk_text = (chunk["section"] + " " + chunk["content"]).lower()
        chunk_words = set(re.findall(r"\b[a-z]{2,}\b", chunk_text))

        # Base term overlap score
        overlap = query_words.intersection(chunk_words)
        score = len(overlap) / len(query_words) if query_words else 0.0

        # Section-specific key phrase relevance boosting
        if "how long" in query_lower or "days" in query_lower or "window" in query_lower or "return policy" in query_lower:
            if "return window" in sec_title:
                score += 0.5
        if "fee" in query_lower or "cost" in query_lower or "pay" in query_lower or "shipping" in query_lower:
            if "shipping fees" in sec_title:
                score += 0.5
        if "refund" in query_lower and ("time" in query_lower or "process" in query_lower or "long" in query_lower or "when" in query_lower):
            if "refund processing" in sec_title:
                score += 0.5
        if "exchange" in query_lower:
            if "exchanges" in sec_title:
                score += 0.5
        if "international" in query_lower or "duty" in query_lower or "taxes" in query_lower:
            if "international returns" in sec_title:
                score += 0.5

        if score > best_score:
            best_score = score
            best_chunk = chunk

    if best_score >= 0.2:
        return best_chunk, best_score

    return None, 0.0


def process_policy_query(user_message: str) -> dict:
    """Processes a policy inquiry using RAG over the policy document.

    Answers strictly grounded in the policy context.
    If the document does not contain the answer, explicitly informs the user.
    """
    chunks = load_and_chunk_policy()
    relevant_chunk, score = retrieve_relevant_chunk(user_message, chunks)

    # Case 1: Policy document does not contain the answer
    if not relevant_chunk:
        return {
            "query": user_message,
            "found": False,
            "section": None,
            "response": (
                "I'm sorry, but our policy document does not contain information regarding your question. "
                "Please contact our customer support team for further assistance."
            ),
        }

    section_name = relevant_chunk["section"]
    section_content = relevant_chunk["content"]

    try:
        from .ai_service import get_ai_completion
    except ImportError:
        from backend.agents.ai_service import get_ai_completion

    prompt = (
        f"Answer the user's question STRICTLY using the provided policy context below.\n"
        f"Do NOT invent or assume any details not mentioned in the context.\n"
        f"If the context does not answer the question, state that the policy document does not contain the answer.\n\n"
        f"Policy Section: [{section_name}]\n"
        f"Policy Context: {section_content}\n\n"
        f"User Question: \"{user_message}\"\n"
        f"Answer:"
    )
    system_prompt = "You are a helpful customer support policy assistant."

    ai_answer = get_ai_completion(
        messages=[{"role": "user", "content": prompt}],
        system_prompt=system_prompt,
        max_tokens=150,
        temperature=0.0,
    )

    if ai_answer:
        return {
            "query": user_message,
            "found": True,
            "section": section_name,
            "response": ai_answer,
            "context": section_content,
        }

    # Fallback RAG response grounded strictly in retrieved section
    fallback_response = (
        f"According to our Store Policy [{section_name}]:\n"
        f"{section_content}"
    )

    return {
        "query": user_message,
        "found": True,
        "section": section_name,
        "response": fallback_response,
        "context": section_content,
    }
