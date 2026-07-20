#!/usr/bin/env python3
"""Local, review-first control centre for smagent.

It deliberately manages configuration and review artefacts only. Publishing is
disabled here until a future explicit Postiz integration is approved.
"""

from __future__ import annotations

import json
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = Path.home() / "Downloads" / "smagent_output"
SETTINGS = ROOT / "dashboard" / "postiz.local.json"
CHANNELS = {
    "soccer": {"name": "GoalHubPro", "handle": "@Goal_HubPro", "niche": "Soccer analysis and highlights"},
    "christian": {"name": "Faith Nexus", "handle": "@Faith_Nexus", "niche": "Faith and Bible study"},
    "trading": {"name": "Trading", "handle": "TBD", "niche": "Market analysis and trading strategies"},
}


def _read_settings() -> dict:
    if not SETTINGS.exists():
        return {"base_url": "", "api_key_env": "POSTIZ_API_KEY"}
    return json.loads(SETTINGS.read_text(encoding="utf-8"))


def _status() -> dict:
    candidates = []
    if OUTPUT_ROOT.exists():
        for video in sorted(OUTPUT_ROOT.rglob("*.mp4"), key=lambda item: item.stat().st_mtime, reverse=True):
            manifest = video.with_name("review_manifest.json")
            review = json.loads(manifest.read_text()) if manifest.exists() else {}
            candidates.append({
                "name": video.name,
                "path": str(video.relative_to(OUTPUT_ROOT)),
                "modified": int(video.stat().st_mtime),
                "channel": review.get("channel", "christian"),
                "review_status": review.get("status", "review_required"),
            })
    settings = _read_settings()
    return {
        "output_root": str(OUTPUT_ROOT),
        "channels": CHANNELS,
        "videos": candidates,
        "postiz": {"base_url": settings.get("base_url", ""), "api_key_env": settings.get("api_key_env", "POSTIZ_API_KEY"), "configured": bool(settings.get("base_url"))},
        "publishing": "disabled_pending_human_approval",
    }


class DashboardHandler(BaseHTTPRequestHandler):
    def _send(self, body: bytes, content_type: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        path = unquote(urlparse(self.path).path)
        if path == "/api/status":
            return self._send(json.dumps(_status()).encode(), "application/json")
        if path.startswith("/artifacts/"):
            target = (OUTPUT_ROOT / path.removeprefix("/artifacts/")).resolve()
            if OUTPUT_ROOT.resolve() not in target.parents or not target.is_file():
                return self._send(b"Not found", "text/plain", HTTPStatus.NOT_FOUND)
            return self._send(target.read_bytes(), mimetypes.guess_type(str(target))[0] or "application/octet-stream")
        asset = ROOT / "dashboard" / ("index.html" if path in {"/", ""} else path.removeprefix("/"))
        if not asset.is_file() or asset.parent != (ROOT / "dashboard"):
            return self._send(b"Not found", "text/plain", HTTPStatus.NOT_FOUND)
        return self._send(asset.read_bytes(), mimetypes.guess_type(str(asset))[0] or "application/octet-stream")

    def do_POST(self) -> None:  # noqa: N802
        if urlparse(self.path).path != "/api/postiz":
            return self._send(b"Not found", "text/plain", HTTPStatus.NOT_FOUND)
        try:
            size = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(size))
            base_url = str(payload.get("base_url", "")).strip().rstrip("/")
            api_key_env = str(payload.get("api_key_env", "POSTIZ_API_KEY")).strip()
            if base_url and not base_url.startswith(("http://", "https://")):
                raise ValueError("Postiz URL must start with http:// or https://")
            if not api_key_env.replace("_", "").isalnum():
                raise ValueError("API key environment variable name is invalid")
            SETTINGS.write_text(json.dumps({"base_url": base_url, "api_key_env": api_key_env}, indent=2) + "\n", encoding="utf-8")
            return self._send(json.dumps({"saved": True}).encode(), "application/json")
        except (ValueError, json.JSONDecodeError) as error:
            return self._send(json.dumps({"error": str(error)}).encode(), "application/json", HTTPStatus.BAD_REQUEST)


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 8766), DashboardHandler)
    print("smagent dashboard: http://127.0.0.1:8766")
    server.serve_forever()


if __name__ == "__main__":
    main()
