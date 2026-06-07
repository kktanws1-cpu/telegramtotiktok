import asyncio
import json
import os
import pathlib
import sys

from src.fetch import get_client, fetch_new_photos
from src.downloader import download_photos, cleanup
from src.tiktok import post_images_to_tiktok, refresh_access_token
from src.github_secrets import update_repo_secret
from src.hosting import upload_photo, wait_until_live, commit_file
from src.image_prep import prepare_for_tiktok

STATE_FILE = pathlib.Path(__file__).parent / "state.json"


def load_state():
    try:
        data = json.loads(STATE_FILE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    data.setdefault("last_id", 0)
    return data


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2))


async def main():
    channel = os.environ.get("TELEGRAM_CHANNEL")
    if not channel:
        print("[bot] Missing TELEGRAM_CHANNEL", file=sys.stderr)
        sys.exit(1)

    # Refresh the TikTok access token (it expires every ~24h) and persist the
    # rotated refresh token back to GitHub secrets for the next run.
    try:
        _, new_refresh = refresh_access_token()
        print("[bot] TikTok access token refreshed")
        update_repo_secret("TIKTOK_REFRESH_TOKEN", new_refresh)
    except Exception as e:
        print(f"[bot] Token refresh failed (will try existing token): {e}", file=sys.stderr)

    state = load_state()
    print(f"[bot] Checking from message id {state['last_id']}")

    client = await get_client()
    try:
        try:
            entity = await client.get_entity(int(channel) if str(channel).lstrip("-").isdigit() else channel)
            name = getattr(entity, "title", None) or getattr(entity, "username", None) or channel
            print(f"[bot] Reading from channel: '{name}' (id={getattr(entity, 'id', channel)})")
        except Exception as e:
            print(f"[bot] Could not resolve channel '{channel}': {e}", file=sys.stderr)

        # In test mode, ignore the saved baseline so we can pull an existing photo.
        fetch_from = 0 if os.environ.get("TEST_ONE_PHOTO") == "true" else state["last_id"]
        groups, new_last_id = await fetch_new_photos(client, channel, fetch_from)

        # One-time baseline: skip all existing photos, just record where we are.
        if os.environ.get("SET_BASELINE") == "true":
            state["last_id"] = new_last_id
            save_state(state)
            commit_file("state.json", json.dumps(state, indent=2).encode(), "Set bot baseline")
            print(f"[bot] BASELINE SET to id {new_last_id}. Backlog skipped; only new photos will post.")
            return

        # Skip any photos already successfully sent (prevents duplicate drafts on re-runs)
        sent_ids = set(state.get("sent_ids", []))
        groups = [[m for m in g if m.id not in sent_ids] for g in groups]
        groups = [g for g in groups if g]

        if not groups:
            print("[bot] No new photos.")
            return

        test_mode = os.environ.get("TEST_ONE_PHOTO") == "true"
        if test_mode:
            # Post exactly one photo and do NOT advance state (keep backlog intact)
            groups = [groups[0][:1]]
            print("[bot] TEST MODE: posting only 1 photo, state will not be saved")

        print(f"[bot] Found {len(groups)} album(s) to post")

        for group in groups:
            caption = next((msg.message for msg in group if msg.message), "")
            local_files = []
            try:
                local_files = await download_photos(client, group)
                # Resize/re-encode to meet TikTok's photo requirements, then host
                photo_urls = []
                for path in local_files:
                    prepare_for_tiktok(path)
                    url = upload_photo(path)
                    photo_urls.append(url)
                # Make sure the last one is live (Pages publishes them together)
                if photo_urls:
                    wait_until_live(photo_urls[-1])
                post_images_to_tiktok(photo_urls, caption)
                print(f"[bot] Posted {len(photo_urls)} photo(s) to TikTok")
                # Record these message ids as sent so re-runs skip them
                if not test_mode:
                    sent_ids.update(m.id for m in group)
            except Exception as e:
                print(f"[bot] Failed: {e}", file=sys.stderr)
            finally:
                cleanup(local_files)

        if not test_mode:
            state["last_id"] = new_last_id
            # Keep the most recent 2000 sent ids (plenty to prevent duplicates)
            state["sent_ids"] = sorted(sent_ids)[-2000:]
            save_state(state)
            commit_file("state.json", json.dumps(state, indent=2).encode(), "Update bot state")
            print(f"[bot] State saved. Next from id: {new_last_id} ({len(sent_ids)} sent total)")
    finally:
        await client.disconnect()


asyncio.run(main())
