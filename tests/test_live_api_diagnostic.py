import os
import sys
import unittest
from pathlib import Path
from dotenv import load_dotenv

# Reliably load .env from project root
PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


def run_live_api_diagnostic():
    """Explicitly invoked live OpenAI API diagnostic runner.

    Tests live API connectivity, distinguishes specific API errors (401, 429, connection error),
    and verifies whether live API calls succeed or fall back safely without leaking keys.
    """
    print("\n========================================")
    print("   OPENAI LIVE API DIAGNOSTIC RUNNER")
    print("========================================")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or not api_key.strip():
        print("[STATUS] FAILED - Missing Key")
        print("[DIAGNOSTIC] OPENAI_API_KEY is not set in root .env file.")
        print("[ACTION REQUIRED] Set OPENAI_API_KEY=your_key in root .env file.")
        print("[FALLBACK ACTIVE] Local offline fallback is active for all agents.\n")
        return False

    key_prefix = api_key[:7] if len(api_key) >= 7 else "sk-***"
    key_suffix = api_key[-4:] if len(api_key) >= 4 else "***"
    masked_key = f"{key_prefix}...{key_suffix}"
    print(f"[CONFIG] OPENAI_API_KEY loaded: {masked_key}")
    print("[CONFIG] Model: gpt-4o-mini")
    print("[TEST] Sending test request to OpenAI ChatCompletions API...")

    try:
        from openai import (
            OpenAI,
            AuthenticationError,
            RateLimitError,
            APIConnectionError,
            APIError,
        )

        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Respond with the exact text OK."}],
            temperature=0.0,
            max_tokens=10,
        )

        if response and response.choices and len(response.choices) > 0:
            result_text = response.choices[0].message.content.strip()
            print("\n[STATUS] LIVE API TEST SUCCESSFUL!")
            print(f"[RESPONSE] OpenAI Response: \"{result_text}\"")
            print("[INFO] Live OpenAI API is fully functional and ready for production routing.\n")
            return True

    except ImportError:
        print("\n[STATUS] FAILED - Package Missing")
        print("[DIAGNOSTIC] OpenAI Python package is not installed.")
        print("[ACTION REQUIRED] Run 'pip install openai'.")
    except AuthenticationError:
        print("\n[STATUS] FAILED - Authentication Error (401)")
        print("[DIAGNOSTIC] Error 401: The configured OPENAI_API_KEY was rejected as invalid by OpenAI servers.")
        print("[ACTION REQUIRED] Check your API key at https://platform.openai.com/api-keys")
    except RateLimitError as e:
        err_msg = str(e)
        if "insufficient_quota" in err_msg or "credit_balance_exhausted" in err_msg:
            print("\n[STATUS] FAILED - Quota Exhausted (429)")
            print("[DIAGNOSTIC] Error 429: You have no remaining OpenAI API credits or your credit balance is $0.00.")
            print("[ACTION REQUIRED] Add credits to your OpenAI account at https://platform.openai.com/settings/organization/billing/")
        else:
            print("\n[STATUS] FAILED - Rate Limit Exceeded (429)")
            print("[DIAGNOSTIC] Error 429: Rate limit exceeded. Try again in a few moments.")
    except APIConnectionError:
        print("\n[STATUS] FAILED - Network Connection Error")
        print("[DIAGNOSTIC] Unable to connect to api.openai.com. Check network/DNS settings.")
    except APIError as e:
        err_type = type(e).__name__
        print(f"\n[STATUS] FAILED - API Error ({err_type})")
        print(f"[DIAGNOSTIC] Details: {e.message if hasattr(e, 'message') else str(e)}")
    except Exception as e:
        err_type = type(e).__name__
        print(f"\n[STATUS] FAILED - Unexpected Error ({err_type})")
        print(f"[DIAGNOSTIC] Details: {str(e)}")

    print("[FALLBACK ACTIVE] Local offline fallback remains active and operational for all agents.\n")
    return False


class TestLiveAPIDiagnostic(unittest.TestCase):

    @unittest.skipIf(
        os.getenv("RUN_LIVE_API_TESTS") != "1",
        "Live API test skipped during automated unittest discover. Run 'python tests/test_live_api_diagnostic.py' directly."
    )
    def test_live_openai_api_connection(self):
        """Explicitly invoked live API test."""
        success = run_live_api_diagnostic()
        self.assertTrue(success, "Live OpenAI API diagnostic test failed.")


if __name__ == "__main__":
    run_live_api_diagnostic()
