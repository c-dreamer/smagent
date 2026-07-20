"""Evidence-first script generation using NVIDIA's OpenAI-compatible NIM API."""

from __future__ import annotations

import json
import os
import re
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()
NIM_URL = os.getenv("NVIDIA_NIM_URL", "https://integrate.api.nvidia.com/v1/chat/completions")

SCRIPT_SCHEMA: dict[str, Any] = {
    "name": "faith_nexus_short",
    "schema": {
        "type": "object", "additionalProperties": False,
        "required": ["title", "hook", "narration", "scenes", "claims", "review_notes"],
        "properties": {
            "title": {"type": "string", "maxLength": 90},
            "hook": {"type": "string", "maxLength": 140},
            "narration": {"type": "string", "maxLength": 1100},
            "scenes": {"type": "array", "minItems": 3, "maxItems": 6,
                "items": {"type": "object", "additionalProperties": False,
                    "required": ["duration_seconds", "narration", "visual_query", "on_screen_text"],
                    "properties": {"duration_seconds": {"type": "number", "minimum": 2, "maximum": 18},
                                   "narration": {"type": "string"},
                                   "visual_query": {"type": "string", "maxLength": 300},
                                   "on_screen_text": {"type": "string", "minLength": 1, "maxLength": 180}}}},
            "claims": {"type": "array", "minItems": 1, "items": {"type": "object", "additionalProperties": False,
                "required": ["text", "source_id"],
                "properties": {"text": {"type": "string"}, "source_id": {"type": "string"}}}},
            "review_notes": {"type": "array", "items": {"type": "string"}},
        },
    },
}


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is required; set it in OpenCode/VPS, never in the repository.")
    return value


def _validate_script(script: dict[str, Any], evidence_pack: dict[str, Any]) -> None:
    """Reject common model artefacts before they enter the media pipeline."""
    known_sources = {source["id"] for source in evidence_pack.get("sources", [])}
    if not script.get("claims"):
        raise ValueError("Model returned no source-bound claims.")
    unknown = {claim["source_id"] for claim in script["claims"]} - known_sources
    if unknown:
        raise ValueError(f"Model cited unknown source IDs: {sorted(unknown)}")

    viewer_text = " ".join([script.get("title", ""), script.get("hook", ""), script.get("narration", "")] + [
        scene.get("narration", "") + " " + scene.get("on_screen_text", "") for scene in script.get("scenes", [])
    ])
    leaked_ids = [source_id for source_id in known_sources if source_id in viewer_text]
    if leaked_ids:
        raise ValueError(f"Model leaked internal source IDs into viewer-facing text: {leaked_ids}")
    if re.match(r"^(start|begin|open) with\b", script.get("hook", "").strip(), flags=re.IGNORECASE):
        raise ValueError("Hook contains generator-direction language instead of viewer-facing copy.")


def generate_faith_script(topic: str, evidence_pack: dict[str, Any]) -> dict[str, Any]:
    """Generate a source-bound Faith Nexus short and reject invented source IDs."""
    api_key = _require_env("NVIDIA_API_KEY")
    model = _require_env("NVIDIA_TEXT_MODEL")
    system = (
        "You write Faith Nexus Christian reflections. Use only supplied evidence for quotations and facts. "
        "Treat interpretation as application, not quotation. Do not promise outcomes, invent Bible wording, "
        "or make claims that cannot cite a source_id. Start with a concrete human moment rather than a vague "
        "instruction to pause, breathe, or trust. Build one clear emotional turn, then land on the supplied "
        "Scripture. Make a calm 35–55 second vertical-video script. Every claim must use a supplied source_id. "
        "Visual queries must work with licensed stock or local ComfyUI. The hook and narration are viewer-facing "
        "copy: never say 'start with', describe instructions, or expose source IDs. Do not ask for depictions of "
        "Jesus, copyrighted characters, logos, or text embedded inside images. Every scene must include one short "
        "2–6 word on-screen phrase that is emotionally specific and suited to a large centre-screen Faith Nexus caption."
    )
    attempts = int(os.getenv("NVIDIA_SCRIPT_ATTEMPTS", "2"))
    last_error: Exception | None = None
    for attempt in range(attempts):
        payload = {
            "model": model, "temperature": 0.35 + (attempt * 0.1),
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": f"Topic: {topic}\n\nEvidence:\n{json.dumps(evidence_pack, ensure_ascii=False)}"}],
            "response_format": {"type": "json_schema", "json_schema": SCRIPT_SCHEMA},
        }
        response = requests.post(NIM_URL, headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, json=payload, timeout=120)
        response.raise_for_status()
        script = json.loads(response.json()["choices"][0]["message"]["content"])
        try:
            _validate_script(script, evidence_pack)
            return script
        except ValueError as error:
            last_error = error
    raise RuntimeError(f"No production-ready script after {attempts} attempt(s): {last_error}")
