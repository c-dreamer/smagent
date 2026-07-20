#!/usr/bin/env python3
"""Recreate the four superseded Christian drafts with the Faith Nexus recipe."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv

from faith_nexus import load_storyboard, words
from pipeline.orchestrator import run_faith_nexus_storyboard

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT.parents[1] / "human-ai.env2")
OUTPUT = Path(os.environ.get("SMAGENT_FAITH_NEXUS_WORKSPACE_DIR", str(Path.home() / "Downloads" / "smagent_output"))) / "faith_nexus_remakes"

RECIPES = [
    {"slug": "proverbs_3_5_6", "title": "When You Cannot See the Road", "reference": "Proverbs 3:5–6", "source_url": "https://ebible.org/eng-web/PRO03.htm", "accent": "#78B6D8", "verse": "Trust in Yahweh with all your heart, and don’t lean on your own understanding. In all your ways acknowledge him, and he will make your paths straight.", "narration": "When you cannot see the road, it is tempting to trust what you can calculate. But understanding was not meant to carry answers. God invites you to rest your next step in him. Scripture says: “Trust in Yahweh with all your heart, and don’t lean on your own understanding. In all your ways acknowledge him, and he will make your paths straight.” Proverbs 3:5–6. You do not need a map tonight. Bring God the decision, the uncertainty, and the path ahead. Walk faithfully with the light you have. Jesus loves you, and stay blessed. Like and subscribe for more Christian content.", "mood": "cool blue dawn, winding path, quiet trust"},
    {"slug": "john_3_16", "title": "Loved Before You Earned It", "reference": "John 3:16", "source_url": "https://ebible.org/eng-web/JHN03.htm", "accent": "#D68A62", "verse": "For God so loved the world, that he gave his only born Son, that whoever believes in him should not perish, but have eternal life.", "narration": "Love can feel distant when life is difficult, but the gospel begins with God moving toward us. Not because we earned it, but because he loved us first. Hear this promise: “For God so loved the world, that he gave his only born Son, that whoever believes in him should not perish, but have eternal life.” John 3:16. This is not a vague hope. In Christ, you are seen, wanted, and invited into life with God. Let that love meet you where you are today. Jesus loves you, and stay blessed. Like and subscribe for more Christian content.", "mood": "warm sunset, welcoming light, gentle love"},
    {"slug": "philippians_4_13", "title": "Strength for This Step", "reference": "Philippians 4:13", "source_url": "https://ebible.org/eng-web/PHI04.htm", "accent": "#A889D5", "verse": "I can do all things through Christ, who strengthens me.", "narration": "Some days demand more than you feel able to give. The task is heavy, the strength is low, and you wonder how you will keep going. But your strength does not begin with your own ability. Scripture says: “I can do all things through Christ, who strengthens me.” Philippians 4:13. This verse is not pressure to perform everything. It is a promise that Christ meets you with strength for the calling in front of you. Take the next faithful step. Jesus loves you, and stay blessed. Like and subscribe for more Christian content.", "mood": "violet sunrise, mountain path, steady courage"},
    {"slug": "isaiah_40_31", "title": "Strength While You Wait", "reference": "Isaiah 40:31", "source_url": "https://ebible.org/eng-web/ISA40.htm", "accent": "#E3A84E", "verse": "but those who wait for Yahweh will renew their strength. They will mount up with wings like eagles. They will run, and not be weary. They will walk, and not faint.", "narration": "Waiting can feel like standing still while others move. You may be tired of hoping, tired of trying, and tired of carrying what you cannot control. Yet God speaks strength into the waiting: “but those who wait for Yahweh will renew their strength. They will mount up with wings like eagles. They will run, and not be weary. They will walk, and not faint.” Isaiah 40:31. Waiting on God is not wasted time. He renews what exhaustion has drained and gives you grace for the next mile. Keep looking to him. Jesus loves you, and stay blessed. Like and subscribe for more Christian content.", "mood": "golden sunrise, open sky, renewed strength"},
]

BEAT_IDEAS = ("an anxious person before sunrise", "hands resting beside an open Bible", "a quiet window with first light", "a winding path through hills", "an ancient olive tree in warm light", "a person taking one small step", "sunlight through clouds", "an open Bible and a candle", "a calm face turning toward light", "a ridge above a valley", "open hands in prayer", "a hopeful figure walking forward", "a reverent cross silhouette on a distant hill")


def storyboard(recipe: dict) -> dict:
    total = len(words(recipe["narration"]))
    ends = [round(total * (index + 1) / len(BEAT_IDEAS)) for index in range(len(BEAT_IDEAS))]
    start = 1
    beats = []
    motions = ("push_in", "pan_right", "pull_out", "pan_left")
    for number, (idea, end) in enumerate(zip(BEAT_IDEAS, ends), 1):
        beats.append({"beat_number": number, "start_word": start, "end_word": end, "image_prompt": f"{idea}, {recipe['mood']}, cinematic devotional realism, no text, no logos, no depiction of Jesus", "camera_motion": motions[(number - 1) % len(motions)], "transition": "cut"})
        start = end + 1
    return {"channel": "christian", "title": recipe["title"], "narration": recipe["narration"], "evidence": {"verse": {"reference": recipe["reference"], "translation": "WEB", "text": recipe["verse"], "source_url": recipe["source_url"]}}, "visual_style": f"Cinematic devotional realism, {recipe['mood']}, cohesive film grain, no text, no logos, no depiction of Jesus, vertical 9:16.", "caption_style": {"accent_hex": recipe["accent"], "caption_hex": "#FFFFFF", "theme_name": recipe["mood"]}, "transition_style": "cut", "visual_beats": beats}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--render", action="store_true", help="Render review candidates with licensed Pexels fallback.")
    args = parser.parse_args()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for recipe in RECIPES:
        target = OUTPUT / recipe["slug"]
        target.mkdir(parents=True, exist_ok=True)
        path = target / "storyboard.json"
        data = storyboard(recipe)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        load_storyboard(path)
        print(f"validated {path}")
        if args.render:
            print(json.dumps(run_faith_nexus_storyboard(str(path), str(target), image_provider="pexels"), indent=2))


if __name__ == "__main__":
    main()
