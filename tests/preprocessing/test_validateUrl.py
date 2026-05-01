import pytest

from app.preprocessing.validateUrl import validateAppStore, validateYoutube


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtube.com/watch?v=dQw4w9WgXcQ",
        "http://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
    ],
)
def test_validateYoutube_accepts_valid_urls(url):
    assert validateYoutube(url) is True


@pytest.mark.parametrize(
    "url",
    [
        "",
        "not a url",
        "https://www.youtube.com/watch?v=tooShort",
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ&feature=share",
        "https://vimeo.com/123456789",
        "https://youtu.be/dQw4w9WgX",
        "ftp://www.youtube.com/watch?v=dQw4w9WgXcQ",
    ],
)
def test_validateYoutube_rejects_invalid_urls(url):
    assert validateYoutube(url) is False


@pytest.mark.parametrize(
    "url",
    [
        "https://apps.apple.com/us/app/instagram/id389801252",
        "http://apps.apple.com/gb/app/some-app/id1234567890",
        "https://www.apps.apple.com/ca/app/duolingo/id570060128",
    ],
)
def test_validateAppStore_accepts_valid_urls(url):
    assert validateAppStore(url) is True


@pytest.mark.parametrize(
    "url",
    [
        "",
        "not a url",
        "https://apps.apple.com/app/instagram/id389801252",
        "https://apps.apple.com/US/app/instagram/id389801252",
        "https://apps.apple.com/us/app/instagram/idABCDEF",
        "https://play.google.com/store/apps/details?id=com.instagram.android",
    ],
)
def test_validateAppStore_rejects_invalid_urls(url):
    assert validateAppStore(url) is False
