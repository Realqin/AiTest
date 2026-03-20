import json
import logging
import re
from typing import Any

import httpx
from fastapi import HTTPException

from app.store.memory_db import db


JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)
logger = logging.getLogger("aitest.llm")


def _chat_completions_url(api_url: str) -> str:
    base = (api_url or "").strip().rstrip("/")
    if not base:
        raise HTTPException(status_code=400, detail="LLM API URL is required")
    if base.endswith("/chat/completions"):
        return base
    return f"{base}/chat/completions"




def _models_url(api_url: str) -> str:
    base = (api_url or "").strip().rstrip("/")
    if not base:
        raise HTTPException(status_code=400, detail="LLM API URL is required")
    if base.endswith("/models"):
        return base
    return f"{base}/models"

def _extract_message_text(message: Any) -> str:
    if isinstance(message, str):
        return message
    if isinstance(message, list):
        parts: list[str] = []
        for item in message:
            if isinstance(item, str):
                parts.append(item)
                continue
            if not isinstance(item, dict):
                continue
            if item.get("type") == "text":
                parts.append(str(item.get("text", "")))
        return "\n".join(part for part in parts if part).strip()
    return ""


def _try_load_json(text: str) -> dict[str, Any] | None:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _extract_balanced_json_object(text: str) -> str | None:
    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escape = False

    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
            continue
        if char == "{":
            depth += 1
            continue
        if char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]

    return None


def _escape_raw_newlines_in_strings(text: str) -> str:
    chars: list[str] = []
    in_string = False
    escape = False

    for char in text:
        if in_string:
            if escape:
                chars.append(char)
                escape = False
                continue
            if char == "\\":
                chars.append(char)
                escape = True
                continue
            if char == '"':
                chars.append(char)
                in_string = False
                continue
            if char == "\n":
                chars.append("\\n")
                continue
            if char == "\r":
                chars.append("\\r")
                continue
            if char == "\t":
                chars.append("\\t")
                continue
            chars.append(char)
            continue

        chars.append(char)
        if char == '"':
            in_string = True

    return "".join(chars)


def _strip_trailing_commas(text: str) -> str:
    return re.sub(r",\s*([}\]])", r"\1", text)


async def call_chat_completion(
    *,
    api_url: str,
    api_key: str,
    model_name: str,
    messages: list[dict[str, str]],
    temperature: float = 0.2,
    max_tokens: int = 1200,
    timeout: float = 90.0,
) -> dict:
    if not api_key:
        raise HTTPException(status_code=400, detail="LLM API Key is required")
    if not model_name:
        raise HTTPException(status_code=400, detail="LLM model name is required")

    url = _chat_completions_url(api_url)
    payload = {
        "model": model_name,
        "messages": messages,
        "stream": False,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    logger.info(
        "llm_request_start url=%s model=%s message_count=%s temperature=%s max_tokens=%s timeout=%s",
        url,
        model_name,
        len(messages),
        temperature,
        max_tokens,
        timeout,
    )

    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            logger.info(
                "llm_request_success url=%s model=%s status_code=%s",
                url,
                model_name,
                response.status_code,
            )
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text or f"HTTP {exc.response.status_code}"
        logger.exception(
            "llm_request_http_error url=%s model=%s status_code=%s detail=%s",
            url,
            model_name,
            exc.response.status_code,
            detail,
        )
        raise HTTPException(status_code=502, detail=f"LLM request failed: {detail}") from exc
    except httpx.HTTPError as exc:
        logger.exception("llm_request_connection_error url=%s model=%s", url, model_name)
        raise HTTPException(status_code=502, detail=f"LLM connection failed: {exc}") from exc

    data = response.json()
    choices = data.get("choices") or []
    if not choices:
        raise HTTPException(status_code=502, detail="LLM response has no choices")

    first_choice = choices[0] or {}
    message = (first_choice.get("message") or {}).get("content")
    content = _extract_message_text(message)
    if not content:
        raise HTTPException(status_code=502, detail="LLM response content is empty")

    logger.info(
        "llm_response_parsed model=%s content_preview=%s",
        data.get("model") or model_name,
        content[:300].replace("\n", "\\n"),
    )

    return {
        "content": content,
        "raw": data,
        "model": data.get("model") or model_name,
    }


async def test_openai_compatible_connection(*, api_url: str, api_key: str, model_name: str) -> dict:
    result = await call_chat_completion(
        api_url=api_url,
        api_key=api_key,
        model_name=model_name,
        messages=[
            {"role": "system", "content": "You are a connectivity probe. Reply with OK only."},
            {"role": "user", "content": "Return OK"},
        ],
        temperature=0,
        max_tokens=16,
        timeout=30.0,
    )
    return {
        "ok": True,
        "message": f"\u6a21\u578b\u8fde\u63a5\u6210\u529f\uff0c\u8fd4\u56de\u7ed3\u679c\uff1a{result['content'][:80]}",
        "model": result["model"],
    }


def extract_json_payload(content: str) -> dict[str, Any]:
    text = (content or "").strip()
    if not text:
        raise ValueError("empty content")

    block_match = JSON_BLOCK_RE.search(text)
    if block_match:
        text = block_match.group(1).strip()

    direct = _try_load_json(text)
    if direct is not None:
        return direct

    candidate = _extract_balanced_json_object(text)
    if candidate is None:
        logger.error("extract_json_payload_failed no_json_object_found content_preview=%s", text[:1000])
        raise ValueError("no json object found")

    repaired_candidates = [
        candidate,
        _escape_raw_newlines_in_strings(candidate),
        _strip_trailing_commas(candidate),
        _strip_trailing_commas(_escape_raw_newlines_in_strings(candidate)),
    ]

    for attempt_index, candidate_text in enumerate(repaired_candidates, start=1):
        parsed = _try_load_json(candidate_text)
        if parsed is not None:
            if attempt_index > 1:
                logger.warning(
                    "extract_json_payload_repaired attempt=%s content_preview=%s",
                    attempt_index,
                    candidate_text[:1000],
                )
            return parsed

    logger.error(
        "extract_json_payload_failed invalid_json candidate_preview=%s raw_preview=%s",
        candidate[:1000],
        text[:1000],
    )
    raise ValueError("invalid json payload from llm")


def get_active_llm_config() -> dict:
    active = next((item for item in db.llm_configs.values() if item.get("enabled")), None)
    if not active:
        raise HTTPException(status_code=400, detail="No active LLM config found")
    if not active.get("api_url") or not active.get("api_key") or not active.get("model_name"):
        raise HTTPException(status_code=400, detail="Active LLM config is incomplete")
    return active


def get_prompt_template_for_type(prompt_type: str) -> dict:
    candidates = [
        item for item in db.prompt_templates.values() if item.get("enabled") and item.get("prompt_type") == prompt_type
    ]
    if not candidates:
        raise HTTPException(status_code=400, detail=f"No enabled prompt template found for {prompt_type}")

    default_item = next((item for item in candidates if item.get("is_default")), None)
    if default_item:
        return default_item

    candidates.sort(key=lambda item: item.get("updated_at", ""), reverse=True)
    return candidates[0]


async def fetch_openai_compatible_models(*, api_url: str, api_key: str, timeout: float = 30.0) -> list[str]:
    if not api_key:
        raise HTTPException(status_code=400, detail="LLM API Key is required")

    url = _models_url(api_url)
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text or f"HTTP {exc.response.status_code}"
        raise HTTPException(status_code=502, detail=f"Fetch model list failed: {detail}") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Fetch model list failed: {exc}") from exc

    payload = response.json()
    data = payload.get("data")
    if not isinstance(data, list):
        raise HTTPException(status_code=502, detail="LLM model list response is invalid")

    models = []
    for item in data:
        if not isinstance(item, dict):
            continue
        model_id = str(item.get("id", "")).strip()
        if model_id:
            models.append(model_id)

    if not models:
        raise HTTPException(status_code=502, detail="No models returned by provider")

    return sorted(set(models))
