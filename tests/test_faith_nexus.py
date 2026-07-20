import json
from pathlib import Path

import pytest

from faith_nexus import load_storyboard, validate_storyboard, words
from media_proc.faith_nexus_renderer import _caption_groups
from quality.review import validate_faith_nexus_bundle


ROOT = Path(__file__).resolve().parents[1]
STORYBOARD = ROOT / "examples" / "faith_nexus_matthew_6_34_storyboard.json"


def test_reference_storyboard_is_source_bound_and_complete():
    storyboard = load_storyboard(STORYBOARD)
    assert storyboard["evidence"]["verse"]["translation"] == "WEB"
    assert len(storyboard["visual_beats"]) == 12


def test_storyboard_rejects_missing_complete_verse():
    storyboard = json.loads(STORYBOARD.read_text())
    storyboard["narration"] = storyboard["narration"].replace(storyboard["evidence"]["verse"]["text"], "Tomorrow will be okay.")
    with pytest.raises(ValueError, match="exact complete WEB"):
        validate_storyboard(storyboard)


def test_caption_events_highlight_each_timed_word():
    events = _caption_groups({"words": [
        {"text": "Peace", "start": 0.0, "end": 0.2},
        {"text": "for", "start": 0.2, "end": 0.4},
        {"text": "today", "start": 0.4, "end": 0.7},
    ]})
    assert len(events) == 3
    assert [event["active"] for event in events] == [0, 1, 2]


def test_caption_events_hold_through_tts_pauses_without_flashing():
    events = _caption_groups({"words": [
        {"text": "Peace", "start": 0.0, "end": 0.2},
        {"text": "for", "start": 0.55, "end": 0.7},
        {"text": "today", "start": 1.2, "end": 1.5},
    ]})
    assert events[0]["end"] == 0.55
    assert events[1]["end"] == 1.2
    assert events[0]["tokens"] == ["Peace", "for", "today"]


def test_bundle_preflight_requires_all_review_inputs(tmp_path):
    storyboard = tmp_path / "storyboard.json"
    storyboard.write_text(STORYBOARD.read_text())
    narration_words = len(words(json.loads(STORYBOARD.read_text())["narration"]))
    timings = tmp_path / "words.json"
    timings.write_text(json.dumps({"words": [{"text": "x", "start": i, "end": i + 0.1} for i in range(narration_words)]}))
    provenance = tmp_path / "provenance.json"
    provenance.write_text(json.dumps({"assets": [{"beat_number": index, "generated": True} for index in range(1, 13)]}))
    captions = tmp_path / "captions.json"
    captions.write_text(json.dumps({"events": [{"start": 0, "end": 0.1}], "audio_duration": 35.0}))
    assert validate_faith_nexus_bundle(storyboard, timings, provenance, captions)["passed"]
