"""Async batch example — fire multiple requests concurrently."""
import asyncio
import sys
sys.path.insert(0, sys.path[0] + "/..")

from llm_client import get_async_client, FAST_MODEL


async def ask(client, question: str) -> str:
    resp = await client.chat.completions.create(
        model=FAST_MODEL,
        messages=[{"role": "user", "content": question}],
    )
    return resp.choices[0].message.content


async def main():
    client = get_async_client()
    questions = ["1+1=?", "2+2=?", "3+3=?"]
    results = await asyncio.gather(*[ask(client, q) for q in questions])
    for q, a in zip(questions, results):
        print(f"  {q} → {a}")


asyncio.run(main())
