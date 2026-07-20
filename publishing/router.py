"""Safe YouTube publishing router with API, Postiz, and Studio fallbacks.

Nothing publishes unless the caller passes ``publish=True``.  Health checks are
read-only and the persistent ledger prevents a retry from silently duplicating
an already-started upload.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from youtube.auth import check_token_validity
from youtube.uploader import upload_video

STATE_DIR = Path.home() / ".local" / "state" / "smagent"
LEDGER_PATH = STATE_DIR / "publish-ledger.json"
CHANNELS = {
    "christian": {"youtube_key": "faithnexus", "env": "CHRISTIAN"},
    "soccer": {"youtube_key": "soccer", "env": "SOCCER"},
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _env(channel: str, suffix: str) -> str:
    return os.environ.get(f"SMAGENT_{CHANNELS[channel]['env']}_{suffix}", "").strip()


def _ledger() -> dict[str, Any]:
    try:
        return json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"schemaVersion": "1.0", "uploads": {}}


def _save_ledger(data: dict[str, Any]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = LEDGER_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(LEDGER_PATH)


def upload_key(channel: str, video: str) -> str:
    source = Path(video)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    return f"{channel}:{digest}"


@dataclass
class PublishRequest:
    channel: str
    video: str
    title: str
    description: str = ""
    tags: list[str] | None = None
    privacy: str = "private"
    made_for_kids: bool = False
    thumbnail: str | None = None

    def validate(self) -> None:
        if self.channel not in CHANNELS:
            raise ValueError(f"Unsupported channel: {self.channel}")
        if not Path(self.video).is_file():
            raise FileNotFoundError(self.video)
        if not 2 <= len(self.title) <= 100:
            raise ValueError("YouTube titles must contain 2-100 characters")
        if self.privacy not in {"private", "unlisted", "public"}:
            raise ValueError("privacy must be private, unlisted, or public")


def youtube_health(channel: str) -> dict[str, Any]:
    token = check_token_validity(CHANNELS[channel]["youtube_key"])
    quota_path = Path(__file__).resolve().parents[1] / "youtube_quota.json"
    try:
        quota = json.loads(quota_path.read_text())
    except FileNotFoundError:
        quota = {"used": 0, "date": None}
    return {"provider": "youtube_api", "ready": bool(token.get("valid")), "token": token, "quota": quota}


def postiz_health(channel: str) -> dict[str, Any]:
    base = os.environ.get("POSTIZ_BASE_URL", "").strip().rstrip("/")
    key = os.environ.get("POSTIZ_API_KEY", "").strip()
    integration = _env(channel, "POSTIZ_INTEGRATION_ID")
    if not (base and key and integration):
        return {"provider": "postiz", "ready": False, "reason": "POSTIZ_BASE_URL, POSTIZ_API_KEY, and channel integration ID are required"}
    try:
        response = requests.get(f"{base}/integrations", headers={"Authorization": key}, timeout=10)
        response.raise_for_status()
        found = next((item for item in response.json() if item.get("id") == integration and item.get("identifier") == "youtube" and not item.get("disabled")), None)
        return {"provider": "postiz", "ready": bool(found), "integration": found or integration}
    except requests.RequestException as error:
        return {"provider": "postiz", "ready": False, "reason": str(error)}


def studio_health(channel: str) -> dict[str, Any]:
    endpoint = os.environ.get("SMAGENT_STUDIO_CDP_URL", "http://127.0.0.1:9222")
    channel_id = _env(channel, "STUDIO_CHANNEL_ID")
    if not channel_id:
        return {"provider": "studio", "ready": False, "reason": "channel-specific Studio channel ID is required"}
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as playwright:
            browser = playwright.chromium.connect_over_cdp(endpoint, timeout=10_000)
            pages = [page.url for context in browser.contexts for page in context.pages]
            browser.close()
        return {"provider": "studio", "ready": True, "channel_id": channel_id, "cdp": endpoint, "open_pages": pages}
    except Exception as error:  # Playwright exposes provider-specific errors.
        return {"provider": "studio", "ready": False, "reason": str(error)}


def health(channel: str) -> dict[str, Any]:
    if channel not in CHANNELS:
        raise ValueError(f"Unsupported channel: {channel}")
    checks = [youtube_health(channel), postiz_health(channel), studio_health(channel)]
    return {"channel": channel, "checked_at": _now(), "providers": checks, "order": [item["provider"] for item in checks if item["ready"]]}


def _postiz_publish(request: PublishRequest) -> dict[str, Any]:
    base = os.environ["POSTIZ_BASE_URL"].rstrip("/")
    key = os.environ["POSTIZ_API_KEY"]
    integration = _env(request.channel, "POSTIZ_INTEGRATION_ID")
    headers = {"Authorization": key}
    with Path(request.video).open("rb") as handle:
        upload = requests.post(f"{base}/upload", headers=headers, files={"file": handle}, timeout=180)
    upload.raise_for_status()
    media = upload.json()
    tag_values = [{"value": tag, "label": tag} for tag in (request.tags or [])]
    payload = {"type": "now", "date": _now(), "shortLink": False, "tags": [], "posts": [{
        "integration": {"id": integration},
        "value": [{"content": request.description, "image": [{"id": media["id"], "path": media["path"]}]}],
        "settings": {"__type": "youtube", "title": request.title, "type": request.privacy,
                     "selfDeclaredMadeForKids": "yes" if request.made_for_kids else "no", "tags": tag_values},
    }]}
    response = requests.post(f"{base}/posts", headers={**headers, "Content-Type": "application/json"}, json=payload, timeout=60)
    response.raise_for_status()
    return {"provider": "postiz", "result": response.json()}


def publish(request: PublishRequest, provider: str = "auto", publish: bool = False) -> dict[str, Any]:
    request.validate()
    snapshot = health(request.channel)
    available = {item["provider"]: item for item in snapshot["providers"] if item["ready"]}
    order = [provider] if provider != "auto" else ["youtube_api", "postiz", "studio"]
    selected = next((name for name in order if name in available), None)
    if not selected:
        return {"status": "blocked", "health": snapshot, "reason": "No channel-specific provider is healthy"}
    key = upload_key(request.channel, request.video)
    ledger = _ledger()
    previous = ledger["uploads"].get(key)
    if previous and previous.get("status") in {"started", "published"}:
        return {"status": "blocked", "reason": "Upload already started; inspect ledger before retrying", "ledger": previous}
    plan = {"status": "dry_run" if not publish else "started", "provider": selected, "channel": request.channel, "video": request.video, "title": request.title, "health": snapshot}
    if not publish:
        return plan
    ledger["uploads"][key] = {**plan, "started_at": _now()}
    _save_ledger(ledger)
    try:
        if selected == "youtube_api":
            result = upload_video(request.video, request.title, request.description, request.tags or [], CHANNELS[request.channel]["youtube_key"], privacy=request.privacy, thumbnail_path=request.thumbnail, made_for_kids=request.made_for_kids)
        elif selected == "postiz":
            result = _postiz_publish(request)
        else:
            raise RuntimeError("Studio publishing requires the channel-specific selector profile; run health only until configured.")
        if result.get("error"):
            raise RuntimeError(result["error"])
        ledger["uploads"][key] = {**plan, "status": "published", "completed_at": _now(), "result": result}
        _save_ledger(ledger)
        return ledger["uploads"][key]
    except Exception as error:
        ledger["uploads"][key] = {**plan, "status": "failed", "completed_at": _now(), "error": str(error)}
        _save_ledger(ledger)
        raise
