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
YOUTUBE_API = keyChecker("YOUTUBE_API")

SUPABASE_URL = keyChecker("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = keyChecker("SUPABASE_SERVICE_ROLE_KEY")