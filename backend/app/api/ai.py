import asyncio
from datetime import datetime, timezone
import json
import logging
import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.llm_client import (
    call_chat_completion,
    extract_json_payload,
    get_active_llm_config,
)
from app.core.model_router import router as model_router
from app.store.memory_db import db, now_iso


router = APIRouter()
logger = logging.getLogger("aitest.ai_review")
logger.setLevel(logging.INFO)
REVIEW_TASKS: dict[str, asyncio.Task] = {}


REVIEW_CHECKS = {
    "\u53ef\u6d4b\u6027\u5206\u6790": {
        "summary": "\u68c0\u67e5\u9700\u6c42\u662f\u5426\u5177\u5907\u660e\u786e\u8f93\u5165\u3001\u8f93\u51fa\u3001\u9a8c\u6536\u6807\u51c6\u4e0e\u8fb9\u754c\u6761\u4ef6\u3002",
        "tip": "\u5efa\u8bae\u8865\u5145\u6210\u529f/\u5931\u8d25\u5224\u5b9a\u4e0e\u6d4b\u8bd5\u6570\u636e\u7ea6\u675f\u3002",
        "keywords": ["\u5fc5\u987b", "\u5e94", "\u652f\u6301", "\u6761\u4ef6", "\u89e6\u53d1", "\u9608\u503c", "\u8bc6\u522b"],
    },
    "\u53ef\u884c\u6027\u5206\u6790": {
        "summary": "\u68c0\u67e5\u5f53\u524d\u65b9\u6848\u5728\u6280\u672f\u3001\u8d44\u6e90\u3001\u73af\u5883\u548c\u5468\u671f\u4e0a\u7684\u843d\u5730\u6027\u3002",
        "tip": "\u5efa\u8bae\u660e\u786e\u4f9d\u8d56\u7cfb\u7edf\u3001\u6027\u80fd\u7ea6\u675f\u548c\u63a5\u53e3\u6761\u4ef6\u3002",
        "keywords": ["\u63a5\u53e3", "\u8054\u52a8", "\u81ea\u52a8", "\u6027\u80fd", "\u8ddd\u79bb", "\u73af\u5883", "\u90e8\u7f72"],
    },
    "\u903b\u8f91\u5206\u6790": {
        "summary": "\u68c0\u67e5\u6d41\u7a0b\u662f\u5426\u95ed\u73af\uff0c\u6761\u4ef6\u5206\u652f\u4e0e\u89d2\u8272\u52a8\u4f5c\u662f\u5426\u81ea\u6d3d\u3002",
        "tip": "\u5efa\u8bae\u8865\u5145\u5f02\u5e38\u6d41\u548c\u8de8\u89d2\u8272\u534f\u540c\u903b\u8f91\u3002",
        "keywords": ["\u5982\u679c", "\u5219", "\u5426\u5219", "\u5f53", "\u5e76\u4e14", "\u6216", "\u4f18\u5148"],
    },
    "\u6e05\u6670\u5ea6\u5206\u6790": {
        "summary": "\u68c0\u67e5\u672f\u8bed\u3001\u8303\u56f4\u3001\u6a21\u5757\u63cf\u8ff0\u548c\u4ea4\u4ed8\u76ee\u6807\u662f\u5426\u6e05\u6670\u3002",
        "tip": "\u5efa\u8bae\u7edf\u4e00\u672f\u8bed\u5e76\u62c6\u5206\u957f\u53e5\uff0c\u964d\u4f4e\u7406\u89e3\u6b67\u4e49\u3002",
        "keywords": ["\u8bf4\u660e", "\u63d0\u793a", "\u9ed8\u8ba4", "\u89c4\u5219", "\u53c2\u6570", "\u8303\u56f4", "\u914d\u7f6e"],
    },
}


def _list_enabled_review_prompts() -> list[dict]:
    items = [
        item for item in db.prompt_templates.values() if item.get("enabled") and item.get("prompt_type") == "\u9700\u6c42\u8bc4\u5ba1"
    ]
    items.sort(key=lambda item: item.get("updated_at", ""), reverse=True)
    return items


def _get_review_prompt_by_name(check_name: str) -> dict:
    prompt = next((item for item in _list_enabled_review_prompts() if item.get("name") == check_name), None)
    if not prompt:
        raise HTTPException(status_code=400, detail=f"No enabled review prompt found for {check_name}")
    return prompt


def _get_review_detail(check_name: str, prompt_template: dict | None = None) -> dict:
    base = REVIEW_CHECKS.get(check_name, {})
    description = str((prompt_template or {}).get("description", "")).strip()
    return {
        "summary": base.get("summary") or description or f"Review requirement content from the perspective of {check_name}.",
        "tip": base.get("tip") or f"Focus on issues that block {check_name} judgment and give requirement-level fixes.",
        "keywords": base.get("keywords", []),
    }


def _serialize_review_checks() -> list[dict]:
    return [
        {
            "name": item.get("name", ""),
            "description": item.get("description", ""),
            "prompt_id": item.get("id", ""),
        }
        for item in _list_enabled_review_prompts()
        if item.get("name")
    ]


def _log_json(event: str, **payload: object) -> None:
    logger.info("%s %s", event, json.dumps(payload, ensure_ascii=False, default=str))


def _serialize_review_run(review_run: dict) -> dict:
    return db.clone(review_run)


def _serialize_review_status(review_run: dict) -> dict:
    checks = review_run.get("checks") or []
    current_step = review_run.get("current_step", 0)
    results = review_run.get("results") or []
    completed_checks = [item.get("name", "") for item in results if item.get("name")]
    running_checks = [check for check in checks if check not in completed_checks]
    current_check = ""
    if checks and 0 <= current_step < len(checks):
        current_check = checks[current_step]
    elif checks and review_run.get("status") == "running":
        current_check = running_checks[0] if running_checks else checks[min(len(results), len(checks) - 1)]

    return {
        "id": review_run.get("id"),
        "requirement_id": review_run.get("requirement_id"),
        "status": review_run.get("status"),
        "progress": review_run.get("progress", 0),
        "current_step": review_run.get("current_step", 0),
        "current_check": current_check,
        "results_count": len(results),
        "total_checks": len(checks),
        "completed_checks": completed_checks,
        "running_checks": running_checks,
        "started_at": review_run.get("started_at"),
        "finished_at": review_run.get("finished_at"),
        "llm_config_id": review_run.get("llm_config_id"),
        "model": review_run.get("model"),
        "error": review_run.get("error"),
    }


def _ensure_review_task(run_id: str) -> None:
    review_run = db.review_runs.get(run_id)
    if not review_run or review_run.get("status") != "running":
        return
    task = REVIEW_TASKS.get(run_id)
    if task and not task.done():
        return
    REVIEW_TASKS[run_id] = asyncio.create_task(_process_review_run(run_id))


class ReviewRequest(BaseModel):
    requirement_id: str
    deep: bool = False


class GenerateRequest(BaseModel):
    requirement_id: str
    case_count: int = Field(default=3, ge=1, le=20)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)


class ReviewStartRequest(BaseModel):
    requirement_id: str
    checks: list[str] = Field(min_length=1)


@router.post("/review")
async def review_requirement(payload: ReviewRequest) -> dict:
    requirement = db.requirements.get(payload.requirement_id)
    if not requirement:
        raise HTTPException(status_code=404, detail="Requirement not found")

    task_type = "deep_review" if payload.deep else "quick_review"
    decision = model_router.pick(task_type=task_type, latency_priority=True)

    content = requirement["body_text"]
    issues = []
    if len(content) < 40:
        issues.append("Requirement text is short. Add context and acceptance criteria.")
    if "TODO" in content.upper():
        issues.append("Found TODO marker. Clarify missing details.")

    score = max(60, 95 - len(issues) * 10)

    return {
        "requirement_id": payload.requirement_id,
        "model": decision.model,
        "route_reason": decision.reason,
        "result": {
            "completeness": score,
            "consistency": score - 3,
            "testability": score - 5,
            "issues": issues,
            "suggestion": "Add preconditions, edge cases, and failure scenarios.",
        },
    }


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _split_content(content: str) -> list[str]:
    parts = re.split("[\n\u3002\uff1b;!?]", content)
    return [item.strip() for item in parts if item.strip()]


def _pick_snippets(content: str, check_name: str) -> list[str]:
    chunks = _split_content(content)
    if not chunks:
        return ["\u9700\u6c42\u6b63\u6587\u4e3a\u7a7a\uff0c\u65e0\u6cd5\u5b8c\u6210\u7cbe\u786e\u5206\u6790\u3002"]

    keywords = REVIEW_CHECKS.get(check_name, {}).get("keywords", [])
    picked = []
    for chunk in chunks:
        if any(keyword in chunk for keyword in keywords):
            picked.append(chunk)
        if len(picked) >= 3:
            break

    if not picked:
        picked = chunks[:3]
    return picked


def _clamp_score(value: int | float | str | None, fallback: int = 80) -> int:
    try:
        score = int(float(value))
    except (TypeError, ValueError):
        return fallback
    return max(0, min(score, 100))


def _normalize_findings(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _build_annotations_from_llm(requirement: dict, check_name: str, index: int, payload: dict, prompt_template: dict | None = None) -> list[dict]:
    content = requirement.get("body_text", "")
    detail = _get_review_detail(check_name, prompt_template)
    annotations = []
    raw_annotations = payload.get("annotations") or []
    for offset, item in enumerate(raw_annotations[:3], start=1):
        if not isinstance(item, dict):
            continue
        quote = str(item.get("quote", "")).strip()
        comment = str(item.get("comment", "")).strip()
        suggestion = str(item.get("suggestion", "")).strip() or detail.get("tip", "\u5efa\u8bae\u8865\u5145\u7ea6\u675f\u548c\u9a8c\u6536\u6807\u51c6\u3002")
        if not quote or quote not in content:
            continue
        if not comment:
            comment = f"\u5efa\u8bae\u8fdb\u4e00\u6b65\u8865\u5145\u201c{quote[:18]}{'...' if len(quote) > 18 else ''}\u201d\u7684\u7ea6\u675f\u3001\u8fb9\u754c\u6216\u9a8c\u6536\u6807\u51c6\u3002"
        annotations.append(
            {
                "id": f"{check_name}-{index + 1}-{offset}",
                "quote": quote,
                "comment_title": check_name,
                "comment": comment,
                "suggestion": suggestion,
                "status": "done",
            }
        )
    return annotations


def _build_review_messages(requirement: dict, check_name: str, prompt_template: dict) -> list[dict[str, str]]:
    detail = _get_review_detail(check_name, prompt_template)
    snippets = _pick_snippets(requirement.get("body_text", ""), check_name)
    body_text = requirement.get("body_text", "")[:12000]
    schema = {
        "score": 0,
        "summary": "",
        "conclusion": "",
        "findings": [""],
        "suggestion": "",
        "annotations": [
            {
                "quote": "",
                "comment": "",
                "suggestion": "",
            }
        ],
    }

    user_prompt = "\n".join(
        [
            f"\u8bc4\u5ba1\u7c7b\u578b\uff1a{check_name}",
            f"\u8bc4\u5ba1\u76ee\u6807\uff1a{detail.get('summary', '')}",
            f"\u91cd\u70b9\u5efa\u8bae\uff1a{detail.get('tip', '')}",
            f"\u9700\u6c42\u6807\u9898\uff1a{requirement.get('title', '')}",
            "\u5019\u9009\u91cd\u70b9\u7247\u6bb5\uff1a",
            *[f"- {item}" for item in snippets],
            "\u9700\u6c42\u6b63\u6587\uff1a",
            body_text,
            "\u8bf7\u4e25\u683c\u8f93\u51fa JSON\uff0c\u4e0d\u8981\u8f93\u51fa\u989d\u5916\u8bf4\u660e\u3002JSON \u7ed3\u6784\u5982\u4e0b\uff1a",
            json.dumps(schema, ensure_ascii=False),
            "\u8981\u6c42\uff1ascore \u4e3a 0-100 \u7684\u6574\u6570\uff1bannotations.quote \u5fc5\u987b\u76f4\u63a5\u5f15\u7528\u9700\u6c42\u539f\u6587\uff1bfindings \u81f3\u5c11\u7ed9\u51fa 1 \u6761\u3002",
        ]
    )

    return [
        {"role": "system", "content": prompt_template.get("content", "\u4f60\u662f\u4e00\u540d\u4e13\u4e1a\u7684\u8f6f\u4ef6\u9700\u6c42\u8bc4\u5ba1\u52a9\u624b\u3002")},
        {"role": "user", "content": user_prompt},
    ]


async def _build_step_result(requirement: dict, check_name: str, index: int, llm_config: dict, prompt_template: dict) -> dict:
    detail = _get_review_detail(check_name, prompt_template)
    messages = _build_review_messages(requirement, check_name, prompt_template)

    _log_json(
        "review_step_request",
        run_step=index + 1,
        check_name=check_name,
        requirement_id=requirement.get("id"),
        requirement_title=requirement.get("title"),
        llm_config_id=llm_config.get("id"),
        llm_config_name=llm_config.get("name"),
        model_name=llm_config.get("model_name"),
        api_url=llm_config.get("api_url"),
        prompt_template_id=prompt_template.get("id"),
        prompt_template_name=prompt_template.get("name"),
        prompt_template_type=prompt_template.get("prompt_type"),
        system_prompt=messages[0]["content"] if messages else "",
        user_prompt=messages[1]["content"] if len(messages) > 1 else "",
    )

    try:
        completion = await call_chat_completion(
            api_url=llm_config["api_url"],
            api_key=llm_config["api_key"],
            model_name=llm_config["model_name"],
            messages=messages,
            temperature=0.2,
            max_tokens=1400,
            timeout=90.0,
        )
        _log_json(
            "review_step_response",
            run_step=index + 1,
            check_name=check_name,
            requirement_id=requirement.get("id"),
            model_name=completion.get("model") or llm_config.get("model_name"),
            raw_response=completion.get("content", ""),
        )
        payload = extract_json_payload(completion["content"])
        annotations = _build_annotations_from_llm(requirement, check_name, index, payload, prompt_template)
        findings = _normalize_findings(payload.get("findings")) or [item["comment"] for item in annotations]
        return {
            "name": check_name,
            "status": "completed",
            "score": _clamp_score(payload.get("score"), 82),
            "summary": str(payload.get("summary", "")).strip() or detail.get("summary", ""),
            "conclusion": str(payload.get("conclusion", "")).strip() or f"{check_name}\u5df2\u5b8c\u6210\uff0c\u8bf7\u6309\u5efa\u8bae\u8865\u5145\u9700\u6c42\u8bf4\u660e\u3002",
            "findings": findings,
            "annotations": annotations,
            "suggestion": str(payload.get("suggestion", "")).strip() or detail.get("tip", "\u5efa\u8bae\u8865\u5145\u7ea6\u675f\u548c\u9a8c\u6536\u6807\u51c6\u3002"),
            "finished_at": now_iso(),
            "raw_response": completion["content"],
        }
    except Exception:
        logger.exception(
            "review_step_failed check_name=%s requirement_id=%s prompt_template_id=%s llm_config_id=%s",
            check_name,
            requirement.get("id"),
            prompt_template.get("id"),
            llm_config.get("id"),
        )
        raise


def _update_requirement_review_state(requirement_id: str, run_id: str, status: str) -> None:
    requirement = db.requirements[requirement_id]
    requirement["review_status"] = "评审完成" if status == "completed" else "待评审" if status == "failed" else "评审中"
    requirement["latest_review_run_id"] = run_id
    requirement["updated_at"] = now_iso()


async def _process_review_run(run_id: str) -> None:
    review_run = db.review_runs.get(run_id)
    if not review_run:
        return

    llm_config = db.llm_configs.get(review_run.get("llm_config_id")) or get_active_llm_config()
    _log_json(
        "review_run_worker_started",
        run_id=review_run.get("id"),
        requirement_id=review_run.get("requirement_id"),
        total_checks=len(review_run.get("checks") or []),
        llm_config_id=llm_config.get("id"),
        model_name=llm_config.get("model_name"),
    )

    try:
        checks = review_run.get("checks") or []
        for index, check_name in enumerate(checks):
            prompt_id = (review_run.get("check_prompt_map") or {}).get(check_name)
            prompt_template = db.prompt_templates.get(prompt_id) if prompt_id else _get_review_prompt_by_name(check_name)
            requirement = db.requirements[review_run["requirement_id"]]
            review_run["current_step"] = index
            review_run["progress"] = int((index / max(len(checks), 1)) * 100)
            _update_requirement_review_state(review_run["requirement_id"], run_id, "running")
            result = await _build_step_result(requirement, check_name, index, llm_config, prompt_template)
            review_run["results"].append(result)
            review_run["progress"] = int((len(review_run["results"]) / max(len(checks), 1)) * 100)
            review_run["updated_at"] = now_iso()

        review_run["status"] = "completed"
        review_run["finished_at"] = now_iso()
        review_run["progress"] = 100
        review_run["current_step"] = max(len(checks) - 1, 0)
        review_run["updated_at"] = now_iso()
        _update_requirement_review_state(review_run["requirement_id"], run_id, "completed")
        _log_json(
            "review_run_worker_completed",
            run_id=run_id,
            requirement_id=review_run.get("requirement_id"),
            results_count=len(review_run.get("results") or []),
        )
    except Exception as exc:  # noqa: BLE001
        review_run["status"] = "failed"
        review_run["finished_at"] = now_iso()
        review_run["updated_at"] = now_iso()
        review_run["error"] = str(exc)
        _update_requirement_review_state(review_run["requirement_id"], run_id, "failed")
        logger.exception("review_run_worker_failed run_id=%s requirement_id=%s", run_id, review_run.get("requirement_id"))
    finally:
        REVIEW_TASKS.pop(run_id, None)


def _update_requirement_review_state(requirement_id: str, run_id: str, status: str) -> None:
    requirement = db.requirements[requirement_id]
    requirement["review_status"] = "评审完成" if status == "completed" else "待评审" if status == "failed" else "评审中"
    requirement["latest_review_run_id"] = run_id
    requirement["updated_at"] = now_iso()


def _sort_review_results(results: list[dict], checks: list[str]) -> list[dict]:
    order_map = {name: index for index, name in enumerate(checks)}
    return sorted(results, key=lambda item: order_map.get(item.get("name", ""), len(checks)))


async def _process_review_run(run_id: str) -> None:
    review_run = db.review_runs.get(run_id)
    if not review_run:
        return

    llm_config = db.llm_configs.get(review_run.get("llm_config_id")) or get_active_llm_config()
    _log_json(
        "review_run_worker_started",
        run_id=review_run.get("id"),
        requirement_id=review_run.get("requirement_id"),
        total_checks=len(review_run.get("checks") or []),
        llm_config_id=llm_config.get("id"),
        model_name=llm_config.get("model_name"),
    )

    try:
        checks = review_run.get("checks") or []
        _update_requirement_review_state(review_run["requirement_id"], run_id, "running")
        review_run["progress"] = 0
        review_run["current_step"] = 0
        review_run["updated_at"] = now_iso()

        async def run_single_check(index: int, check_name: str) -> dict:
            prompt_id = (review_run.get("check_prompt_map") or {}).get(check_name)
            prompt_template = db.prompt_templates.get(prompt_id) if prompt_id else _get_review_prompt_by_name(check_name)
            requirement = db.requirements[review_run["requirement_id"]]
            return await _build_step_result(requirement, check_name, index, llm_config, prompt_template)

        tasks = [asyncio.create_task(run_single_check(index, check_name)) for index, check_name in enumerate(checks)]

        for completed_task in asyncio.as_completed(tasks):
            result = await completed_task
            review_run["results"].append(result)
            review_run["results"] = _sort_review_results(review_run["results"], checks)
            completed_count = len(review_run["results"])
            review_run["progress"] = int((completed_count / max(len(checks), 1)) * 100)
            review_run["current_step"] = min(completed_count, max(len(checks) - 1, 0))
            review_run["updated_at"] = now_iso()

        review_run["status"] = "completed"
        review_run["finished_at"] = now_iso()
        review_run["progress"] = 100
        review_run["current_step"] = max(len(checks) - 1, 0)
        review_run["updated_at"] = now_iso()
        _update_requirement_review_state(review_run["requirement_id"], run_id, "completed")
        _log_json(
            "review_run_worker_completed",
            run_id=run_id,
            requirement_id=review_run.get("requirement_id"),
            results_count=len(review_run.get("results") or []),
        )
    except Exception as exc:  # noqa: BLE001
        review_run["status"] = "failed"
        review_run["finished_at"] = now_iso()
        review_run["updated_at"] = now_iso()
        review_run["error"] = str(exc)
        _update_requirement_review_state(review_run["requirement_id"], run_id, "failed")
        logger.exception("review_run_worker_failed run_id=%s requirement_id=%s", run_id, review_run.get("requirement_id"))
    finally:
        REVIEW_TASKS.pop(run_id, None)


@router.get("/reviews/checks")
async def list_review_checks() -> dict:
    return {"items": _serialize_review_checks()}


@router.post("/reviews/start")
async def start_review(payload: ReviewStartRequest) -> dict:
    requirement = db.requirements.get(payload.requirement_id)
    if not requirement:
        raise HTTPException(status_code=404, detail="Requirement not found")

    enabled_prompts = {item.get("name"): item for item in _list_enabled_review_prompts() if item.get("name")}
    checks = [item for item in payload.checks if item in enabled_prompts]
    if not checks:
        raise HTTPException(status_code=400, detail="No valid review checks selected")

    llm_config = get_active_llm_config()
    _log_json(
        "review_run_started",
        requirement_id=payload.requirement_id,
        checks=checks,
        llm_config_id=llm_config.get("id"),
        llm_config_name=llm_config.get("name"),
        model_name=llm_config.get("model_name"),
        api_url=llm_config.get("api_url"),
        prompt_map={check_name: enabled_prompts[check_name]["id"] for check_name in checks},
    )

    run_id = db.new_id("review_runs")
    review_run = {
        "id": run_id,
        "requirement_id": payload.requirement_id,
        "checks": checks,
        "status": "running",
        "progress": 0,
        "current_step": 0,
        "results": [],
        "started_at": now_iso(),
        "finished_at": None,
        "updated_at": now_iso(),
        "model": llm_config["model_name"],
        "route_reason": f"active llm config: {llm_config['name']}",
        "llm_config_id": llm_config["id"],
        "check_prompt_map": {check_name: enabled_prompts[check_name]["id"] for check_name in checks},
        "prompt_template_name": ", ".join(checks),
    }
    db.review_runs[run_id] = review_run
    db.requirement_reviews[payload.requirement_id].append(run_id)
    _update_requirement_review_state(payload.requirement_id, run_id, "running")
    REVIEW_TASKS[run_id] = asyncio.create_task(_process_review_run(run_id))
    return _serialize_review_run(review_run)


@router.get("/reviews/{run_id}")
async def get_review_run(run_id: str) -> dict:
    review_run = db.review_runs.get(run_id)
    if not review_run:
        raise HTTPException(status_code=404, detail="Review run not found")
    _ensure_review_task(run_id)
    return _serialize_review_run(review_run)


@router.get("/reviews/{run_id}/status")
async def get_review_run_status(run_id: str) -> dict:
    review_run = db.review_runs.get(run_id)
    if not review_run:
        raise HTTPException(status_code=404, detail="Review run not found")
    _ensure_review_task(run_id)
    return _serialize_review_status(review_run)


@router.get("/reviews/by-requirement/{requirement_id}")
async def list_review_runs(requirement_id: str) -> dict:
    if requirement_id not in db.requirements:
        raise HTTPException(status_code=404, detail="Requirement not found")
    run_ids = db.requirement_reviews.get(requirement_id, [])
    for run_id in run_ids:
        _ensure_review_task(run_id)
    runs = [_serialize_review_run(db.review_runs[run_id]) for run_id in reversed(run_ids)]
    return {"items": runs}


@router.post("/generate-cases")
async def generate_cases(payload: GenerateRequest) -> dict:
    requirement = db.requirements.get(payload.requirement_id)
    if not requirement:
        raise HTTPException(status_code=404, detail="Requirement not found")

    decision = model_router.pick(task_type="test_generation", latency_priority=True)
    generated = []
    for idx in range(1, payload.case_count + 1):
        generated.append(
            {
                "title": f"{requirement['title']} - Auto Case {idx}",
                "steps": ["Prepare data", "Execute action", "Observe output"],
                "expected": ["Output matches requirement"],
                "priority": "P2" if idx > 1 else "P1",
            }
        )

    return {
        "requirement_id": payload.requirement_id,
        "model": decision.model,
        "route_reason": decision.reason,
        "cases": generated,
    }


@router.post("/chat")
async def chat(payload: ChatRequest) -> dict:
    decision = model_router.pick(task_type="chat", latency_priority=True)
    return {
        "model": decision.model,
        "route_reason": decision.reason,
        "answer": f"Received: {payload.message}. Start by refining acceptance criteria.",
    }
