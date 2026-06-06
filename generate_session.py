"""
Run this ONCE locally to generate your TELEGRAM_SESSION_STRING.
Copy the printed string and save it as a GitHub secret.

Usage:
    pip install telethon
    python generate_session.py
"""
from telethon.sync import TelegramClient
from telethon.sessions import StringSession

api_id = int(input("Enter your API ID: "))
api_hash = input("Enter your API hash: ")

with TelegramClient(StringSession(), api_id, api_hash) as client:
    print("\n=== YOUR SESSION STRING (save this as TELEGRAM_SESSION_STRING) ===")
    print(client.session.save())
    print("=" * 60)
