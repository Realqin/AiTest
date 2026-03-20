from fastapi import APIRouter

from app.store.memory_db import db


router = APIRouter()


@router.get("")
async def list_dictionaries(group: str | None = None) -> dict:
    items = [item for item in db.dictionaries.values() if item.get("enabled", True)]
    if group:
        items = [item for item in items if item.get("group") == group]
    items.sort(key=lambda item: (item.get("group", ""), item.get("sort_order", 0), item.get("created_at", ""), item.get("id", "")))
    return {"items": [db.clone(item) for item in items]}
