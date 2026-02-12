import re

YOUTUBE_REGEX = re.compile(r"^https?://((www\.)?youtube\.com/watch\?v=|youtu\.be/)[A-Za-z0-9_-]{11}$")
APP_STORE_REGEX = re.compile(r"^https?:\/\/(www\.)?apps\.apple\.com\/[a-z]{2}\/app\/[A-Za-z0-9\-]+\/id\d+$")

EMOJI_REGEX = re.compile(
    "[" 
    "\U0001F600-\U0001F64F"  # Emoticons
    "\U0001F300-\U0001F5FF"  # Symbols & Pictographs
    "\U0001F680-\U0001F6FF"  # Transport & Map
    "\U0001F1E0-\U0001F1FF"  # Flags
    "\U00002702-\U000027B0"  # Dingbats
    "\U000024C2-\U0001F251"
    "]+",
    flags=re.UNICODE
)