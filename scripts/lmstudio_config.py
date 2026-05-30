from __future__ import annotations

import os
from dataclasses import dataclass


DEFAULT_BASE_URL = "http://127.0.0.1:1234/v1"
DEFAULT_API_KEY = "lm-studio"
CHAT_READINESS_PROMPT = "Reply with the word OK and nothing else."


@dataclass(frozen=True)
class LMStudioSettings:
    base_url: str
    api_key: str
    chat_model: str
    embedding_model: str
    max_tokens: int
    temperature: float


def _loaded_model_help(settings: LMStudioSettings, models: list[str]) -> str:
    loaded = "\n".join(f"  - {model}" for model in models) or "  <none>"
    return f"""LM Studio is reachable at {settings.base_url}, but the configured models are not ready.

Loaded models reported by LM Studio:
{loaded}

Load both a chat model and an embedding-capable model in the LM Studio Developer page, or with:

  lms server start
  lms load "$LMSTUDIO_CHAT_MODEL" --identifier "$LMSTUDIO_CHAT_MODEL"
  lms load "$LMSTUDIO_EMBEDDING_MODEL" --identifier "$LMSTUDIO_EMBEDDING_MODEL"

Then rerun:

  ./scripts/dnd-beyond-basic --check-lmstudio
"""


def normalize_base_url(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    if normalized.endswith("/v1"):
        return normalized
    return f"{normalized}/v1"


def get_lmstudio_settings(require_models: bool = True) -> LMStudioSettings:
    chat_model = os.getenv("LMSTUDIO_CHAT_MODEL")
    embedding_model = os.getenv("LMSTUDIO_EMBEDDING_MODEL")

    if require_models and not chat_model:
        raise RuntimeError(
            "Set LMSTUDIO_CHAT_MODEL to the model identifier loaded in LM Studio."
        )
    if require_models and not embedding_model:
        raise RuntimeError(
            "Set LMSTUDIO_EMBEDDING_MODEL to an embedding-capable model in LM Studio."
        )

    return LMStudioSettings(
        base_url=normalize_base_url(os.getenv("LMSTUDIO_BASE_URL", DEFAULT_BASE_URL)),
        api_key=os.getenv("LMSTUDIO_API_KEY", DEFAULT_API_KEY),
        chat_model=chat_model or "",
        embedding_model=embedding_model or "",
        max_tokens=int(os.getenv("LMSTUDIO_MAX_TOKENS", "1024")),
        temperature=float(os.getenv("LMSTUDIO_TEMPERATURE", "0.1")),
    )


def _make_client(settings: LMStudioSettings | None = None):
    from openai import OpenAI

    settings = settings or get_lmstudio_settings(require_models=False)
    return OpenAI(base_url=settings.base_url, api_key=settings.api_key)


def response_to_text(response) -> str:
    content = getattr(response, "content", response)
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                parts.append(item.get("text", ""))
        return "\n".join(part for part in parts if part).strip()
    return str(content).strip() if content is not None else ""


def make_llm(settings: LMStudioSettings | None = None):
    from langchain_openai import ChatOpenAI

    settings = settings or get_lmstudio_settings()
    return ChatOpenAI(
        model=settings.chat_model,
        base_url=settings.base_url,
        api_key=settings.api_key,
        max_tokens=settings.max_tokens,
        temperature=settings.temperature,
    )


def make_embeddings(settings: LMStudioSettings | None = None):
    from langchain_openai import OpenAIEmbeddings

    settings = settings or get_lmstudio_settings()
    return OpenAIEmbeddings(
        model=settings.embedding_model,
        base_url=settings.base_url,
        api_key=settings.api_key,
        check_embedding_ctx_length=False,
    )


def list_lmstudio_models(settings: LMStudioSettings | None = None) -> list[str]:
    client = _make_client(settings)
    return [model.id for model in client.models.list().data]


def require_lmstudio_ready() -> LMStudioSettings:
    settings = get_lmstudio_settings()
    try:
        models = list_lmstudio_models(settings)
    except Exception as exc:
        raise RuntimeError(
            f"Could not reach LM Studio at {settings.base_url}: {exc}"
        ) from exc

    missing_models = [
        model
        for model in (settings.chat_model, settings.embedding_model)
        if model not in models
    ]
    if missing_models:
        raise RuntimeError(
            _loaded_model_help(settings, models)
            + "\nMissing configured model(s): "
            + ", ".join(missing_models)
        )

    try:
        make_embeddings(settings).embed_query("LM Studio embedding readiness check")
    except Exception as exc:
        raise RuntimeError(
            _loaded_model_help(settings, models)
            + "\nThe embedding readiness check failed. Make sure "
            + f"{settings.embedding_model!r} is an embedding-capable model.\n"
            + f"Original error: {exc}"
        ) from exc

    try:
        chat_response = make_llm(settings).invoke(CHAT_READINESS_PROMPT)
    except Exception as exc:
        raise RuntimeError(
            _loaded_model_help(settings, models)
            + "\nThe chat readiness check failed. Make sure "
            + f"{settings.chat_model!r} is a chat-capable model.\n"
            + f"Original error: {exc}"
        ) from exc

    if not response_to_text(chat_response):
        raise RuntimeError(
            _loaded_model_help(settings, models)
            + "\nThe chat readiness check returned an empty response. Make sure "
            + f"{settings.chat_model!r} is loaded as a chat-capable model."
        )

    return settings


def print_lmstudio_check() -> None:
    settings = get_lmstudio_settings(require_models=False)
    print(f"LM Studio base URL: {settings.base_url}", flush=True)

    try:
        models = list_lmstudio_models(settings)
    except Exception as exc:
        raise SystemExit(f"Could not reach LM Studio at {settings.base_url}: {exc}")

    if not models:
        print(_loaded_model_help(settings, models))
        return

    print("Models visible to the local server:")
    for model in models:
        print(f"  - {model}")

    if not os.getenv("LMSTUDIO_CHAT_MODEL"):
        print("Set LMSTUDIO_CHAT_MODEL to one of the chat model identifiers above.")
    if not os.getenv("LMSTUDIO_EMBEDDING_MODEL"):
        print(
            "Set LMSTUDIO_EMBEDDING_MODEL to an embedding-capable model identifier."
        )

    if os.getenv("LMSTUDIO_CHAT_MODEL") and os.getenv("LMSTUDIO_EMBEDDING_MODEL"):
        try:
            require_lmstudio_ready()
        except RuntimeError as exc:
            raise SystemExit(str(exc)) from exc
        print("LM Studio chat and embedding models are ready.")
