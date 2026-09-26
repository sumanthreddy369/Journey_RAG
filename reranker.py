"""Optional ONNX Runtime cross-encoder reranking for Journey RAG.

Export a compatible Hugging Face sequence-classification model to ONNX and set
``JOURNEY_ONNX_RERANKER_DIR`` to its directory.  When unset, the application
uses Qdrant's vector ranking unchanged.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Protocol


class Tokenizer(Protocol):
    def __call__(self, questions: list[str], passages: list[str], **kwargs: Any) -> dict[str, Any]: ...


class Session(Protocol):
    def get_inputs(self) -> list[Any]: ...
    def run(self, output_names: list[str] | None, inputs: dict[str, Any]) -> list[Any]: ...


class OnnxCrossEncoderReranker:
    """Ranks Qdrant candidates with a locally stored ONNX cross-encoder."""

    def __init__(self, model_dir: str | Path, *, tokenizer: Tokenizer | None = None, session: Session | None = None):
        self.model_dir = Path(model_dir)
        if tokenizer is None or session is None:
            try:
                import onnxruntime as ort
                from transformers import AutoTokenizer
            except ImportError as exc:
                raise RuntimeError(
                    "Install the optional reranker dependencies: pip install onnxruntime transformers numpy"
                ) from exc

            tokenizer = tokenizer or AutoTokenizer.from_pretrained(self.model_dir)
            model_path = self._find_model_path()
            session = session or ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])

        self.tokenizer = tokenizer
        self.session = session

    def _find_model_path(self) -> Path:
        for candidate in (self.model_dir / "model.onnx", self.model_dir / "onnx" / "model.onnx"):
            if candidate.is_file():
                return candidate
        raise FileNotFoundError(
            f"No model.onnx found under {self.model_dir}. Export a sequence-classification reranker first."
        )

    def score(self, question: str, passages: list[str]) -> list[float]:
        if not passages:
            return []
        encoded = self.tokenizer(
            [question] * len(passages),
            passages,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="np",
        )
        expected_inputs = {input_.name for input_ in self.session.get_inputs()}
        inputs = {name: value for name, value in encoded.items() if name in expected_inputs}
        logits = self.session.run(None, inputs)[0]
        # Most cross-encoders emit [batch, 1].  Support a flat output too.
        return [float(row[0] if hasattr(row, "__len__") else row) for row in logits]

    def rerank(self, question: str, candidates: list[Any], top_k: int) -> list[Any]:
        texts = [str(candidate.payload.get("text", "")) for candidate in candidates]
        scores = self.score(question, texts)
        ordered = sorted(zip(scores, candidates), key=lambda item: item[0], reverse=True)
        return [candidate for _, candidate in ordered[:top_k]]


def configured_reranker() -> OnnxCrossEncoderReranker | None:
    """Return the configured local reranker, or None when the feature is disabled."""
    model_dir = os.getenv("JOURNEY_ONNX_RERANKER_DIR")
    return OnnxCrossEncoderReranker(model_dir) if model_dir else None
