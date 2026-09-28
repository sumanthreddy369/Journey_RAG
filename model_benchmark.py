"""Small local Ollama latency benchmark for documented Journey model choices."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from time import perf_counter
from typing import Any, Callable

import ollama


def benchmark_model(model: str, prompt: str, *, chat: Callable[..., dict[str, Any]] = ollama.chat) -> dict[str, Any]:
    """Run one local chat request and return a compact, reproducible timing record."""
    started = perf_counter()
    response = chat(model=model, messages=[{"role": "user", "content": prompt}])
    elapsed = perf_counter() - started
    content = response["message"]["content"]
    return {"model": model, "latency_seconds": round(elapsed, 3), "response_characters": len(content)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark local Ollama models with the same prompt.")
    parser.add_argument("--models", nargs="+", required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--output", default="benchmark_results/model_benchmark.json")
    args = parser.parse_args()
    results = [benchmark_model(model, args.prompt) for model in args.models]
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
