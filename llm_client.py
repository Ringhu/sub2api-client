"""
OpenAI-compatible LLM client for any sub2api-style reverse proxy.

Works with any proxy that exposes an OpenAI-compatible surface at
``$OPENAI_BASE_URL`` and authenticates via ``$OPENAI_API_KEY``. Supports:

  - Chat Completions   : ``/v1/chat/completions``    -> ``chat(prompt)``
  - Responses API      : ``/v1/responses``           -> ``respond(prompt)``
  - Image generation   : ``/v1/images/generations``  -> ``generate_image(prompt)``
  - Image editing      : ``/v1/images/edits``        -> ``edit_image(prompt, image=...)``

Usage:
    from llm_client import chat, generate_image
    print(chat("Hello"))
    pngs = generate_image("a red apple on a white table", save_to="apple.png")

Environment variables (also loads ``.env`` if present):
    OPENAI_BASE_URL   reverse-proxy endpoint, e.g. https://your-proxy/v1
    OPENAI_API_KEY    API key issued by the proxy
"""
from __future__ import annotations

import base64
import warnings
from functools import lru_cache
from pathlib import Path
from typing import Iterable

import httpx
from dotenv import load_dotenv
from openai import AsyncOpenAI, OpenAI

load_dotenv()  # loads .env if present; real env vars take precedence


# ─────────────────────────── Model whitelists ────────────────────────────
# Last probed 2026-04-23 against a sub2api-style proxy. Your proxy may
# expose a different subset — run ``python probe_models.py`` to re-verify.
# Models absent from these sets still *work* if your proxy supports them,
# but ``check_model()`` will emit a warning as a sanity signal.

TEXT_MODELS: frozenset[str] = frozenset({
    # GPT-5.5 (newest)
    "gpt-5.5",
    # GPT-5.4 family
    "gpt-5.4", "gpt-5.4-2026-03-05", "gpt-5.4-mini", "gpt-5.4-nano",
    # GPT-5.3
    "gpt-5.3-codex",
    # GPT-5.2 family
    "gpt-5.2", "gpt-5.2-2025-12-11", "gpt-5.2-chat-latest",
    "gpt-5.2-codex", "gpt-5.2-pro", "gpt-5.2-pro-2025-12-11",
    # GPT-5.1 family
    "gpt-5.1", "gpt-5.1-2025-11-13", "gpt-5.1-chat-latest",
    "gpt-5.1-codex", "gpt-5.1-codex-max", "gpt-5.1-codex-mini",
    # GPT-5.0 family
    "gpt-5", "gpt-5-2025-08-07", "gpt-5-chat", "gpt-5-chat-latest",
    "gpt-5-codex", "gpt-5-mini", "gpt-5-mini-2025-08-07",
    "gpt-5-nano", "gpt-5-nano-2025-08-07",
    "gpt-5-pro", "gpt-5-pro-2025-10-06",
    # o-series reasoning
    "o1", "o1-mini", "o1-preview", "o1-pro",
    "o3", "o3-mini", "o3-pro",
    "o4-mini",
    # GPT-4.5 / 4.1 / 4o / 4 / 3.5
    "gpt-4.5-preview",
    "gpt-4.1", "gpt-4.1-mini", "gpt-4.1-nano",
    "gpt-4o", "gpt-4o-2024-08-06", "gpt-4o-2024-11-20",
    "gpt-4o-mini", "gpt-4o-mini-2024-07-18",
    "gpt-4o-audio-preview", "gpt-4o-realtime-preview",
    "chatgpt-4o-latest",
    "gpt-4", "gpt-4-turbo", "gpt-4-turbo-preview",
    "gpt-3.5-turbo", "gpt-3.5-turbo-0125",
    "gpt-3.5-turbo-1106", "gpt-3.5-turbo-16k",
})

IMAGE_MODELS: frozenset[str] = frozenset({
    "gpt-image-1",
    "gpt-image-1.5",
    "gpt-image-2",
})

# Convenience handles. Override at call time via ``model=...``.
DEFAULT_MODEL = "gpt-5.5"
FAST_MODEL = "gpt-5.4-mini"
PRO_MODEL = "gpt-5.2-pro"
REASONING_MODEL = "o3-pro"
DEFAULT_IMAGE_MODEL = "gpt-image-2"

# Back-compat alias (older code may import SUPPORTED_MODELS).
SUPPORTED_MODELS = TEXT_MODELS


# ─────────────────────────── Model validation ────────────────────────────
def check_model(model: str, *, kind: str = "text") -> None:
    """Warn (but don't block) if ``model`` isn't in the expected whitelist.

    ``kind`` is ``"text"`` (default) or ``"image"``.
    """
    whitelist = IMAGE_MODELS if kind == "image" else TEXT_MODELS
    if model not in whitelist:
        sample = ", ".join(sorted(whitelist)[:8])
        warnings.warn(
            f"Model '{model}' is not in the tested {kind} whitelist. "
            f"It may be unsupported by your proxy. "
            f"Examples of known-good {kind} models: {sample}, ...",
            stacklevel=3,
        )


# ─────────────────────────── HTTP + SDK clients ──────────────────────────
def _make_httpx_client() -> httpx.Client:
    """Build an httpx client that ignores env proxy vars.

    Some local setups export ``ALL_PROXY=socks://...`` which httpx can't
    dial through without extras. ``trust_env=False`` sidesteps that.
    """
    return httpx.Client(trust_env=False)


def _make_async_httpx_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(trust_env=False)


@lru_cache(maxsize=1)
def get_client(**kwargs) -> OpenAI:
    """Return a singleton ``OpenAI`` client.

    Reads ``OPENAI_BASE_URL`` and ``OPENAI_API_KEY`` from the environment.
    Pass keyword overrides (e.g. ``base_url=...``) to construct a distinct
    client; those bypass the cache.
    """
    kwargs.setdefault("http_client", _make_httpx_client())
    return OpenAI(timeout=120, max_retries=2, **kwargs)


@lru_cache(maxsize=1)
def get_async_client(**kwargs) -> AsyncOpenAI:
    """Return a singleton ``AsyncOpenAI`` client."""
    kwargs.setdefault("http_client", _make_async_httpx_client())
    return AsyncOpenAI(timeout=120, max_retries=2, **kwargs)


# ───────────────────────────── Text helpers ──────────────────────────────
def chat(prompt: str, *, model: str = DEFAULT_MODEL, **kwargs) -> str:
    """One-shot Chat Completions call. Returns the assistant's text."""
    check_model(model, kind="text")
    resp = get_client().chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        **kwargs,
    )
    return resp.choices[0].message.content


def respond(input_: str, *, model: str = DEFAULT_MODEL, **kwargs) -> str:
    """One-shot Responses API call. Returns the aggregated output text.

    ``store=False`` is set by default; pass ``store=True`` explicitly to
    opt in to server-side retention (if your proxy supports it).
    """
    check_model(model, kind="text")
    kwargs.setdefault("store", False)
    resp = get_client().responses.create(
        model=model,
        input=input_,
        **kwargs,
    )
    return resp.output_text


# ───────────────────────────── Image helpers ─────────────────────────────
def _decode_and_maybe_save(
    items: Iterable, save_to: str | Path | None
) -> list[bytes]:
    """Decode b64_json payloads to bytes; write the first one if requested."""
    blobs: list[bytes] = []
    for item in items:
        b64 = getattr(item, "b64_json", None)
        if b64 is None and isinstance(item, dict):
            b64 = item.get("b64_json")
        if not b64:
            continue
        blobs.append(base64.b64decode(b64))
    if save_to and blobs:
        Path(save_to).write_bytes(blobs[0])
    return blobs


def generate_image(
    prompt: str,
    *,
    model: str = DEFAULT_IMAGE_MODEL,
    size: str = "1024x1024",
    n: int = 1,
    save_to: str | Path | None = None,
    **kwargs,
) -> list[bytes]:
    """Call ``/v1/images/generations``.

    Returns a list of PNG byte payloads (one per generated image).
    If ``save_to`` is provided, the first image is also written there.

    Note: image models (``gpt-image-*``) reject ``/v1/chat/completions``
    with HTTP 400 — they are only callable via this endpoint and
    ``/v1/images/edits``.
    """
    check_model(model, kind="image")
    kwargs.setdefault("response_format", "b64_json")
    resp = get_client().images.generate(
        model=model, prompt=prompt, size=size, n=n, **kwargs
    )
    return _decode_and_maybe_save(resp.data, save_to)


def edit_image(
    prompt: str,
    image: str | Path | bytes,
    *,
    mask: str | Path | bytes | None = None,
    model: str = DEFAULT_IMAGE_MODEL,
    size: str = "1024x1024",
    n: int = 1,
    save_to: str | Path | None = None,
    **kwargs,
) -> list[bytes]:
    """Call ``/v1/images/edits`` (multipart).

    ``image`` and ``mask`` may be a file path or raw bytes. ``mask`` is
    optional — some image models accept edit prompts without a mask.
    Returns a list of PNG byte payloads. The OpenAI SDK handles multipart
    assembly internally.
    """
    check_model(model, kind="image")
    kwargs.setdefault("response_format", "b64_json")

    def _open(src):
        if isinstance(src, (bytes, bytearray)):
            return src
        return open(src, "rb")

    image_handle = _open(image)
    mask_handle = _open(mask) if mask is not None else None
    try:
        call_kwargs = dict(
            model=model, prompt=prompt, image=image_handle,
            size=size, n=n, **kwargs,
        )
        if mask_handle is not None:
            call_kwargs["mask"] = mask_handle
        resp = get_client().images.edit(**call_kwargs)
    finally:
        for h in (image_handle, mask_handle):
            if hasattr(h, "close"):
                h.close()
    return _decode_and_maybe_save(resp.data, save_to)
