from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.store.memory_db import db, now_iso


router = APIRouter()


class ProjectIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=1000)
    creator: str = Field(default="admin", max_length=50)


@router.get("")
async def list_projects(
    keyword: str = "",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
) -> dict:
    items = list(db.projects.values())
    key = keyword.strip().lower()
    if key:
        items = [
            item
            for item in items
            if key in item["name"].lower() or key in item["description"].lower()
        ]

    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    page_items = items[start:end]
    return {"items": page_items, "total": total, "page": page, "page_size": page_size}


@router.post("")
async def create_project(payload: ProjectIn) -> dict:
    project_id = db.new_id("projects")
    record = {
        "id": project_id,
        "name": payload.name,
        "description": payload.description,
        "creator": payload.creator,
        "created_at": now_iso(),
    }
    db.projects[project_id] = db.clone(record)
    return record


@router.put("/{project_id}")
async def update_project(project_id: str, payload: ProjectIn) -> dict:
    project = db.projects.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    project.update(
        {
            "name": payload.name,
            "description": payload.description,
            "creator": payload.creator,
        }
    )
    return project


@router.delete("/{project_id}")
async def delete_project(project_id: str) -> dict:
    if project_id not in db.projects:
        raise HTTPException(status_code=404, detail="Project not found")
    del db.projects[project_id]
    return {"ok": True}
