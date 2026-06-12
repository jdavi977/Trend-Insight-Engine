import os
from dotenv import load_dotenv

load_dotenv()

def keyChecker(name: str) -> str:
    val = os.getenv(name)
    if not val:
        raise RuntimeError(
            f"Missing required environment variable: {name}. Check your .env file or deployable environment."
        )
    return val

OPENAI_KEY = keyChecker("OPENAI_KEY")

SUPABASE_URL = keyChecker("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = keyChecker("SUPABASE_SERVICE_ROLE_KEY")

# Daily OpenAI spend ceiling in USD (PRD §8, US-S5, slice 2 §6). When the
# in-process running spend total for the current UTC day reaches this value,
# POST /runs returns 429 budget_exhausted. Optional: unset → no cap (the guard
# is disabled), which is the lenient failure mode for local/dev. The running
# total lives in app/clients/openai.py and resets at UTC midnight.
_daily_budget_raw = os.getenv("OPENAI_DAILY_BUDGET_USD")
OPENAI_DAILY_BUDGET_USD: float | None = (
    float(_daily_budget_raw) if _daily_budget_raw else None
)