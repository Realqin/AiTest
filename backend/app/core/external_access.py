from pathlib import Path
from urllib.parse import urlparse

from app.core.jira_config import get_allowed_jira_hosts, get_public_jira_config

STORAGE_ROOT = Path(__file__).resolve().parent.parent / "storage"
REQUIREMENT_UPLOAD_DIR = STORAGE_ROOT / "requirements"
REQUIREMENT_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

UPLOAD_RULES = {
    "allowed_extensions": {".pdf", ".doc", ".docx", ".txt", ".md"},
    "text_preview_extensions": {".txt", ".md"},
    "browser_preview_extensions": {".pdf"},
}

EXTERNAL_SOURCE_RULES = {
    "jira": {
        "enabled": True,
        "allowed_hosts": set(),
        "allowed_schemes": {"http", "https"},
    },
    "docs": {
        "enabled": True,
        "allowed_hosts": set(),
        "allowed_schemes": {"http", "https"},
    },
}


def is_allowed_external_url(source: str, url: str) -> bool:
    rule = EXTERNAL_SOURCE_RULES.get(source)
    if not rule or not rule.get("enabled"):
        return False
    parsed = urlparse(url)
    if parsed.scheme not in rule["allowed_schemes"]:
        return False
    host = parsed.netloc.lower()
    allowed_hosts = get_allowed_jira_hosts() if source == "jira" else rule.get("allowed_hosts", set())
    if not allowed_hosts:
        return source != "jira"
    return host in allowed_hosts


def get_public_source_config() -> dict:
    public_jira = get_public_jira_config()
    return {
        "upload_extensions": sorted(UPLOAD_RULES["allowed_extensions"]),
        "sources": {
            "jira": {
                "enabled": public_jira["enabled"],
                "configured": public_jira["configured"],
                "active_profile": public_jira["active_profile"],
                "base_url": public_jira["base_url"],
                "allowed_hosts": public_jira["allowed_hosts"],
            },
            "docs": {
                "enabled": EXTERNAL_SOURCE_RULES["docs"]["enabled"],
                "allowed_hosts": sorted(EXTERNAL_SOURCE_RULES["docs"].get("allowed_hosts", set())),
            },
        },
    }
