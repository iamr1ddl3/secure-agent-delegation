"""OpenRouter chat client (OpenAI-compatible), as in P1. Truncated or empty output is an error, never an answer."""
from __future__ import annotations

import os
import time
from pathlib import Path

import yaml

CONFIG = yaml.safe_load((Path(__file__).resolve().parents[2] / "config/models.yaml").read_text())


class LLMError(Exception):
    pass


class LLM:
    """`llm(system, user) -> text`. Keeps running totals of cost and per-call latency for the eval reports."""

    def __init__(self, model_id: str, api_key: str | None = None, *, max_tokens: int | None = None):
        from openai import OpenAI

        self.model_id = model_id
        self.max_tokens = max_tokens or CONFIG["defaults"]["max_tokens"]
        self.cost_usd, self.latencies_ms = 0.0, []
        self._client = OpenAI(api_key=api_key or os.environ["OPENROUTER_API_KEY"],
                              base_url="https://openrouter.ai/api/v1", timeout=60, max_retries=2)

    def __call__(self, system: str, user: str) -> str:
        t0 = time.perf_counter()
        try:
            r = self._client.chat.completions.create(
                model=self.model_id, temperature=CONFIG["defaults"]["temperature"], max_tokens=self.max_tokens,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                extra_body={"usage": {"include": True}})  # OpenRouter returns the dollar cost
        except Exception as e:
            raise LLMError(f"{type(e).__name__}: {str(e)[:200]}") from e
        self.latencies_ms.append((time.perf_counter() - t0) * 1000)
        self.cost_usd += float(((r.usage.model_extra or {}) if r.usage else {}).get("cost") or 0)
        choice = r.choices[0]
        if choice.finish_reason == "length":
            raise LLMError(f"output truncated at max_tokens={self.max_tokens} ({self.model_id})")
        text = (choice.message.content or "").strip()
        if not text:
            raise LLMError(f"empty completion (finish_reason={choice.finish_reason})")
        return text
