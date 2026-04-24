"""Responses API example (same wire protocol the OpenAI Responses endpoint uses)."""
import sys
sys.path.insert(0, sys.path[0] + "/..")

from llm_client import respond, DEFAULT_MODEL

print(f"Model: {DEFAULT_MODEL}")
print(respond(
    "Explain Transformers in one sentence.",
    reasoning={"effort": "high"},
))
