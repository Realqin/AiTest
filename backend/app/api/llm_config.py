from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.llm_client import fetch_openai_compatible_models, test_openai_compatible_connection
from app.store.memory_db import db, now_iso


router = APIRouter()


class LlmConfigCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    api_url: str = Field(min_length=1, max_length=500)
    api_key: str = Field(min_length=1, max_length=500)
    model_name: str = Field(min_length=1, max_length=100)
    context_limit: int = Field(default=128000, ge=1)
    vision_enabled: bool = False
    stream_enabled: bool = True
    enabled: bool = False


class LlmConfigUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    api_url: str = Field(min_length=1, max_length=500)
    api_key: str = Field(default="", max_length=500)
    model_name: str = Field(min_length=1, max_length=100)
    context_limit: int = Field(default=128000, ge=1)
    vision_enabled: bool = False
    stream_enabled: bool = True
    enabled: bool = False


class TogglePayload(BaseModel):
    enabled: bool


class LlmConnectionTestIn(BaseModel):
    api_url: str = Field(min_length=1, max_length=500)
    api_key: str = Field(default="", max_length=500)
    model_name: str = Field(min_length=1, max_length=100)
    config_id: str | None = None


class LlmModelsFetchIn(BaseModel):
    api_url: str = Field(min_length=1, max_length=500)
    api_key: str = Field(default="", max_length=500)
    config_id: str | None = None



def _serialize(record: dict) -> dict:
    payload = db.clone(record)
    payload["has_api_key"] = bool(payload.get("api_key"))
    payload["api_key"] = ""
    return payload



def _deactivate_other_configs(active_id: str) -> None:
    for config_id, config in db.llm_configs.items():
        if config_id != active_id and config.get("enabled"):
            config["enabled"] = False
            config["updated_at"] = now_iso()


@router.get("")
async def list_llm_configs() -> list[dict]:
    items = sorted(db.llm_configs.values(), key=lambda item: item.get("created_at", ""))
    return [_serialize(item) for item in items]


@router.post("")
async def create_llm_config(payload: LlmConfigCreate) -> dict:
    config_id = db.new_id("llm_configs")
    timestamp = now_iso()
    record = {
        "id": config_id,
        "name": payload.name,
        "api_url": payload.api_url,
        "api_key": payload.api_key,
        "model_name": payload.model_name,
        "context_limit": payload.context_limit,
        "vision_enabled": payload.vision_enabled,
        "stream_enabled": payload.stream_enabled,
        "enabled": payload.enabled,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    db.llm_configs[config_id] = db.clone(record)
    if payload.enabled:
        _deactivate_other_configs(config_id)
    return _serialize(record)


@router.post("/test-connection")
async def test_llm_connection(payload: LlmConnectionTestIn) -> dict:
    api_key = payload.api_key.strip()
    if not api_key and payload.config_id:
        record = db.llm_configs.get(payload.config_id)
        if not record:
            raise HTTPException(status_code=404, detail="LLM config not found")
        api_key = record.get("api_key", "")

    return await test_openai_compatible_connection(
        api_url=payload.api_url,
        api_key=api_key,
        model_name=payload.model_name,
    )


@router.post("/models")
async def fetch_llm_models(payload: LlmModelsFetchIn) -> dict:
    api_key = payload.api_key.strip()
    if not api_key and payload.config_id:
        record = db.llm_configs.get(payload.config_id)
        if not record:
            raise HTTPException(status_code=404, detail="LLM config not found")
        api_key = record.get("api_key", "")

    models = await fetch_openai_compatible_models(
        api_url=payload.api_url,
        api_key=api_key,
    )
    return {"items": models}


@router.put("/{config_id}")
async def update_llm_config(config_id: str, payload: LlmConfigUpdate) -> dict:
    config = db.llm_configs.get(config_id)
    if not config:
        raise HTTPException(status_code=404, detail="LLM config not found")

    config.update(
        {
            "name": payload.name,
            "api_url": payload.api_url,
            "model_name": payload.model_name,
            "context_limit": payload.context_limit,
            "vision_enabled": payload.vision_enabled,
            "stream_enabled": payload.stream_enabled,
            "enabled": payload.enabled,
            "updated_at": now_iso(),
        }
    )
    if payload.api_key:
        config["api_key"] = payload.api_key
    if payload.enabled:
        _deactivate_other_configs(config_id)
    return _serialize(config)


@router.post("/{config_id}/toggle")
async def toggle_llm_config(config_id: str, payload: TogglePayload) -> dict:
    config = db.llm_configs.get(config_id)
    if not config:
        raise HTTPException(status_code=404, detail="LLM config not found")
    config["enabled"] = payload.enabled
    config["updated_at"] = now_iso()
    if payload.enabled:
        _deactivate_other_configs(config_id)
    return _serialize(config)


@router.delete("/{config_id}")
async def delete_llm_config(config_id: str) -> dict:
    if config_id not in db.llm_configs:
        raise HTTPException(status_code=404, detail="LLM config not found")
    del db.llm_configs[config_id]
    return {"ok": True}
