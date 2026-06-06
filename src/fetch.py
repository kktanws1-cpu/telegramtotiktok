import os
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import MessageMediaPhoto


async def get_client():
    api_id = int(os.environ["TELEGRAM_API_ID"])
    api_hash = os.environ["TELEGRAM_API_HASH"]
    session_string = os.environ["TELEGRAM_SESSION_STRING"]
    client = TelegramClient(StringSession(session_string), api_id, api_hash)
    await client.start()
    return client


async def fetch_new_photos(client, channel, last_id):
    """Return list of (grouped_id, [messages]) for all photo messages after last_id."""
    messages = []
    async for msg in client.iter_messages(channel, min_id=last_id, limit=100):
        if msg.media and isinstance(msg.media, MessageMediaPhoto):
            messages.append(msg)

    if not messages:
        return [], last_id

    # Group by media_group_id (albums)
    albums = {}
    singles = []
    for msg in reversed(messages):
        if msg.grouped_id:
            albums.setdefault(msg.grouped_id, []).append(msg)
        else:
            singles.append([msg])

    groups = list(albums.values()) + singles
    new_last_id = max(msg.id for msg in messages)
    return groups, new_last_id
