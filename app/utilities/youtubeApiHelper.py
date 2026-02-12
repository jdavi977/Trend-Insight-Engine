import os
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

YOUTUBE_API = os.getenv("YOUTUBE_API")

def getVideoCategories():
    service = build('youtube', 'v3', developerKey=YOUTUBE_API)
    request = service.videoCategories().list(
        part="snippet",
        regionCode="US",
    )
    list = []
    response = request.execute()

    for item in response["items"]:
        snippet = item["snippet"]
        list.append({
            "Id": item["id"],
            "Title": snippet["title"]
        })
    service.close()
    return list

if __name__ == "__main__":
    print(getVideoCategories())