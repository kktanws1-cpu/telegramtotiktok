# Telegram → TikTok Bot — Full Documentation

A personal automation that copies new photos from a **private Telegram channel**
to a **TikTok account's inbox** for review and publishing. Runs automatically
every day on GitHub Actions — no server, no PC needed.

---

## 1. What it does

Every day (midnight UTC) the bot:

1. Logs into Telegram as you (user session) and reads the channel **"Farmz Affiliates"**.
2. Finds photos posted **since the last run** (tracked by message ID).
3. Downloads each photo and **resizes** it to TikTok's limit (max 1080px).
4. **Hosts** the photo publicly on GitHub Pages (TikTok requires a public URL for photos).
5. Sends it to your **TikTok Inbox** via the Content Posting API (`PULL_FROM_URL`).
6. Saves its progress back to the repo so it never reposts duplicates.

You then open the TikTok app → **Inbox tab** → review → publish the ones you want.

---

## 2. Architecture

```
Telegram channel
      │  (Telethon user session)
      ▼
  bot.py  ── downloads ──►  resize (Pillow, ≤1080px)
      │                          │
      │                          ▼
      │                   GitHub Pages (docs/photos/*.jpg)  ◄── public URL
      │                          │
      ▼                          ▼
 TikTok Content Posting API (PULL_FROM_URL, MEDIA_UPLOAD)
      │
      ▼
 Your TikTok Inbox  ──►  you review & publish
```

Runs on **GitHub Actions** (`.github/workflows/bot.yml`), scheduled via cron.

---

## 3. Repository layout

| File | Purpose |
|---|---|
| `bot.py` | Main orchestration: fetch → resize → host → post → save state |
| `src/fetch.py` | Reads new photos from the Telegram channel (Telethon) |
| `src/downloader.py` | Downloads photos to a temp folder |
| `src/image_prep.py` | Resizes/re-encodes photos to ≤1080px JPEG |
| `src/hosting.py` | Commits photos to GitHub Pages; commits state.json |
| `src/tiktok.py` | TikTok token refresh + Content Posting API calls |
| `src/github_secrets.py` | Saves the rotated TikTok refresh token back to GitHub secrets |
| `get_tiktok_token.py` | One-time helper to get the first TikTok token (OAuth + PKCE) |
| `generate_session.py` | One-time helper to create the Telegram session string |
| `state.json` | Bot progress: `last_id` + `sent_ids` (prevents duplicates) |
| `docs/` | GitHub Pages site: hosts photos + domain verification + legal pages |
| `.github/workflows/bot.yml` | The daily GitHub Actions schedule |

---

## 4. Required GitHub secrets

Settings → Secrets and variables → Actions:

| Secret | What it is |
|---|---|
| `TELEGRAM_API_ID` | From my.telegram.org |
| `TELEGRAM_API_HASH` | From my.telegram.org |
| `TELEGRAM_SESSION_STRING` | From `generate_session.py` (a user login session) |
| `TELEGRAM_CHANNEL` | The channel's numeric ID (e.g. `-1002321888598`) |
| `TIKTOK_CLIENT_KEY` | From TikTok developer app |
| `TIKTOK_CLIENT_SECRET` | From TikTok developer app |
| `TIKTOK_REFRESH_TOKEN` | From `get_tiktok_token.py` (auto-rotated thereafter) |
| `GH_PAT` | GitHub fine-grained token w/ **Secrets: read+write** (saves rotated token) |

`GITHUB_TOKEN` is provided automatically by Actions (used to commit photos/state;
the job has `permissions: contents: write`).

---

## 5. Optional settings (add as secrets to change behavior)

| Secret | Effect | Default |
|---|---|---|
| `TIKTOK_POST_MODE` | `MEDIA_UPLOAD` (inbox review) or `DIRECT_POST` (auto-post) | `MEDIA_UPLOAD` |
| `TIKTOK_PRIVACY_LEVEL` | For direct post: `SELF_ONLY`, `PUBLIC_TO_EVERYONE`, etc. | `SELF_ONLY` |
| `DEFAULT_CAPTION` | Caption used when a photo has none | empty |
| `SCAN_LIMIT` | How many recent messages to scan per run | `200` |

Temporary run flags (set in the workflow `env:` for one run, then remove):

| Flag | Effect |
|---|---|
| `TEST_ONE_PHOTO: "true"` | Send exactly 1 photo (ignores baseline, doesn't save state) |
| `SET_BASELINE: "true"` | Record current position without posting (skip backlog) |

---

## 6. One-time setup (already done — for reference)

1. **Telegram API:** create an app at my.telegram.org → get API ID + hash.
2. **Session string:** run `generate_session.py` locally, log in, copy the string.
3. **Channel ID:** from web.telegram.org URL (the `-100...` number).
4. **TikTok app:** create at developers.tiktok.com → add Login Kit + Content
   Posting API (Direct Post) → scopes `video.publish`, `video.upload`,
   `user.info.basic`.
5. **TikTok token:** run `get_tiktok_token.py` (uses OAuth + PKCE) → get access +
   refresh tokens.
6. **GitHub Pages:** Settings → Pages → Deploy from branch `main` / `/docs`.
7. **Domain verification:** TikTok URL properties → URL prefix →
   `https://kktanws1-cpu.github.io/telegramtotiktok/` → host the signature file
   in `docs/` → Verify.
8. **Add the 8 secrets** (section 4).
9. **Baseline run** (`SET_BASELINE`) to skip the old backlog.

---

## 7. Daily operation

- The bot runs itself at **00:00 UTC** (change the cron in `bot.yml`).
- New channel photos → appear in your **TikTok Inbox tab** (NOT Drafts/Profile).
- Review and publish the ones you want; you pick public/private at publish time.
- The TikTok access token (24h life) is refreshed automatically each run using
  the refresh token, and the rotated refresh token is saved back to GitHub.

### Manual run
Actions → "Telegram → TikTok Bot" → **Run workflow**.

### Change the schedule
Edit `.github/workflows/bot.yml`:
```yaml
on:
  schedule:
    - cron: '0 0 * * *'   # minute hour day month weekday (UTC)
```

---

## 8. Key learning points (the hard-won lessons)

1. **Private Telegram channels need a USER session, not a bot.** Bots can't be
   added to channels you don't admin. Telethon with a user session string works.

2. **Numeric channel IDs must be passed as integers** to Telethon, or it treats
   `-100...` as a username and fails.

3. **TikTok OAuth requires PKCE.** The `code_challenge` must be **base64url**
   SHA-256 of the verifier (standard S256) — not hex.

4. **Authorization codes expire in ~1 minute and are single-use.** Capture and
   exchange them immediately (or auto-capture with a local redirect).

5. **TikTok photo posts only support `PULL_FROM_URL`, not `FILE_UPLOAD`.**
   `FILE_UPLOAD` is video-only. Photos must be at a **public, domain-verified URL**.
   → This is why we host on GitHub Pages and verify the domain.

6. **Unaudited (sandbox) apps:**
   - `DIRECT_POST` only works to a **private account**
     (`unaudited_client_can_only_post_to_private_accounts`).
   - `MEDIA_UPLOAD` (inbox) works with a **public account** — you publish manually.

7. **Photo size limit is 1080p.** Larger images fail with
   `picture_size_check_failed`. Resize before posting.

8. **TikTok title max is 90 characters.** Longer captions cause
   `invalid_params: post info is empty or incorrect`. Truncate the title.

9. **Posted photos land in the TikTok Inbox tab**, under System notifications —
   NOT in "Drafts" and NOT on your Profile.

10. **GitHub Actions runners are ephemeral.** State (`state.json`) must be
    committed back to the repo each run, or progress is lost and photos repost.

11. **TikTok refresh tokens rotate.** Each refresh returns a new refresh token;
    the bot saves it back to GitHub secrets (needs a PAT with Secrets write).

12. **GitHub Pages has a publish delay.** After committing a photo, poll the URL
    until it returns 200 before telling TikTok to pull it.

13. **Production audit requires a demo video** showing the UI flow — hard for a
    headless bot. Sandbox + inbox mode avoids the audit entirely for personal use.

---

## 9. Troubleshooting

| Symptom | Cause / Fix |
|---|---|
| `No new photos` | Nothing posted to the channel since last run (normal) |
| `picture_size_check_failed` | Image > 1080p — handled by `image_prep.py` |
| `post info is empty or incorrect` | Caption/title > 90 chars — truncated in `tiktok.py` |
| `unaudited_client_can_only_post_to_private_accounts` | Use inbox mode, or set account private for direct post |
| Photo not visible in TikTok | Look in **Inbox tab → System notifications**, not Drafts |
| `code_challenge` error | PKCE must be base64url S256 |
| `Authorization code is expired` | Exchange the code within ~1 minute |
| Token refresh fails | Refresh token expired (365d) — re-run `get_tiktok_token.py` |

---

## 10. Limitations

- Posts go to your **own** TikTok account only (the one that authorized the app).
- In sandbox, fully-automatic **public** posting isn't available — you publish
  from the inbox manually (which is the intended review step here).
- Each run scans the most recent `SCAN_LIMIT` (200) messages.
- The refresh token is valid ~365 days; re-authorize once a year.

---

*Generated for the Telegram → TikTok Bot project.*
