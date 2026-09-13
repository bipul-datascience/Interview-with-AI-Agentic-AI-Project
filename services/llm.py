"""Groq client and structured-output helpers for the model-driven workflow."""

from __future__ import annotations

import json
import os
from typing import TypeVar

from dotenv import load_dotenv
from groq import Groq
from pydantic import BaseModel

load_dotenv()
ModelT = TypeVar("ModelT", bound=BaseModel)


class LLMConfigurationError(RuntimeError):
    pass


def _client() -> Groq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise LLMConfigurationError("GROQ_API_KEY is missing. Add it to your local .env file and restart Streamlit.")
    return Groq(api_key=api_key)


def structured_completion(*, system: str, user: str, schema: type[ModelT], temperature: float = 0.2) -> ModelT:
    response = _client().chat.completions.create(
        model=os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
        temperature=temperature,
        response_format={"type": "json_schema", "json_schema": {"name": schema.__name__.lower(), "strict": True, "schema": schema.model_json_schema()}},
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
    )
    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("The model returned an empty response. Please try again.")
    return schema.model_validate(json.loads(content))
