"""SEO-optimized YouTube metadata generator for the social media agent."""

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional

# Ensure the parent 'social-media' directory is on sys.path so that
# absolute imports like `from config import CHANNELS` resolve correctly
# when this file is executed as `python3 metadata/optimizer.py ...`.
_HERE = os.path.dirname(os.path.abspath(__file__))
_PARENT = os.path.dirname(_HERE)
if _PARENT not in sys.path:
    sys.path.insert(0, _PARENT)

from config import CHANNELS  # noqa: E402

# YouTube category IDs
CATEGORY_IDS = {
    "soccer": 17,
    "christian": 22,
    "trading": 28,
}

# Niche-specific base tag pools
BASE_TAGS: Dict[str, List[str]] = {
    "soccer": [
        "football", "soccer", "premier league", "world cup", "goal highlights",
        "analysis", "match review", "football analysis", "soccer highlights",
        "goals", "skills", "tactics", "football news", "soccer news",
    ],
    "christian": [
        "bible", "faith", "jesus", "christian", "devotional", "prayer",
        "scripture", "gospel", "worship", "church", "christian life",
        "bible study", "faith journey", "spiritual growth", "testimony",
    ],
    "trading": [
        "trading", "forex", "stocks", "market analysis", "investing",
        "finance", "stock market", "trading strategy", "forex trading",
        "technical analysis", "crypto", "day trading", "financial education",
    ],
}


def _build_title(channel: str, topic: str) -> str:
    """Generate a 30-60 character title using the per-channel formula."""
    channel_cfg = CHANNELS.get(channel)
    channel_name = channel_cfg.name if channel_cfg else channel

    formulas = {
        "soccer": f"{topic} | {channel_name}",
        "christian": f"{topic} — {channel_name}",
        "trading": f"{topic} 📊 {channel_name}",
    }
    title = formulas.get(channel, f"{topic} | {channel_name}")

    # Clamp to 30-60 characters
    if len(title) < 30:
        # Pad with a relevant suffix without exceeding 60
        extra = " — Watch Now"
        title = (title + extra)[:60]
    elif len(title) > 60:
        title = title[:57] + "..."

    return title


def _build_description(
    channel: str,
    topic: str,
    scenes: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Build a 500-2000 character description with 3+ paragraphs."""
    channel_cfg = CHANNELS.get(channel)
    channel_name = channel_cfg.name if channel_cfg else channel
    channel_handle = channel_cfg.handle if channel_cfg else f"@{channel}"
    niche = channel_cfg.niche if channel_cfg else channel

    # Paragraph 1: summary
    p1 = (
        f"In this video, we explore {topic}. "
        f"{channel_name} brings you {niche} content "
        f"designed to inform, engage, and inspire our community. "
        f"Whether you're a longtime follower or new to the channel, "
        f"this video delivers the insights and highlights you're looking for."
    )

    # Paragraph 2: timestamped chapters from script scenes
    chapters: List[str] = []
    if scenes:
        cumulative = 0
        for scene in scenes:
            scene_num = scene.get("scene_number", 0)
            duration = scene.get("duration_seconds", 0)
            desc = scene.get("description", "")
            start = cumulative
            end = cumulative + duration
            chapters.append(f"{start // 60}:{start % 60:02d} - {desc}")
            cumulative = end

    if chapters:
        chapter_lines = "\n".join(f"  {c}" for c in chapters)
        p2 = (
            f"Chapters:\n{chapter_lines}\n\n"
            f"Follow along as we break down each section and cover "
            f"everything you need to know about {topic}."
        )
    else:
        p2 = (
            f"Follow along as we break down everything you need to know "
            f"about {topic}. We cover the key moments, analysis, and takeaways "
            f"that make this video worth your time."
        )

    # Paragraph 3: CTA + channel description
    p3 = (
        f"Enjoyed the video? Hit the LIKE button and SUBSCRIBE to {channel_name} "
        f"({channel_handle}) for more {niche} content. "
        f"Turn on notifications so you never miss an upload!\n\n"
        f"Connect with us:\n"
        f"  • Channel: {channel_handle}\n"
        f"  • Niche: {niche}\n\n"
        f"Thanks for watching — see you in the next one!"
    )

    # Trading disclaimer
    disclaimer = ""
    if channel == "trading":
        disclaimer = (
            "\n\n---\n"
            "Disclaimer: This is not financial advice. "
            "Trading involves risk. Always do your own research before making "
            "any investment decisions."
        )

    description = f"{p1}\n\n{p2}\n\n{p3}{disclaimer}"

    # Ensure minimum length
    if len(description) < 500:
        description += (
            "\n\nDon't forget to share this video with friends who might find it useful. "
            "We appreciate your support and feedback — drop a comment below!"
        )

    return description


def _build_tags(channel: str, topic: str) -> List[str]:
    """Generate 10-15 relevant tags."""
    channel_cfg = CHANNELS.get(channel)
    channel_name = channel_cfg.name if channel_cfg else channel

    base = list(BASE_TAGS.get(channel, []))
    # Derive topic keywords (simple split)
    topic_words = [w.lower().strip(".,!?") for w in topic.split() if len(w) > 2]
    derived = list(dict.fromkeys(topic_words))  # preserve order, dedupe

    tags: List[str] = []
    # Always include channel name
    tags.append(channel_name.lower())

    # Add derived topic words first (most relevant)
    for word in derived:
        if word not in tags and len(tags) < 15:
            tags.append(word)

    # Fill remaining with base niche tags
    for tag in base:
        if tag not in tags and len(tags) < 15:
            tags.append(tag)

    # Pad to at least 10 if needed
    generic_fallbacks = ["video", "guide", "tips", "how to", "explained"]
    for tag in generic_fallbacks:
        if len(tags) >= 10:
            break
        if tag not in tags:
            tags.append(tag)

    return tags[:15]


def generate_metadata(
    channel: str,
    topic: str,
    script: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Generate SEO-optimized YouTube metadata for a given channel and topic.

    Args:
        channel: Channel key (soccer, christian, trading).
        topic: Main video topic.
        script: Optional parsed script JSON with a 'scenes' list.

    Returns:
        Metadata dict with title, description, tags, categoryId, language,
        made_for_kids.
    """
    if channel not in CHANNELS:
        raise ValueError(
            f"Unknown channel '{channel}'. "
            f"Valid channels: {list(CHANNELS.keys())}"
        )

    scenes: Optional[List[Dict[str, Any]]] = None
    if script and isinstance(script, dict):
        scenes = script.get("scenes")

    title = _build_title(channel, topic)
    description = _build_description(channel, topic, scenes)
    tags = _build_tags(channel, topic)
    category_id = CATEGORY_IDS.get(channel, 0)

    return {
        "title": title,
        "description": description,
        "tags": tags,
        "categoryId": category_id,
        "language": "en",
        "made_for_kids": False,
    }


def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate SEO-optimized YouTube metadata."
    )
    parser.add_argument(
        "--channel",
        required=True,
        choices=list(CHANNELS.keys()),
        help="Channel key (soccer, christian, trading).",
    )
    parser.add_argument(
        "--topic",
        required=True,
        help="Main video topic.",
    )
    parser.add_argument(
        "--script",
        default=None,
        help="Path to script JSON file (optional, for timestamps).",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path to write metadata JSON.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = _parse_args(argv)

    script_data: Optional[Dict[str, Any]] = None
    if args.script:
        with open(args.script, "r", encoding="utf-8") as f:
            script_data = json.load(f)

    metadata = generate_metadata(
        channel=args.channel,
        topic=args.topic,
        script=script_data,
    )

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    return 0


if __name__ == "__main__":
    sys.exit(main())
