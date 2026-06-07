"""
Hosts photos publicly via GitHub Pages so TikTok can PULL_FROM_URL them.

It commits each photo into docs/photos/ using the GitHub Contents API, then
waits until the GitHub Pages URL is live before returning it.

Requires env:
  GITHUB_TOKEN       - auto-provided by GitHub Actions (needs contents: write)
  GITHUB_REPOSITORY  - auto-provided, e.g. "kktanws1-cpu/telegramtotiktok"
"""
import os
import time
import base64
import pathlib
import requests


def _repo_parts():
    repo = os.environ["GITHUB_REPOSITORY"]  # "owner/name"
    owner, name = repo.split("/", 1)
    return owner, name


def pages_base_url():
    owner, name = _repo_parts()
    return f"https://{owner.lower()}.github.io/{name}"


def upload_photo(local_path):
    """Commit one photo to docs/photos/ and return its public Pages URL."""
    token = os.environ["GITHUB_TOKEN"]
    owner, name = _repo_parts()
    filename = pathlib.Path(local_path).name
    repo_path = f"docs/photos/{filename}"

    with open(local_path, "rb") as f:
        content_b64 = base64.b64encode(f.read()).decode()

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    r = requests.put(
        f"https://api.github.com/repos/{owner}/{name}/contents/{repo_path}",
        headers=headers,
        json={
            "message": f"Add photo {filename} for TikTok post",
            "content": content_b64,
            "branch": "main",
        },
    )
    if r.status_code not in (200, 201):
        raise RuntimeError(f"GitHub upload failed: {r.status_code} {r.text}")

    return f"{pages_base_url()}/photos/{filename}"


def commit_file(repo_path, content_bytes, message):
    """Create or update a file in the repo via the Contents API (persists state)."""
    token = os.environ["GITHUB_TOKEN"]
    owner, name = _repo_parts()
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    api = f"https://api.github.com/repos/{owner}/{name}/contents/{repo_path}"

    # If the file already exists we must pass its current sha to update it.
    sha = None
    g = requests.get(api, headers=headers, params={"ref": "main"})
    if g.status_code == 200:
        sha = g.json().get("sha")

    body = {
        "message": message,
        "content": base64.b64encode(content_bytes).decode(),
        "branch": "main",
    }
    if sha:
        body["sha"] = sha

    r = requests.put(api, headers=headers, json=body)
    if r.status_code not in (200, 201):
        raise RuntimeError(f"GitHub commit failed: {r.status_code} {r.text}")
    print(f"[hosting] Committed {repo_path}")


def wait_until_live(url, timeout=300):
    """Poll the URL until GitHub Pages has published it (HTTP 200)."""
    deadline = time.time() + timeout
    attempt = 0
    while time.time() < deadline:
        attempt += 1
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code == 200:
                print(f"[hosting] Live after {attempt} check(s): {url}")
                return True
        except requests.RequestException:
            pass
        print(f"[hosting] Waiting for Pages to publish (attempt {attempt})...")
        time.sleep(10)
    raise RuntimeError(f"Photo URL not live after {timeout}s: {url}")
