import os
import base64
import requests
from nacl import encoding, public


def update_repo_secret(secret_name, secret_value):
    """Update a GitHub Actions repository secret via the API.
    Requires env: GH_PAT (token with 'secrets: write'), GITHUB_REPOSITORY (owner/repo).
    Returns True on success, False otherwise (never raises, so the bot keeps running)."""
    pat = os.environ.get("GH_PAT")
    repo = os.environ.get("GITHUB_REPOSITORY")  # auto-set by GitHub Actions
    if not pat or not repo:
        print("[github] GH_PAT or GITHUB_REPOSITORY missing - skipping secret update")
        return False

    headers = {
        "Authorization": f"Bearer {pat}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    # 1. Get the repo public key
    r = requests.get(
        f"https://api.github.com/repos/{repo}/actions/secrets/public-key",
        headers=headers,
    )
    if r.status_code != 200:
        print(f"[github] Failed to get public key: {r.status_code} {r.text}")
        return False
    key_data = r.json()

    # 2. Encrypt the secret value with the repo public key (libsodium sealed box)
    pub_key = public.PublicKey(key_data["key"].encode(), encoding.Base64Encoder())
    sealed_box = public.SealedBox(pub_key)
    encrypted = sealed_box.encrypt(secret_value.encode())
    encrypted_b64 = base64.b64encode(encrypted).decode()

    # 3. PUT the encrypted secret
    r = requests.put(
        f"https://api.github.com/repos/{repo}/actions/secrets/{secret_name}",
        headers=headers,
        json={"encrypted_value": encrypted_b64, "key_id": key_data["key_id"]},
    )
    if r.status_code in (201, 204):
        print(f"[github] Secret {secret_name} updated successfully")
        return True
    print(f"[github] Failed to update secret: {r.status_code} {r.text}")
    return False
