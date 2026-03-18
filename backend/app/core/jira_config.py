import json
from pathlib import Path
from urllib.parse import urlparse


CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"
JIRA_ACCOUNTS_FILE = CONFIG_DIR / "jira_accounts.json"

DEFAULT_JIRA_ACCOUNTS = {
    "active_profile": "default",
    "profiles": {
        "default": {
            "enabled": False,
            "base_url": "http://jira.example.com:8080",
            "auth_type": "bearer",
            "username": "",
            "token": "",
            "api_path": "/rest/api/2",
            "verify_ssl": False,
        }
    },
}


def _ensure_config_file() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not JIRA_ACCOUNTS_FILE.exists():
        JIRA_ACCOUNTS_FILE.write_text(
            json.dumps(DEFAULT_JIRA_ACCOUNTS, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def load_jira_accounts() -> dict:
    _ensure_config_file()
    try:
        return json.loads(JIRA_ACCOUNTS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return DEFAULT_JIRA_ACCOUNTS


def get_active_jira_profile() -> dict:
    payload = load_jira_accounts()
    active_profile = payload.get("active_profile", "default")
    profiles = payload.get("profiles", {})
    profile = profiles.get(active_profile, {})
    return {
        "name": active_profile,
        "enabled": bool(profile.get("enabled", False)),
        "base_url": str(profile.get("base_url", "")).rstrip("/"),
        "auth_type": str(profile.get("auth_type", "bearer")).lower(),
        "username": str(profile.get("username", "")),
        "token": str(profile.get("token", "")),
        "api_path": str(profile.get("api_path", "/rest/api/2")),
        "verify_ssl": bool(profile.get("verify_ssl", False)),
    }


def get_allowed_jira_hosts() -> set[str]:
    payload = load_jira_accounts()
    hosts: set[str] = set()
    for profile in payload.get("profiles", {}).values():
        base_url = str(profile.get("base_url", "")).strip()
        if not base_url:
            continue
        parsed = urlparse(base_url)
        if parsed.netloc:
            hosts.add(parsed.netloc.lower())
    return hosts


def get_public_jira_config() -> dict:
    profile = get_active_jira_profile()
    return {
        "enabled": profile["enabled"],
        "configured": bool(profile["base_url"] and profile["token"]),
        "active_profile": profile["name"],
        "base_url": profile["base_url"],
        "allowed_hosts": sorted(get_allowed_jira_hosts()),
    }
