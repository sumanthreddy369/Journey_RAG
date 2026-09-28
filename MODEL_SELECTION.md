# Local model selection

## Configured behavior

`query.py` and `learning.py` read `JOURNEY_LLM_MODEL`. When it is unset, both
use `llama3.2`. This keeps the current default stable while allowing another
installed Ollama model to be selected without code changes.

```powershell
$env:JOURNEY_LLM_MODEL = "qwen3:0.6b"
$env:JOURNEY_RETRIEVAL_MODE = "hybrid"
.\venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8002
```

## Benchmark command

```powershell
.\venv\Scripts\python.exe model_benchmark.py `
  --models llama3.2:latest qwen3:0.6b `
  --prompt "In one sentence, define a MATLAB scalar."
```

The script writes latency and response-character counts to
`benchmark_results/model_benchmark.json`. The directory is ignored by Git.
It does not calculate groundedness, faithfulness, or quality; a benchmark
winner must not be claimed from latency alone.

## Status

| Item | Status |
| --- | --- |
| Default Llama selection | Complete. |
| Qwen selection through environment variable | Complete. |
| Local timing utility | Complete. |
| Completed model comparison results | Partial; save a full run before reporting results. |
| Fine-tuning, LoRA, QLoRA | Target, not built yet. |
| vLLM, SGLang, llama.cpp serving | Target, not built yet. |
