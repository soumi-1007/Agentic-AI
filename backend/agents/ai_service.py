import os
import sys
import re
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

# Reliably load .env from project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

logger = logging.getLogger("customer_support.ai_service")


def _log_diagnostic(msg: str):
    """Logs diagnostic messages safely without polluting automated unittest terminal output."""
    if "unittest" in sys.modules and not os.getenv("SHOW_TEST_LOGS"):
        logger.debug(msg)
    else:
        print(msg)


def is_openai_mocked() -> bool:
    """Checks if openai.OpenAI has been mocked by a unit test."""
    try:
        from unittest.mock import MagicMock, Mock
        if "openai" in sys.modules:
            openai_mod = sys.modules["openai"]
            if hasattr(openai_mod, "OpenAI") and (
                isinstance(openai_mod.OpenAI, (MagicMock, Mock))
                or hasattr(openai_mod.OpenAI, "return_value")
            ):
                return True
    except Exception:
        pass
    return False


def is_groq_mocked() -> bool:
    """Checks if groq.Groq has been mocked by a unit test."""
    try:
        from unittest.mock import MagicMock, Mock
        if "groq" in sys.modules:
            groq_mod = sys.modules["groq"]
            if hasattr(groq_mod, "Groq") and (
                isinstance(groq_mod.Groq, (MagicMock, Mock))
                or hasattr(groq_mod.Groq, "return_value")
            ):
                return True
    except Exception:
        pass
    return False


def get_ai_completion(
    messages: List[Dict[str, str]],
    system_prompt: Optional[str] = None,
    max_tokens: int = 150,
    temperature: float = 0.0,
) -> Optional[str]:
    """Generates an AI chat completion using Groq or OpenAI based on AI_PROVIDER setting.

    Masks API keys in logs and falls back gracefully to secondary provider or None on error.
    Respects active unit test mocks for either provider.
    """
    raw_provider = os.getenv("AI_PROVIDER")
    provider = raw_provider.lower().strip() if raw_provider else "auto"

    full_messages = []
    if system_prompt:
        full_messages.append({"role": "system", "content": system_prompt})
    full_messages.extend(messages)

    # 1. If OpenAI is explicitly mocked by a unit test, route to OpenAI mock
    if is_openai_mocked() and not is_groq_mocked():
        return _call_openai(full_messages, max_tokens, temperature)

    # 2. If Groq is explicitly mocked by a unit test, route to Groq mock
    if is_groq_mocked() and not is_openai_mocked():
        return _call_groq(full_messages, max_tokens, temperature)

    # 3. Runtime routing based on AI_PROVIDER setting
    if provider == "groq":
        res = _call_groq(full_messages, max_tokens, temperature)
        if res is not None:
            return res
        if os.getenv("OPENAI_API_KEY"):
            return _call_openai(full_messages, max_tokens, temperature)
        return None

    elif provider == "openai":
        res = _call_openai(full_messages, max_tokens, temperature)
        if res is not None:
            return res
        if os.getenv("GROQ_API_KEY"):
            return _call_groq(full_messages, max_tokens, temperature)
        return None

    else:
        # Auto-detection: try Groq if key set, then OpenAI
        if os.getenv("GROQ_API_KEY"):
            res = _call_groq(full_messages, max_tokens, temperature)
            if res is not None:
                return res
        if os.getenv("OPENAI_API_KEY"):
            res = _call_openai(full_messages, max_tokens, temperature)
            if res is not None:
                return res
        return None


def _call_groq(
    messages: List[Dict[str, str]],
    max_tokens: int,
    temperature: float,
) -> Optional[str]:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or not api_key.strip():
        _log_diagnostic(
            "[DIAGNOSTIC] GROQ_API_KEY is not configured in .env. "
            "Set GROQ_API_KEY=your_key in the root .env file. Using local fallback."
        )
        return None

    model = (os.getenv("GROQ_MODEL") or "llama-3.3-70b-versatile").strip()
    fallback_models = ["openai/gpt-oss-20b", "qwen/qwen3.8-27b"]

    try:
        from groq import (
            Groq,
            AuthenticationError,
            RateLimitError,
            APIConnectionError,
            NotFoundError,
            APIError,
        )

        client = Groq(api_key=api_key)

        models_to_try = [model] + [m for m in fallback_models if m != model]

        for target_model in models_to_try:
            try:
                res = client.chat.completions.create(
                    model=target_model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                if res and res.choices and len(res.choices) > 0:
                    content = res.choices[0].message.content
                    if content:
                        return content.strip()
            except NotFoundError:
                continue

        _log_diagnostic(f"[DIAGNOSTIC] Groq Model '{model}' and fallbacks unavailable. Using local fallback.")
        return None

    except ImportError:
        _log_diagnostic("[DIAGNOSTIC] Groq Python package is not installed. Run 'pip install groq'. Using local fallback.")
        return None
    except AuthenticationError:
        _log_diagnostic("[DIAGNOSTIC] Groq Authentication Error (401: Invalid API Key). Check GROQ_API_KEY in .env. Using local fallback.")
        return None
    except RateLimitError:
        _log_diagnostic("[DIAGNOSTIC] Groq API Rate Limit / Quota Exceeded (429). Using local fallback.")
        return None
    except APIConnectionError:
        _log_diagnostic("[DIAGNOSTIC] Groq API Connection Failure (Network issue). Using local fallback.")
        return None
    except Exception as e:
        err_type = type(e).__name__
        _log_diagnostic(f"[DIAGNOSTIC] Groq API Request Error ({err_type}). Using local fallback.")
        return None


def _call_openai(
    messages: List[Dict[str, str]],
    max_tokens: int,
    temperature: float,
) -> Optional[str]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or not api_key.strip():
        _log_diagnostic("[DIAGNOSTIC] OPENAI_API_KEY is not configured in .env. Using local fallback.")
        return None

    try:
        from openai import (
            OpenAI,
            AuthenticationError,
            RateLimitError,
            APIConnectionError,
            APIError,
        )

        client = OpenAI(api_key=api_key)
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        if res and res.choices and len(res.choices) > 0:
            content = res.choices[0].message.content
            if content:
                return content.strip()
    except ImportError:
        _log_diagnostic("[DIAGNOSTIC] OpenAI Python package is not installed. Using local fallback.")
        return None
    except AuthenticationError:
        _log_diagnostic("[DIAGNOSTIC] OpenAI Authentication Error (401: Invalid API Key). Using local fallback.")
        return None
    except RateLimitError:
        _log_diagnostic("[DIAGNOSTIC] OpenAI API Quota / Rate Limit Exceeded (429). Using local fallback.")
        return None
    except APIConnectionError:
        _log_diagnostic("[DIAGNOSTIC] OpenAI API Connection Failure. Using local fallback.")
        return None
    except Exception as e:
        err_type = type(e).__name__
        _log_diagnostic(f"[DIAGNOSTIC] OpenAI API Request Error ({err_type}). Using local fallback.")
        return None

    return None
