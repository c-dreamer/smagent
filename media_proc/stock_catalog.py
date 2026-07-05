#!/usr/bin/env python3
"""
Stock asset catalog — manages local stock footage library for all channels.

Stores asset metadata (path, orientation, duration, keywords, used count)
in a local JSON catalog so the pipeline can auto-select the best clip for any scene.

Built from existing local Pexels footage (no API keys needed for existing assets).
"""

import json
import os
from pathlib import Path
from typing import Optional

CATALOG_PATH = Path.home() / "videos" / "stock_catalog.json"
SOURCE_DIR = Path.home() / "videos" / "source"


def _get_media_info(path: str) -> dict:
    """Get duration, dimensions using ffprobe."""
    import subprocess
    info = {"path": path, "file": os.path.basename(path)}
    try:
        # Duration
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", path],
            capture_output=True, text=True, timeout=10
        )
        info["duration"] = round(float(r.stdout.strip()), 2)
        
        # Dimensions + orientation
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height",
             "-of", "csv=p=0", path],
            capture_output=True, text=True, timeout=10
        )
        parts = r.stdout.strip().split(",")
        w, h = int(parts[0]), int(parts[1])
        info["width"] = w
        info["height"] = h
        info["orientation"] = "portrait" if h > w else "landscape"
        
        # File size
        info["size_mb"] = round(os.path.getsize(path) / 1024 / 1024, 1)
    except Exception as e:
        info["error"] = str(e)
    return info


def scan_local_assets() -> list[dict]:
    """Scan SOURCE_DIR for all video files and catalog them."""
    assets = []
    if not SOURCE_DIR.is_dir():
        return assets
    for f in sorted(SOURCE_DIR.glob("*.mp4")):
        assets.append(_get_media_info(str(f)))
    return assets


def build_catalog(force: bool = False) -> list[dict]:
    """Build or return cached catalog."""
    if CATALOG_PATH.exists() and not force:
        with open(CATALOG_PATH) as f:
            return json.load(f)
    assets = scan_local_assets()
    with open(CATALOG_PATH, "w") as f:
        json.dump(assets, f, indent=2)
    print(f"Catalog built: {len(assets)} assets -> {CATALOG_PATH}")
    return assets


def get_clips_for_channel(channel: str, min_duration: float = 0) -> list[dict]:
    """Get all clips suitable for a given channel."""
    assets = build_catalog()
    orientation_map = {
        "soccer": "landscape",
        "trading": "landscape",
        "christian": "portrait",
    }
    target = orientation_map.get(channel, "landscape")
    results = [a for a in assets if a.get("orientation") == target and a.get("duration", 0) >= min_duration]
    results.sort(key=lambda x: x.get("duration", 0), reverse=True)
    return results


def pick_clip(channel: str, needed_duration: float) -> Optional[dict]:
    """Pick the best clip for a scene of needed_duration seconds."""
    clips = get_clips_for_channel(channel, min_duration=needed_duration * 0.8)
    if not clips:
        clips = get_clips_for_channel(channel)
    if clips:
        return clips[0]  # longest matching clip
    return None


if __name__ == "__main__":
    # CLI test
    assets = build_catalog(force=True)
    for ch in ["soccer", "christian", "trading"]:
        clips = get_clips_for_channel(ch)
        print(f"\n{ch}: {len(clips)} clips available")
        for c in clips[:3]:
            print(f"  {c['file']} ({c['duration']}s, {c['width']}x{c['height']})")
