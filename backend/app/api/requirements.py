import base64
import html
import mimetypes
import re
import sys
import zipfile
from pathlib import Path
from uuid import uuid4
from xml.etree import ElementTree as ET

VENDOR_DIR = Path(__file__).resolve().parents[2] / "vendor"
if str(VENDOR_DIR) not in sys.path:
    sys.path.insert(0, str(VENDOR_DIR))

import mammoth
from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.core.external_access import (
    REQUIREMENT_UPLOAD_DIR,
    UPLOAD_RULES,
    get_public_source_config,
    is_allowed_external_url,
)
from app.core.jira_client import fetch_jira_binary, fetch_jira_issue
from app.store.memory_db import db, now_iso


router = APIRouter()


class RequirementIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1)
    project: str = Field(default="演示项目", max_length=100)
    status: str = Field(default="草稿", max_length=50)
    creator: str = Field(default="admin", max_length=50)
    summary: str = Field(default="", max_length=500)
    start_date: str | None = None
    end_date: str | None = None


class BulkDeleteIn(BaseModel):
    ids: list[str] = Field(default_factory=list)


DOCX_STYLE = """
<div class='docx-preview'>
{content}
</div>
""".strip()


DOCX_NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "pic": "http://schemas.openxmlformats.org/drawingml/2006/picture",
    "v": "urn:schemas-microsoft-com:vml",
}


def _strip_xml_namespaces(xml_text: str) -> str:
    return re.sub(r"</?w:[^>]+?>", lambda m: m.group(0).replace("w:", ""), xml_text)


def _extract_docx_plain_text(target: Path) -> str:
    try:
        with zipfile.ZipFile(target) as archive:
            xml_bytes = archive.read("word/document.xml")
    except Exception:
        return ""

    xml_text = xml_bytes.decode("utf-8", errors="ignore")
    xml_text = _strip_xml_namespaces(xml_text)
    xml_text = xml_text.replace("</t>", "")
    xml_text = re.sub(r"<tab[^>]*/>", "    ", xml_text)
    xml_text = re.sub(r"<br[^>]*/>", "\n", xml_text)
    xml_text = re.sub(r"</p>", "\n", xml_text)
    xml_text = re.sub(r"<[^>]+>", "", xml_text)
    xml_text = html.unescape(xml_text)
    lines = [line.strip() for line in xml_text.splitlines()]
    return "\n".join(line for line in lines if line)[:50000]


def _guess_image_content_type(name: str) -> str:
    content_type, _ = mimetypes.guess_type(name)
    return content_type or "application/octet-stream"


def _docx_rel_map(archive: zipfile.ZipFile) -> dict[str, str]:
    rels = {}
    try:
        rel_xml = archive.read("word/_rels/document.xml.rels")
    except Exception:
        return rels

    root = ET.fromstring(rel_xml)
    for rel in root:
        rel_id = rel.attrib.get("Id")
        target = rel.attrib.get("Target")
        if rel_id and target:
            if not target.startswith("word/"):
                target = f"word/{target.lstrip('/')}"
            rels[rel_id] = target
    return rels


def _image_tag_from_rel(archive: zipfile.ZipFile, rels: dict[str, str], rel_id: str | None) -> str:
    if not rel_id:
        return ""
    target = rels.get(rel_id)
    if not target:
        return ""
    try:
        data = archive.read(target)
    except Exception:
        return ""
    encoded = base64.b64encode(data).decode("ascii")
    content_type = _guess_image_content_type(target)
    return f'<img src="data:{content_type};base64,{encoded}" alt="????" />'


def _render_docx_run(archive: zipfile.ZipFile, rels: dict[str, str], run: ET.Element) -> str:
    parts: list[str] = []
    for child in list(run):
        tag = child.tag
        if tag == f'{{{DOCX_NS["w"]}}}t':
            parts.append(html.escape(child.text or ""))
        elif tag in {f'{{{DOCX_NS["w"]}}}br', f'{{{DOCX_NS["w"]}}}cr'}:
            parts.append("<br />")
        elif tag == f'{{{DOCX_NS["w"]}}}tab':
            parts.append("&nbsp;&nbsp;&nbsp;&nbsp;")
        elif tag == f'{{{DOCX_NS["w"]}}}drawing':
            blip = child.find('.//a:blip', DOCX_NS)
            rel_id = None if blip is None else blip.attrib.get(f'{{{DOCX_NS["r"]}}}embed')
            parts.append(_image_tag_from_rel(archive, rels, rel_id))
        elif tag == f'{{{DOCX_NS["w"]}}}pict':
            image = child.find('.//v:imagedata', DOCX_NS)
            rel_id = None if image is None else image.attrib.get(f'{{{DOCX_NS["r"]}}}id')
            parts.append(_image_tag_from_rel(archive, rels, rel_id))
    return ''.join(parts)


def _render_docx_paragraph(archive: zipfile.ZipFile, rels: dict[str, str], paragraph: ET.Element) -> str:
    content = ''.join(_render_docx_run(archive, rels, run) for run in paragraph.findall('w:r', DOCX_NS))
    if not content.strip():
        content = '&nbsp;'
    return f'<p>{content}</p>'


def _render_docx_table(archive: zipfile.ZipFile, rels: dict[str, str], table: ET.Element) -> str:
    rows_html = []
    for row in table.findall('w:tr', DOCX_NS):
        cells_html = []
        for cell in row.findall('w:tc', DOCX_NS):
            cell_parts = []
            for child in list(cell):
                if child.tag == f'{{{DOCX_NS["w"]}}}p':
                    cell_parts.append(_render_docx_paragraph(archive, rels, child))
                elif child.tag == f'{{{DOCX_NS["w"]}}}tbl':
                    cell_parts.append(_render_docx_table(archive, rels, child))
            cells_html.append(f'<td>{"".join(cell_parts)}</td>')
        rows_html.append(f'<tr>{"".join(cells_html)}</tr>')
    return f'<table>{"".join(rows_html)}</table>'


def _build_docx_xml_preview(target: Path) -> tuple[str, str, str]:
    try:
        with zipfile.ZipFile(target) as archive:
            root = ET.fromstring(archive.read("word/document.xml"))
            rels = _docx_rel_map(archive)
            body = root.find('w:body', DOCX_NS)
            if body is None:
                return "document", "", ""

            parts: list[str] = []
            for child in list(body):
                if child.tag == f'{{{DOCX_NS["w"]}}}p':
                    parts.append(_render_docx_paragraph(archive, rels, child))
                elif child.tag == f'{{{DOCX_NS["w"]}}}tbl':
                    parts.append(_render_docx_table(archive, rels, child))

            content_html = ''.join(parts)
            preview_html = DOCX_STYLE.format(content=content_html)
            preview_text = _extract_docx_plain_text(target)
            return "html", preview_text, preview_html
    except Exception:
        return "document", "", ""


def _build_docx_preview(target: Path) -> tuple[str, str, str]:
    try:
        with target.open("rb") as docx_file:
            result = mammoth.convert_to_html(docx_file, convert_image=mammoth.images.data_uri)
        preview_html = DOCX_STYLE.format(content=result.value)
        preview_text = html.unescape(re.sub(r"<[^>]+>", " ", result.value))
        preview_text = re.sub(r"\s+", " ", preview_text).strip()[:50000]
        return "html", preview_text, preview_html
    except Exception:
        preview_type, preview_text, preview_html = _build_docx_xml_preview(target)
        if preview_type == "html":
            return preview_type, preview_text, preview_html
        preview_text = _extract_docx_plain_text(target)
        if preview_text:
            preview_html = DOCX_STYLE.format(
                content="".join(f"<p>{html.escape(line)}</p>" for line in preview_text.splitlines())
            )
            return "html", preview_text, preview_html
        return "document", "", ""


def _refresh_requirement_docx_preview(requirement: dict) -> None:
    stored_file_name = requirement.get("stored_file_name", "")
    if not stored_file_name.lower().endswith(".docx"):
        return

    target = REQUIREMENT_UPLOAD_DIR / stored_file_name
    if not target.exists():
        return

    preview_type, _preview_text, preview_html = _build_docx_preview(target)
    if preview_type == "html" and preview_html:
        requirement["preview_type"] = preview_type
        requirement["preview_html"] = preview_html


def serialize_requirement_list_item(requirement: dict) -> dict:
    return {
        "id": requirement["id"],
        "title": requirement["title"],
        "project": requirement["project"],
        "creator": requirement["creator"],
        "created_date": requirement.get("created_date", ""),
        "created_at": requirement.get("created_at", ""),
        "updated_at": requirement.get("updated_at", ""),
        "import_method": requirement.get("import_method", "manual"),
        "review_status": requirement.get("review_status", "???"),
        "latest_review_run_id": requirement.get("latest_review_run_id"),
        "source_name": requirement.get("source_name", ""),
        "file_name": requirement.get("file_name", ""),
    }


def serialize_requirement_detail(requirement: dict) -> dict:
    file_url = ""
    if requirement.get("stored_file_name"):
        file_url = f"/assets/requirements/{requirement['stored_file_name']}"
    return {
        "id": requirement["id"],
        "title": requirement["title"],
        "project": requirement["project"],
        "body_text": requirement.get("body_text", ""),
        "review_status": requirement.get("review_status", "???"),
        "latest_review_run_id": requirement.get("latest_review_run_id"),
        "preview_type": requirement.get("preview_type", "text"),
        "preview_html": requirement.get("preview_html", ""),
        "file_url": file_url,
        "file_name": requirement.get("file_name", ""),
        "source_url": requirement.get("source_url", ""),
        "import_method": requirement.get("import_method", "manual"),
    }


def build_requirement_record(payload: dict) -> dict:
    req_id = db.new_id("requirements")
    created_date = now_iso()[:10]
    return {
        "id": req_id,
        "title": payload["title"],
        "body_text": payload["body_text"],
        "project": payload.get("project", "演示项目"),
        "status": payload.get("status", "草稿"),
        "creator": payload.get("creator", "admin"),
        "summary": payload.get("summary") or payload["body_text"][:80],
        "start_date": payload.get("start_date"),
        "end_date": payload.get("end_date"),
        "created_date": created_date,
        "version": 1,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "import_method": payload.get("import_method", "manual"),
        "source_name": payload.get("source_name", ""),
        "source_url": payload.get("source_url", ""),
        "file_name": payload.get("file_name", ""),
        "stored_file_name": payload.get("stored_file_name", ""),
        "preview_type": payload.get("preview_type", "text"),
        "preview_html": payload.get("preview_html", ""),
        "review_status": payload.get("review_status", "待评审"),
        "latest_review_run_id": payload.get("latest_review_run_id"),
    }


@router.get("/import-config")
async def get_import_config() -> dict:
    return get_public_source_config()


@router.get("/jira-fetch")
async def jira_fetch(issue_ref: str = Query(..., min_length=1)) -> dict:
    return await fetch_jira_issue(issue_ref)


@router.get("/jira-proxy")
async def jira_proxy(url: str = Query(..., min_length=1)) -> Response:
    if not is_allowed_external_url("jira", url):
        raise HTTPException(status_code=400, detail="Jira asset URL is not allowed by policy")
    content, content_type = await fetch_jira_binary(url)
    return Response(content=content, media_type=content_type)


@router.get("")
async def list_requirements(
    keyword: str = "",
    project: str = "",
    review_status: str = "",
    creator: str = "",
    start_date: str = "",
    end_date: str = "",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
) -> dict:
    items = [item for item in db.requirements.values() if not item.get("hidden")]

    def normalize_filter_datetime(value: str) -> str:
        return (value or "").replace("T", " ").strip()

    def date_in_range(item_date: str) -> bool:
        if not item_date:
            return True
        normalized_item_date = normalize_filter_datetime(item_date)
        normalized_start = normalize_filter_datetime(start_date)
        normalized_end = normalize_filter_datetime(end_date)
        if normalized_start and normalized_item_date < normalized_start:
            return False
        if normalized_end and normalized_item_date > normalized_end:
            return False
        return True

    keyword_lower = keyword.strip().lower()
    if keyword_lower:
        items = [
            item
            for item in items
            if keyword_lower in item["title"].lower()
            or keyword_lower in item["body_text"].lower()
            or keyword_lower in item["summary"].lower()
        ]
    if project:
        items = [item for item in items if item["project"] == project]
    if review_status:
        items = [item for item in items if item.get("review_status", "???") == review_status]
    if creator:
        items = [item for item in items if item["creator"] == creator]
    if start_date or end_date:
        items = [item for item in items if date_in_range(item.get("created_at", ""))]

    items.sort(key=lambda item: item.get("created_at", ""), reverse=True)

    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    page_items = [serialize_requirement_list_item(item) for item in items[start:end]]
    return {"items": page_items, "total": total, "page": page, "page_size": page_size}


@router.post("")
async def create_requirement(payload: RequirementIn) -> dict:
    record = build_requirement_record({**payload.model_dump(), "body_text": payload.content})
    db.requirements[record["id"]] = db.clone(record)
    db.requirement_versions[record["id"]].append(
        {"version": 1, "content": payload.content, "created_at": now_iso()}
    )
    return serialize_requirement_detail(record)


@router.post("/import")
async def import_requirement(
    project: str = Form(...),
    title: str = Form(""),
    creator: str = Form("admin"),
    import_method: str = Form("file"),
    jira_url: str = Form(""),
    status: str = Form("草稿"),
    summary: str = Form(""),
    file: UploadFile | None = File(default=None),
) -> dict:
    body_text = ""
    file_name = ""
    stored_file_name = ""
    preview_type = "text"
    preview_html = ""
    source_url = ""
    source_name = ""
    resolved_title = title.strip()

    if import_method == "jira":
        if not jira_url:
            raise HTTPException(status_code=400, detail="Jira issue key or URL is required")
        jira_issue = await fetch_jira_issue(jira_url)
        if not is_allowed_external_url("jira", jira_issue["source_url"]):
            raise HTTPException(status_code=400, detail="Jira URL is not allowed by policy")
        source_url = jira_issue["source_url"]
        source_name = jira_issue["source_name"]
        resolved_title = resolved_title or jira_issue["title"]
        body_text = jira_issue["body_text"]
        preview_type = jira_issue["preview_type"]
        preview_html = jira_issue["preview_html"]
        summary = summary or jira_issue["summary"]
    else:
        if file is None:
            raise HTTPException(status_code=400, detail="File is required")
        suffix = Path(file.filename or "").suffix.lower()
        if suffix not in UPLOAD_RULES["allowed_extensions"]:
            raise HTTPException(status_code=400, detail="Unsupported file type")
        file_name = file.filename or f"requirement{suffix}"
        resolved_title = resolved_title or Path(file_name).stem
        stored_file_name = f"{uuid4()}{suffix}"
        target = REQUIREMENT_UPLOAD_DIR / stored_file_name
        data = await file.read()
        target.write_bytes(data)
        body_text = f"Imported from file: {file_name}"
        source_name = "上传文件"
        if suffix in UPLOAD_RULES["text_preview_extensions"]:
            preview_type = "text"
            body_text = data.decode("utf-8", errors="ignore")[:50000]
        elif suffix == ".docx":
            preview_type, body_text, preview_html = _build_docx_preview(target)
        elif suffix in UPLOAD_RULES["browser_preview_extensions"]:
            preview_type = "document"
        else:
            preview_type = "document"

    if not resolved_title:
        raise HTTPException(status_code=400, detail="Title could not be resolved")

    record = build_requirement_record(
        {
            "title": resolved_title,
            "body_text": body_text,
            "project": project,
            "status": status,
            "creator": creator,
            "summary": summary or body_text[:80] or resolved_title,
            "import_method": import_method,
            "source_name": source_name,
            "source_url": source_url,
            "file_name": file_name,
            "stored_file_name": stored_file_name,
            "preview_type": preview_type,
            "preview_html": preview_html,
            "review_status": "待评审",
        }
    )
    db.requirements[record["id"]] = db.clone(record)
    db.requirement_versions[record["id"]].append(
        {"version": 1, "content": record["body_text"], "created_at": now_iso()}
    )
    return serialize_requirement_detail(record)


@router.get("/{requirement_id}")
async def get_requirement(requirement_id: str) -> dict:
    requirement = db.requirements.get(requirement_id)
    if not requirement:
        raise HTTPException(status_code=404, detail="Requirement not found")
    _refresh_requirement_docx_preview(requirement)
    return serialize_requirement_detail(requirement)


@router.get("/{requirement_id}/preview")
async def preview_requirement(requirement_id: str) -> dict:
    requirement = db.requirements.get(requirement_id)
    if not requirement:
        raise HTTPException(status_code=404, detail="Requirement not found")
    _refresh_requirement_docx_preview(requirement)
    file_url = ""
    if requirement.get("stored_file_name"):
        file_url = f"/assets/requirements/{requirement['stored_file_name']}"
    return {
        "id": requirement["id"],
        "title": requirement["title"],
        "project": requirement["project"],
        "body_text": requirement["body_text"],
        "review_status": requirement.get("review_status", "待评审"),
        "latest_review_run_id": requirement.get("latest_review_run_id"),
        "preview_type": requirement.get("preview_type", "text"),
        "preview_html": requirement.get("preview_html", ""),
        "file_url": file_url,
        "file_name": requirement.get("file_name", ""),
        "source_url": requirement.get("source_url", ""),
        "import_method": requirement.get("import_method", "manual"),
    }


@router.put("/{requirement_id}")
async def update_requirement(requirement_id: str, payload: RequirementIn) -> dict:
    requirement = db.requirements.get(requirement_id)
    if not requirement:
        raise HTTPException(status_code=404, detail="Requirement not found")
    requirement["title"] = payload.title
    requirement["body_text"] = payload.content
    requirement["project"] = payload.project
    requirement["status"] = payload.status
    requirement["creator"] = payload.creator
    requirement["summary"] = payload.summary or payload.content[:80]
    requirement["start_date"] = payload.start_date
    requirement["end_date"] = payload.end_date
    requirement["preview_type"] = "text"
    requirement["preview_html"] = ""
    requirement["version"] += 1
    requirement["updated_at"] = now_iso()
    db.requirement_versions[requirement_id].append(
        {"version": requirement["version"], "content": payload.content, "created_at": now_iso()}
    )
    return serialize_requirement_detail(requirement)


@router.post("/bulk-delete")
async def bulk_delete_requirements(payload: BulkDeleteIn) -> dict:
    deleted = 0
    for requirement_id in payload.ids:
        if requirement_id in db.requirements:
            item = db.requirements[requirement_id]
            if item.get("stored_file_name"):
                target = REQUIREMENT_UPLOAD_DIR / item["stored_file_name"]
                if target.exists():
                    target.unlink()
            del db.requirements[requirement_id]
            db.requirement_versions.pop(requirement_id, None)
            db.requirement_reviews.pop(requirement_id, None)
            deleted += 1
    return {"ok": True, "deleted": deleted}


@router.delete("/{requirement_id}")
async def delete_requirement(requirement_id: str) -> dict:
    if requirement_id not in db.requirements:
        raise HTTPException(status_code=404, detail="Requirement not found")
    item = db.requirements[requirement_id]
    if item.get("stored_file_name"):
        target = REQUIREMENT_UPLOAD_DIR / item["stored_file_name"]
        if target.exists():
            target.unlink()
    del db.requirements[requirement_id]
    db.requirement_versions.pop(requirement_id, None)
    db.requirement_reviews.pop(requirement_id, None)
    return {"ok": True}


@router.get("/{requirement_id}/versions")
async def list_versions(requirement_id: str) -> list[dict]:
    if requirement_id not in db.requirements:
        raise HTTPException(status_code=404, detail="Requirement not found")
    return db.requirement_versions[requirement_id]
