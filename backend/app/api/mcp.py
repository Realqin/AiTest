from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.store.memory_db import db


router = APIRouter()


class MCPToolIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1)
    endpoint: str = Field(min_length=1)


@router.get("/tools")
async def list_tools() -> list[dict]:
    return list(db.mcp_tools.values())


@router.post("/tools")
async def register_tool(payload: MCPToolIn) -> dict:
    tool_id = db.new_id("mcp_tools")
    record = {
        "id": tool_id,
        "name": payload.name,
        "description": payload.description,
        "endpoint": payload.endpoint,
    }
    db.mcp_tools[tool_id] = db.clone(record)
    return record


@router.delete("/tools/{tool_id}")
async def unregister_tool(tool_id: str) -> dict:
    if tool_id not in db.mcp_tools:
        raise HTTPException(status_code=404, detail="Tool not found")
    del db.mcp_tools[tool_id]
    return {"ok": True}
