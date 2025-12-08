from config.regex import YOUTUBE_REGEX, APP_STORE_REGEX

def validateYoutube(url: str):
    return YOUTUBE_REGEX.match(url) is not None
    
def validateAppStore(url: str):
    return APP_STORE_REGEX.match(url) is not None

