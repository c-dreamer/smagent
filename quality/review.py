"""Human-first quality gate; reviewers may include Codex but production never depends on it."""

from __future__ import annotations

from typing import Any

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
