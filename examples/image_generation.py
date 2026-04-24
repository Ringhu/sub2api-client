"""Minimal /v1/images/generations example."""
import sys
sys.path.insert(0, sys.path[0] + "/..")

from llm_client import generate_image, DEFAULT_IMAGE_MODEL

print(f"Model: {DEFAULT_IMAGE_MODEL}")

blobs = generate_image(
    "a red apple on a clean white table, soft natural light",
    size="1024x1024",
    save_to="apple.png",
)

print(f"Generated {len(blobs)} image(s); first is {len(blobs[0])} bytes, saved to apple.png")
