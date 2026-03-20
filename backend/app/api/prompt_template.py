from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.store.memory_db import db, now_iso


router = APIRouter()


class PromptTemplateIn(BaseModel):
    prompt_type: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)
    content: str = Field(default="", max_length=20000)
    base_content: str = Field(default="", max_length=10000)
    response_type: str = Field(default="", max_length=100)
    response_format: str = Field(default="", max_length=10000)
    remark: str = Field(default="", max_length=200)
    enabled: bool = True
    is_default: bool = False
    is_preset: bool = False


class TogglePayload(BaseModel):
    enabled: bool


def _normalize_prompt_text(value: str) -> str:
    text = str(value or "")
    if "\\" not in text:
        return text
    return (
        text.replace("\\r\\n", "\n")
        .replace("\\n", "\n")
        .replace("\\t", "\t")
        .replace('\\"', '"')
        .replace("\\'", "'")
    )


def _compose_prompt_content(base_content: str, response_type: str, response_format: str) -> str:
    sections = [str(base_content or "").strip()]
    if response_type:
        sections.append(f"返回类型：{response_type}")
    if response_format:
        sections.append(f"返回格式：\n{response_format}")
    return "\n\n".join([section for section in sections if section]).strip()


def _resolve_prompt_fields(payload: dict) -> tuple[str, str, str, str]:
    raw_content = _normalize_prompt_text(payload.get("content", ""))
    base_content = _normalize_prompt_text(payload.get("base_content", "")) or raw_content
    response_type = str(payload.get("response_type", "") or "").strip()
    response_format = _normalize_prompt_text(payload.get("response_format", ""))
    rendered_content = _compose_prompt_content(base_content, response_type, response_format)
    return base_content, response_type, response_format, rendered_content


def _serialize_prompt_template(prompt: dict) -> dict:
    result = db.clone(prompt)
    base_content, response_type, response_format, rendered_content = _resolve_prompt_fields(result)
    result["base_content"] = base_content
    result["response_type"] = response_type
    result["response_format"] = response_format
    result["content"] = rendered_content
    result["is_preset"] = bool(result.get("is_preset", False))
    return result


def _is_json_response_type(value: str) -> bool:
    return value in {"json-object", "json-array"}


def _unset_defaults(prompt_type: str, current_id: str) -> None:
    for prompt_id, prompt in db.prompt_templates.items():
        if prompt_id != current_id and prompt.get("prompt_type") == prompt_type and prompt.get("is_default"):
            prompt["is_default"] = False
            prompt["updated_at"] = now_iso()


@router.get("")
async def list_prompt_templates() -> list[dict]:
    items = sorted(db.prompt_templates.values(), key=lambda item: item.get("created_at", ""))
    return [_serialize_prompt_template(item) for item in items]


@router.post("")
async def create_prompt_template(payload: PromptTemplateIn) -> dict:
    prompt_id = db.new_id("prompt_templates")
    timestamp = now_iso()
    base_content, response_type, response_format, rendered_content = _resolve_prompt_fields(payload.model_dump())
    record = {
        "id": prompt_id,
        "prompt_type": payload.prompt_type,
        "name": payload.name,
        "description": payload.description,
        "content": rendered_content,
        "base_content": base_content,
        "response_type": response_type,
        "response_format": response_format,
        "remark": payload.remark,
        "enabled": payload.enabled,
        "is_default": payload.is_default,
        "is_preset": payload.is_preset,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    db.prompt_templates[prompt_id] = db.clone(record)
    if payload.is_default:
        _unset_defaults(payload.prompt_type, prompt_id)
    return _serialize_prompt_template(record)


@router.put("/{prompt_id}")
async def update_prompt_template(prompt_id: str, payload: PromptTemplateIn) -> dict:
    prompt = db.prompt_templates.get(prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt template not found")

    is_preset = bool(prompt.get("is_preset", False))

    base_content, response_type, response_format, rendered_content = _resolve_prompt_fields(payload.model_dump())
    prompt.update(
        {
            "prompt_type": payload.prompt_type,
            "name": payload.name,
            "description": payload.description,
            "content": rendered_content,
            "base_content": base_content,
            "response_type": response_type,
            "response_format": response_format,
            "remark": payload.remark,
            "enabled": payload.enabled,
            "is_default": payload.is_default,
            "is_preset": is_preset,
            "updated_at": now_iso(),
        }
    )
    if payload.is_default:
        _unset_defaults(payload.prompt_type, prompt_id)
    return _serialize_prompt_template(prompt)


@router.post("/{prompt_id}/toggle")
async def toggle_prompt_template(prompt_id: str, payload: TogglePayload) -> dict:
    prompt = db.prompt_templates.get(prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt template not found")
    prompt["enabled"] = payload.enabled
    prompt["updated_at"] = now_iso()
    return prompt


@router.delete("/{prompt_id}")
async def delete_prompt_template(prompt_id: str) -> dict:
    if prompt_id not in db.prompt_templates:
        raise HTTPException(status_code=404, detail="Prompt template not found")
    del db.prompt_templates[prompt_id]
    return {"ok": True}
