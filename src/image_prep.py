"""
Prepare images to satisfy TikTok's photo requirements:
  - Format: JPEG
  - Max 1080p (we cap the longest side at 1080px)
  - Re-encode cleanly so TikTok's picture_size_check passes
"""
import os
from PIL import Image

MAX_SIDE = 1080  # TikTok: maximum 1080p


def prepare_for_tiktok(path):
    """Resize/re-encode an image in place so TikTok accepts it.
    Returns the path (same path, .jpg)."""
    img = Image.open(path)

    # Flatten transparency / convert to RGB for JPEG
    if img.mode in ("RGBA", "P", "LA"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        img = img.convert("RGBA")
        background.paste(img, mask=img.split()[-1])
        img = background
    elif img.mode != "RGB":
        img = img.convert("RGB")

    # Downscale so the longest side is at most MAX_SIDE (preserve aspect ratio)
    w, h = img.size
    longest = max(w, h)
    if longest > MAX_SIDE:
        scale = MAX_SIDE / longest
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    img.save(path, format="JPEG", quality=90)
    new_w, new_h = img.size
    size_kb = os.path.getsize(path) / 1024
    print(f"[image_prep] {os.path.basename(path)} -> {new_w}x{new_h} ({size_kb:.1f} KB)")
    return path
