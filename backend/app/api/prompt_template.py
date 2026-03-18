from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.store.memory_db import db, now_iso


router = APIRouter()


class PromptTemplateIn(BaseModel):
    prompt_type: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)
    content: str = Field(min_length=1, max_length=10000)
    remark: str = Field(default="", max_length=200)
    enabled: bool = True
    is_default: bool = False


class TogglePayload(BaseModel):
    enabled: bool


def _unset_defaults(prompt_type: str, current_id: str) -> None:
    for prompt_id, prompt in db.prompt_templates.items():
        if prompt_id != current_id and prompt.get("prompt_type") == prompt_type and prompt.get("is_default"):
            prompt["is_default"] = False
            prompt["updated_at"] = now_iso()


@router.get("")
async def list_prompt_templates() -> list[dict]:
    return sorted(db.prompt_templates.values(), key=lambda item: item.get("created_at", ""))


@router.post("")
async def create_prompt_template(payload: PromptTemplateIn) -> dict:
    prompt_id = db.new_id("prompt_templates")
    timestamp = now_iso()
    record = {
        "id": prompt_id,
        "prompt_type": payload.prompt_type,
        "name": payload.name,
        "description": payload.description,
        "content": payload.content,
        "remark": payload.remark,
        "enabled": payload.enabled,
        "is_default": payload.is_default,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    db.prompt_templates[prompt_id] = db.clone(record)
    if payload.is_default:
        _unset_defaults(payload.prompt_type, prompt_id)
    return record


@router.put("/{prompt_id}")
async def update_prompt_template(prompt_id: str, payload: PromptTemplateIn) -> dict:
    prompt = db.prompt_templates.get(prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt template not found")
    prompt.update(
        {
            "prompt_type": payload.prompt_type,
            "name": payload.name,
            "description": payload.description,
            "content": payload.content,
            "remark": payload.remark,
            "enabled": payload.enabled,
            "is_default": payload.is_default,
            "updated_at": now_iso(),
        }
    )
    if payload.is_default:
        _unset_defaults(payload.prompt_type, prompt_id)
    return prompt


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
