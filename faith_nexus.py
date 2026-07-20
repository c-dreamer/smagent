"""Faith Nexus devotional contracts: Scripture, storyboard, and timing checks."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

WEB_SOURCE = "https://ebible.org/eng-web/MAT06.htm"
PLACEHOLDERS = {"", "none", "n/a", "na", "todo", "tbd"}


def words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9]+(?:['’][A-Za-z0-9]+)?", text)


def validate_evidence(evidence: dict[str, Any]) -> None:
    """Ensure an exact WEB quotation is available before a devotional is rendered."""
    verse = evidence.get("verse", {})
    required = ("reference", "translation", "text", "source_url")
    missing = [field for field in required if not str(verse.get(field, "")).strip()]
    if missing:
        raise ValueError(f"Evidence is missing verse fields: {', '.join(missing)}")
    if verse["translation"].upper() != "WEB":
        raise ValueError("Faith Nexus defaults to the public-domain WEB translation.")
    if len(words(verse["text"])) < 8:
        raise ValueError("The supplied Bible quotation is incomplete.")


def validate_storyboard(storyboard: dict[str, Any]) -> None:
    """Reject a storyboard that cannot be honestly rendered or reviewed."""
    validate_evidence(storyboard.get("evidence", {}))
    narration = storyboard.get("narration", "")
    word_count = len(words(narration))
    if not 85 <= word_count <= 105:
        raise ValueError(f"Narration needs 85-105 words; received {word_count}.")
    verse = storyboard["evidence"]["verse"]
    if verse["text"] not in narration:
        raise ValueError("Narration must contain the exact complete WEB quotation.")
    beats = storyboard.get("visual_beats", [])
    if not 10 <= len(beats) <= 18:
        raise ValueError("Faith Nexus requires 10-18 visual beats.")
    expected = list(range(1, len(beats) + 1))
    if [beat.get("beat_number") for beat in beats] != expected:
        raise ValueError("Visual beats must have consecutive beat_number values.")
    total_words = len(words(narration))
    previous_end = 0
    for beat in beats:
        if not str(beat.get("image_prompt", "")).strip() or beat.get("image_prompt", "").strip().lower() in PLACEHOLDERS:
            raise ValueError(f"Beat {beat.get('beat_number')} has no production image prompt.")
        if beat.get("camera_motion") not in {"push_in", "pull_out", "pan_left", "pan_right", "still"}:
            raise ValueError(f"Beat {beat.get('beat_number')} has an unsupported camera motion.")
        start, end = int(beat.get("start_word", 0)), int(beat.get("end_word", 0))
        if start != previous_end + 1 or end < start or end > total_words:
            raise ValueError("Visual beat word ranges must cover narration sequentially without gaps.")
        previous_end = end
    if previous_end != total_words:
        raise ValueError("Visual beat ranges must cover all narration words.")


def load_storyboard(path: str | Path) -> dict[str, Any]:
    import json
    storyboard = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_storyboard(storyboard)
    return storyboard
