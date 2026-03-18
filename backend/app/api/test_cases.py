import json
from copy import deepcopy

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.llm_client import (
    call_chat_completion,
    extract_json_payload,
    get_active_llm_config,
)
from app.store.memory_db import db, now_iso


router = APIRouter()

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
KNOWLEDGE_BASE_OPTIONS = [
    "需求文档知识库",
    "历史用例知识库",
    "缺陷案例知识库",
    "接口文档知识库",
]
TEST_CASE_STAGE_PROMPTS = {
    "clarify": {
        "name": "测试用例-需求澄清",
        "title": "需求澄清",
        "subtitle": "先澄清模型对需求的理解、风险与待确认问题。",
        "button_text": "生成需求澄清",
        "description": "用于从需求文档中提炼测试前必须澄清的问题、范围和风险。",
        "default_content": (
            "你是一位资深测试分析师。请基于输入的需求信息输出“需求澄清”结果，帮助测试人员在编写测试点和测试用例前完成信息补齐。\n"
            "输出要求：\n"
            "1. 先给出对需求目标、核心流程、关键角色的理解。\n"
            "2. 列出阻碍测试设计的关键信息缺口，优先关注业务规则、输入输出、异常处理、权限、状态流转、依赖系统、验收标准。\n"
            "3. 给出建议向产品或研发确认的问题清单，问题要具体、可回答。\n"
            "4. 给出主要测试风险和可能造成的影响。\n"
            "5. 使用清晰分段和项目符号，内容可直接给测试人员使用。"
        ),
    },
    "test_points": {
        "name": "测试用例-测试点梳理",
        "title": "测试点梳理",
        "subtitle": "把需求拆成可验证、可执行的测试点。",
        "button_text": "生成测试点",
        "description": "用于按测试设计视角梳理功能、边界、异常和兼容等测试点。",
        "default_content": (
            "你是一位资深测试设计专家。请基于需求正文以及前序阶段结论，输出“测试点梳理”结果。\n"
            "输出要求：\n"
            "1. 按模块或流程拆解测试点，优先覆盖主流程、分支流程、边界条件、异常处理、权限控制、数据校验、状态流转。\n"
            "2. 明确每个测试点的验证目标，避免只写标题不写检查点。\n"
            "3. 补充接口联动、数据一致性、兼容性、性能和稳定性等非功能测试点。\n"
            "4. 对高风险测试点进行单独标记并说明原因。\n"
            "5. 输出要结构化，便于后续直接转成测试用例。"
        ),
    },
    "review": {
        "name": "测试用例-审批确认",
        "title": "审批确认",
        "subtitle": "确认范围、优先级、通过标准与遗留风险。",
        "button_text": "生成审批确认",
        "description": "用于在测试点基础上形成提测前的确认清单、优先级和准出建议。",
        "default_content": (
            "你是一位测试负责人，请基于需求正文、需求澄清和测试点梳理结果，输出“审批确认”结论。\n"
            "输出要求：\n"
            "1. 明确本次测试范围、非测试范围和优先级建议。\n"
            "2. 给出进入测试执行前需要确认的前置条件、测试数据准备、环境依赖、角色权限和联调条件。\n"
            "3. 明确通过标准和验收口径，尤其是哪些结果可判定为通过、失败、阻塞。\n"
            "4. 列出尚未解决但需要知会的遗留风险、假设条件和规避建议。\n"
            "5. 内容适合评审和审批场景，语言简洁明确。"
        ),
    },
    "cases": {
        "name": "测试用例-生成用例",
        "title": "生成用例",
        "subtitle": "按确认结果产出结构化测试用例。",
        "button_text": "生成测试用例",
        "description": "用于生成可执行、可编辑、可直接入库的结构化测试用例。",
        "default_content": (
            "你是一位资深测试工程师。请基于需求正文及前序阶段结果，生成结构化测试用例。\n"
            "输出要求：\n"
            "1. 优先覆盖核心业务流、关键异常分支、边界场景、权限差异、状态流转和高风险点。\n"
            "2. 每条用例都要包含 test_point、title、preconditions、steps、expected、priority、case_type。\n"
            "3. steps 必须是可执行动作，expected 必须是可验证结果，禁止笼统描述。\n"
            "4. priority 使用 P1/P2/P3，P1 表示核心高风险场景。\n"
            "5. case_type 必须从用户选中的用例类型中选择。"
        ),
    },
}
WORKFLOW_STAGES = [
    {key: value for key, value in meta.items() if key in {"title", "subtitle", "button_text"}} | {"key": key}
    for key, meta in TEST_CASE_STAGE_PROMPTS.items()
]
WORKFLOW_STAGE_MAP = {item["key"]: item for item in WORKFLOW_STAGES}


class TestCaseIn(BaseModel):
    requirement_id: str = ""
    title: str = Field(min_length=1, max_length=200)
    test_point: str = ""
    preconditions: list[str] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    expected: list[str] = Field(default_factory=list)
    priority: str = "P2"
    case_type: str = ""
    module: str = ""
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


class WorkflowSnapshotPayload(BaseModel):
    stage_key: str
    note: str = ""


class WorkflowRollbackPayload(BaseModel):
    stage_key: str


class TestCaseModuleIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    parent_id: str = ""


def _find_stage_prompt_template(stage_key: str) -> dict:
    stage_meta = TEST_CASE_STAGE_PROMPTS[stage_key]
    candidates = [
        item
        for item in db.prompt_templates.values()
        if item.get("enabled")
        and item.get("prompt_type") == TEST_CASE_PROMPT_TYPE
        and item.get("name") == stage_meta["name"]
    ]
    if candidates:
        candidates.sort(key=lambda item: item.get("updated_at", ""), reverse=True)
        return candidates[0]
    return {
        "id": "",
        "prompt_type": TEST_CASE_PROMPT_TYPE,
        "name": stage_meta["name"],
        "description": stage_meta["description"],
        "content": stage_meta["default_content"],
        "remark": "system-default",
        "enabled": True,
        "is_default": False,
    }


def _resolve_requirement_id(requirement_id: str) -> str:
    return requirement_id or db.MANUAL_CASE_REQUIREMENT_ID


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
        "case_types": ["功能测试"] if stage_key == "cases" else [],
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
    case_type = str(case_item.get("case_type", default_case_type)).strip()
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
    workflow["current_stage_index"] = min(max(int(raw.get("current_stage_index", 0) or 0), 0), len(WORKFLOW_STAGES) - 1)
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
        current["case_types"] = list(saved.get("case_types", current["case_types"]))
        current["knowledge_bases"] = list(saved.get("knowledge_bases", []))
        current["use_knowledge_base"] = bool(saved.get("use_knowledge_base", False))
        stages.append(current)
    workflow["stages"] = stages
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
                "case_type_options": CASE_TYPE_OPTIONS if stage["key"] == "cases" else [],
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
    title = requirement.get("title", "当前需求")
    summary = requirement.get("summary", requirement.get("body_text", "")[:120])
    if stage_key == "clarify":
        content = (
            f"一、需求理解\n- 当前需求围绕“{title}”展开，需优先明确目标、主流程和验收边界。\n"
            f"- 需求摘要：{summary}\n\n"
            "二、待澄清问题\n"
            "- 关键输入、输出及业务规则是否已经完整定义。\n"
            "- 异常分支、权限差异、失败处理是否有明确约束。\n"
            "- 验收口径是否可以直接支持测试通过/失败判定。\n\n"
            "三、主要风险\n"
            "- 若关键规则缺失，后续测试点和测试用例会出现覆盖不足或口径不一致。\n"
        )
        if prompt:
            content += f"\n四、人工补充关注点\n- {prompt}\n"
        return content, []
    if stage_key == "test_points":
        content = (
            "一、核心测试点\n"
            "- 主流程成功路径\n"
            "- 关键字段校验与边界值\n"
            "- 失败提示与异常恢复\n"
            "- 权限/角色差异\n\n"
            "二、补充测试点\n"
            "- 外部系统或接口联动\n"
            "- 数据一致性与状态流转\n"
            "- 非功能项：性能、稳定性、兼容性\n"
        )
        if prompt:
            content += f"\n三、额外关注\n- {prompt}\n"
        return content, []
    if stage_key == "review":
        content = (
            "一、审批确认结论\n"
            "- 当前测试范围可继续推进，但建议先明确关键边界和通过标准。\n\n"
            "二、待确认项\n"
            "- 是否所有关键场景都具备明确可验证结果。\n"
            "- 是否已有统一的前置数据准备方案。\n"
            "- 是否需要补充高优先级风险场景。\n"
        )
        if prompt:
            content += f"\n三、人工补充要求\n- {prompt}\n"
        return content, []

    resolved_case_types = case_types or ["功能测试"]
    cases = [
        {
            "title": f"{title}-主流程验证",
            "test_point": "核心业务主流程",
            "preconditions": ["准备满足前置条件的数据和账号"],
            "priority": "P1",
            "steps": ["准备测试数据", "执行主流程操作", "检查执行结果"],
            "expected": ["页面或接口返回成功", "状态变更正确", "无异常提示"],
            "case_type": resolved_case_types[0],
        },
        {
            "title": f"{title}-异常路径验证",
            "test_point": "异常输入与失败提示",
            "preconditions": ["准备非法或缺失输入样例"],
            "priority": "P1",
            "steps": ["构造非法或缺失输入", "执行操作", "观察错误提示和回滚行为"],
            "expected": ["系统阻止非法提交", "错误提示明确", "无脏数据残留"],
            "case_type": resolved_case_types[min(1, len(resolved_case_types) - 1)],
        },
    ]
    content = "已生成结构化测试用例草稿，可在下方继续编辑并保存。"
    if prompt:
        content += f"\n额外关注：{prompt}"
    if use_knowledge_base and knowledge_bases:
        content += f"\n已结合知识库：{'、'.join(knowledge_bases)}"
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
    case_types = case_types or []
    knowledge_bases = knowledge_bases or []

    if stage_key == "cases":
        schema = {
            "content": "",
            "cases": [
                {
                    "test_point": "",
                    "title": "",
                    "preconditions": [""],
                    "steps": [""],
                    "expected": [""],
                    "priority": "P2",
                    "case_type": "",
                }
            ],
        }
        stage_instruction = (
            "请输出结构化测试用例，字段必须包含 test_point、title、preconditions、steps、expected、priority、case_type。"
        )
    else:
        schema = {"content": ""}
        stage_instruction = f"请输出“{WORKFLOW_STAGE_MAP[stage_key]['title']}”阶段结果。"

    extra_sections = []
    if stage_key == "cases":
        extra_sections.extend(
            [
                f"用户选择的用例类型：{'、'.join(case_types) if case_types else '功能测试'}",
                f"是否使用知识库：{'是' if use_knowledge_base else '否'}",
                f"选择的知识库：{'、'.join(knowledge_bases) if knowledge_bases else '无'}",
                "请确保 case_type 必须从用户选择的用例类型中取值。",
            ]
        )

    user_prompt = "\n".join(
        [
            f"当前阶段：{WORKFLOW_STAGE_MAP[stage_key]['title']}",
            stage_instruction,
            f"阶段提示词模板名称：{stage_prompt_template.get('name', '')}",
            "阶段提示词模板内容：",
            stage_prompt_template.get("content", ""),
            f"人工补充提示词：{prompt or '无'}",
            *extra_sections,
            context,
            "请严格输出 JSON，不要输出额外解释。JSON 结构如下：",
            json.dumps(schema, ensure_ascii=False),
        ]
    )

    try:
        completion = await call_chat_completion(
            api_url=llm_config["api_url"],
            api_key=llm_config["api_key"],
            model_name=llm_config["model_name"],
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是一位资深测试分析助手，擅长需求理解、测试点设计、审批确认和测试用例设计。"
                        "你必须输出符合要求的 JSON。"
                    ),
                },
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=1800,
            timeout=90.0,
        )
        payload = extract_json_payload(completion["content"])
        content = str(payload.get("content", "")).strip()
        cases = payload.get("cases", []) if isinstance(payload.get("cases"), list) else []
        normalized_cases = []
        default_case_type = case_types[0] if case_types else "功能测试"
        for index, item in enumerate(cases, start=1):
            normalized = _normalize_case(item, index, requirement.get("title", "需求"), default_case_type)
            if normalized:
                normalized_cases.append(normalized)
        if not content and stage_key != "cases":
            raise ValueError("empty stage content")
        if stage_key == "cases" and not normalized_cases:
            raise ValueError("empty cases")
        return content or "已生成结构化测试用例草稿。", normalized_cases
    except Exception:
        return _fallback_stage_result(
            stage_key,
            requirement,
            prompt,
            workflow,
            case_types=case_types,
            knowledge_bases=knowledge_bases,
            use_knowledge_base=use_knowledge_base,
        )


def _sync_generated_cases(requirement_id: str, generated_cases: list[dict]) -> None:
    requirement = db.requirements.get(requirement_id)
    module_name = requirement.get("title", "") if requirement else ""
    existing = [
        item
        for item in db.test_cases.values()
        if item["requirement_id"] == requirement_id and item.get("source") == "workflow"
    ]
    for item in existing:
        del db.test_cases[item["id"]]

    for index, item in enumerate(generated_cases, start=1):
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
            "case_type": item.get("case_type", ""),
            "module": item.get("module") or module_name,
            "stage": item.get("stage", ""),
            "review_status": item.get("review_status", "待审核"),
            "creator": item.get("creator", "admin"),
            "version": 1,
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "source": "workflow",
        }
        db.test_cases[case_id] = db.clone(record)


@router.get("")
async def list_test_cases(requirement_id: str | None = None) -> list[dict]:
    cases = list(db.test_cases.values())
    if requirement_id:
        return [item for item in cases if item["requirement_id"] == requirement_id]
    return cases


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
    has_cases = any(item.get("module") == module.get("name") for item in db.test_cases.values())
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
        "case_type": payload.case_type,
        "module": payload.module or (requirement.get("title", "") if requirement else ""),
        "stage": payload.stage,
        "review_status": payload.review_status or "待审核",
        "creator": payload.creator or "admin",
        "version": 1,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    db.test_cases[case_id] = db.clone(record)
    return record


@router.put("/{case_id}")
async def update_test_case(case_id: str, payload: TestCaseIn) -> dict:
    test_case = db.test_cases.get(case_id)
    if not test_case:
        raise HTTPException(status_code=404, detail="Test case not found")
    resolved_requirement_id = _resolve_requirement_id(payload.requirement_id)
    requirement = db.requirements.get(resolved_requirement_id)
    if not requirement:
        raise HTTPException(status_code=404, detail="Requirement not found")
    test_case.update(
        {
            "requirement_id": resolved_requirement_id,
            "title": payload.title,
            "test_point": payload.test_point,
            "preconditions": payload.preconditions,
            "steps": payload.steps,
            "expected": payload.expected,
            "priority": payload.priority,
            "case_type": payload.case_type,
            "module": payload.module or (requirement.get("title", "") if requirement else test_case.get("module", "")),
            "stage": payload.stage,
            "review_status": payload.review_status or test_case.get("review_status", "待审核"),
            "creator": payload.creator or test_case.get("creator", "admin"),
            "version": test_case["version"] + 1,
            "updated_at": now_iso(),
        }
    )
    return test_case


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
    stage["content"] = payload.content
    stage["prompt"] = payload.prompt
    if payload.stage_key == "cases":
        normalized_cases = []
        default_case_type = payload.case_types[0] if payload.case_types else "功能测试"
        for index, item in enumerate(payload.generated_cases, start=1):
            normalized = _normalize_case(item, index, requirement.get("title", "需求"), default_case_type)
            if normalized:
                normalized_cases.append(normalized)
        stage["generated_cases"] = normalized_cases
        stage["case_types"] = payload.case_types or stage.get("case_types", [])
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

    content, generated_cases = await _generate_stage_result(
        requirement,
        workflow,
        payload.stage_key,
        payload.prompt,
        case_types=payload.case_types,
        knowledge_bases=payload.knowledge_bases,
        use_knowledge_base=payload.use_knowledge_base,
    )
    stage = workflow["stages"][stage_index]
    stage["prompt"] = payload.prompt
    stage["content"] = content
    stage["generated_cases"] = generated_cases
    if payload.stage_key == "cases":
        stage["case_types"] = payload.case_types or stage.get("case_types", [])
        stage["knowledge_bases"] = payload.knowledge_bases
        stage["use_knowledge_base"] = payload.use_knowledge_base
    stage["updated_at"] = now_iso()
    workflow = _persist_workflow(requirement, workflow)
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
    stage["content"] = payload.content
    stage["prompt"] = payload.prompt
    if payload.stage_key == "cases":
        normalized_cases = []
        default_case_type = payload.case_types[0] if payload.case_types else "功能测试"
        for index, item in enumerate(payload.generated_cases, start=1):
            normalized = _normalize_case(item, index, requirement.get("title", "需求"), default_case_type)
            if normalized:
                normalized_cases.append(normalized)
        stage["generated_cases"] = normalized_cases
        stage["case_types"] = payload.case_types or stage.get("case_types", [])
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
    for index in range(stage_index, len(workflow["stages"])):
        workflow["stages"][index]["confirmed_at"] = None
        workflow["stages"][index]["updated_at"] = now_iso()
    workflow = _persist_workflow(requirement, workflow)
    return _serialize_workflow(requirement, workflow)
