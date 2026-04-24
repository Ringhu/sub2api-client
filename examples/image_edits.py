"""Minimal /v1/images/edits example.

Requires an existing PNG on disk. If apple.png doesn't exist yet, run
examples/image_generation.py first to create one.
"""
import sys
from pathlib import Path
sys.path.insert(0, sys.path[0] + "/..")

from llm_client import edit_image, generate_image, DEFAULT_IMAGE_MODEL

src = Path("apple.png")
if not src.exists():
    print("apple.png not found — generating source image first...")
    generate_image("a red apple on a white table", save_to=src)

print(f"Model: {DEFAULT_IMAGE_MODEL}")
blobs = edit_image(
    "turn the apple green, keep everything else the same",
    image=src,
    size="1024x1024",
    save_to="apple_green.png",
)
print(f"Edited {len(blobs)} image(s); saved first to apple_green.png ({len(blobs[0])} bytes)")
