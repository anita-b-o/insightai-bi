from __future__ import annotations

import logging
import time
from fastapi import HTTPException, status
from openai import APIConnectionError, APIStatusError, APITimeoutError, AsyncOpenAI, OpenAIError

from app.core.config import settings
from app.core.observability import log_event

logger = logging.getLogger("app.openai")
client = AsyncOpenAI(api_key=settings.openai_api_key, timeout=settings.openai_timeout_seconds)


def extract_text(response) -> str | None:
    try:
        if hasattr(response, "output_text") and response.output_text:
            text = str(response.output_text).strip()
            if text:
                return text

        texts: list[str] = []
        for item in getattr(response, "output", []) or []:
            if getattr(item, "type", None) == "message":
                for content in getattr(item, "content", []) or []:
                    if getattr(content, "type", None) == "output_text":
                        text = str(getattr(content, "text", "")).strip()
                        if text:
                            texts.append(text)

        extracted = "\n".join(texts).strip()
        return extracted or None
    except Exception:
        return None


def _serialize_response(response) -> object:
    if hasattr(response, "model_dump"):
        try:
            return response.model_dump()
        except Exception:
            pass
    return response


def _classify_openai_error(exc: Exception) -> tuple[str, str]:
    if isinstance(exc, APITimeoutError):
        return ("openai_timeout", "transient")
    if isinstance(exc, APIConnectionError):
        return ("openai_connection_error", "transient")
    if isinstance(exc, APIStatusError):
        status_code = getattr(exc, "status_code", None)
        if status_code == 429:
            return ("openai_rate_limit", "transient")
        if status_code and status_code >= 500:
            return ("openai_upstream_error", "transient")
        return ("openai_status_error", "permanent")
    return ("openai_unknown_error", "permanent")


async def request_openai_text(
    system_prompt: str,
    user_prompt: str,
    *,
    error_prefix: str,
) -> str:
    if not settings.openai_api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OPENAI_API_KEY is not configured",
        )

    openai_input = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    prompt_chars = len(system_prompt) + len(user_prompt)
    attempts = max(1, settings.openai_max_retries + 1)
    response = None

    for attempt in range(1, attempts + 1):
        started_at = time.perf_counter()
        try:
            log_event(
                logger,
                logging.INFO,
                "openai_request_started",
                model=settings.openai_model,
                attempt=attempt,
                prompt_chars=prompt_chars,
            )
            response = await client.responses.create(
                model=settings.openai_model,
                input=openai_input,
            )
            log_event(
                logger,
                logging.INFO,
                "openai_request_succeeded",
                model=settings.openai_model,
                attempt=attempt,
                duration_ms=int((time.perf_counter() - started_at) * 1000),
                response_id=getattr(response, "id", None),
            )
            break
        except (APIStatusError, APIConnectionError, APITimeoutError) as exc:
            error_code, error_class = _classify_openai_error(exc)
            log_event(
                logger,
                logging.WARNING,
                "openai_request_failed",
                model=settings.openai_model,
                attempt=attempt,
                duration_ms=int((time.perf_counter() - started_at) * 1000),
                error_code=error_code,
                error_class=error_class,
                status_code=getattr(exc, "status_code", None),
            )
            if error_class == "transient" and attempt < attempts:
                continue
            detail = error_prefix
            if isinstance(exc, APIStatusError) and getattr(exc, "message", None):
                detail = f"OpenAI API error: {exc.message}"
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail) from exc
        except OpenAIError as exc:
            log_event(
                logger,
                logging.ERROR,
                "openai_request_failed",
                model=settings.openai_model,
                attempt=attempt,
                duration_ms=int((time.perf_counter() - started_at) * 1000),
                error_code="openai_unknown_error",
                error_class="permanent",
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"{error_prefix}: {exc}",
            ) from exc

    output_text = extract_text(response)
    if not output_text:
        log_event(
            logger,
            logging.ERROR,
            "openai_empty_response",
            model=settings.openai_model,
            response_id=getattr(response, "id", None),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AI returned no usable content. Check logs.",
        )
    return output_text
