import os
from dotenv import load_dotenv

load_dotenv

OPENAI_KEY = os.getenv("OPENAI_KEY")
YOUTUBE_API = os.getenv("YOUTUBE_API")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")