"""Human-first quality gate; reviewers may include Codex but production never depends on it."""

from __future__ import annotations

from typing import Any
from pathlib import Path
import json

from faith_nexus import load_storyboard, words

REQUIRED_DIMENSIONS = (
    "emotional_specificity",
    "source_fidelity",
    "visual_coherence",
    "voice_caption_sync",
    "brand_fit",
    "technical_finish",
    "provenance",
)


def blank_review(reviewer: str = "human") -> dict[str, Any]:
    return {
        "reviewer": reviewer,
        "scale": "1-5",
        "dimensions": {name: None for name in REQUIRED_DIMENSIONS},
        "blocking_issues": [],
        "notes": "",
        "approved": False,
    }


def assess_review(review: dict[str, Any], minimum_score: int = 4) -> dict[str, Any]:
    """Return an explicit decision; a reviewer name never changes the gate."""
    dimensions = review.get("dimensions", {})
    missing = [name for name in REQUIRED_DIMENSIONS if dimensions.get(name) is None]
    invalid = [name for name in REQUIRED_DIMENSIONS if dimensions.get(name) not in (None, 1, 2, 3, 4, 5)]
    below_bar = [name for name in REQUIRED_DIMENSIONS if isinstance(dimensions.get(name), int) and dimensions[name] < minimum_score]
    blocking = review.get("blocking_issues", [])
    return {
        "approved": not missing and not invalid and not below_bar and not blocking and bool(review.get("approved")),
        "missing_dimensions": missing,
        "invalid_dimensions": invalid,
        "below_bar": below_bar,
        "blocking_issues": blocking,
    }


def validate_faith_nexus_bundle(storyboard_path: str | Path, timing_path: str | Path,
                                provenance_path: str | Path, caption_path: str | Path) -> dict[str, Any]:
    """Machine preflight; human review still decides whether the candidate publishes."""
    storyboard = load_storyboard(storyboard_path)
    timings = json.loads(Path(timing_path).read_text(encoding="utf-8"))
    provenance = json.loads(Path(provenance_path).read_text(encoding="utf-8"))
    captions = json.loads(Path(caption_path).read_text(encoding="utf-8"))
    checks = {
        "exact_web_verse": storyboard["evidence"]["verse"]["text"] in storyboard["narration"],
        "timed_every_word": len(timings.get("words", [])) == len(words(storyboard["narration"])),
        "one_visual_per_beat": len(provenance.get("assets", [])) == len(storyboard["visual_beats"]),
        "generated_visuals": bool(provenance.get("assets")) and all(asset.get("generated") is True for asset in provenance["assets"]),
        "caption_events": bool(captions.get("events")),
        "continuous_caption_track": bool(captions.get("caption_track_continuous")) and Path(str(captions.get("caption_track", ""))).is_file(),
        "cta_animation": (not captions.get("cta_required")) or Path(str(captions.get("cta_asset", ""))).is_file(),
        "audio_duration": float(captions.get("audio_duration", 0)) > 0,
    }
    return {"passed": all(checks.values()), "checks": checks, "requires_human_approval": True}
