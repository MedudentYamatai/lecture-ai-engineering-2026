"""第5回 宿題: 同じ質問・モデルで取得方法を比べる。

    uv run python -m scripts.eval_rag --modes base topk10 neighbors hybrid --repeats 3 --out result.json
"""

import argparse
import json
import re
import statistics
import time
from pathlib import Path

from pydantic_ai.exceptions import ModelHTTPError
from pydantic_ai.messages import ToolReturnPart

from app import agent as agent_module, retrieval, tools
from app.config import MODEL

QUESTIONS = Path("lectures/05/homework/questions.jsonl")
MODES = {
    "base": (agent_module.INSTRUCTIONS, tools.search_materials, 5),
    "topk10": (agent_module.INSTRUCTIONS, tools.search_materials, 10),
    "neighbors": (agent_module.NEIGHBOR_INSTRUCTIONS, tools.search_materials_with_neighbors, 5),
    "hybrid": (agent_module.HYBRID_INSTRUCTIONS, tools.search_materials_hybrid, 5),
}


def cited_pages(answer: str) -> set[str]:
    """「第2回・PDF p.51, 52」のような引用を {"2:51", "2:52"} にする。"""
    cited = set()
    for lecture, numbers in re.findall(r"第\s*(\d+)\s*回[・\s]*PDF\s*p\.?\s*([\d０-９,，、\sp.\-〜–]+)", answer):
        cited.update(f"{lecture}:{int(n)}" for n in re.findall(r"\d+", numbers))
    return cited


def retrieved_pages(result) -> tuple[set[str], int]:
    pages, calls = set(), 0
    for message in result.all_messages():
        for part in message.parts:
            if isinstance(part, ToolReturnPart):
                calls += 1
                pages.update(f"{r['lecture']}:{r['page']}" for r in json.loads(part.content).get("results", []))
    return pages, calls


def run_once(mode: str, question: dict) -> dict:
    instructions, tool, top_k = MODES[mode]
    retrieval.RAG_TOP_K = top_k
    for attempt in range(6):
        try:
            started = time.perf_counter()
            with agent_module.agent.override(instructions=instructions, tools=[tool]):
                result = agent_module.agent.run_sync(question["question"], model=agent_module.build_model())
            elapsed = time.perf_counter() - started
            break
        except ModelHTTPError as e:
            if e.status_code not in (429, 500, 503) or attempt == 5:
                raise
            time.sleep(15 * (attempt + 1))
    answer = str(result.output)
    pages, calls = retrieved_pages(result)
    cited = cited_pages(answer)
    gold = set(question["gold"])
    return {
        "mode": mode, "id": question["id"], "answer": answer, "tool_calls": calls,
        "retrieved": sorted(pages), "cited": sorted(cited),
        "gold_retrieved": len(gold & pages), "gold_cited": len(gold & cited), "gold_total": len(gold),
        "unsupported_citations": sorted(cited - pages),
        "keywords_ok": all(any(word in answer for word in group) for group in question["must"]),
        "seconds": round(elapsed, 2), "input_tokens": result.usage.input_tokens,
        "output_tokens": result.usage.output_tokens, "requests": result.usage.requests,
        "cost_usd": None if result.usage.cost is None else float(result.usage.cost),
    }


def summarize(runs: list[dict]) -> dict:
    gold = sum(r["gold_total"] for r in runs) or 1
    return {
        "runs": len(runs),
        "gold_retrieved_rate": round(sum(r["gold_retrieved"] for r in runs) / gold, 3),
        "gold_cited_rate": round(sum(r["gold_cited"] for r in runs) / gold, 3),
        "keywords_ok_rate": round(sum(r["keywords_ok"] for r in runs) / len(runs), 3),
        "unsupported_citation_runs": sum(bool(r["unsupported_citations"]) for r in runs),
        "median_seconds": statistics.median(r["seconds"] for r in runs),
        "mean_input_tokens": round(statistics.mean(r["input_tokens"] for r in runs)),
        "mean_tool_calls": round(statistics.mean(r["tool_calls"] for r in runs), 2),
        "total_cost_usd": None if any(r["cost_usd"] is None for r in runs)
        else round(sum(r["cost_usd"] for r in runs), 6),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--modes", nargs="+", choices=MODES, default=list(MODES))
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    questions = [json.loads(line) for line in QUESTIONS.read_text(encoding="utf-8").splitlines()]
    runs = []
    for repeat in range(args.repeats):
        for question in questions:
            for mode in args.modes:
                runs.append({"repeat": repeat, **run_once(mode, question)})
                print(f"{repeat} {question['id']} {mode}", flush=True)
                args.out.write_text(json.dumps({"model": MODEL, "runs": runs}, ensure_ascii=False, indent=1), encoding="utf-8")
    summary = {mode: summarize([r for r in runs if r["mode"] == mode]) for mode in args.modes}
    args.out.write_text(json.dumps({"model": MODEL, "summary": summary, "runs": runs}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
