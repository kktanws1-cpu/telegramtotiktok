import os
import time
import pathlib

DOWNLOADS_DIR = pathlib.Path(__file__).parent.parent / "downloads"


async def download_photos(client, messages):
    """Download all photos in a group of messages. Returns list of file paths."""
    DOWNLOADS_DIR.mkdir(exist_ok=True)
    paths = []
    for msg in messages:
        filename = DOWNLOADS_DIR / f"{int(time.time() * 1000)}_{msg.id}.jpg"
        await client.download_media(msg.media, file=str(filename))
        size_kb = os.path.getsize(filename) / 1024
        print(f"[downloader] {filename.name} ({size_kb:.1f} KB)")
        paths.append(str(filename))
    return paths


def cleanup(paths):
    for p in paths:
        try:
            os.remove(p)
        except FileNotFoundError:
            pass
