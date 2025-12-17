from config.regex import EMOJI_REGEX
import re

def remove_emojis(data):
    cleaned = []
    for row in data:
        new_row = row.copy()
        new_row["Content"] = EMOJI_REGEX.sub("", row["Content"])
        cleaned.append(new_row)
    return cleaned

def keyword_filtering(data, keywords):
    filtered = []
    for row in data:
        for key in keywords:
            pattern = re.compile(r"\b" + re.escape(key) + r"\b")
            match = pattern.search(row['Content'])
            if match:
                filtered.append(row)
                pass
            else:
                pass
    return filtered

def exclude_keywords(data, keywords):
    filtered = []
    for row in data:
        for key in keywords:
            pattern = re.compile(r"\b" + re.escape(key) + r"\b")
            match = pattern.search(row['Content'])
            if not match:
                filtered.append(row)
                pass
            else:
                pass
    return filtered

def remove_duplicates(data):
    unique = list({c["Content"]: c for c in data}.values())
    return unique