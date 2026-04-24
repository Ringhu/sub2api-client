#!/usr/bin/env python3
"""
Probe which models actually work on your OpenAI-compatible proxy.

The list of models returned by ``/v1/models`` is advisory: some proxies
expose model IDs they don't actually serve, and fail at call time. This
tool issues a minimal request per model and reports which endpoints work.

Usage:
    python probe_models.py                      # test chat/completions (default)
    python probe_models.py --endpoint responses
    python probe_models.py --endpoint images    # only image-generation models
    python probe_models.py --endpoint both      # chat + responses (no images)
    python probe_models.py --endpoint all       # chat + responses + images
"""

import argparse

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


def probe_chat(client: OpenAI, model: str) -> tuple[bool, str]:
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=5,
        )
        text = resp.choices[0].message.content or ""
        return True, text[:40]
    except Exception as e:
        return False, str(e)[:80]


def probe_responses(client: OpenAI, model: str) -> tuple[bool, str]:
    try:
        resp = client.responses.create(
            model=model,
            input="ping",
            max_output_tokens=16,
            store=False,
        )
        return True, resp.output_text[:40]
    except Exception as e:
        return False, str(e)[:80]


def probe_image(client: OpenAI, model: str) -> tuple[bool, str]:
    try:
        resp = client.images.generate(
            model=model,
            prompt="a small red dot on white",
            size="1024x1024",
            n=1,
            response_format="b64_json",
        )
        b64 = resp.data[0].b64_json or ""
        return True, f"b64_json len={len(b64)}"
    except Exception as e:
        return False, str(e)[:80]


def is_image_model(model_id: str) -> bool:
    return "image" in model_id or model_id.startswith("dall-e")


def main():
    parser = argparse.ArgumentParser(description="Probe model availability")
    parser.add_argument(
        "--endpoint",
        choices=["chat", "responses", "images", "both", "all"],
        default="chat",
        help=("Which endpoint(s) to test. 'both' = chat + responses (text only). "
              "'all' = chat + responses + images."),
    )
    args = parser.parse_args()

    client = OpenAI(timeout=90, max_retries=0)

    models = [m.id for m in client.models.list().data]
    models.sort()
    print(f"Found {len(models)} models. Testing endpoint={args.endpoint}...\n")

    ok_list, fail_list = [], []

    for m in models:
        results: dict[str, tuple[bool, str]] = {}

        if args.endpoint == "images":
            if not is_image_model(m):
                continue
            results["image"] = probe_image(client, m)
        elif args.endpoint == "all":
            if is_image_model(m):
                results["image"] = probe_image(client, m)
            else:
                results["chat"] = probe_chat(client, m)
                results["resp"] = probe_responses(client, m)
        else:
            if is_image_model(m):
                continue  # image models can't serve chat/responses
            if args.endpoint in ("chat", "both"):
                results["chat"] = probe_chat(client, m)
            if args.endpoint in ("responses", "both"):
                results["resp"] = probe_responses(client, m)

        if not results:
            continue

        all_ok = all(ok for ok, _ in results.values())
        status = "OK" if all_ok else "FAIL"
        detail = " | ".join(
            f"{k}={'ok' if ok else err}" for k, (ok, err) in results.items()
        )
        print(f"  {status:4s}  {m:30s}  {detail}")

        (ok_list if all_ok else fail_list).append(m)

    print(f"\n{'=' * 60}")
    print(f"OK:   {len(ok_list)} / {len(ok_list) + len(fail_list)} tested")
    for m in ok_list:
        print(f"  + {m}")
    print(f"FAIL: {len(fail_list)}")
    for m in fail_list:
        print(f"  - {m}")


if __name__ == "__main__":
    main()
