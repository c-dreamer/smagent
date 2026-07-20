"""Portable run manifests for reproducibility and human quality approval."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def create_manifest(channel: str, topic: str, evidence: dict[str, Any], script: dict[str, Any], assets: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "version": 1, "channel": channel, "topic": topic,
        "created_at": datetime.now(timezone.utc).isoformat(), "status": "pending_human_approval",
        "evidence": evidence, "script": script, "assets": assets,
        "quality_gate": {
            "visual_reference_reviewed": False,
            "source_licences_verified": False,
            "scripture_verified": False,
            "production_readiness_reviewed": False,
            "human_approved": False,
        },
    }


def write_manifest(path: str | Path, manifest: dict[str, Any]) -> None:
    Path(path).write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
