import re

YOUTUBE_REGEX = re.compile(r"^https?://((www\.)?youtube\.com/watch\?v=|youtu\.be/)[A-Za-z0-9_-]{11}$")
APP_STORE_REGEX = re.compile(r"^https?:\/\/(www\.)?apps\.apple\.com\/[a-z]{2}\/app\/[A-Za-z0-9\-]+\/id\d+$")

EMOJI_REGEX = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # Emoticons
    "\U0001F300-\U0001F5FF"  # Symbols & Pictographs
    "\U0001F680-\U0001F6FF"  # Transport & Map
    "\U0001F700-\U0001F77F"  # Alchemical Symbols
    "\U0001F780-\U0001F7FF"  # Geometric Shapes Extended
    "\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
    "\U0001F900-\U0001F9FF"  # Supplemental Symbols & Pictographs
    "\U0001FA00-\U0001FA6F"  # Chess Symbols
    "\U0001FA70-\U0001FAFF"  # Symbols & Pictographs Extended-A
    "\U0001F1E0-\U0001F1FF"  # Flags
    "\U00002600-\U000026FF"  # Miscellaneous Symbols
    "\U00002700-\U000027BF"  # Dingbats
    "\U0000FE00-\U0000FE0F"  # Variation Selectors
    "\U0001F018-\U0001F270"  # Various asian characters
    "\U000024C2-\U0001F251"
    "\U0000200D"             # Zero Width Joiner
    "\U000020E3"             # Combining Enclosing Keycap
    "]+",
    flags=re.UNICODE,
)