import re

YOUTUBE_REGEX = re.compile(r"^https?://((www\.)?youtube\.com/watch\?v=|youtu\.be/)[A-Za-z0-9_-]{11}$")

def validateURL(url: str):
    return YOUTUBE_REGEX.match(url) is not None
    
