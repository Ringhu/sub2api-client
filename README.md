# sub2api-client

A minimal, reference Python client for **any sub2api-style OpenAI-compatible reverse proxy**
(e.g. projects in the `one-api` / `new-api` / `sub2api` family).

Once you've pointed `OPENAI_BASE_URL` + `OPENAI_API_KEY` at your proxy, this
library gives you one-line helpers for:

| Endpoint                    | Helper                    |
|-----------------------------|---------------------------|
| `POST /v1/chat/completions` | `chat(prompt)`            |
| `POST /v1/responses`        | `respond(prompt)`         |
| `POST /v1/images/generations` | `generate_image(prompt)` |
| `POST /v1/images/edits`     | `edit_image(prompt, image=...)` |
| `GET  /v1/models` (probe)   | `python probe_models.py`  |

The unmodified `openai` SDK still works — this is a thin helper layer for
common cases, plus a whitelist of models known to work against a
representative sub2api proxy (tested 2026-04-23).

中文说明见 [README.zh.md](README.zh.md)。

## Quick start

```bash
git clone https://github.com/Ringhu/sub2api-client
cd sub2api-client
pip install -e .

cp .env.example .env
# then open .env and fill in your proxy's URL + API key
```

Smoke test:

```bash
python examples/chat_completions.py
```

If that prints a one-sentence explanation of Transformers, you're done.

## Library usage

```python
from llm_client import chat, respond, generate_image, edit_image

# Chat Completions
print(chat("Hello in one word."))

# Responses API (e.g. for reasoning-effort control on o-series models)
print(respond("What's 17 * 23?", model="o3-mini", reasoning={"effort": "low"}))

# Image generation — returns a list of PNG bytes
generate_image("a red apple on a white table", save_to="apple.png")

# Image edit (multipart upload)
edit_image("turn the apple green", image="apple.png", save_to="green.png")
```

The raw SDK client is still available if you want streaming, tools, or any
other SDK feature:

```python
from llm_client import get_client
client = get_client()
stream = client.chat.completions.create(
    model="gpt-5.5", messages=[{"role": "user", "content": "hi"}], stream=True,
)
```

## Available models

Last verified **2026-04-23** against a representative sub2api proxy.
Your proxy may expose a different subset — run `python probe_models.py` to
re-check your own.

### Text models (chat / responses)

| Family        | IDs                                                                                                   | Notes                               |
|---------------|-------------------------------------------------------------------------------------------------------|-------------------------------------|
| **GPT-5.5**   | `gpt-5.5`                                                                                             | **Default.** Newest, best quality.   |
| GPT-5.4       | `gpt-5.4`, `gpt-5.4-2026-03-05`, `gpt-5.4-mini`, `gpt-5.4-nano`                                       | 1M context on full variant.          |
| GPT-5.3       | `gpt-5.3-codex`                                                                                       | Code-focused.                        |
| GPT-5.2       | `gpt-5.2`, `gpt-5.2-2025-12-11`, `gpt-5.2-chat-latest`, `gpt-5.2-codex`, `gpt-5.2-pro`, `gpt-5.2-pro-2025-12-11` | `pro` for high-quality reasoning.    |
| GPT-5.1       | `gpt-5.1`, `gpt-5.1-2025-11-13`, `gpt-5.1-chat-latest`, `gpt-5.1-codex`, `gpt-5.1-codex-max`, `gpt-5.1-codex-mini` |                                      |
| GPT-5.0       | `gpt-5`, `gpt-5-chat`, `gpt-5-chat-latest`, `gpt-5-codex`, `gpt-5-mini`, `gpt-5-nano`, `gpt-5-pro` (+ pinned variants) |                                      |
| **o-series**  | `o1`, `o1-mini`, `o1-preview`, `o1-pro`, `o3`, `o3-mini`, `o3-pro`, `o4-mini`                         | Reasoning. Pair with `reasoning={...}` on Responses API. |
| GPT-4.5 / 4.1 | `gpt-4.5-preview`, `gpt-4.1`, `gpt-4.1-mini`, `gpt-4.1-nano`                                          |                                      |
| GPT-4o        | `gpt-4o`, `gpt-4o-2024-08-06`, `gpt-4o-2024-11-20`, `gpt-4o-mini`, `gpt-4o-audio-preview`, `gpt-4o-realtime-preview`, `chatgpt-4o-latest` | Audio / realtime require SDK support. |
| GPT-4 / 3.5   | `gpt-4`, `gpt-4-turbo`, `gpt-4-turbo-preview`, `gpt-3.5-turbo` (+ pinned variants)                    | Legacy — kept for compatibility.     |

### Image models (generations / edits only — **not** chat)

| ID              | Notes                        |
|-----------------|------------------------------|
| `gpt-image-2`   | **Default.** Newest.         |
| `gpt-image-1.5` |                              |
| `gpt-image-1`   |                              |

Calling any `gpt-image-*` model on `/v1/chat/completions` returns HTTP 400
("not supported"). Use `/v1/images/generations` or `/v1/images/edits`
(via `generate_image()` / `edit_image()`).

## Environment variables

| Variable          | Purpose                                            |
|-------------------|----------------------------------------------------|
| `OPENAI_BASE_URL` | Your proxy's OpenAI-compatible root, e.g. `https://your-proxy/v1`. |
| `OPENAI_API_KEY`  | API key issued by your proxy.                       |
| `OPENAI_API_BASE` | Some libraries (LiteLLM, LlamaIndex) read this instead — keep it in sync with `OPENAI_BASE_URL`. |

`.env` in the project root is loaded automatically via `python-dotenv`.
`.env` is gitignored by default; don't commit real credentials.

## Third-party libraries

The `openai` SDK's convention of reading `OPENAI_BASE_URL` / `OPENAI_API_KEY`
at construction time means most libraries built on top of the SDK work
out of the box:

```python
# LangChain
from langchain_openai import ChatOpenAI
llm = ChatOpenAI(model="gpt-5.5")

# LiteLLM — prefix the model with "openai/" so LiteLLM routes via the SDK
import litellm
resp = litellm.completion(model="openai/gpt-5.5", messages=[...])

# LlamaIndex
from llama_index.llms.openai import OpenAI as LlamaOpenAI
llm = LlamaOpenAI(model="gpt-5.5")
```

## Gotchas

1. **Local `ALL_PROXY=socks://...` breaks httpx.** If you've set a SOCKS
   proxy in your shell, `httpx` (which the OpenAI SDK uses) will try to
   dial through it and fail. `llm_client` defends against this by building
   an `httpx.Client(trust_env=False)`. If you see `Could not resolve proxy`
   errors from code that bypasses this helper, unset `ALL_PROXY` or
   replicate the `trust_env=False` pattern.

2. **Responses API `store` defaults.** The SDK defaults `store=True` on
   `client.responses.create()`. Some proxies don't implement server-side
   retention and will error. `respond()` sets `store=False` by default.

3. **Model IDs in `/v1/models` aren't authoritative.** A proxy may list
   models it can't actually serve. Always call `probe_models.py` before
   committing to a model.

4. **Image models fail on the chat endpoint.** HTTP 400 is expected —
   use `generate_image()` / `edit_image()` instead.

## Probing your proxy

```bash
# Test chat + responses on every text model (default)
python probe_models.py --endpoint both

# Test image models
python probe_models.py --endpoint images

# Test everything
python probe_models.py --endpoint all
```

Output shows per-model OK/FAIL plus a summary list of working models.

## Project layout

```
sub2api-client/
├── llm_client.py           # Client factory + chat/respond/image helpers
├── probe_models.py         # Per-model availability diagnostic
├── examples/
│   ├── chat_completions.py
│   ├── responses_api.py
│   ├── async_batch.py
│   ├── image_generation.py
│   └── image_edits.py
├── .env.example
├── pyproject.toml
├── LICENSE                 # MIT
└── README.md               # you are here
```

## License

MIT. See [LICENSE](LICENSE).

This project is not affiliated with OpenAI or any specific proxy implementation.
Model availability and naming are determined entirely by the proxy you point it at.
