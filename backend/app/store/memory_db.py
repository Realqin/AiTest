from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import Boolean, DateTime, Integer, JSON, String, Text, create_engine, delete, func, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker


def now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _parse_iso(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def _format_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat(timespec="seconds") + "Z"


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AITEST_", env_file=".env", extra="ignore")

    database_url: str = "mysql+pymysql://root:root@127.0.0.1:3306/aitest?charset=utf8mb4"
    echo_sql: bool = False


class Base(DeclarativeBase):
    pass


class IdSequenceRecord(Base):
    __tablename__ = "id_sequences"

    scope: Mapped[str] = mapped_column(String(64), primary_key=True)
    current_value: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class StructuredRecordMixin:
    iso_datetime_fields: tuple[str, ...] = ()

    @classmethod
    def core_field_names(cls) -> tuple[str, ...]:
        return tuple(
            column.name
            for column in cls.__table__.columns
            if column.name not in {"extra_data"} and not column.name.startswith("_")
        )

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "StructuredRecordMixin":
        record = cls()
        record.apply_payload(payload)
        return record

    def apply_payload(self, payload: dict[str, Any]) -> None:
        extra = deepcopy(payload)
        for field_name in self.core_field_names():
            if field_name not in payload:
                continue
            value = payload[field_name]
            if field_name in self.iso_datetime_fields:
                value = _parse_iso(value)
            setattr(self, field_name, deepcopy(value))
            extra.pop(field_name, None)
        self.extra_data = extra

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        for field_name in self.core_field_names():
            value = getattr(self, field_name)
            if field_name in self.iso_datetime_fields:
                value = _format_iso(value)
            payload[field_name] = deepcopy(value)
        if getattr(self, "extra_data", None):
            payload.update(deepcopy(self.extra_data))
        return payload


class ProjectRecord(StructuredRecordMixin, Base):
    __tablename__ = "projects"

    iso_datetime_fields = ("created_at", "updated_at")

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    creator: Mapped[str] = mapped_column(String(50), nullable=False, default="admin", index=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    extra_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class RequirementRecord(StructuredRecordMixin, Base):
    __tablename__ = "requirements"

    iso_datetime_fields = ("created_at", "updated_at")

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    body_text: Mapped[str] = mapped_column(Text, nullable=False)
    project: Mapped[str] = mapped_column(String(100), nullable=False, default="演示项目", index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="草稿", index=True)
    creator: Mapped[str] = mapped_column(String(50), nullable=False, default="admin", index=True)
    summary: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    start_date: Mapped[str | None] = mapped_column(String(32), nullable=True)
    end_date: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_date: Mapped[str] = mapped_column(String(10), nullable=False, default="")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    import_method: Mapped[str] = mapped_column(String(20), nullable=False, default="manual", index=True)
    source_name: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    source_url: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    file_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    stored_file_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    preview_type: Mapped[str] = mapped_column(String(20), nullable=False, default="text")
    preview_html: Mapped[str] = mapped_column(Text, nullable=False, default="")
    review_status: Mapped[str] = mapped_column(String(20), nullable=False, default="待评审", index=True)
    latest_review_run_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    extra_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class TestCaseRecord(StructuredRecordMixin, Base):
    __tablename__ = "test_cases"

    iso_datetime_fields = ("created_at", "updated_at")

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    requirement_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    steps: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    expected: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    priority: Mapped[str] = mapped_column(String(10), nullable=False, default="P2", index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    extra_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class TestCaseModuleRecord(StructuredRecordMixin, Base):
    __tablename__ = "test_case_modules"

    iso_datetime_fields = ("created_at", "updated_at")

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    parent_id: Mapped[str] = mapped_column(String(64), nullable=False, default="", index=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    extra_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class AgentConfigRecord(StructuredRecordMixin, Base):
    __tablename__ = "agent_configs"

    iso_datetime_fields = ("created_at", "updated_at")

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    role: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    prompt_template: Mapped[str] = mapped_column(Text, nullable=False)
    model_policy: Mapped[str] = mapped_column(String(50), nullable=False, default="balanced")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    extra_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class LlmConfigRecord(StructuredRecordMixin, Base):
    __tablename__ = "llm_configs"

    iso_datetime_fields = ("created_at", "updated_at")

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    api_url: Mapped[str] = mapped_column(String(500), nullable=False)
    api_key: Mapped[str] = mapped_column(String(500), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    context_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=128000)
    vision_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    stream_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    extra_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class PromptTemplateRecord(StructuredRecordMixin, Base):
    __tablename__ = "prompt_templates"

    iso_datetime_fields = ("created_at", "updated_at")

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    prompt_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    remark: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    extra_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class MCPToolRecord(StructuredRecordMixin, Base):
    __tablename__ = "mcp_tools"

    iso_datetime_fields = ("created_at", "updated_at")

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    endpoint: Mapped[str] = mapped_column(String(1000), nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    extra_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class ReviewRunRecord(StructuredRecordMixin, Base):
    __tablename__ = "review_runs"

    iso_datetime_fields = ("started_at", "finished_at", "created_at", "updated_at")

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    requirement_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running", index=True)
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_step: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    model: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    route_reason: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    llm_config_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    prompt_template_name: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    checks: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    results: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    check_prompt_map: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    extra_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class RequirementVersionRecord(StructuredRecordMixin, Base):
    __tablename__ = "requirement_versions"

    iso_datetime_fields = ("created_at",)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    requirement_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    extra_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class RequirementReviewRecord(Base):
    __tablename__ = "requirement_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    requirement_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class ListFieldProxy(list):
    def __init__(self, parent: "RecordProxy", field_name: str, values: list[Any]) -> None:
        super().__init__(deepcopy(values))
        self._parent = parent
        self._field_name = field_name

    def _commit(self) -> None:
        self._parent._set_nested_list(self._field_name, list(self))

    def append(self, item: Any) -> None:
        super().append(item)
        self._commit()

    def extend(self, values: list[Any]) -> None:
        super().extend(values)
        self._commit()

    def clear(self) -> None:
        super().clear()
        self._commit()

    def pop(self, index: int = -1) -> Any:
        item = super().pop(index)
        self._commit()
        return item

    def __setitem__(self, index: int, value: Any) -> None:
        super().__setitem__(index, value)
        self._commit()

    def __delitem__(self, index: int) -> None:
        super().__delitem__(index)
        self._commit()


class RecordProxy(dict):
    def __init__(self, repository: "StructuredRepository", payload: dict[str, Any]) -> None:
        super().__init__(deepcopy(payload))
        self._repository = repository

    def _persist(self) -> None:
        self._repository.save(dict(self))

    def _set_nested_list(self, field_name: str, values: list[Any]) -> None:
        dict.__setitem__(self, field_name, values)
        self._persist()

    def __getitem__(self, key: str) -> Any:
        value = dict.__getitem__(self, key)
        if isinstance(value, list):
            return ListFieldProxy(self, key, value)
        return value

    def __setitem__(self, key: str, value: Any) -> None:
        dict.__setitem__(self, key, value)
        self._persist()

    def update(self, *args: Any, **kwargs: Any) -> None:
        dict.update(self, *args, **kwargs)
        self._persist()

    def pop(self, key: str, default: Any = None) -> Any:
        value = dict.pop(self, key, default)
        self._persist()
        return value


class PersistentListProxy(list):
    def __init__(self, repository: "ListRepositoryBase", owner_id: str, values: list[Any]) -> None:
        super().__init__(deepcopy(values))
        self._repository = repository
        self._owner_id = owner_id

    def append(self, item: Any) -> None:
        super().append(item)
        self._repository.append(self._owner_id, item)


class StructuredRepository:
    def __init__(self, session_factory: sessionmaker[Session], model: type[StructuredRecordMixin]) -> None:
        self._session_factory = session_factory
        self._model = model

    def _build_proxy(self, row: StructuredRecordMixin) -> RecordProxy:
        return RecordProxy(self, row.to_payload())

    def save(self, payload: dict[str, Any]) -> dict[str, Any]:
        payload = deepcopy(payload)
        record_id = payload["id"]
        with self._session_factory() as session:
            row = session.get(self._model, record_id)
            if row is None:
                row = self._model.from_payload(payload)
                session.add(row)
            else:
                row.apply_payload(payload)
            session.commit()
        return payload

    def get(self, record_id: str) -> RecordProxy | None:
        with self._session_factory() as session:
            row = session.get(self._model, record_id)
            if row is None:
                return None
            return self._build_proxy(row)

    def values(self) -> list[RecordProxy]:
        with self._session_factory() as session:
            order_field = getattr(self._model, "created_at", self._model.id)
            rows = session.execute(select(self._model).order_by(order_field.asc())).scalars().all()
            return [self._build_proxy(row) for row in rows]

    def items(self) -> list[tuple[str, RecordProxy]]:
        values = self.values()
        return [(item["id"], item) for item in values]

    def __getitem__(self, record_id: str) -> RecordProxy:
        item = self.get(record_id)
        if item is None:
            raise KeyError(record_id)
        return item

    def __setitem__(self, record_id: str, payload: dict[str, Any]) -> None:
        payload = deepcopy(payload)
        payload["id"] = record_id
        self.save(payload)

    def __delitem__(self, record_id: str) -> None:
        with self._session_factory() as session:
            row = session.get(self._model, record_id)
            if row is None:
                raise KeyError(record_id)
            session.delete(row)
            session.commit()

    def __contains__(self, record_id: str) -> bool:
        with self._session_factory() as session:
            return session.get(self._model, record_id) is not None

    def pop(self, record_id: str, default: Any = None) -> Any:
        item = self.get(record_id)
        if item is None:
            return default
        self.__delitem__(record_id)
        return dict(item)


class ListRepositoryBase:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def get(self, owner_id: str, default: Any = None) -> list[Any]:
        values = self._load(owner_id)
        if not values and default is not None:
            return default
        return values

    def __getitem__(self, owner_id: str) -> PersistentListProxy:
        return PersistentListProxy(self, owner_id, self._load(owner_id))

    def pop(self, owner_id: str, default: Any = None) -> Any:
        values = self._load(owner_id)
        if not values:
            return default
        self.delete_all(owner_id)
        return values

    def delete_all(self, owner_id: str) -> None:
        raise NotImplementedError

    def append(self, owner_id: str, item: Any) -> None:
        raise NotImplementedError

    def _load(self, owner_id: str) -> list[Any]:
        raise NotImplementedError


class RequirementVersionRepository(ListRepositoryBase):
    def _load(self, owner_id: str) -> list[Any]:
        with self._session_factory() as session:
            rows = session.execute(
                select(RequirementVersionRecord)
                .where(RequirementVersionRecord.requirement_id == owner_id)
                .order_by(RequirementVersionRecord.position.asc())
            ).scalars().all()
            return [row.to_payload() for row in rows]

    def append(self, owner_id: str, item: Any) -> None:
        with self._session_factory() as session:
            next_position = (
                session.execute(
                    select(func.max(RequirementVersionRecord.position)).where(
                        RequirementVersionRecord.requirement_id == owner_id
                    )
                ).scalar_one()
                or 0
            ) + 1
            payload = deepcopy(item)
            row = RequirementVersionRecord.from_payload(
                {
                    "requirement_id": owner_id,
                    "position": next_position,
                    "version": payload.get("version", next_position),
                    "content": payload.get("content", ""),
                    "created_at": payload.get("created_at", now_iso()),
                    **payload,
                }
            )
            session.add(row)
            session.commit()

    def delete_all(self, owner_id: str) -> None:
        with self._session_factory() as session:
            session.execute(delete(RequirementVersionRecord).where(RequirementVersionRecord.requirement_id == owner_id))
            session.commit()


class RequirementReviewRepository(ListRepositoryBase):
    def _load(self, owner_id: str) -> list[Any]:
        with self._session_factory() as session:
            rows = session.execute(
                select(RequirementReviewRecord)
                .where(RequirementReviewRecord.requirement_id == owner_id)
                .order_by(RequirementReviewRecord.position.asc())
            ).scalars().all()
            return [row.run_id for row in rows]

    def append(self, owner_id: str, item: Any) -> None:
        with self._session_factory() as session:
            next_position = (
                session.execute(
                    select(func.max(RequirementReviewRecord.position)).where(
                        RequirementReviewRecord.requirement_id == owner_id
                    )
                ).scalar_one()
                or 0
            ) + 1
            session.add(
                RequirementReviewRecord(
                    requirement_id=owner_id,
                    position=next_position,
                    run_id=str(item),
                )
            )
            session.commit()

    def delete_all(self, owner_id: str) -> None:
        with self._session_factory() as session:
            session.execute(delete(RequirementReviewRecord).where(RequirementReviewRecord.requirement_id == owner_id))
            session.commit()


class DatabaseStore:
    MANUAL_CASE_REQUIREMENT_ID = "manual_case_root"

    def __init__(self) -> None:
        settings = DatabaseSettings()
        self.engine = create_engine(settings.database_url, echo=settings.echo_sql, pool_pre_ping=True)
        self.session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)
        Base.metadata.create_all(self.engine)

        self.projects = StructuredRepository(self.session_factory, ProjectRecord)
        self.requirements = StructuredRepository(self.session_factory, RequirementRecord)
        self.test_cases = StructuredRepository(self.session_factory, TestCaseRecord)
        self.test_case_modules = StructuredRepository(self.session_factory, TestCaseModuleRecord)
        self.agent_configs = StructuredRepository(self.session_factory, AgentConfigRecord)
        self.llm_configs = StructuredRepository(self.session_factory, LlmConfigRecord)
        self.prompt_templates = StructuredRepository(self.session_factory, PromptTemplateRecord)
        self.mcp_tools = StructuredRepository(self.session_factory, MCPToolRecord)
        self.review_runs = StructuredRepository(self.session_factory, ReviewRunRecord)
        self.requirement_versions = RequirementVersionRepository(self.session_factory)
        self.requirement_reviews = RequirementReviewRepository(self.session_factory)
        self._seed_admin_data()

    def new_id(self, scope: str = "global") -> str:
        with self.session_factory() as session:
            row = session.execute(
                select(IdSequenceRecord).where(IdSequenceRecord.scope == scope).with_for_update()
            ).scalar_one_or_none()
            if row is None:
                row = IdSequenceRecord(scope=scope, current_value=0)
                session.add(row)
                session.flush()
            row.current_value += 1
            next_value = row.current_value
            session.commit()
        return f"{next_value:012d}"

    def clone(self, payload: dict[str, Any]) -> dict[str, Any]:
        return deepcopy(dict(payload))

    def _seed_admin_data(self) -> None:
        created_at = now_iso()
        updated_at = now_iso()
        self._ensure_manual_case_requirement(created_at, updated_at)

        if not self.llm_configs.values():
            for payload in [
                {
                    "name": "qwen",
                    "api_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                    "api_key": "demo-qwen-key",
                    "model_name": "qwen3.5-flash",
                    "context_limit": 128000,
                    "vision_enabled": False,
                    "stream_enabled": True,
                    "enabled": False,
                    "created_at": created_at,
                    "updated_at": updated_at,
                },
                {
                    "name": "glm",
                    "api_url": "https://open.bigmodel.cn/api/paas/v4",
                    "api_key": "demo-glm-key",
                    "model_name": "glm-4.5-air",
                    "context_limit": 128000,
                    "vision_enabled": False,
                    "stream_enabled": True,
                    "enabled": True,
                    "created_at": created_at,
                    "updated_at": updated_at,
                },
            ]:
                record = {"id": self.new_id("llm_configs"), **payload}
                self.llm_configs[record["id"]] = record

        if not self.prompt_templates.values():
            for payload in [
                {
                    "prompt_type": "通用对话",
                    "name": "默认通用提示词",
                    "description": "默认的测试助手提示词，适用于日常问答与分析。",
                    "content": "你是一位专业的测试工程助手，擅长需求分析、用例设计、缺陷分析和测试建议。请用清晰、简洁、可执行的方式回答问题。",
                    "remark": "",
                    "enabled": True,
                    "is_default": True,
                    "created_at": created_at,
                    "updated_at": updated_at,
                },
                {
                    "prompt_type": "需求评审",
                    "name": "可测性分析",
                    "description": "用于输出需求文档的可测性分析结果。",
                    "content": "请基于需求文档输出可测性分析结果，重点说明哪些信息缺失会导致无法编写测试用例或无法判断通过失败。",
                    "remark": "",
                    "enabled": True,
                    "is_default": False,
                    "created_at": created_at,
                    "updated_at": updated_at,
                },
            ]:
                record = {"id": self.new_id("prompt_templates"), **payload}
                self.prompt_templates[record["id"]] = record

        self._ensure_test_case_prompt_templates(created_at, updated_at)

    def _ensure_manual_case_requirement(self, created_at: str, updated_at: str) -> None:
        if self.requirements.get(self.MANUAL_CASE_REQUIREMENT_ID):
            return
        record = {
            "id": self.MANUAL_CASE_REQUIREMENT_ID,
            "title": "手工用例挂载需求",
            "body_text": "系统保留记录，用于承载未绑定需求的手工测试用例。",
            "project": "系统内置",
            "status": "隐藏",
            "creator": "system",
            "summary": "hidden-manual-case-root",
            "created_date": created_at[:10],
            "version": 1,
            "import_method": "manual",
            "review_status": "待评审",
            "created_at": created_at,
            "updated_at": updated_at,
            "hidden": True,
        }
        self.requirements[record["id"]] = record

    def _ensure_test_case_prompt_templates(self, created_at: str, updated_at: str) -> None:
        defaults = [
            {
                "prompt_type": "测试用例",
                "name": "测试用例-需求澄清",
                "description": "用于从需求中提炼测试前必须澄清的问题、边界和风险。",
                "content": (
                    "你是一位资深测试分析师。请基于输入的需求信息输出“需求澄清”结果，帮助测试人员在编写测试点和测试用例前完成信息补齐。\n"
                    "输出要求：\n"
                    "1. 先给出对需求目标、核心流程、关键角色的理解。\n"
                    "2. 列出阻碍测试设计的关键信息缺口，优先关注业务规则、输入输出、异常处理、权限、状态流转、依赖系统、验收标准。\n"
                    "3. 给出建议向产品或研发确认的问题清单，问题要具体、可回答。\n"
                    "4. 给出主要测试风险和可能造成的影响。\n"
                    "5. 使用清晰分段和项目符号，内容可直接给测试人员使用。"
                ),
                "remark": "test-case-stage:clarify",
            },
            {
                "prompt_type": "测试用例",
                "name": "测试用例-测试点梳理",
                "description": "用于按测试设计视角梳理功能、边界、异常和兼容等测试点。",
                "content": (
                    "你是一位资深测试设计专家。请基于需求正文以及前序阶段结论，输出“测试点梳理”结果。\n"
                    "输出要求：\n"
                    "1. 按模块或流程拆解测试点，优先覆盖主流程、分支流程、边界条件、异常处理、权限控制、数据校验、状态流转。\n"
                    "2. 明确每个测试点的验证目标，避免只写标题不写检查点。\n"
                    "3. 补充接口联动、数据一致性、兼容性、性能和稳定性等非功能测试点。\n"
                    "4. 对高风险测试点进行单独标记并说明原因。\n"
                    "5. 输出要结构化，便于后续直接转成测试用例。"
                ),
                "remark": "test-case-stage:test_points",
            },
            {
                "prompt_type": "测试用例",
                "name": "测试用例-审批确认",
                "description": "用于形成提测前的确认清单、优先级和准出建议。",
                "content": (
                    "你是一位测试负责人，请基于需求正文、需求澄清和测试点梳理结果，输出“审批确认”结论。\n"
                    "输出要求：\n"
                    "1. 明确本次测试范围、非测试范围和优先级建议。\n"
                    "2. 给出进入测试执行前需要确认的前置条件、测试数据准备、环境依赖、角色权限和联调条件。\n"
                    "3. 明确通过标准和验收口径，尤其是哪些结果可判定为通过、失败、阻塞。\n"
                    "4. 列出尚未解决但需要知会的遗留风险、假设条件和规避建议。\n"
                    "5. 内容适合评审和审批场景，语言简洁明确。"
                ),
                "remark": "test-case-stage:review",
            },
            {
                "prompt_type": "测试用例",
                "name": "测试用例-生成用例",
                "description": "用于生成可执行的结构化测试用例草稿。",
                "content": (
                    "你是一位资深测试工程师。请基于需求正文及前序阶段结果，生成结构化测试用例。\n"
                    "输出要求：\n"
                    "1. 优先覆盖核心业务流、关键异常分支、边界场景、权限差异、状态流转和高风险点。\n"
                    "2. 每条用例都要包含 title、priority、steps、expected。\n"
                    "3. steps 必须是可执行动作，expected 必须是可验证结果，禁止笼统描述。\n"
                    "4. priority 使用 P1/P2/P3，P1 表示核心高风险场景。\n"
                    "5. 除结构化数据外，可补充一段总体说明，指出本轮用例覆盖重点与未覆盖风险。"
                ),
                "remark": "test-case-stage:cases",
            },
        ]

        existing_keys = {(item.get("prompt_type"), item.get("name")) for item in self.prompt_templates.values()}
        for payload in defaults:
            identity = (payload["prompt_type"], payload["name"])
            if identity in existing_keys:
                continue
            record = {
                "id": self.new_id("prompt_templates"),
                **payload,
                "enabled": True,
                "is_default": False,
                "created_at": created_at,
                "updated_at": updated_at,
            }
            self.prompt_templates[record["id"]] = record


db = DatabaseStore()
