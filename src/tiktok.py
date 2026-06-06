import os
import time
import requests

TIKTOK_API = "https://open.tiktokapis.com/v2"

# Holds the access token in memory after refresh (so we don't rely on env only)
_ACCESS_TOKEN = {"value": os.environ.get("TIKTOK_ACCESS_TOKEN")}


def refresh_access_token():
    """Use the refresh token to get a fresh access token.
    Returns (access_token, new_refresh_token). Raises on failure."""
    client_key = os.environ["TIKTOK_CLIENT_KEY"]
    client_secret = os.environ["TIKTOK_CLIENT_SECRET"]
    refresh_token = os.environ["TIKTOK_REFRESH_TOKEN"]

    resp = requests.post(
        f"{TIKTOK_API}/oauth/token/",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "client_key": client_key,
            "client_secret": client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
    )
    data = resp.json()
    if "access_token" not in data:
        raise RuntimeError(f"TikTok token refresh failed: {data}")

    _ACCESS_TOKEN["value"] = data["access_token"]
    new_refresh = data.get("refresh_token", refresh_token)
    return data["access_token"], new_refresh


def _headers():
    token = _ACCESS_TOKEN["value"] or os.environ.get("TIKTOK_ACCESS_TOKEN")
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=UTF-8",
    }


def _init_pull(photo_urls, caption):
    """Initialize a PHOTO direct post using PULL_FROM_URL (required for photos)."""
    payload = {
        "media_type": "PHOTO",
        "post_mode": "DIRECT_POST",
        "post_info": {
            "title": caption or os.environ.get("DEFAULT_CAPTION", ""),
            # Unaudited/sandbox apps must use SELF_ONLY; override via secret once approved.
            "privacy_level": os.environ.get("TIKTOK_PRIVACY_LEVEL", "SELF_ONLY"),
            "disable_comment": os.environ.get("TIKTOK_ALLOW_COMMENT") != "true",
        },
        "source_info": {
            "source": "PULL_FROM_URL",
            "photo_images": photo_urls,
            "photo_cover_index": 0,  # 0-based; first image is the cover
        },
    }
    r = requests.post(f"{TIKTOK_API}/post/publish/content/init/", json=payload, headers=_headers())
    data = r.json()
    if data.get("error", {}).get("code") != "ok":
        raise RuntimeError(f"TikTok init failed: {data.get('error')}")
    return data["data"]["publish_id"]


def _wait_for_publish(publish_id, timeout=120):
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = requests.post(
            f"{TIKTOK_API}/post/publish/status/fetch/",
            json={"publish_id": publish_id},
            headers=_headers(),
        )
        data = r.json().get("data", {})
        status = data.get("status")
        print(f"[tiktok] Status: {status}")
        if status == "PUBLISH_COMPLETE":
            return
        if status == "FAILED":
            reason = data.get("fail_reason") or data.get("error_code") or data
            raise RuntimeError(f"Publish failed: {reason} | full={data}")
        time.sleep(5)
    raise RuntimeError("TikTok publish timed out")


def post_images_to_tiktok(photo_urls, caption=""):
    """photo_urls: list of public, domain-verified image URLs (PULL_FROM_URL)."""
    if not (_ACCESS_TOKEN["value"] or os.environ.get("TIKTOK_ACCESS_TOKEN")):
        raise RuntimeError("No TikTok access token available (refresh may have failed)")
    if len(photo_urls) > 35:
        raise RuntimeError("Max 35 images per TikTok post")

    publish_id = _init_pull(photo_urls, caption)
    print(f"[tiktok] publish_id: {publish_id}")
    _wait_for_publish(publish_id)
    print(f"[tiktok] Posted! publish_id: {publish_id}")
