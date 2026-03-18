from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.store.memory_db import db


router = APIRouter()


class AgentConfigIn(BaseModel):
    role: str = Field(min_length=1, max_length=100)
    prompt_template: str = Field(min_length=1)
    model_policy: str = Field(default="balanced")
    enabled: bool = True


@router.get("")
async def list_agent_configs() -> list[dict]:
    return list(db.agent_configs.values())


@router.post("")
async def create_agent_config(payload: AgentConfigIn) -> dict:
    config_id = db.new_id("agent_configs")
    record = {
        "id": config_id,
        "role": payload.role,
        "prompt_template": payload.prompt_template,
        "model_policy": payload.model_policy,
        "enabled": payload.enabled,
    }
    db.agent_configs[config_id] = db.clone(record)
    return record


@router.put("/{config_id}")
async def update_agent_config(config_id: str, payload: AgentConfigIn) -> dict:
    config = db.agent_configs.get(config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Agent config not found")
    config.update(
        {
            "role": payload.role,
            "prompt_template": payload.prompt_template,
            "model_policy": payload.model_policy,
            "enabled": payload.enabled,
        }
    )
    return config


@router.delete("/{config_id}")
async def delete_agent_config(config_id: str) -> dict:
    if config_id not in db.agent_configs:
        raise HTTPException(status_code=404, detail="Agent config not found")
    del db.agent_configs[config_id]
    return {"ok": True}
