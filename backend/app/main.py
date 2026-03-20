from pathlib import Path

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api import agent_config, ai, dictionaries, llm_config, mcp, projects, prompt_template, requirements, test_cases


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


app = FastAPI(
    title="AiTest API",
    version="0.1.0",
    description="All APIs are managed by OpenAPI Swagger.",
    docs_url="/swagger",
    redoc_url=None,
    openapi_url="/openapi.json",
    openapi_tags=[
        {"name": "projects", "description": "Project CRUD and query"},
        {"name": "requirements", "description": "Requirement CRUD, import and preview"},
        {"name": "test-cases", "description": "Test case CRUD and requirement mapping"},
        {"name": "agents", "description": "Agent role and prompt configuration"},
        {"name": "llm-configs", "description": "LLM configuration management"},
        {"name": "prompt-templates", "description": "Prompt template management"},
        {"name": "dictionaries", "description": "Dictionary data management"},
        {"name": "ai", "description": "AI review, generation, and chat"},
        {"name": "mcp", "description": "MCP tool registration and management"},
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

storage_dir = Path(__file__).resolve().parent / "storage"
app.mount("/assets", StaticFiles(directory=storage_dir), name="assets")


@app.get("/docs", include_in_schema=False)
async def docs_redirect() -> RedirectResponse:
    return RedirectResponse(url="/swagger")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
app.include_router(requirements.router, prefix="/api/requirements", tags=["requirements"])
app.include_router(test_cases.router, prefix="/api/test-cases", tags=["test-cases"])
app.include_router(ai.router, prefix="/api/ai", tags=["ai"])
app.include_router(agent_config.router, prefix="/api/agents", tags=["agents"])
app.include_router(llm_config.router, prefix="/api/llm-configs", tags=["llm-configs"])
app.include_router(prompt_template.router, prefix="/api/prompts", tags=["prompt-templates"])
app.include_router(dictionaries.router, prefix="/api/dictionaries", tags=["dictionaries"])
app.include_router(mcp.router, prefix="/api/mcp", tags=["mcp"])
