import base64
import mimetypes
import re
from html import escape, unescape
from urllib.parse import urljoin, urlparse

import httpx
from fastapi import HTTPException

from app.core.jira_config import get_active_jira_profile

ISSUE_KEY_RE = re.compile(r"([A-Z][A-Z0-9]+-\d+)")
HTML_TAG_RE = re.compile(r"<[^>]+>")
IMG_SRC_RE = re.compile(r'(<img[^>]+src=)(["\'])(?P<url>.*?)(\2)', re.IGNORECASE)
WIKI_IMAGE_RE = re.compile(r'!(?P<name>[^!|]+)(?:\|[^!]*)?!')


def _extract_issue_key(issue_ref: str) -> str:
    match = ISSUE_KEY_RE.search((issue_ref or "").upper())
    if not match:
        raise HTTPException(status_code=400, detail="Invalid Jira issue key or URL")
    return match.group(1)


def _flatten_adf(node) -> str:
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, list):
        return "".join(_flatten_adf(item) for item in node)
    if not isinstance(node, dict):
        return ""

    node_type = node.get("type")
    if node_type in {"paragraph", "heading", "bulletList", "orderedList", "listItem", "tableRow", "tableCell"}:
        return _flatten_adf(node.get("content", [])) + "\n"
    if node_type == "text":
        return str(node.get("text", ""))
    if node_type in {"hardBreak", "rule"}:
        return "\n"
    return _flatten_adf(node.get("content", []))


def _normalize_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        return _flatten_adf(value).strip()
    return str(value).strip()


def _html_to_text(value: str) -> str:
    plain = HTML_TAG_RE.sub(" ", value or "")
    plain = unescape(plain)
    plain = re.sub(r"\s+", " ", plain)
    return plain.strip()


def _pick_auth_headers(profile: dict) -> tuple[dict, httpx.Auth | None]:
    token = profile.get("token", "")
    username = profile.get("username", "")
    auth_type = profile.get("auth_type", "bearer")
    if auth_type == "basic":
        return {}, httpx.BasicAuth(username=username, password=token)
    return {"Authorization": f"Bearer {token}"}, None


def _to_absolute_url(raw_url: str, base_url: str) -> str:
    raw_url = (raw_url or "").strip()
    if not raw_url:
        return ""
    if raw_url.startswith("http://") or raw_url.startswith("https://"):
        return raw_url
    if raw_url.startswith("/"):
        return urljoin(base_url + "/", raw_url.lstrip("/"))
    return ""


async def _fetch_binary_with_client(client: httpx.AsyncClient, asset_url: str, headers: dict, auth) -> tuple[bytes, str]:
    try:
        response = await client.get(asset_url, headers=headers, auth=auth)
        response.raise_for_status()
    except httpx.HTTPError:
        return b"", ""
    content_type = response.headers.get("content-type") or mimetypes.guess_type(asset_url)[0] or "application/octet-stream"
    return response.content, content_type


async def _inline_remote_images(html: str, base_url: str, client: httpx.AsyncClient, headers: dict, auth) -> str:
    if not html:
        return ""

    cache: dict[str, str] = {}

    async def resolve_data_uri(raw_url: str) -> str:
        target_url = _to_absolute_url(raw_url, base_url)
        if not target_url:
            return raw_url
        if target_url in cache:
            return cache[target_url]
        content, content_type = await _fetch_binary_with_client(client, target_url, headers, auth)
        if not content:
            cache[target_url] = raw_url
            return raw_url
        data_uri = f"data:{content_type};base64,{base64.b64encode(content).decode('ascii')}"
        cache[target_url] = data_uri
        return data_uri

    parts = []
    cursor = 0
    for match in IMG_SRC_RE.finditer(html):
        parts.append(html[cursor:match.start()])
        prefix = match.group(1)
        quote_char = match.group(2)
        raw_url = match.group("url")
        resolved = await resolve_data_uri(raw_url)
        parts.append(f"{prefix}{quote_char}{resolved}{quote_char}")
        cursor = match.end()
    parts.append(html[cursor:])
    return "".join(parts)


async def _render_wiki_markup(text: str, attachments: dict[str, str], client: httpx.AsyncClient, headers: dict, auth) -> str:
    if not text:
        return ""

    blocks = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        pieces = []
        cursor = 0
        for match in WIKI_IMAGE_RE.finditer(line):
            pieces.append(escape(line[cursor:match.start()]))
            name = match.group("name").strip()
            asset_url = attachments.get(name, "")
            if asset_url:
                content, content_type = await _fetch_binary_with_client(client, asset_url, headers, auth)
                if content:
                    data_uri = f"data:{content_type};base64,{base64.b64encode(content).decode('ascii')}"
                    pieces.append(f"<img src=\"{data_uri}\" alt=\"{escape(name)}\" />")
                else:
                    pieces.append(escape(name))
            else:
                pieces.append(escape(name))
            cursor = match.end()
        pieces.append(escape(line[cursor:]))
        blocks.append(f"<p>{''.join(pieces)}</p>")
    return "".join(blocks)


async def fetch_jira_binary(asset_url: str) -> tuple[bytes, str]:
    profile = get_active_jira_profile()
    if not profile.get("enabled"):
        raise HTTPException(status_code=400, detail="Jira integration is disabled")
    if not profile.get("base_url") or not profile.get("token"):
        raise HTTPException(status_code=400, detail="Jira account config is incomplete")

    parsed = urlparse(asset_url)
    base_host = urlparse(profile["base_url"]).netloc.lower()
    if parsed.scheme not in {"http", "https"} or parsed.netloc.lower() != base_host:
        raise HTTPException(status_code=400, detail="Jira asset URL is not allowed")

    headers, auth = _pick_auth_headers(profile)
    async with httpx.AsyncClient(timeout=30.0, verify=profile.get("verify_ssl", False), follow_redirects=True) as client:
        content, content_type = await _fetch_binary_with_client(client, asset_url, headers, auth)
        if not content:
            raise HTTPException(status_code=502, detail="Failed to fetch Jira asset")
        return content, content_type


async def fetch_jira_issue(issue_ref: str) -> dict:
    profile = get_active_jira_profile()
    if not profile.get("enabled"):
        raise HTTPException(status_code=400, detail="Jira integration is disabled")
    if not profile.get("base_url") or not profile.get("token"):
        raise HTTPException(status_code=400, detail="Jira account config is incomplete")

    issue_key = _extract_issue_key(issue_ref)
    headers, auth = _pick_auth_headers(profile)
    api_path = profile.get("api_path", "/rest/api/2").rstrip("/")
    issue_url = f"{profile['base_url']}{api_path}/issue/{issue_key}"

    async with httpx.AsyncClient(timeout=30.0, verify=profile.get("verify_ssl", False), follow_redirects=True) as client:
        try:
            response = await client.get(
                issue_url,
                params={"expand": "renderedFields,names"},
                headers=headers,
                auth=auth,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text or f"Jira responded with {exc.response.status_code}"
            raise HTTPException(status_code=502, detail=f"Failed to fetch Jira issue: {detail}") from exc
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"Failed to connect to Jira: {exc}") from exc

        payload = response.json()
        fields = payload.get("fields", {})
        rendered_fields = payload.get("renderedFields", {})
        attachments = {
            (item.get("filename") or "").strip(): _to_absolute_url(item.get("content") or item.get("thumbnail") or "", profile["base_url"])
            for item in fields.get("attachment") or []
            if (item.get("filename") or "").strip()
        }

        summary = _normalize_text(fields.get("summary")) or issue_key
        description = _normalize_text(fields.get("description"))
        rendered_description_raw = rendered_fields.get("description", "") or ""
        rendered_description = await _inline_remote_images(rendered_description_raw, profile["base_url"], client, headers, auth)
        description_text = description or _html_to_text(rendered_description_raw)
        if not rendered_description and description:
            rendered_description = await _render_wiki_markup(description, attachments, client, headers, auth)

        status_name = _normalize_text((fields.get("status") or {}).get("name"))
        reporter = _normalize_text((fields.get("reporter") or {}).get("displayName"))
        assignee = _normalize_text((fields.get("assignee") or {}).get("displayName"))
        raw_comments = (fields.get("comment") or {}).get("comments", [])
        comments = []
        comment_html_blocks = []
        for item in raw_comments[:10]:
            author = _normalize_text((item.get("author") or {}).get("displayName")) or "\u672a\u77e5\u7528\u6237"
            body_value = item.get("body")
            body_text = _normalize_text(body_value)
            if body_text:
                comments.append(f"- {author}: {body_text}")
            body_html = body_value if isinstance(body_value, str) and "<" in body_value else ""
            if body_html:
                rendered_body = await _inline_remote_images(body_html, profile["base_url"], client, headers, auth)
            else:
                rendered_body = await _render_wiki_markup(body_text, attachments, client, headers, auth)
            if rendered_body:
                comment_html_blocks.append(f"<article class=\"jira-comment\"><h4>{author}</h4>{rendered_body}</article>")

    sections = [f"Jira\u5355\u53f7: {issue_key}", f"\u6807\u9898: {summary}"]
    if status_name:
        sections.append(f"\u72b6\u6001: {status_name}")
    if reporter:
        sections.append(f"\u62a5\u544a\u4eba: {reporter}")
    if assignee:
        sections.append(f"\u7ecf\u529e\u4eba: {assignee}")
    if description_text:
        sections.extend(["", "\u9700\u6c42\u5185\u5bb9:", description_text])
    if comments:
        sections.extend(["", "\u5907\u6ce8\u5185\u5bb9:", *comments])

    comments_html = ""
    if comment_html_blocks:
        comments_html = "<section class=\"jira-comments\"><h3>\u5907\u6ce8\u5185\u5bb9</h3>" + "".join(comment_html_blocks) + "</section>"

    preview_html = ""
    if rendered_description or comments_html:
        preview_html = (
            "<div class=\"docx-preview jira-preview\">"
            f"<h2>{summary}</h2>"
            f"<section class=\"jira-description\"><h3>\u9700\u6c42\u5185\u5bb9</h3>{rendered_description or f'<p>{escape(description_text)}</p>'}</section>"
            f"{comments_html}"
            "</div>"
        )

    return {
        "issue_key": issue_key,
        "title": f"{issue_key} - {summary}",
        "body_text": "\n".join(sections).strip(),
        "preview_type": "html" if preview_html else "text",
        "preview_html": preview_html,
        "source_url": urljoin(profile["base_url"] + "/", f"browse/{issue_key}"),
        "source_name": "Jira",
        "summary": description_text[:160] or summary,
    }
