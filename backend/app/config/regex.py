import re

YOUTUBE_REGEX = re.compile(r"^https?://((www\.)?youtube\.com/watch\?v=|youtu\.be/)[A-Za-z0-9_-]{11}$")
APP_STORE_REGEX = re.compile(r"^https?:\/\/(www\.)?apps\.apple\.com\/[a-z]{2}\/app\/[A-Za-z0-9\-]+\/id\d+$")