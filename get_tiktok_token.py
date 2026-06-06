"""
Run this ONCE locally to get your TikTok access token (and refresh token).

Uses the registered redirect URI https://dashboard-qmng.onrender.com/ with PKCE.

IMPORTANT: The authorization code expires within ~1 minute and is single-use.
So when the browser redirects, copy the URL and paste it back IMMEDIATELY.
Keep this terminal and the browser side by side before you start.

Usage:
    pip install requests
    python get_tiktok_token.py
"""
import urllib.parse
import webbrowser
import secrets
import hashlib
import base64
import requests

REDIRECT_URI = "https://dashboard-qmng.onrender.com/"
SCOPE = "video.publish,video.upload,user.info.basic"

client_key = input("Enter your TikTok Client Key: ").strip()
client_secret = input("Enter your TikTok Client Secret: ").strip()

# PKCE (standard S256 = base64url, no padding)
code_verifier = secrets.token_urlsafe(48)
digest = hashlib.sha256(code_verifier.encode()).digest()
code_challenge = base64.urlsafe_b64encode(digest).decode().rstrip("=")

auth_params = {
    "client_key": client_key,
    "scope": SCOPE,
    "response_type": "code",
    "redirect_uri": REDIRECT_URI,
    "state": "tgtotiktok",
    "code_challenge": code_challenge,
    "code_challenge_method": "S256",
}
auth_url = "https://www.tiktok.com/v2/auth/authorize/?" + urllib.parse.urlencode(auth_params)

print("\n" + "=" * 60)
print("STEP 1: A browser will open. Log in and click Authorize.")
print("STEP 2: The page redirects to dashboard-qmng.onrender.com")
print("        (it may look like a normal website - that's fine).")
print("STEP 3: IMMEDIATELY copy the FULL URL from the address bar")
print("        and paste it below. Do this within ~1 minute!")
print("=" * 60 + "\n")
input("Press ENTER when you are ready, then approve quickly... ")

webbrowser.open(auth_url)
print("\nIf the browser didn't open, paste this URL manually:\n")
print(auth_url + "\n")

redirected = input("Paste the full redirected URL here NOW: ").strip()

# Extract code (do NOT mangle it)
parsed = urllib.parse.urlparse(redirected)
query = urllib.parse.parse_qs(parsed.query)
code = query.get("code", [None])[0]
if not code:
    code = redirected  # in case they pasted just the code

print("\nExchanging code for access token...\n")
resp = requests.post(
    "https://open.tiktokapis.com/v2/oauth/token/",
    headers={"Content-Type": "application/x-www-form-urlencoded"},
    data={
        "client_key": client_key,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI,
        "code_verifier": code_verifier,
    },
)
data = resp.json()

if "access_token" in data:
    print("=" * 60)
    print("SUCCESS!")
    print("=" * 60)
    print("ACCESS TOKEN (save as TIKTOK_ACCESS_TOKEN):")
    print(data["access_token"])
    print("-" * 60)
    print("REFRESH TOKEN (save as TIKTOK_REFRESH_TOKEN):")
    print(data.get("refresh_token"))
    print("-" * 60)
    print(f"Access token expires in: {data.get('expires_in')} seconds (~24h)")
    print(f"Refresh token expires in: {data.get('refresh_expires_in')} seconds (~365d)")
    print("=" * 60)
else:
    print("ERROR getting token:")
    print(data)
    print("\nIf it says 'expired', just run the script again and paste FASTER.")
