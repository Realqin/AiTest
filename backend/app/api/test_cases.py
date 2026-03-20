import json
import logging
from typing import Any
from copy import deepcopy

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.llm_client import (
    call_chat_completion,
    extract_json_payload,
    get_active_llm_config,
)
from app.store.memory_db import db, now_iso


router = APIRouter()
logger = logging.getLogger("aitest.test_case_workflow")


def _log_workflow_event(event: str, **payload: object) -> None:
    logger.info("%s %s", event, json.dumps(payload, ensure_ascii=False, default=str))


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


def _get_dictionary_items(group: str, fallback: list[dict] | list[str]) -> list[dict]:
    items = [item for item in db.dictionaries.values() if item.get("enabled", True) and item.get("group") == group]
    items.sort(key=lambda item: (item.get("sort_order", 0), item.get("created_at", ""), item.get("id", "")))
    if items:
        return [db.clone(item) for item in items]
    if fallback and isinstance(fallback[0], str):
        return [{"key": item, "value": item} for item in fallback]
    return [db.clone(item) for item in fallback]

TEST_CASE_PROMPT_TYPE = "测试用例"
CASE_TYPE_OPTIONS = [
    "冒烟测试",
    "功能测试",
    "边界测试",
    "异常测试",
    "权限测试",
    "安全测试",
    "兼容性测试",
]
CASE_PRIORITY_OPTIONS = [
    {"key": "P0", "value": "高级"},
    {"key": "P1", "value": "中级"},
    {"key": "P2", "value": "低级"},
    {"key": "P3", "value": "最低级"},
]
KNOWLEDGE_BASE_OPTIONS = [
    "需求文档知识库",
    "历史用例知识库",
    "缺陷案例知识库",
    "接口文档知识库",
]
STANDALONE_TEST_CASE_PROMPT = {
    "remark": "test-case-standalone:general",
    "name": "\u6d4b\u8bd5\u7528\u4f8b-\u901a\u7528",
    "description": "\u7528\u4e8e\u5728\u7528\u4f8b\u7ba1\u7406\u4e2d\u7ed3\u5408\u622a\u56fe\u3001\u8865\u5145\u8bf4\u660e\u548c\u6d4b\u8bd5\u7c7b\u578b\u76f4\u63a5\u751f\u6210\u7ed3\u6784\u5316\u6d4b\u8bd5\u7528\u4f8b\u3002",
    "default_content": (
        "\u4f60\u662f\u4e00\u4f4d\u8d44\u6df1\u6d4b\u8bd5\u5de5\u7a0b\u5e08\u3002\u8bf7\u57fa\u4e8e\u7528\u6237\u63d0\u4f9b\u7684\u9875\u9762\u622a\u56fe\u3001\u8865\u5145\u8bf4\u660e\u3001\u6d4b\u8bd5\u7c7b\u578b\u548c\u53ef\u9009\u77e5\u8bc6\u5e93\u4fe1\u606f\uff0c\u751f\u6210\u7ed3\u6784\u5316\u6d4b\u8bd5\u7528\u4f8b\u3002\n"
        "\u8f93\u51fa\u8981\u6c42\uff1a\n"
        "1. \u4f18\u5148\u8bc6\u522b\u9875\u9762\u4e2d\u7684\u6838\u5fc3\u6d41\u7a0b\u3001\u8f93\u5165\u9879\u3001\u72b6\u6001\u3001\u6309\u94ae\u3001\u63d0\u793a\u4fe1\u606f\u3001\u5217\u8868\u5b57\u6bb5\u548c\u6821\u9a8c\u89c4\u5219\u3002\n"
        "2. \u7ed3\u5408\u7528\u6237\u8865\u5145\u7684\u4e1a\u52a1\u89c4\u5219\uff0c\u8986\u76d6\u4e3b\u6d41\u7a0b\u3001\u5f02\u5e38\u6d41\u7a0b\u3001\u8fb9\u754c\u6761\u4ef6\u3001\u6743\u9650\u5dee\u5f02\u548c\u9ad8\u98ce\u9669\u573a\u666f\u3002\n"
        "3. \u6bcf\u6761\u7528\u4f8b\u90fd\u5fc5\u987b\u5305\u542b test_point\u3001title\u3001preconditions\u3001steps\u3001expected\u3001priority\u3001case_type\u3002\n"
        "4. steps \u5fc5\u987b\u662f\u53ef\u6267\u884c\u52a8\u4f5c\uff0cexpected \u5fc5\u987b\u662f\u53ef\u9a8c\u8bc1\u7ed3\u679c\uff0c\u907f\u514d\u7b3c\u7edf\u63cf\u8ff0\u3002\n"
        "5. case_type \u5fc5\u987b\u4ece\u7528\u6237\u9009\u62e9\u7684\u6d4b\u8bd5\u7c7b\u578b\u4e2d\u53d6\u503c\u3002"
    ),
}

TEST_CASE_STAGE_PROMPTS = {
    "clarify": {
        "name": "\u6d4b\u8bd5\u7528\u4f8b-\u9700\u6c42\u5206\u6790",
        "title": "\u9700\u6c42\u5206\u6790",
        "subtitle": "\u5148\u5206\u6790\u8fd9\u4e2a\u9700\u6c42\u5305\u542b\u54ea\u4e9b\u529f\u80fd\u70b9\u3001\u4e3b\u6d41\u7a0b\u548c\u5173\u952e\u5206\u652f\u3002",
        "button_text": "\u751f\u6210\u9700\u6c42\u5206\u6790",
        "description": "\u7528\u4e8e\u5148\u8bc6\u522b\u9700\u6c42\u4e2d\u7684\u529f\u80fd\u70b9\u3001\u4e1a\u52a1\u6b65\u9aa4\u3001\u89d2\u8272\u548c\u8fb9\u754c\uff0c\u4e3a\u540e\u7eed\u6d4b\u8bd5\u70b9\u4e0e\u7528\u4f8b\u751f\u6210\u5efa\u7acb\u7ed3\u6784\u5316\u8f93\u5165\u3002",
        "remark": "test-case-stage:clarify",
        "default_content": (
            "\u4f60\u662f\u4e00\u4f4d\u8d44\u6df1\u6d4b\u8bd5\u5206\u6790\u5e08\u3002\u8bf7\u57fa\u4e8e\u8f93\u5165\u7684\u9700\u6c42\u4fe1\u606f\u8f93\u51fa\u201c\u9700\u6c42\u62c6\u89e3\u201d\u7ed3\u679c\uff0c\u76ee\u6807\u662f\u5148\u660e\u786e\u8be5\u9700\u6c42\u5305\u542b\u591a\u5c11\u4e2a\u529f\u80fd\u70b9\uff0c\u4ee5\u53ca\u6bcf\u4e2a\u529f\u80fd\u70b9\u5bf9\u5e94\u7684\u4e3b\u6d41\u7a0b\u3001\u5173\u952e\u5206\u652f\u548c\u8fb9\u754c\u3002\n"
            "\u8f93\u51fa\u8981\u6c42\uff1a\n"
            "1. \u5148\u603b\u7ed3\u9700\u6c42\u76ee\u6807\uff0c\u5e76\u6982\u62ec\u8be5\u9700\u6c42\u8986\u76d6\u7684\u4e1a\u52a1\u8303\u56f4\u3002\n"
            "2. \u62c6\u5206\u51fa\u660e\u786e\u7684\u529f\u80fd\u70b9\u6e05\u5355\uff0c\u7ed9\u6bcf\u4e2a\u529f\u80fd\u70b9\u7f16\u53f7\uff0c\u540d\u79f0\u8981\u5177\u4f53\uff0c\u907f\u514d\u8fc7\u4e8e\u7b3c\u7edf\u3002\n"
            "3. \u5bf9\u6bcf\u4e2a\u529f\u80fd\u70b9\u8865\u5145\u8bf4\u660e\uff1a\u89e6\u53d1\u89d2\u8272\u3001\u524d\u7f6e\u6761\u4ef6\u3001\u6838\u5fc3\u64cd\u4f5c\u3001\u5173\u952e\u7ed3\u679c\u3002\n"
            "4. \u5982\u5b58\u5728\u91cd\u8981\u5206\u652f\u3001\u5f02\u5e38\u5904\u7406\u3001\u6743\u9650\u5dee\u5f02\u3001\u72b6\u6001\u6d41\u8f6c\u6216\u5916\u90e8\u4f9d\u8d56\uff0c\u9700\u8981\u5728\u5bf9\u5e94\u529f\u80fd\u70b9\u4e0b\u5355\u72ec\u6807\u51fa\u3002\n"
            "5. \u8f93\u51fa\u8981\u7ed3\u6784\u5316\uff0c\u4fbf\u4e8e\u540e\u7eed\u76f4\u63a5\u7ee7\u7eed\u751f\u6210\u6d4b\u8bd5\u70b9\u6216\u601d\u7ef4\u5bfc\u56fe\uff1b\u4e0d\u8981\u989d\u5916\u589e\u52a0\u201c\u9700\u6c42\u6f84\u6e05\u201d\u201c\u77e5\u8bc6\u70b9\u68b3\u7406\u201d\u7b49\u8282\u70b9\u524d\u7f00\u3002"
        ),
    },
    "test_points": {
        "name": "\u6d4b\u8bd5\u7528\u4f8b-\u6d4b\u8bd5\u70b9\u68b3\u7406",
        "title": "\u6d4b\u8bd5\u70b9\u68b3\u7406",
        "subtitle": "\u57fa\u4e8e\u9700\u6c42\u62c6\u89e3\u7ed3\u679c\uff0c\u628a\u6bcf\u4e2a\u529f\u80fd\u70b9\u5c55\u5f00\u4e3a\u53ef\u9a8c\u8bc1\u7684\u6d4b\u8bd5\u70b9\u3002",
        "button_text": "\u751f\u6210\u6d4b\u8bd5\u70b9",
        "description": "\u7528\u4e8e\u6309\u6d4b\u8bd5\u8bbe\u8ba1\u89c6\u89d2\u68b3\u7406\u529f\u80fd\u70b9\u5bf9\u5e94\u7684\u4e3b\u6d41\u7a0b\u3001\u5206\u652f\u3001\u8fb9\u754c\u3001\u5f02\u5e38\u548c\u975e\u529f\u80fd\u6d4b\u8bd5\u70b9\u3002",
        "remark": "test-case-stage:test_points",
        "default_content": (
            "\u4f60\u662f\u4e00\u4f4d\u8d44\u6df1\u6d4b\u8bd5\u8bbe\u8ba1\u4e13\u5bb6\u3002\u8bf7\u57fa\u4e8e\u9700\u6c42\u6b63\u6587\u4ee5\u53ca\u524d\u5e8f\u9636\u6bb5\u7684\u9700\u6c42\u62c6\u89e3\u7ed3\u679c\uff0c\u8f93\u51fa\u201c\u6d4b\u8bd5\u70b9\u68b3\u7406\u201d\u7ed3\u679c\u3002\n"
            "\u8f93\u51fa\u8981\u6c42\uff1a\n"
            "1. \u6309\u529f\u80fd\u70b9\u5206\u7ec4\u68b3\u7406\u6d4b\u8bd5\u70b9\uff0c\u4f18\u5148\u8986\u76d6\u4e3b\u6d41\u7a0b\u3001\u5206\u652f\u6d41\u7a0b\u3001\u8fb9\u754c\u6761\u4ef6\u3001\u5f02\u5e38\u5904\u7406\u3001\u6743\u9650\u63a7\u5236\u3001\u6570\u636e\u6821\u9a8c\u548c\u72b6\u6001\u6d41\u8f6c\u3002\n"
            "2. \u6bcf\u4e2a\u6d4b\u8bd5\u70b9\u90fd\u8981\u5199\u660e\u9a8c\u8bc1\u76ee\u6807\uff0c\u907f\u514d\u53ea\u5217\u6807\u9898\u3002\n"
            "3. \u8865\u5145\u63a5\u53e3\u8054\u52a8\u3001\u6570\u636e\u4e00\u81f4\u6027\u3001\u517c\u5bb9\u6027\u3001\u6027\u80fd\u548c\u7a33\u5b9a\u6027\u7b49\u5fc5\u8981\u7684\u975e\u529f\u80fd\u6d4b\u8bd5\u70b9\u3002\n"
            "4. \u5bf9\u9ad8\u98ce\u9669\u6d4b\u8bd5\u70b9\u8fdb\u884c\u5355\u72ec\u6807\u8bc6\uff0c\u5e76\u8bf4\u660e\u98ce\u9669\u539f\u56e0\u3002\n"
            "5. \u8f93\u51fa\u8981\u7ed3\u6784\u5316\uff0c\u4fbf\u4e8e\u540e\u7eed\u76f4\u63a5\u8f6c\u6362\u6210\u6d4b\u8bd5\u7528\u4f8b\u6216\u601d\u7ef4\u5bfc\u56fe\uff1b\u4e0d\u8981\u989d\u5916\u589e\u52a0\u9636\u6bb5\u524d\u7f00\u8282\u70b9\u3002"
        ),
    },
    "cases": {
        "name": "\u6d4b\u8bd5\u7528\u4f8b-\u751f\u6210\u7528\u4f8b",
        "title": "\u751f\u6210\u7528\u4f8b",
        "subtitle": "\u57fa\u4e8e\u9700\u6c42\u62c6\u89e3\u548c\u6d4b\u8bd5\u70b9\u68b3\u7406\u7ed3\u679c\u4ea7\u51fa\u7ed3\u6784\u5316\u6d4b\u8bd5\u7528\u4f8b\u3002",
        "button_text": "\u751f\u6210\u6d4b\u8bd5\u7528\u4f8b",
        "description": "\u7528\u4e8e\u751f\u6210\u53ef\u6267\u884c\u3001\u53ef\u7f16\u8f91\u3001\u53ef\u76f4\u63a5\u5165\u5e93\u7684\u7ed3\u6784\u5316\u6d4b\u8bd5\u7528\u4f8b\u3002",
        "remark": "test-case-stage:cases",
        "default_content": (
            "\u4f60\u662f\u4e00\u4f4d\u8d44\u6df1\u6d4b\u8bd5\u5de5\u7a0b\u5e08\u3002\u8bf7\u57fa\u4e8e\u9700\u6c42\u6b63\u6587\u53ca\u524d\u5e8f\u9636\u6bb5\u7ed3\u679c\uff0c\u751f\u6210\u7ed3\u6784\u5316\u6d4b\u8bd5\u7528\u4f8b\u3002\n"
            "\u8f93\u51fa\u8981\u6c42\uff1a\n"
            "1. \u4f18\u5148\u8986\u76d6\u6838\u5fc3\u4e1a\u52a1\u6d41\u3001\u5173\u952e\u5f02\u5e38\u5206\u652f\u3001\u8fb9\u754c\u573a\u666f\u3001\u6743\u9650\u5dee\u5f02\u3001\u72b6\u6001\u6d41\u8f6c\u548c\u9ad8\u98ce\u9669\u70b9\u3002\n"
            "2. \u6bcf\u6761\u7528\u4f8b\u90fd\u8981\u5305\u542b test_point\u3001title\u3001preconditions\u3001steps\u3001expected\u3001priority\u3001case_type\u3002\n"
            "3. steps \u5fc5\u987b\u662f\u53ef\u6267\u884c\u52a8\u4f5c\uff0cexpected \u5fc5\u987b\u662f\u53ef\u9a8c\u8bc1\u7ed3\u679c\uff0c\u7981\u6b62\u7b3c\u7edf\u63cf\u8ff0\u3002\n"
            "4. priority \u4f7f\u7528 P1/P2/P3\uff0cP1 \u8868\u793a\u6838\u5fc3\u9ad8\u98ce\u9669\u573a\u666f\u3002\n"
            "5. case_type \u5fc5\u987b\u4ece\u7528\u6237\u9009\u4e2d\u7684\u7528\u4f8b\u7c7b\u578b\u4e2d\u9009\u62e9\u3002"
        ),
    },
}
WORKFLOW_STAGES = [
    {key: value for key, value in meta.items() if key in {"title", "subtitle", "button_text"}} | {"key": key}
    for key, meta in TEST_CASE_STAGE_PROMPTS.items()
]
WORKFLOW_STAGE_MAP = {item["key"]: item for item in WORKFLOW_STAGES}

CASE_TYPE_DICTIONARY_FALLBACK = [
    {"key": "smoke", "value": "冒烟测试"},
    {"key": "functional", "value": "功能测试"},
    {"key": "boundary", "value": "边界测试"},
    {"key": "exception", "value": "异常测试"},
    {"key": "permission", "value": "权限测试"},
    {"key": "security", "value": "安全测试"},
    {"key": "compatibility", "value": "兼容性测试"},
]

CASE_TYPE_LABEL_TO_KEY = {item["value"]: item["key"] for item in CASE_TYPE_DICTIONARY_FALLBACK}
CASE_TYPE_KEY_TO_LABEL = {item["key"]: item["value"] for item in CASE_TYPE_DICTIONARY_FALLBACK}


class TestCaseIn(BaseModel):
    requirement_id: str = ""
    module_id: str = ""
    title: str = Field(min_length=1, max_length=200)
    test_point: str = ""
    preconditions: list[str] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    expected: list[str] = Field(default_factory=list)
    priority: str = "P2"
    case_type: str = ""
    stage: str = ""
    review_status: str = "待审核"
    creator: str = "admin"


class WorkflowDraftPayload(BaseModel):
    stage_key: str
    content: str = ""
    prompt: str = ""
    generated_cases: list[dict] = Field(default_factory=list)
    case_types: list[str] = Field(default_factory=list)
    knowledge_bases: list[str] = Field(default_factory=list)
    use_knowledge_base: bool = False


class WorkflowGeneratePayload(BaseModel):
    stage_key: str
    prompt: str = ""
    case_types: list[str] = Field(default_factory=list)
    knowledge_bases: list[str] = Field(default_factory=list)
    use_knowledge_base: bool = False


class StandaloneCaseGeneratePayload(BaseModel):
    prompt: str = ""
    case_types: list[str] = Field(default_factory=list)
    knowledge_bases: list[str] = Field(default_factory=list)
    image_data_urls: list[str] = Field(default_factory=list)
    use_knowledge_base: bool = False


class WorkflowSnapshotPayload(BaseModel):
    stage_key: str
    note: str = ""


class WorkflowRollbackPayload(BaseModel):
    stage_key: str


class TestCaseModuleIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    parent_id: str = ""


def _build_prompt_template(name: str, description: str, default_content: str, remark: str = "") -> dict:
    candidates = [
        item
        for item in db.prompt_templates.values()
        if item.get("enabled")
        and item.get("prompt_type") == TEST_CASE_PROMPT_TYPE
        and ((remark and item.get("remark") == remark) or (not remark and item.get("name") == name))
    ]
    if not candidates and remark:
        candidates = [
            item
            for item in db.prompt_templates.values()
            if item.get("enabled")
            and item.get("prompt_type") == TEST_CASE_PROMPT_TYPE
            and item.get("name") == name
        ]
    if candidates:
        candidates.sort(key=lambda item: item.get("updated_at", ""), reverse=True)
        template = db.clone(candidates[0])
        template["content"] = _normalize_prompt_text(template.get("content", ""))
        return template
    return {
        "id": "",
        "prompt_type": TEST_CASE_PROMPT_TYPE,
        "name": name,
        "description": description,
        "content": _normalize_prompt_text(default_content),
        "remark": "system-default",
        "enabled": True,
        "is_default": False,
    }


def _find_stage_prompt_template(stage_key: str) -> dict:
    stage_meta = TEST_CASE_STAGE_PROMPTS[stage_key]
    return _build_prompt_template(stage_meta["name"], stage_meta["description"], stage_meta["default_content"], stage_meta.get("remark", ""))


def _find_standalone_prompt_template() -> dict:
    return _build_prompt_template(
        STANDALONE_TEST_CASE_PROMPT["name"],
        STANDALONE_TEST_CASE_PROMPT["description"],
        STANDALONE_TEST_CASE_PROMPT["default_content"],
        STANDALONE_TEST_CASE_PROMPT.get("remark", ""),
    )


def _resolve_requirement_id(requirement_id: str) -> str:
    return requirement_id or db.MANUAL_CASE_REQUIREMENT_ID


def _normalize_case_type_key(case_type: str, available_items: list[dict] | None = None) -> str:
    value = str(case_type or "").strip()
    if not value:
        return ""
    options = available_items or _get_dictionary_items("case_type", CASE_TYPE_DICTIONARY_FALLBACK)
    key_by_label = {
        str(item.get("value", "")).strip(): str(item.get("key", "")).strip()
        for item in options
        if item.get("key")
    }
    valid_keys = {str(item.get("key", "")).strip() for item in options if item.get("key")}
    if value in valid_keys:
        return value
    return key_by_label.get(value, CASE_TYPE_LABEL_TO_KEY.get(value, value))


def _resolve_module(module_id: str | None) -> dict | None:
    resolved_id = str(module_id or "").strip()
    if not resolved_id:
        return None
    return db.test_case_modules.get(resolved_id)


def _serialize_test_case(item: dict) -> dict:
    case = db.clone(item)
    module = _resolve_module(case.get("module_id"))
    case["module_name"] = module.get("name", "") if module else ""
    case_type = str(case.get("case_type", "")).strip()
    case["case_type_label"] = CASE_TYPE_KEY_TO_LABEL.get(case_type, case_type)
    return case


def _case_type_labels(case_types: list[str]) -> list[str]:
    return [CASE_TYPE_KEY_TO_LABEL.get(item, item) for item in case_types if item]


def _build_case_sidebar_payload() -> dict:
    all_cases = list(db.test_cases.values())
    module_case_count = {}
    requirement_case_count = {}
    total_linked = 0

    for item in all_cases:
        module_id = str(item.get("module_id", "") or "")
        if module_id:
            module_case_count[module_id] = module_case_count.get(module_id, 0) + 1
        requirement_id = str(item.get("requirement_id", "") or "")
        if requirement_id and requirement_id != db.MANUAL_CASE_REQUIREMENT_ID:
            requirement_case_count[requirement_id] = requirement_case_count.get(requirement_id, 0) + 1
            total_linked += 1

    module_nodes = {
        item["id"]: {
            "id": item["id"],
            "name": item.get("name", ""),
            "parent_id": item.get("parent_id", ""),
            "sort_order": item.get("sort_order", 0),
            "direct_count": module_case_count.get(item["id"], 0),
            "count": module_case_count.get(item["id"], 0),
            "children": [],
        }
        for item in db.test_case_modules.values()
    }
    module_roots = []
    for node in module_nodes.values():
        parent_id = node.get("parent_id", "")
        if parent_id and parent_id in module_nodes:
            module_nodes[parent_id]["children"].append(node)
        else:
            module_roots.append(node)

    def finalize_module(node: dict) -> int:
        node["children"].sort(key=lambda item: (item.get("sort_order", 0), item.get("name", ""), item.get("id", "")))
        total = node.get("direct_count", 0)
        for child in node["children"]:
            total += finalize_module(child)
        node["count"] = total
        return total

    for root in module_roots:
        finalize_module(root)
    module_roots.sort(key=lambda item: (item.get("sort_order", 0), item.get("name", ""), item.get("id", "")))

    project_nodes = {}
    for requirement in [item for item in db.requirements.values() if not item.get("hidden")]:
        project_id = requirement.get("project_id") or f"unknown:{requirement.get('project', '')}"
        project_name = requirement.get("project", "") or "未分组项目"
        project_node = project_nodes.setdefault(
            project_id,
            {
                "id": f"req-project:{project_id}",
                "project_id": project_id,
                "name": project_name,
                "count": 0,
                "children": [],
            },
        )
        count = requirement_case_count.get(requirement["id"], 0)
        project_node["children"].append(
            {
                "id": f"req:{requirement['id']}",
                "requirement_id": requirement["id"],
                "name": requirement.get("title") or requirement.get("summary") or requirement["id"],
                "count": count,
                "children": [],
            }
        )
        project_node["count"] += count

    requirement_projects = list(project_nodes.values())
    requirement_projects.sort(key=lambda item: (item.get("name", ""), item.get("project_id", "")))
    for item in requirement_projects:
        item["children"].sort(key=lambda child: (child.get("name", ""), child.get("requirement_id", "")))

    return {
        "all_count": len(all_cases),
        "linked_count": total_linked,
        "module_tree": module_roots,
        "requirement_tree": {
            "id": "requirement-root",
            "name": "需求类",
            "count": total_linked,
            "children": requirement_projects,
        },
    }


def _build_default_stage(stage_key: str) -> dict:
    meta = WORKFLOW_STAGE_MAP[stage_key]
    return {
        "key": stage_key,
        "title": meta["title"],
        "subtitle": meta["subtitle"],
        "content": "",
        "prompt": "",
        "confirmed_at": None,
        "updated_at": now_iso(),
        "snapshots": [],
        "generated_cases": [],
        "case_types": ["functional"] if stage_key == "cases" else [],
        "knowledge_bases": [],
        "use_knowledge_base": False,
    }


def _build_default_workflow(requirement_id: str) -> dict:
    return {
        "requirement_id": requirement_id,
        "current_stage_index": 0,
        "completed": False,
        "updated_at": now_iso(),
        "stages": [_build_default_stage(item["key"]) for item in WORKFLOW_STAGES],
    }


def _normalize_case(case_item: dict, index: int, fallback_title: str, default_case_type: str = "") -> dict | None:
    if not isinstance(case_item, dict):
        return None
    title = str(case_item.get("title", "")).strip() or f"{fallback_title}-用例{index}"
    test_point = str(case_item.get("test_point", "")).strip()
    priority = str(case_item.get("priority", "P2")).strip() or "P2"
    case_type = _normalize_case_type_key(case_item.get("case_type", default_case_type))
    preconditions = [str(item).strip() for item in case_item.get("preconditions", []) if str(item).strip()]
    steps = [str(item).strip() for item in case_item.get("steps", []) if str(item).strip()]
    expected = [str(item).strip() for item in case_item.get("expected", []) if str(item).strip()]
    return {
        "title": title,
        "test_point": test_point,
        "preconditions": preconditions,
        "steps": steps,
        "expected": expected,
        "priority": priority,
        "case_type": case_type,
    }


def _normalize_workflow(requirement: dict) -> dict:
    raw = deepcopy(requirement.get("test_case_workflow") or {})
    workflow = _build_default_workflow(requirement["id"])
    raw_index = int(raw.get("current_stage_index", 0) or 0)
    workflow["current_stage_index"] = min(max(raw_index, 0), len(WORKFLOW_STAGES) - 1)
    workflow["completed"] = bool(raw.get("completed", False))
    workflow["updated_at"] = raw.get("updated_at") or workflow["updated_at"]

    raw_stage_map = {item.get("key"): item for item in raw.get("stages", []) if isinstance(item, dict) and item.get("key")}
    stages = []
    for stage_meta in WORKFLOW_STAGES:
        current = _build_default_stage(stage_meta["key"])
        saved = raw_stage_map.get(stage_meta["key"], {})
        current["content"] = str(saved.get("content", current["content"]))
        current["prompt"] = str(saved.get("prompt", current["prompt"]))
        current["confirmed_at"] = saved.get("confirmed_at")
        current["updated_at"] = saved.get("updated_at") or current["updated_at"]
        current["snapshots"] = deepcopy(saved.get("snapshots", []))
        current["generated_cases"] = deepcopy(saved.get("generated_cases", []))
        current["case_types"] = [
            _normalize_case_type_key(item)
            for item in list(saved.get("case_types", current["case_types"]))
            if _normalize_case_type_key(item)
        ]
        current["knowledge_bases"] = list(saved.get("knowledge_bases", []))
        current["use_knowledge_base"] = bool(saved.get("use_knowledge_base", False))
        stages.append(current)

    workflow["stages"] = stages
    if workflow["current_stage_index"] >= len(stages):
        workflow["current_stage_index"] = len(stages) - 1
    return workflow

def _stage_index(stage_key: str) -> int:
    if stage_key not in WORKFLOW_STAGE_MAP:
        raise HTTPException(status_code=400, detail="Invalid workflow stage")
    return next(index for index, item in enumerate(WORKFLOW_STAGES) if item["key"] == stage_key)


def _serialize_workflow(requirement: dict, workflow: dict) -> dict:
    current_index = workflow.get("current_stage_index", 0)
    stages = []
    for index, stage in enumerate(workflow.get("stages", [])):
        prompt_template = _find_stage_prompt_template(stage["key"])
        status = "locked"
        if stage.get("confirmed_at"):
            status = "confirmed"
        if index == current_index and not workflow.get("completed"):
            status = "editing"
        if workflow.get("completed") and stage.get("confirmed_at"):
            status = "confirmed"
        stages.append(
            {
                **deepcopy(stage),
                "status": status,
                "is_active": index == current_index and not workflow.get("completed"),
                "is_locked": index > current_index and not workflow.get("completed"),
                "button_text": WORKFLOW_STAGE_MAP[stage["key"]]["button_text"],
                "template_name": prompt_template.get("name", ""),
                "template_content": prompt_template.get("content", ""),
                "case_type_options": (
                    _get_dictionary_items("case_type", CASE_TYPE_DICTIONARY_FALLBACK)
                    if stage["key"] == "cases"
                    else []
                ),
                "priority_options": (
                    _get_dictionary_items("case_priority", CASE_PRIORITY_OPTIONS)
                    if stage["key"] == "cases"
                    else []
                ),
                "knowledge_base_options": KNOWLEDGE_BASE_OPTIONS if stage["key"] == "cases" else [],
            }
        )
    return {
        "requirement": {
            "id": requirement["id"],
            "title": requirement.get("title", ""),
            "project": requirement.get("project", ""),
            "summary": requirement.get("summary", ""),
            "body_text": requirement.get("body_text", ""),
        },
        "workflow": {
            "requirement_id": workflow["requirement_id"],
            "current_stage_index": current_index,
            "completed": workflow.get("completed", False),
            "updated_at": workflow.get("updated_at"),
            "stages": stages,
        },
    }


def _persist_workflow(requirement: dict, workflow: dict) -> dict:
    workflow["updated_at"] = now_iso()
    requirement["test_case_workflow"] = workflow
    requirement["updated_at"] = now_iso()
    return workflow


def _gather_stage_context(requirement: dict, workflow: dict, stage_index: int) -> str:
    sections = [
        f"需求标题：{requirement.get('title', '')}",
        f"需求摘要：{requirement.get('summary', '')}",
        "需求正文：",
        requirement.get("body_text", "")[:12000],
    ]
    for index, stage in enumerate(workflow.get("stages", [])):
        if index >= stage_index:
            break
        if stage.get("content"):
            sections.extend([f"前序阶段[{stage['title']}]内容：", stage["content"][:6000]])
    return "\n".join(item for item in sections if item)


def _fallback_stage_result(
    stage_key: str,
    requirement: dict,
    prompt: str,
    workflow: dict,
    case_types: list[str] | None = None,
    knowledge_bases: list[str] | None = None,
    use_knowledge_base: bool = False,
) -> tuple[str, list[dict]]:
    title = requirement.get("title", "\u5f53\u524d\u9700\u6c42")
    summary = requirement.get("summary", requirement.get("body_text", "")[:120])
    if stage_key == "clarify":
        content = (
            f"\u4e00\u3001\u9700\u6c42\u76ee\u6807\n- \u5f53\u524d\u9700\u6c42\u56f4\u7ed5\u201c{title}\u201d\u5c55\u5f00\uff0c\u9700\u5148\u8bc6\u522b\u5b8c\u6574\u529f\u80fd\u70b9\u540e\u518d\u7ee7\u7eed\u6d4b\u8bd5\u8bbe\u8ba1\u3002\n"
            f"- \u9700\u6c42\u6458\u8981\uff1a{summary}\n\n"
            "\u4e8c\u3001\u529f\u80fd\u70b9\u62c6\u89e3\n"
            "- \u529f\u80fd\u70b91\uff1a\u4e3b\u6d41\u7a0b\u529f\u80fd\n"
            "- \u529f\u80fd\u70b92\uff1a\u5173\u952e\u5206\u652f/\u5f02\u5e38\u5904\u7406\n"
            "- \u529f\u80fd\u70b93\uff1a\u6743\u9650\u3001\u72b6\u6001\u6216\u5916\u90e8\u4f9d\u8d56\u76f8\u5173\u80fd\u529b\n\n"
            "\u4e09\u3001\u62c6\u89e3\u5173\u6ce8\u9879\n"
            "- \u6bcf\u4e2a\u529f\u80fd\u70b9\u9700\u8fdb\u4e00\u6b65\u660e\u786e\u89e6\u53d1\u89d2\u8272\u3001\u524d\u7f6e\u6761\u4ef6\u3001\u5173\u952e\u64cd\u4f5c\u548c\u9884\u671f\u7ed3\u679c\u3002\n"
            "- \u9700\u8981\u989d\u5916\u5173\u6ce8\u8fb9\u754c\u6761\u4ef6\u3001\u5f02\u5e38\u5206\u652f\u3001\u72b6\u6001\u6d41\u8f6c\u548c\u5916\u90e8\u7cfb\u7edf\u4ea4\u4e92\u3002\n"
        )
        if prompt:
            content += f"\n\u56db\u3001\u4eba\u5de5\u8865\u5145\u5173\u6ce8\u70b9\n- {prompt}\n"
        return content, []
    if stage_key == "test_points":
        content = (
            "\u4e00\u3001\u6309\u529f\u80fd\u70b9\u68b3\u7406\u6d4b\u8bd5\u70b9\n"
            "- \u529f\u80fd\u70b9\u4e3b\u6d41\u7a0b\u9a8c\u8bc1\n"
            "- \u529f\u80fd\u70b9\u5206\u652f\u6d41\u7a0b\u9a8c\u8bc1\n"
            "- \u8f93\u5165\u8f93\u51fa\u4e0e\u8fb9\u754c\u6821\u9a8c\n"
            "- \u5f02\u5e38\u5904\u7406\u4e0e\u5931\u8d25\u63d0\u793a\n"
            "- \u6743\u9650/\u89d2\u8272\u5dee\u5f02\n\n"
            "\u4e8c\u3001\u8865\u5145\u6d4b\u8bd5\u70b9\n"
            "- \u5916\u90e8\u7cfb\u7edf\u6216\u63a5\u53e3\u8054\u52a8\n"
            "- \u6570\u636e\u4e00\u81f4\u6027\u4e0e\u72b6\u6001\u6d41\u8f6c\n"
            "- \u975e\u529f\u80fd\u9879\uff1a\u6027\u80fd\u3001\u7a33\u5b9a\u6027\u3001\u517c\u5bb9\u6027\n"
        )
        if prompt:
            content += f"\n\u4e09\u3001\u989d\u5916\u5173\u6ce8\n- {prompt}\n"
        return content, []

    resolved_case_types = [_normalize_case_type_key(item) for item in (case_types or ["functional"]) if _normalize_case_type_key(item)]
    if not resolved_case_types:
        resolved_case_types = ["functional"]
    cases = [
        {
            "title": f"{title}-\u4e3b\u6d41\u7a0b\u9a8c\u8bc1",
            "test_point": "\u6838\u5fc3\u4e1a\u52a1\u4e3b\u6d41\u7a0b",
            "preconditions": ["\u51c6\u5907\u6ee1\u8db3\u524d\u7f6e\u6761\u4ef6\u7684\u6570\u636e\u548c\u8d26\u53f7"],
            "priority": "P1",
            "steps": ["\u51c6\u5907\u6d4b\u8bd5\u6570\u636e", "\u6267\u884c\u4e3b\u6d41\u7a0b\u64cd\u4f5c", "\u68c0\u67e5\u6267\u884c\u7ed3\u679c"],
            "expected": ["\u9875\u9762\u6216\u63a5\u53e3\u8fd4\u56de\u6210\u529f", "\u72b6\u6001\u53d8\u66f4\u6b63\u786e", "\u65e0\u5f02\u5e38\u63d0\u793a"],
            "case_type": resolved_case_types[0],
        },
        {
            "title": f"{title}-\u5f02\u5e38\u8def\u5f84\u9a8c\u8bc1",
            "test_point": "\u5f02\u5e38\u8f93\u5165\u4e0e\u5931\u8d25\u63d0\u793a",
            "preconditions": ["\u51c6\u5907\u975e\u6cd5\u6216\u7f3a\u5931\u8f93\u5165\u6837\u4f8b"],
            "priority": "P1",
            "steps": ["\u6784\u9020\u975e\u6cd5\u6216\u7f3a\u5931\u8f93\u5165", "\u6267\u884c\u64cd\u4f5c", "\u89c2\u5bdf\u9519\u8bef\u63d0\u793a\u548c\u56de\u6eda\u884c\u4e3a"],
            "expected": ["\u7cfb\u7edf\u963b\u6b62\u975e\u6cd5\u63d0\u4ea4", "\u9519\u8bef\u63d0\u793a\u660e\u786e", "\u65e0\u810f\u6570\u636e\u6b8b\u7559"],
            "case_type": resolved_case_types[min(1, len(resolved_case_types) - 1)],
        },
    ]
    content = "\u5df2\u751f\u6210\u7ed3\u6784\u5316\u6d4b\u8bd5\u7528\u4f8b\u8349\u7a3f\uff0c\u53ef\u5728\u4e0b\u65b9\u7ee7\u7eed\u7f16\u8f91\u5e76\u4fdd\u5b58\u3002"
    if prompt:
        content += f"\n\u989d\u5916\u5173\u6ce8\uff1a{prompt}"
    if use_knowledge_base and knowledge_bases:
        content += f"\n\u5df2\u7ed3\u5408\u77e5\u8bc6\u5e93\uff1a{'\u3001'.join(knowledge_bases)}"
    return content, cases


async def _generate_stage_result(
    requirement: dict,
    workflow: dict,
    stage_key: str,
    prompt: str,
    case_types: list[str] | None = None,
    knowledge_bases: list[str] | None = None,
    use_knowledge_base: bool = False,
) -> tuple[str, list[dict]]:
    stage_index = _stage_index(stage_key)
    context = _gather_stage_context(requirement, workflow, stage_index)
    llm_config = get_active_llm_config()
    stage_prompt_template = _find_stage_prompt_template(stage_key)
    normalized_prompt = _normalize_prompt_text(prompt)
    case_types = case_types or []
    knowledge_bases = knowledge_bases or []

    extra_sections = []
    if stage_key == "cases":
        extra_sections.extend(
            [
                f"用户选择的用例类型：{'、'.join(case_types) if case_types else 'functional'}",
                f"是否使用知识库：{'是' if use_knowledge_base else '否'}",
                f"选择的知识库：{'、'.join(knowledge_bases) if knowledge_bases else '无'}",
                "请确保 case_type 必须从用户选择的用例类型中取值。",
            ]
        )

    prompt_sections = [
        f"当前阶段：{WORKFLOW_STAGE_MAP[stage_key]['title']}",
        f"阶段提示词模板名称：{stage_prompt_template.get('name', '')}",
        "阶段提示词模板内容：",
        stage_prompt_template.get("content", ""),
        f"人工补充提示词：{normalized_prompt or '无'}",
        *extra_sections,
        context,
    ]
    user_prompt = "\n".join(prompt_sections)

    _log_workflow_event(
        "workflow_generate_prepare",
        requirement_id=requirement.get("id"),
        requirement_title=requirement.get("title"),
        stage_key=stage_key,
        stage_title=WORKFLOW_STAGE_MAP[stage_key]["title"],
        llm_config_id=llm_config.get("id"),
        llm_config_name=llm_config.get("name"),
        model_name=llm_config.get("model_name"),
        api_url=llm_config.get("api_url"),
        prompt_template_id=stage_prompt_template.get("id"),
        prompt_template_name=stage_prompt_template.get("name"),
        prompt_template_content=stage_prompt_template.get("content", ""),
        manual_prompt=normalized_prompt,
        case_types=case_types,
        knowledge_bases=knowledge_bases,
        use_knowledge_base=use_knowledge_base,
        context_preview=context[:1000],
        user_prompt=user_prompt,
    )

    try:
        max_tokens = 3600 if stage_key == "cases" else 1800
        completion = await call_chat_completion(
            api_url=llm_config["api_url"],
            api_key=llm_config["api_key"],
            model_name=llm_config["model_name"],
            messages=[
                {
                    "role": "system",
                    "content": "你是一位资深测试分析助手，擅长需求理解、测试点设计、审批确认和测试用例设计。",
                },
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=max_tokens,
            timeout=90.0,
        )
        _log_workflow_event(
            "workflow_generate_llm_response",
            requirement_id=requirement.get("id"),
            stage_key=stage_key,
            model_name=completion.get("model") or llm_config.get("model_name"),
            raw_response=completion.get("content", ""),
        )
        if stage_key != "cases":
            content = str(completion.get("content", "")).strip()
            if not content:
                raise ValueError("empty stage content")
            return content, []

        payload = extract_json_payload(completion["content"])
        _log_workflow_event(
            "workflow_generate_json_parsed",
            requirement_id=requirement.get("id"),
            stage_key=stage_key,
            parsed_keys=sorted(payload.keys()),
        )
        content = str(payload.get("content", "")).strip()
        cases = payload.get("cases", []) if isinstance(payload.get("cases"), list) else []
        normalized_cases = []
        default_case_type = case_types[0] if case_types else "functional"
        for index, item in enumerate(cases, start=1):
            normalized = _normalize_case(item, index, requirement.get("title", "需求"), default_case_type)
            if normalized:
                normalized_cases.append(normalized)
        if not normalized_cases:
            raise ValueError("empty cases")
        return content or "已生成结构化测试用例草稿。", normalized_cases
    except Exception as exc:
        logger.exception(
            "workflow_generate_failed requirement_id=%s stage_key=%s prompt_template_id=%s llm_config_id=%s",
            requirement.get("id"),
            stage_key,
            stage_prompt_template.get("id"),
            llm_config.get("id"),
        )
        _log_workflow_event(
            "workflow_generate_fallback",
            requirement_id=requirement.get("id"),
            stage_key=stage_key,
            reason=str(exc),
        )
        if stage_key == "cases":
            raise HTTPException(status_code=502, detail=f"生成用例失败：{exc}") from exc
        return _fallback_stage_result(
            stage_key,
            requirement,
            normalized_prompt,
            workflow,
            case_types=case_types,
            knowledge_bases=knowledge_bases,
            use_knowledge_base=use_knowledge_base,
        )


async def _generate_standalone_cases(
    prompt: str,
    case_types: list[str] | None = None,
    knowledge_bases: list[str] | None = None,
    image_data_urls: list[str] | None = None,
    use_knowledge_base: bool = False,
) -> tuple[str, list[dict], dict]:
    llm_config = get_active_llm_config()
    stage_prompt_template = _find_standalone_prompt_template()
    normalized_prompt = _normalize_prompt_text(prompt)
    normalized_case_types = [
        _normalize_case_type_key(item)
        for item in (case_types or [])
        if _normalize_case_type_key(item)
    ]
    normalized_knowledge_bases = [str(item).strip() for item in (knowledge_bases or []) if str(item).strip()]
    normalized_images = [str(item).strip() for item in (image_data_urls or []) if str(item).strip()]

    prompt_sections = [
        "Generate structured test cases based on the following information.",
        f"Prompt template: {stage_prompt_template.get('name', '')}",
        "System prompt:",
        stage_prompt_template.get("content", ""),
        f"User prompt: {normalized_prompt or 'None'}",
        f"Case types: {', '.join(normalized_case_types) if normalized_case_types else 'functional'}",
        f"Use knowledge base: {'yes' if use_knowledge_base else 'no'}",
        f"Knowledge bases: {', '.join(normalized_knowledge_bases) if normalized_knowledge_bases else 'None'}",
        f"Attached screenshots: {len(normalized_images)}",
        'Read the screenshots carefully and extract visible UI, fields, states, data patterns, actions, and validations before producing cases.',
        'Return JSON only in the shape {"content": string, "cases": array}. Each case must include test_point, title, preconditions, steps, expected, priority, case_type.',
    ]
    user_prompt = "\n".join(item for item in prompt_sections if item)

    user_content: list[dict[str, Any]] = [{"type": "text", "text": user_prompt}]
    for image_url in normalized_images:
        user_content.append({"type": "image_url", "image_url": {"url": image_url}})

    try:
        completion = await call_chat_completion(
            api_url=llm_config["api_url"],
            api_key=llm_config["api_key"],
            model_name=llm_config["model_name"],
            messages=[
                {
                    "role": "system",
                    "content": "You are a senior QA engineer. Read the provided text and screenshots, then return structured test cases in JSON only.",
                },
                {"role": "user", "content": user_content},
            ],
            temperature=0.2,
            max_tokens=3600,
            timeout=90.0,
        )
        payload = extract_json_payload(completion["content"])
        content = str(payload.get("content", "")).strip()
        raw_cases = payload.get("cases", []) if isinstance(payload.get("cases"), list) else []
        default_case_type = normalized_case_types[0] if normalized_case_types else "functional"
        normalized_cases: list[dict] = []
        for index, item in enumerate(raw_cases, start=1):
            normalized = _normalize_case(item, index, "Standalone case generation", default_case_type)
            if normalized:
                normalized_cases.append(normalized)
        if not normalized_cases:
            raise ValueError("empty cases")
        return content or "Generated test cases. You can continue editing and save them below.", normalized_cases, stage_prompt_template
    except Exception as exc:
        _log_workflow_event(
            "standalone_case_generate_fallback",
            reason=str(exc),
            case_types=normalized_case_types,
            knowledge_bases=normalized_knowledge_bases,
            use_knowledge_base=use_knowledge_base,
            image_count=len(normalized_images),
        )
        fallback_prompt = normalized_prompt
        if normalized_images:
            fallback_prompt = (fallback_prompt + "\n" if fallback_prompt else "") + f"Attached screenshots: {len(normalized_images)}"
        fallback_content, fallback_cases = _fallback_stage_result(
            "cases",
            {"title": "Standalone case generation", "summary": fallback_prompt},
            fallback_prompt,
            {"stages": []},
            case_types=normalized_case_types,
            knowledge_bases=normalized_knowledge_bases,
            use_knowledge_base=use_knowledge_base,
        )
        return fallback_content, fallback_cases, stage_prompt_template


def _sync_generated_cases(requirement_id: str, generated_cases: list[dict]) -> None:
    def identity_key(item: dict) -> tuple[str, str]:
        return (
            str(item.get("test_point", "")).strip(),
            str(item.get("title", "")).strip(),
        )

    existing_cases = [
        item
        for item in db.test_cases.values()
        if item["requirement_id"] == requirement_id
    ]
    existing_by_key: dict[tuple[str, str], dict] = {}
    for item in existing_cases:
        key = identity_key(item)
        if not any(key):
            continue
        current = existing_by_key.get(key)
        if current is None or current.get("source") != "workflow":
            existing_by_key[key] = item

    for index, item in enumerate(generated_cases, start=1):
        record_key = identity_key(item)
        existing = existing_by_key.get(record_key) if any(record_key) else None
        if existing:
            existing.update(
                {
                    "title": item.get("title") or existing.get("title") or f"自动生成用例-{index}",
                    "test_point": item.get("test_point", ""),
                    "preconditions": item.get("preconditions", []),
                    "steps": item.get("steps", []),
                    "expected": item.get("expected", []),
                    "priority": item.get("priority", "P2"),
                    "case_type": _normalize_case_type_key(item.get("case_type", "")),
                    "module_id": item.get("module_id", existing.get("module_id", "")) or "",
                    "stage": item.get("stage", existing.get("stage", "")),
                    "review_status": item.get("review_status", existing.get("review_status", "待审核")),
                    "creator": item.get("creator", existing.get("creator", "admin")),
                    "version": int(existing.get("version", 1) or 1) + 1,
                    "updated_at": now_iso(),
                }
            )
            continue

        case_id = db.new_id("test_cases")
        record = {
            "id": case_id,
            "requirement_id": requirement_id,
            "title": item.get("title") or f"自动生成用例-{index}",
            "test_point": item.get("test_point", ""),
            "preconditions": item.get("preconditions", []),
            "steps": item.get("steps", []),
            "expected": item.get("expected", []),
            "priority": item.get("priority", "P2"),
            "case_type": _normalize_case_type_key(item.get("case_type", "")),
            "module_id": "",
            "stage": item.get("stage", ""),
            "review_status": item.get("review_status", "待审核"),
            "creator": item.get("creator", "admin"),
            "version": 1,
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "source": "workflow",
        }
        db.test_cases[case_id] = db.clone(record)


@router.get("/generator/config")
async def get_standalone_case_generator_config() -> dict:
    prompt_template = _find_standalone_prompt_template()
    return {
        "template_name": prompt_template.get("name", ""),
        "template_content": prompt_template.get("content", ""),
    }


@router.post("/generator/generate")
async def generate_standalone_case_generator(payload: StandaloneCaseGeneratePayload) -> dict:
    content, generated_cases, prompt_template = await _generate_standalone_cases(
        prompt=payload.prompt,
        case_types=payload.case_types,
        knowledge_bases=payload.knowledge_bases,
        image_data_urls=payload.image_data_urls,
        use_knowledge_base=payload.use_knowledge_base,
    )
    return {
        "content": content,
        "generated_cases": generated_cases,
        "template_name": prompt_template.get("name", ""),
        "template_content": prompt_template.get("content", ""),
    }


@router.get("")
async def list_test_cases(
    requirement_id: str | None = None,
    keyword: str | None = None,
    priority: str | None = None,
    case_type: str | None = None,
    module_id: str | None = None,
    project_id: str | None = None,
    project: str | None = None,
    linked_only: bool | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=1000),
) -> dict:
    cases = list(db.test_cases.values())
    normalized_case_type = _normalize_case_type_key(case_type) if case_type else ""
    if requirement_id:
        cases = [item for item in cases if item["requirement_id"] == requirement_id]
    if linked_only:
        cases = [item for item in cases if item.get("requirement_id") not in {"", "manual_case_root", None}]
    resolved_project_id = project_id or project
    if resolved_project_id:
        cases = [
            item
            for item in cases
            if (db.requirements.get(item.get("requirement_id")) or {}).get("project_id", "") == resolved_project_id
        ]
    if module_id:
        cases = [item for item in cases if (item.get("module_id") or "") == module_id]
    if priority:
        cases = [item for item in cases if (item.get("priority") or "") == priority]
    if normalized_case_type:
        cases = [item for item in cases if (item.get("case_type") or "") == normalized_case_type]
    if keyword:
        normalized = keyword.strip().lower()
        cases = [
            item
            for item in cases
            if normalized in (item.get("title") or "").lower()
            or normalized in (item.get("test_point") or "").lower()
        ]
    cases.sort(key=lambda item: (item.get("updated_at", ""), item.get("created_at", ""), item.get("id", "")), reverse=True)
    total = len(cases)
    start = (page - 1) * page_size
    end = start + page_size
    page_items = [_serialize_test_case(item) for item in cases[start:end]]
    return {"items": page_items, "total": total, "page": page, "page_size": page_size}


@router.get("/sidebar")
async def get_test_case_sidebar() -> dict:
    return _build_case_sidebar_payload()


@router.get("/modules")
async def list_test_case_modules() -> list[dict]:
    modules = list(db.test_case_modules.values())
    return sorted(modules, key=lambda item: (item.get("sort_order", 0), item.get("created_at", ""), item.get("id", "")))


@router.post("/modules")
async def create_test_case_module(payload: TestCaseModuleIn) -> dict:
    if payload.parent_id and payload.parent_id not in db.test_case_modules:
        raise HTTPException(status_code=404, detail="Parent module not found")
    module_id = db.new_id("test_case_modules")
    siblings = [item for item in db.test_case_modules.values() if item.get("parent_id", "") == payload.parent_id]
    record = {
        "id": module_id,
        "name": payload.name.strip(),
        "parent_id": payload.parent_id,
        "sort_order": len(siblings) + 1,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    db.test_case_modules[module_id] = db.clone(record)
    return record


@router.put("/modules/{module_id}")
async def update_test_case_module(module_id: str, payload: TestCaseModuleIn) -> dict:
    module = db.test_case_modules.get(module_id)
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    if payload.parent_id == module_id:
        raise HTTPException(status_code=400, detail="Parent module is invalid")
    if payload.parent_id and payload.parent_id not in db.test_case_modules:
        raise HTTPException(status_code=404, detail="Parent module not found")
    module.update(
        {
            "name": payload.name.strip(),
            "parent_id": payload.parent_id,
            "updated_at": now_iso(),
        }
    )
    return module


@router.delete("/modules/{module_id}")
async def delete_test_case_module(module_id: str) -> dict:
    module = db.test_case_modules.get(module_id)
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    has_children = any(item.get("parent_id") == module_id for item in db.test_case_modules.values())
    if has_children:
        raise HTTPException(status_code=400, detail="Please delete child modules first")
    has_cases = any(item.get("module_id") == module_id for item in db.test_cases.values())
    if has_cases:
        raise HTTPException(status_code=400, detail="Please move or delete related test cases first")
    del db.test_case_modules[module_id]
    return {"ok": True}


@router.post("")
async def create_test_case(payload: TestCaseIn) -> dict:
    resolved_requirement_id = _resolve_requirement_id(payload.requirement_id)
    requirement = db.requirements.get(resolved_requirement_id)
    if not requirement:
        raise HTTPException(status_code=404, detail="Requirement not found")
    module = _resolve_module(payload.module_id)
    if payload.module_id and not module:
        raise HTTPException(status_code=404, detail="Module not found")
    case_id = db.new_id("test_cases")
    record = {
        "id": case_id,
        "requirement_id": resolved_requirement_id,
        "title": payload.title,
        "test_point": payload.test_point,
        "preconditions": payload.preconditions,
        "steps": payload.steps,
        "expected": payload.expected,
        "priority": payload.priority,
        "case_type": _normalize_case_type_key(payload.case_type),
        "module_id": payload.module_id if module else "",
        "stage": payload.stage,
        "review_status": payload.review_status or "待审核",
        "creator": payload.creator or "admin",
        "version": 1,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    db.test_cases[case_id] = db.clone(record)
    return _serialize_test_case(record)


@router.put("/{case_id}")
async def update_test_case(case_id: str, payload: TestCaseIn) -> dict:
    test_case = db.test_cases.get(case_id)
    if not test_case:
        raise HTTPException(status_code=404, detail="Test case not found")
    resolved_requirement_id = _resolve_requirement_id(payload.requirement_id)
    requirement = db.requirements.get(resolved_requirement_id)
    if not requirement:
        raise HTTPException(status_code=404, detail="Requirement not found")
    module = _resolve_module(payload.module_id)
    if payload.module_id and not module:
        raise HTTPException(status_code=404, detail="Module not found")
    test_case.update(
        {
            "requirement_id": resolved_requirement_id,
            "title": payload.title,
            "test_point": payload.test_point,
            "preconditions": payload.preconditions,
            "steps": payload.steps,
            "expected": payload.expected,
            "priority": payload.priority,
            "case_type": _normalize_case_type_key(payload.case_type),
            "module_id": payload.module_id if module else "",
            "stage": payload.stage,
            "review_status": payload.review_status or test_case.get("review_status", "待审核"),
            "creator": payload.creator or test_case.get("creator", "admin"),
            "version": test_case["version"] + 1,
            "updated_at": now_iso(),
        }
    )
    return _serialize_test_case(test_case)


@router.delete("/{case_id}")
async def delete_test_case(case_id: str) -> dict:
    if case_id not in db.test_cases:
        raise HTTPException(status_code=404, detail="Test case not found")
    del db.test_cases[case_id]
    return {"ok": True}


@router.get("/workflow/{requirement_id}")
async def get_test_case_workflow(requirement_id: str) -> dict:
    requirement = db.requirements.get(requirement_id)
    if not requirement:
        raise HTTPException(status_code=404, detail="Requirement not found")
    workflow = _normalize_workflow(requirement)
    return _serialize_workflow(requirement, workflow)


@router.put("/workflow/{requirement_id}/draft")
async def update_workflow_draft(requirement_id: str, payload: WorkflowDraftPayload) -> dict:
    requirement = db.requirements.get(requirement_id)
    if not requirement:
        raise HTTPException(status_code=404, detail="Requirement not found")
    workflow = _normalize_workflow(requirement)
    stage_index = _stage_index(payload.stage_key)
    stage = workflow["stages"][stage_index]
    selected_case_types = [_normalize_case_type_key(item) for item in payload.case_types if _normalize_case_type_key(item)]
    stage["content"] = payload.content
    stage["prompt"] = payload.prompt
    if payload.stage_key == "cases":
        normalized_cases = []
        default_case_type = selected_case_types[0] if selected_case_types else "functional"
        for index, item in enumerate(payload.generated_cases, start=1):
            normalized = _normalize_case(item, index, requirement.get("title", "需求"), default_case_type)
            if normalized:
                normalized_cases.append(normalized)
        stage["generated_cases"] = normalized_cases
        stage["case_types"] = selected_case_types or stage.get("case_types", [])
        stage["knowledge_bases"] = payload.knowledge_bases
        stage["use_knowledge_base"] = payload.use_knowledge_base
        _sync_generated_cases(requirement_id, normalized_cases)
    stage["updated_at"] = now_iso()
    workflow = _persist_workflow(requirement, workflow)
    return _serialize_workflow(requirement, workflow)


@router.post("/workflow/{requirement_id}/generate")
async def generate_workflow_stage(requirement_id: str, payload: WorkflowGeneratePayload) -> dict:
    requirement = db.requirements.get(requirement_id)
    if not requirement:
        raise HTTPException(status_code=404, detail="Requirement not found")
    workflow = _normalize_workflow(requirement)
    stage_index = _stage_index(payload.stage_key)
    if stage_index > workflow["current_stage_index"] and not workflow.get("completed"):
        raise HTTPException(status_code=400, detail="Current stage is locked")
    selected_case_types = [_normalize_case_type_key(item) for item in payload.case_types if _normalize_case_type_key(item)]

    _log_workflow_event(
        "workflow_generate_requested",
        requirement_id=requirement_id,
        stage_key=payload.stage_key,
        prompt=payload.prompt,
        case_types=selected_case_types,
        knowledge_bases=payload.knowledge_bases,
        use_knowledge_base=payload.use_knowledge_base,
        existing_generated_case_count=len(workflow["stages"][stage_index].get("generated_cases", [])),
    )

    content, generated_cases = await _generate_stage_result(
        requirement,
        workflow,
        payload.stage_key,
        payload.prompt,
        case_types=selected_case_types,
        knowledge_bases=payload.knowledge_bases,
        use_knowledge_base=payload.use_knowledge_base,
    )
    stage = workflow["stages"][stage_index]
    stage["prompt"] = payload.prompt
    stage["content"] = content
    stage["generated_cases"] = generated_cases
    if payload.stage_key == "cases":
        stage["case_types"] = selected_case_types or stage.get("case_types", [])
        stage["knowledge_bases"] = payload.knowledge_bases
        stage["use_knowledge_base"] = payload.use_knowledge_base
    stage["updated_at"] = now_iso()
    workflow = _persist_workflow(requirement, workflow)
    _log_workflow_event(
        "workflow_generate_completed",
        requirement_id=requirement_id,
        stage_key=payload.stage_key,
        content_length=len(content or ""),
        generated_case_count=len(generated_cases),
    )
    return _serialize_workflow(requirement, workflow)


@router.post("/workflow/{requirement_id}/snapshot")
async def save_workflow_snapshot(requirement_id: str, payload: WorkflowSnapshotPayload) -> dict:
    requirement = db.requirements.get(requirement_id)
    if not requirement:
        raise HTTPException(status_code=404, detail="Requirement not found")
    workflow = _normalize_workflow(requirement)
    stage_index = _stage_index(payload.stage_key)
    stage = workflow["stages"][stage_index]
    snapshot = {
        "id": db.new_id("workflow_snapshots"),
        "saved_at": now_iso(),
        "note": payload.note or f"{stage['title']}快照",
        "content": stage.get("content", ""),
        "prompt": stage.get("prompt", ""),
        "generated_cases": deepcopy(stage.get("generated_cases", [])),
    }
    stage["snapshots"] = [snapshot, *stage.get("snapshots", [])]
    stage["updated_at"] = now_iso()
    workflow = _persist_workflow(requirement, workflow)
    return _serialize_workflow(requirement, workflow)


@router.post("/workflow/{requirement_id}/confirm")
async def confirm_workflow_stage(requirement_id: str, payload: WorkflowDraftPayload) -> dict:
    requirement = db.requirements.get(requirement_id)
    if not requirement:
        raise HTTPException(status_code=404, detail="Requirement not found")
    workflow = _normalize_workflow(requirement)
    stage_index = _stage_index(payload.stage_key)
    if stage_index != workflow["current_stage_index"] and not workflow.get("completed"):
        raise HTTPException(status_code=400, detail="Only the current active stage can be confirmed")

    stage = workflow["stages"][stage_index]
    selected_case_types = [_normalize_case_type_key(item) for item in payload.case_types if _normalize_case_type_key(item)]
    stage["content"] = payload.content
    stage["prompt"] = payload.prompt
    if payload.stage_key == "cases":
        normalized_cases = []
        default_case_type = selected_case_types[0] if selected_case_types else "functional"
        for index, item in enumerate(payload.generated_cases, start=1):
            normalized = _normalize_case(item, index, requirement.get("title", "需求"), default_case_type)
            if normalized:
                normalized_cases.append(normalized)
        stage["generated_cases"] = normalized_cases
        stage["case_types"] = selected_case_types or stage.get("case_types", [])
        stage["knowledge_bases"] = payload.knowledge_bases
        stage["use_knowledge_base"] = payload.use_knowledge_base
        _sync_generated_cases(requirement_id, normalized_cases)
    stage["confirmed_at"] = now_iso()
    stage["updated_at"] = now_iso()

    if stage_index >= len(workflow["stages"]) - 1:
        workflow["completed"] = True
    else:
        workflow["current_stage_index"] = stage_index + 1
    workflow = _persist_workflow(requirement, workflow)
    return _serialize_workflow(requirement, workflow)


@router.post("/workflow/{requirement_id}/rollback")
async def rollback_workflow_stage(requirement_id: str, payload: WorkflowRollbackPayload) -> dict:
    requirement = db.requirements.get(requirement_id)
    if not requirement:
        raise HTTPException(status_code=404, detail="Requirement not found")
    workflow = _normalize_workflow(requirement)
    stage_index = _stage_index(payload.stage_key)
    workflow["current_stage_index"] = stage_index
    workflow["completed"] = False
    current_time = now_iso()

    target_stage = workflow["stages"][stage_index]
    target_stage["confirmed_at"] = None
    target_stage["updated_at"] = current_time

    for index in range(stage_index + 1, len(workflow["stages"])):
        reset_stage = _build_default_stage(workflow["stages"][index]["key"])
        reset_stage["updated_at"] = current_time
        workflow["stages"][index] = reset_stage

    workflow = _persist_workflow(requirement, workflow)
    return _serialize_workflow(requirement, workflow)
