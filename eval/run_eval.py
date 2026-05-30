import argparse
import asyncio
import json
import sys
from collections import defaultdict
from pathlib import Path

from app.clients import aclient
from app.config import settings
from app.db import SessionLocal
from app.rag.generate import generate
from app.rag.hybrid import hybrid_search
from app.rag.retrieve import retrieve  # C1 dense-only baseline

GOLDEN = Path(__file__).parent / "golden.jsonl"
FAITHFULNESS_FLOOR = 0.8

JUDGE = (
    "You are grading an answer for faithfulness to its sources. "
    "Return ONLY a float 0.0-1.0: 1.0 if every claim is supported by the "
    "sources, 0.0 if the answer contradicts or invents facts."
)


async def judge_faithfulness(answer: str, context: str) -> float:
    resp = await aclient.chat.completions.create(
        model=settings.chat_model,
        temperature=0,
        messages=[
            {
                "role": "user",
                "content": f"{JUDGE}\n\nSOURCES:\n{context}\n\nANSWER:\n{answer}",
            }
        ],
    )
    try:
        return float(resp.choices[0].message.content.strip())
    except ValueError:
        return 0.0


async def evaluate(retriever_name: str) -> dict:
    golden = [json.loads(line) for line in GOLDEN.read_text().splitlines() if line.strip()]
    hits, faiths = 0, []
    by_type_hits: dict[str, list[int]] = defaultdict(list)
    async with SessionLocal() as session:
        for row in golden:
            # far_leak rows carry a scope to apply as a hard source filter
            scope = row.get("scope")
            if retriever_name == "dense":
                chunks = await retrieve(session, row["q"], k=5)
            else:
                chunks = await hybrid_search(
                    session, row["q"], k=5, source_system=scope
                )
            # expect_source may be a string or a list (near_neighbor)
            expected = row["expect_source"]
            expected = expected if isinstance(expected, list) else [expected]
            hit = any(
                any(e in (c.source_system or "") for e in expected) for c in chunks
            )
            hits += int(hit)
            by_type_hits[row["type"]].append(int(hit))
            ans = await generate(row["q"], chunks)
            ctx = "\n".join(c.content for c in chunks)
            faiths.append(await judge_faithfulness(ans["answer"], ctx))
    return {
        "retriever": retriever_name,
        "retrieval_hit_rate": round(hits / len(golden), 3),
        "avg_faithfulness": round(sum(faiths) / len(faiths), 3),
        "hit_rate_by_type": {
            t: round(sum(v) / len(v), 3) for t, v in sorted(by_type_hits.items())
        },
    }


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--gate",
        action="store_true",
        help=f"exit non-zero if avg_faithfulness < {FAITHFULNESS_FLOOR}",
    )
    args = parser.parse_args()

    results = []
    for name in ("dense", "hybrid"):
        res = await evaluate(name)
        print(res)
        results.append(res)

    if args.gate:
        hybrid = next(r for r in results if r["retriever"] == "hybrid")
        if hybrid["avg_faithfulness"] < FAITHFULNESS_FLOOR:
            print(
                f"GATE FAILED: hybrid avg_faithfulness "
                f"{hybrid['avg_faithfulness']} < {FAITHFULNESS_FLOOR}",
                file=sys.stderr,
            )
            sys.exit(1)
        print(f"GATE PASSED: faithfulness >= {FAITHFULNESS_FLOOR}")


if __name__ == "__main__":
    asyncio.run(main())
