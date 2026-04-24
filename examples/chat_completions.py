"""Minimal sync chat completions example."""
import sys
sys.path.insert(0, sys.path[0] + "/..")

from llm_client import chat, DEFAULT_MODEL

print(f"Model: {DEFAULT_MODEL}")
print(chat("Explain Transformers in one sentence."))
