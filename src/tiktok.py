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


def _init_upload(image_count, caption):
    payload = {
        "media_type": "PHOTO",
        "post_mode": "DIRECT_POST",
        "post_info": {
            "title": caption or os.environ.get("DEFAULT_CAPTION", ""),
            "privacy_level": os.environ.get("TIKTOK_PRIVACY_LEVEL", "PUBLIC_TO_EVERYONE"),
            "disable_comment": os.environ.get("TIKTOK_ALLOW_COMMENT") != "true",
            "disable_duet": os.environ.get("TIKTOK_ALLOW_DUET") != "true",
            "disable_stitch": os.environ.get("TIKTOK_ALLOW_STITCH") != "true",
        },
        "source_info": {
            "source": "FILE_UPLOAD",
            "photo_images_count": image_count,
            "photo_cover_index": 1,
        },
    }
    r = requests.post(f"{TIKTOK_API}/post/publish/content/init/", json=payload, headers=_headers())
    data = r.json()
    if data.get("error", {}).get("code") != "ok":
        raise RuntimeError(f"TikTok init failed: {data.get('error')}")
    return data["data"]["publish_id"], data["data"]["upload_urls"]


def _upload_images(upload_urls, file_paths):
    for i, (url, path) in enumerate(zip(upload_urls, file_paths)):
        print(f"[tiktok] Uploading image {i + 1}/{len(file_paths)}...")
        size = os.path.getsize(path)
        with open(path, "rb") as f:
            requests.put(url, data=f, headers={
                "Content-Type": "image/jpeg",
                "Content-Length": str(size),
            })


def _wait_for_publish(publish_id, timeout=60):
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = requests.post(
            f"{TIKTOK_API}/post/publish/status/fetch/",
            json={"publish_id": publish_id},
            headers=_headers(),
        )
        status = r.json().get("data", {}).get("status")
        print(f"[tiktok] Status: {status}")
        if status == "PUBLISH_COMPLETE":
            return
        if status == "FAILED":
            raise RuntimeError(f"Publish failed (publish_id: {publish_id})")
        time.sleep(5)
    raise RuntimeError("TikTok publish timed out")


def post_images_to_tiktok(file_paths, caption=""):
    if not os.environ.get("TIKTOK_ACCESS_TOKEN"):
        raise RuntimeError("TIKTOK_ACCESS_TOKEN is not set")
    if len(file_paths) > 35:
        raise RuntimeError("Max 35 images per TikTok post")

    publish_id, upload_urls = _init_upload(len(file_paths), caption)
    print(f"[tiktok] publish_id: {publish_id}")
    _upload_images(upload_urls, file_paths)
    _wait_for_publish(publish_id)
    print(f"[tiktok] Posted! publish_id: {publish_id}")
