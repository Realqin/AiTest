from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import Boolean, DateTime, Integer, JSON, String, Text, create_engine, delete, func, inspect, select, text
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
    project_id: Mapped[str] = mapped_column(String(64), nullable=False, default="", index=True)
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
    test_point: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    preconditions: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    steps: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    expected: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    priority: Mapped[str] = mapped_column(String(10), nullable=False, default="P2", index=True)
    case_type: Mapped[str] = mapped_column(String(64), nullable=False, default="", index=True)
    module_id: Mapped[str] = mapped_column(String(64), nullable=False, default="", index=True)
    stage: Mapped[str] = mapped_column(String(50), nullable=False, default="", index=True)
    review_status: Mapped[str] = mapped_column(String(20), nullable=False, default="", index=True)
    creator: Mapped[str] = mapped_column(String(50), nullable=False, default="admin", index=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="", index=True)
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
    is_preset: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    extra_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class DictionaryRecord(StructuredRecordMixin, Base):
    __tablename__ = "dictionaries"

    iso_datetime_fields = ("created_at", "updated_at")

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    group: Mapped[str] = mapped_column("group", String(100), nullable=False, default="", index=True)
    key: Mapped[str] = mapped_column("key", String(100), nullable=False, index=True)
    value: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
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


PRESET_PROMPT_IDENTITIES = {
    ("\u901a\u7528\u5bf9\u8bdd", "\u9ed8\u8ba4\u901a\u7528\u63d0\u793a\u8bcd"),
    ("\u9700\u6c42\u8bc4\u5ba1", "\u53ef\u6d4b\u6027\u5206\u6790"),
    ("\u6d4b\u8bd5\u7528\u4f8b", "\u6d4b\u8bd5\u7528\u4f8b-\u9700\u6c42\u5206\u6790"),
    ("\u6d4b\u8bd5\u7528\u4f8b", "\u6d4b\u8bd5\u7528\u4f8b-\u6d4b\u8bd5\u70b9\u68b3\u7406"),
    ("\u6d4b\u8bd5\u7528\u4f8b", "\u6d4b\u8bd5\u7528\u4f8b-\u751f\u6210\u7528\u4f8b"),
    ("\u6d4b\u8bd5\u7528\u4f8b", "\u6d4b\u8bd5\u7528\u4f8b-\u901a\u7528"),
}

ALLOWED_TEST_CASE_PROMPT_NAMES = {
    "\u6d4b\u8bd5\u7528\u4f8b-\u9700\u6c42\u5206\u6790",
    "\u6d4b\u8bd5\u7528\u4f8b-\u6d4b\u8bd5\u70b9\u68b3\u7406",
    "\u6d4b\u8bd5\u7528\u4f8b-\u751f\u6210\u7528\u4f8b",
    "\u6d4b\u8bd5\u7528\u4f8b-\u901a\u7528",
}

PRESET_PROMPT_REMARKS = {
    "test-case-stage:clarify",
    "test-case-stage:test_points",
    "test-case-stage:cases",
}


def _is_preset_prompt(payload: dict[str, Any]) -> bool:
    prompt_type = str(payload.get("prompt_type", "") or "")
    if prompt_type == "\u6d4b\u8bd5\u7528\u4f8b":
        return True
    identity = (prompt_type, str(payload.get("name", "") or ""))
    remark = str(payload.get("remark", "") or "")
    return identity in PRESET_PROMPT_IDENTITIES or remark in PRESET_PROMPT_REMARKS


class DatabaseStore:
    MANUAL_CASE_REQUIREMENT_ID = "manual_case_root"

    def __init__(self) -> None:
        settings = DatabaseSettings()
        self.engine = create_engine(settings.database_url, echo=settings.echo_sql, pool_pre_ping=True)
        self.session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)
        Base.metadata.create_all(self.engine)
        self._apply_schema_updates()

        self.projects = StructuredRepository(self.session_factory, ProjectRecord)
        self.requirements = StructuredRepository(self.session_factory, RequirementRecord)
        self.test_cases = StructuredRepository(self.session_factory, TestCaseRecord)
        self.test_case_modules = StructuredRepository(self.session_factory, TestCaseModuleRecord)
        self.agent_configs = StructuredRepository(self.session_factory, AgentConfigRecord)
        self.llm_configs = StructuredRepository(self.session_factory, LlmConfigRecord)
        self.prompt_templates = StructuredRepository(self.session_factory, PromptTemplateRecord)
        self.dictionaries = StructuredRepository(self.session_factory, DictionaryRecord)
        self.mcp_tools = StructuredRepository(self.session_factory, MCPToolRecord)
        self.review_runs = StructuredRepository(self.session_factory, ReviewRunRecord)
        self.requirement_versions = RequirementVersionRepository(self.session_factory)
        self.requirement_reviews = RequirementReviewRepository(self.session_factory)
        self._migrate_legacy_data()
        self._seed_admin_data()

    def _apply_schema_updates(self) -> None:
        table_updates = {
            "dictionaries": [
                ("group", "`group` VARCHAR(100) NOT NULL DEFAULT ''"),
                ("sort_order", "sort_order INT NOT NULL DEFAULT 0"),
                ("enabled", "enabled TINYINT(1) NOT NULL DEFAULT 1"),
            ],
            "test_cases": [
                ("test_point", "test_point VARCHAR(200) NOT NULL DEFAULT ''"),
                ("preconditions", "preconditions JSON NULL"),
                ("case_type", "case_type VARCHAR(64) NOT NULL DEFAULT ''"),
                ("module_id", "module_id VARCHAR(64) NOT NULL DEFAULT ''"),
                ("stage", "stage VARCHAR(50) NOT NULL DEFAULT ''"),
                ("review_status", "review_status VARCHAR(20) NOT NULL DEFAULT ''"),
                ("creator", "creator VARCHAR(50) NOT NULL DEFAULT 'admin'"),
                ("source", "source VARCHAR(20) NOT NULL DEFAULT ''"),
            ],
            "requirements": [
                ("project_id", "project_id VARCHAR(64) NOT NULL DEFAULT ''"),
            ],
            "prompt_templates": [
                ("is_preset", "is_preset TINYINT(1) NOT NULL DEFAULT 0"),
            ],
        }

        with self.engine.begin() as connection:
            for table_name, columns in table_updates.items():
                existing_columns = {item["name"] for item in inspect(connection).get_columns(table_name)}
                for column_name, ddl in columns:
                    if column_name in existing_columns:
                        continue
                    connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {ddl}"))

    def _migrate_legacy_data(self) -> None:
        dictionary_key_map = {
            ("case_priority", "高级"): ("P0", "高级", 1),
            ("case_priority", "中级"): ("P1", "中级", 2),
            ("case_priority", "低级"): ("P2", "低级", 3),
            ("case_priority", "最低级"): ("P3", "最低级", 4),
            ("case_type", "冒烟测试"): ("smoke", "冒烟测试", 1),
            ("case_type", "功能测试"): ("functional", "功能测试", 2),
            ("case_type", "边界测试"): ("boundary", "边界测试", 3),
            ("case_type", "异常测试"): ("exception", "异常测试", 4),
            ("case_type", "权限测试"): ("permission", "权限测试", 5),
            ("case_type", "安全测试"): ("security", "安全测试", 6),
            ("case_type", "兼容性测试"): ("compatibility", "兼容性测试", 7),
        }

        for item in self.dictionaries.values():
            migrated = self.clone(item)
            group = migrated.get("group", "")
            value = migrated.get("value", "")
            mapped = dictionary_key_map.get((group, value))
            if mapped:
                migrated["key"], migrated["value"], migrated["sort_order"] = mapped
            migrated["group"] = group
            migrated["sort_order"] = int(migrated.get("sort_order", 0) or 0)
            migrated["enabled"] = bool(migrated.get("enabled", True))
            self.dictionaries.save(migrated)

        case_type_key_by_label = {
            item.get("value"): item.get("key")
            for item in self.dictionaries.values()
            if item.get("group") == "case_type" and item.get("value")
        }
        module_id_by_name = {
            item.get("name"): item.get("id")
            for item in self.test_case_modules.values()
            if item.get("name")
        }
        project_id_by_name = {
            item.get("name"): item.get("id")
            for item in self.projects.values()
            if item.get("name")
        }

        for item in self.requirements.values():
            migrated = self.clone(item)
            if not migrated.get("project_id"):
                migrated["project_id"] = project_id_by_name.get(str(migrated.get("project", "") or "").strip(), "")
            self.requirements.save(migrated)

        for item in self.test_cases.values():
            migrated = self.clone(item)
            legacy_module_name = str(migrated.pop("module", "") or "").strip()
            if not migrated.get("module_id") and legacy_module_name:
                migrated["module_id"] = module_id_by_name.get(legacy_module_name, "")
            if not migrated.get("case_type") and migrated.get("case_type_label"):
                migrated["case_type"] = case_type_key_by_label.get(migrated.get("case_type_label"), "")
            if migrated.get("case_type") in case_type_key_by_label:
                migrated["case_type"] = case_type_key_by_label[migrated["case_type"]]
            migrated["test_point"] = str(migrated.get("test_point", "") or "")
            migrated["preconditions"] = list(migrated.get("preconditions", []) or [])
            migrated["module_id"] = str(migrated.get("module_id", "") or "")
            migrated["stage"] = str(migrated.get("stage", "") or "")
            migrated["creator"] = str(migrated.get("creator", "admin") or "admin")
            migrated["review_status"] = str(migrated.get("review_status", "") or "")
            migrated["source"] = str(migrated.get("source", "") or "")
            self.test_cases.save(migrated)

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
        self._ensure_dictionary_records(created_at, updated_at)

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
                    "is_preset": True,
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
                    "is_preset": True,
                    "created_at": created_at,
                    "updated_at": updated_at,
                },
            ]:
                record = {"id": self.new_id("prompt_templates"), **payload}
                self.prompt_templates[record["id"]] = record


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

    def _ensure_dictionary_records(self, created_at: str, updated_at: str) -> None:
        defaults = [
            {"group": "case_type", "key": "smoke", "value": "\u5192\u70df\u6d4b\u8bd5", "sort_order": 10},
            {"group": "case_type", "key": "functional", "value": "\u529f\u80fd\u6d4b\u8bd5", "sort_order": 20},
            {"group": "case_type", "key": "boundary", "value": "\u8fb9\u754c\u6d4b\u8bd5", "sort_order": 30},
            {"group": "case_type", "key": "exception", "value": "\u5f02\u5e38\u6d4b\u8bd5", "sort_order": 40},
            {"group": "case_type", "key": "permission", "value": "\u6743\u9650\u6d4b\u8bd5", "sort_order": 50},
            {"group": "case_type", "key": "security", "value": "\u5b89\u5168\u6d4b\u8bd5", "sort_order": 60},
            {"group": "case_type", "key": "compatibility", "value": "\u517c\u5bb9\u6027\u6d4b\u8bd5", "sort_order": 70},
            {"group": "case_priority", "key": "P0", "value": "\u9ad8\u7ea7", "sort_order": 10},
            {"group": "case_priority", "key": "P1", "value": "\u4e2d\u7ea7", "sort_order": 20},
            {"group": "case_priority", "key": "P2", "value": "\u4f4e\u7ea7", "sort_order": 30},
            {"group": "case_priority", "key": "P3", "value": "\u6700\u4f4e\u7ea7", "sort_order": 40},
        ]

        existing_keys = {(item.get("group"), item.get("key")) for item in self.dictionaries.values()}
        for payload in defaults:
            identity = (payload["group"], payload["key"])
            if identity in existing_keys:
                continue
            record = {
                "id": self.new_id("dictionaries"),
                **payload,
                "enabled": True,
                "created_at": created_at,
                "updated_at": updated_at,
            }
            self.dictionaries[record["id"]] = record

    def _ensure_test_case_prompt_templates(self, created_at: str, updated_at: str) -> None:
        defaults = [
            {
                "prompt_type": "\u6d4b\u8bd5\u7528\u4f8b",
                "name": "\u6d4b\u8bd5\u7528\u4f8b-\u9700\u6c42\u5206\u6790",
                "description": "\u7528\u4e8e\u5148\u8bc6\u522b\u9700\u6c42\u4e2d\u7684\u529f\u80fd\u70b9\u3001\u4e3b\u6d41\u7a0b\u3001\u5173\u952e\u5206\u652f\u548c\u8fb9\u754c\u3002",
                "content": (
                    "\u4f60\u662f\u4e00\u4f4d\u8d44\u6df1\u6d4b\u8bd5\u5206\u6790\u5e08\u3002\u8bf7\u57fa\u4e8e\u8f93\u5165\u7684\u9700\u6c42\u4fe1\u606f\u8f93\u51fa\u201c\u9700\u6c42\u62c6\u89e3\u201d\u7ed3\u679c\uff0c\u76ee\u6807\u662f\u5148\u660e\u786e\u8be5\u9700\u6c42\u5305\u542b\u591a\u5c11\u4e2a\u529f\u80fd\u70b9\uff0c\u4ee5\u53ca\u6bcf\u4e2a\u529f\u80fd\u70b9\u5bf9\u5e94\u7684\u4e3b\u6d41\u7a0b\u3001\u5173\u952e\u5206\u652f\u548c\u8fb9\u754c\u3002\n"
                    "\u8f93\u51fa\u8981\u6c42\uff1a\n"
                    "1. \u5148\u603b\u7ed3\u9700\u6c42\u76ee\u6807\uff0c\u5e76\u6982\u62ec\u8be5\u9700\u6c42\u8986\u76d6\u7684\u4e1a\u52a1\u8303\u56f4\u3002\n"
                    "2. \u62c6\u5206\u51fa\u660e\u786e\u7684\u529f\u80fd\u70b9\u6e05\u5355\uff0c\u7ed9\u6bcf\u4e2a\u529f\u80fd\u70b9\u7f16\u53f7\uff0c\u540d\u79f0\u8981\u5177\u4f53\uff0c\u907f\u514d\u8fc7\u4e8e\u7b3c\u7edf\u3002\n"
                    "3. \u5bf9\u6bcf\u4e2a\u529f\u80fd\u70b9\u8865\u5145\u8bf4\u660e\uff1a\u89e6\u53d1\u89d2\u8272\u3001\u524d\u7f6e\u6761\u4ef6\u3001\u6838\u5fc3\u64cd\u4f5c\u3001\u5173\u952e\u7ed3\u679c\u3002\n"
                    "4. \u5982\u5b58\u5728\u91cd\u8981\u5206\u652f\u3001\u5f02\u5e38\u5904\u7406\u3001\u6743\u9650\u5dee\u5f02\u3001\u72b6\u6001\u6d41\u8f6c\u6216\u5916\u90e8\u4f9d\u8d56\uff0c\u9700\u8981\u5728\u5bf9\u5e94\u529f\u80fd\u70b9\u4e0b\u5355\u72ec\u6807\u51fa\u3002\n"
                    "5. \u8f93\u51fa\u8981\u7ed3\u6784\u5316\uff0c\u4fbf\u4e8e\u540e\u7eed\u76f4\u63a5\u7ee7\u7eed\u751f\u6210\u6d4b\u8bd5\u70b9\u6216\u601d\u7ef4\u5bfc\u56fe\uff1b\u4e0d\u8981\u989d\u5916\u589e\u52a0\u201c\u9700\u6c42\u6f84\u6e05\u201d\u201c\u77e5\u8bc6\u70b9\u68b3\u7406\u201d\u7b49\u8282\u70b9\u524d\u7f00\u3002"
                ),
                "remark": "test-case-stage:clarify",
            },
            {
                "prompt_type": "\u6d4b\u8bd5\u7528\u4f8b",
                "name": "\u6d4b\u8bd5\u7528\u4f8b-\u6d4b\u8bd5\u70b9\u68b3\u7406",
                "description": "\u7528\u4e8e\u6309\u6d4b\u8bd5\u8bbe\u8ba1\u89c6\u89d2\u68b3\u7406\u529f\u80fd\u70b9\u5bf9\u5e94\u7684\u4e3b\u6d41\u7a0b\u3001\u5206\u652f\u3001\u8fb9\u754c\u3001\u5f02\u5e38\u548c\u975e\u529f\u80fd\u6d4b\u8bd5\u70b9\u3002",
                "content": (
                    "\u4f60\u662f\u4e00\u4f4d\u8d44\u6df1\u6d4b\u8bd5\u8bbe\u8ba1\u4e13\u5bb6\u3002\u8bf7\u57fa\u4e8e\u9700\u6c42\u6b63\u6587\u4ee5\u53ca\u524d\u5e8f\u9636\u6bb5\u7684\u9700\u6c42\u62c6\u89e3\u7ed3\u679c\uff0c\u8f93\u51fa\u201c\u6d4b\u8bd5\u70b9\u68b3\u7406\u201d\u7ed3\u679c\u3002\n"
                    "\u8f93\u51fa\u8981\u6c42\uff1a\n"
                    "1. \u6309\u529f\u80fd\u70b9\u5206\u7ec4\u68b3\u7406\u6d4b\u8bd5\u70b9\uff0c\u4f18\u5148\u8986\u76d6\u4e3b\u6d41\u7a0b\u3001\u5206\u652f\u6d41\u7a0b\u3001\u8fb9\u754c\u6761\u4ef6\u3001\u5f02\u5e38\u5904\u7406\u3001\u6743\u9650\u63a7\u5236\u3001\u6570\u636e\u6821\u9a8c\u548c\u72b6\u6001\u6d41\u8f6c\u3002\n"
                    "2. \u6bcf\u4e2a\u6d4b\u8bd5\u70b9\u90fd\u8981\u5199\u660e\u9a8c\u8bc1\u76ee\u6807\uff0c\u907f\u514d\u53ea\u5217\u6807\u9898\u3002\n"
                    "3. \u8865\u5145\u63a5\u53e3\u8054\u52a8\u3001\u6570\u636e\u4e00\u81f4\u6027\u3001\u517c\u5bb9\u6027\u3001\u6027\u80fd\u548c\u7a33\u5b9a\u6027\u7b49\u5fc5\u8981\u7684\u975e\u529f\u80fd\u6d4b\u8bd5\u70b9\u3002\n"
                    "4. \u5bf9\u9ad8\u98ce\u9669\u6d4b\u8bd5\u70b9\u8fdb\u884c\u5355\u72ec\u6807\u8bc6\uff0c\u5e76\u8bf4\u660e\u98ce\u9669\u539f\u56e0\u3002\n"
                    "5. \u8f93\u51fa\u8981\u7ed3\u6784\u5316\uff0c\u4fbf\u4e8e\u540e\u7eed\u76f4\u63a5\u8f6c\u6362\u6210\u6d4b\u8bd5\u7528\u4f8b\u6216\u601d\u7ef4\u5bfc\u56fe\uff1b\u4e0d\u8981\u989d\u5916\u589e\u52a0\u9636\u6bb5\u524d\u7f00\u8282\u70b9\u3002"
                ),
                "remark": "test-case-stage:test_points",
            },
            {
                "prompt_type": "\u6d4b\u8bd5\u7528\u4f8b",
                "name": "\u6d4b\u8bd5\u7528\u4f8b-\u751f\u6210\u7528\u4f8b",
                "description": "\u7528\u4e8e\u751f\u6210\u53ef\u6267\u884c\u3001\u53ef\u7f16\u8f91\u3001\u53ef\u76f4\u63a5\u5165\u5e93\u7684\u7ed3\u6784\u5316\u6d4b\u8bd5\u7528\u4f8b\u3002",
                "content": (
                    "\u4f60\u662f\u4e00\u4f4d\u8d44\u6df1\u6d4b\u8bd5\u5de5\u7a0b\u5e08\u3002\u8bf7\u57fa\u4e8e\u9700\u6c42\u6b63\u6587\u53ca\u524d\u5e8f\u9636\u6bb5\u7ed3\u679c\uff0c\u751f\u6210\u7ed3\u6784\u5316\u6d4b\u8bd5\u7528\u4f8b\u3002\n"
                    "\u8f93\u51fa\u8981\u6c42\uff1a\n"
                    "1. \u4f18\u5148\u8986\u76d6\u6838\u5fc3\u4e1a\u52a1\u6d41\u3001\u5173\u952e\u5f02\u5e38\u5206\u652f\u3001\u8fb9\u754c\u573a\u666f\u3001\u6743\u9650\u5dee\u5f02\u3001\u72b6\u6001\u6d41\u8f6c\u548c\u9ad8\u98ce\u9669\u70b9\u3002\n"
                    "2. \u6bcf\u6761\u7528\u4f8b\u90fd\u8981\u5305\u542b title\u3001priority\u3001steps\u3001expected\u3002\n"
                    "3. steps \u5fc5\u987b\u662f\u53ef\u6267\u884c\u52a8\u4f5c\uff0cexpected \u5fc5\u987b\u662f\u53ef\u9a8c\u8bc1\u7ed3\u679c\uff0c\u7981\u6b62\u7b3c\u7edf\u63cf\u8ff0\u3002\n"
                    "4. priority \u4f7f\u7528 P1/P2/P3\uff0cP1 \u8868\u793a\u6838\u5fc3\u9ad8\u98ce\u9669\u573a\u666f\u3002\n"
                    "5. \u9664\u7ed3\u6784\u5316\u6570\u636e\u5916\uff0c\u53ef\u8865\u5145\u4e00\u6bb5\u6574\u4f53\u8bf4\u660e\uff0c\u6307\u51fa\u672c\u8f6e\u7528\u4f8b\u8986\u76d6\u91cd\u70b9\u4e0e\u672a\u8986\u76d6\u98ce\u9669\u3002"
                ),
                "remark": "test-case-stage:cases",
            },
            {
                "prompt_type": "\u6d4b\u8bd5\u7528\u4f8b",
                "name": "\u6d4b\u8bd5\u7528\u4f8b-\u901a\u7528",
                "description": "\u7528\u4e8e\u5728\u7528\u4f8b\u7ba1\u7406\u4e2d\u7ed3\u5408\u622a\u56fe\u3001\u8865\u5145\u8bf4\u660e\u548c\u6d4b\u8bd5\u7c7b\u578b\u76f4\u63a5\u751f\u6210\u7ed3\u6784\u5316\u6d4b\u8bd5\u7528\u4f8b\u3002",
                "content": (
                    "\u4f60\u662f\u4e00\u4f4d\u8d44\u6df1\u6d4b\u8bd5\u5de5\u7a0b\u5e08\u3002\u8bf7\u57fa\u4e8e\u7528\u6237\u63d0\u4f9b\u7684\u9875\u9762\u622a\u56fe\u3001\u8865\u5145\u8bf4\u660e\u3001\u6d4b\u8bd5\u7c7b\u578b\u548c\u53ef\u9009\u77e5\u8bc6\u5e93\u4fe1\u606f\uff0c\u751f\u6210\u7ed3\u6784\u5316\u6d4b\u8bd5\u7528\u4f8b\u3002\n"
                    "\u8f93\u51fa\u8981\u6c42\uff1a\n"
                    "1. \u4f18\u5148\u8bc6\u522b\u9875\u9762\u4e2d\u7684\u6838\u5fc3\u6d41\u7a0b\u3001\u8f93\u5165\u9879\u3001\u72b6\u6001\u3001\u6309\u94ae\u3001\u63d0\u793a\u4fe1\u606f\u3001\u5217\u8868\u5b57\u6bb5\u548c\u6821\u9a8c\u89c4\u5219\u3002\n"
                    "2. \u7ed3\u5408\u7528\u6237\u8865\u5145\u7684\u4e1a\u52a1\u89c4\u5219\uff0c\u8986\u76d6\u4e3b\u6d41\u7a0b\u3001\u5f02\u5e38\u6d41\u7a0b\u3001\u8fb9\u754c\u6761\u4ef6\u3001\u6743\u9650\u5dee\u5f02\u548c\u9ad8\u98ce\u9669\u573a\u666f\u3002\n"
                    "3. \u6bcf\u6761\u7528\u4f8b\u90fd\u5fc5\u987b\u5305\u542b test_point\u3001title\u3001preconditions\u3001steps\u3001expected\u3001priority\u3001case_type\u3002\n"
                    "4. steps \u5fc5\u987b\u662f\u53ef\u6267\u884c\u52a8\u4f5c\uff0cexpected \u5fc5\u987b\u662f\u53ef\u9a8c\u8bc1\u7ed3\u679c\uff0c\u907f\u514d\u7b3c\u7edf\u63cf\u8ff0\u3002\n"
                    "5. case_type \u5fc5\u987b\u4ece\u7528\u6237\u9009\u62e9\u7684\u6d4b\u8bd5\u7c7b\u578b\u4e2d\u53d6\u503c\u3002"
                ),
                "remark": "test-case-standalone:general",
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
                "is_preset": True,
                "created_at": created_at,
                "updated_at": updated_at,
            }
            self.prompt_templates[record["id"]] = record


db = DatabaseStore()
