"""Licensed Pexels video retrieval with per-asset provenance records.

This is deliberately a source-acquisition layer, not a generic downloader. It
only retrieves Pexels API results and retains attribution required to review the
asset's licence before publication.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()
# The shared private env file is optional: deployments should pass credentials as
# normal environment variables, while this workstation keeps its keys outside
# the repository.
load_dotenv(Path(__file__).resolve().parents[3] / "human-ai.env2")

API_URL = "https://api.pexels.com/v1/videos/search"


def _api_key() -> str:
    key = os.getenv("PEXELS_API_KEY")
    if not key:
        raise RuntimeError("PEXELS_API_KEY is required; add it to the OpenCode/VPS environment or local untracked .env.")
    return key


def _scene_query(scene: dict[str, Any]) -> str:
    return scene.get("visual_query") or scene.get("description") or scene.get("visual_cue") or "quiet thoughtful moment"


def search_videos(query: str, *, orientation: str = "portrait", per_page: int = 15) -> list[dict[str, Any]]:
    response = requests.get(
        API_URL,
        headers={"Authorization": _api_key()},
        params={"query": query, "orientation": orientation, "size": "large", "per_page": per_page},
        timeout=30,
    )
    response.raise_for_status()
    return response.json().get("videos", [])


def choose_video(videos: list[dict[str, Any]], required_seconds: float) -> tuple[dict[str, Any], dict[str, Any]]:
    """Prefer portrait HD files long enough for the scene, without hiding the selection."""
    candidates: list[tuple[int, dict[str, Any], dict[str, Any]]] = []
    for video in videos:
        duration = float(video.get("duration") or 0)
        for file in video.get("video_files", []):
            if file.get("file_type") != "video/mp4" or not file.get("link"):
                continue
            width, height = int(file.get("width") or 0), int(file.get("height") or 0)
            is_portrait = height > width
            long_enough = duration >= required_seconds
            # A 1080×1920 Short gains no visible quality from an enormous UHD
            # transfer, while the larger download makes a batch less reliable.
            pixels = width * height
            target_pixels = 1080 * 1920
            delivery_fit = -abs(pixels - target_pixels)
            score = (10_000_000 if long_enough else 0) + (1_000_000 if is_portrait else 0) + delivery_fit
            candidates.append((score, video, file))
    if not candidates:
        raise ValueError("Pexels returned no downloadable MP4 files for this scene.")
    _score, video, file = max(candidates, key=lambda item: item[0])
    return video, file


def _download(url: str, destination: Path) -> None:
    with requests.get(url, stream=True, timeout=180) as response:
        response.raise_for_status()
        with destination.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    handle.write(chunk)


def _write_manifest(path: Path, assets: list[dict[str, Any]]) -> None:
    path.write_text(json.dumps({"assets": assets}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def retrieve_scenes(script: dict[str, Any], destination: str | Path, manifest_path: str | Path | None = None) -> list[dict[str, Any]]:
    """Retrieve clips and checkpoint provenance after each completed scene."""
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    manifest = Path(manifest_path) if manifest_path else None
    assets: list[dict[str, Any]] = []
    if manifest and manifest.is_file():
        assets = json.loads(manifest.read_text(encoding="utf-8")).get("assets", [])
    completed = {asset.get("scene_number") for asset in assets if Path(asset.get("local_path", "")).is_file()}
    for index, scene in enumerate(script.get("scenes", []), start=1):
        if scene.get("scene_number", index) in completed:
            continue
        query = _scene_query(scene)
        duration = float(scene.get("duration_seconds") or 6)
        video, video_file = choose_video(search_videos(query), duration)
        filename = f"scene_{index:02d}_pexels_{video['id']}.mp4"
        path = destination / filename
        _download(video_file["link"], path)
        assets.append({
            "scene_number": scene.get("scene_number", index),
            "provider": "Pexels",
            "licence": "Pexels License (verify before publication)",
            "query": query,
            "asset_id": video["id"],
            "asset_url": video.get("url"),
            "creator": video.get("user", {}).get("name"),
            "creator_url": video.get("user", {}).get("url"),
            "duration_seconds": video.get("duration"),
            "selected_file": {"width": video_file.get("width"), "height": video_file.get("height"), "quality": video_file.get("quality")},
            "local_path": str(path),
        })
        if manifest:
            _write_manifest(manifest, assets)
    return assets


def main() -> None:
    parser = argparse.ArgumentParser(description="Retrieve licensed Pexels visual clips for an evidence-bound script.")
    parser.add_argument("--script", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--manifest", required=True, help="Write visual asset provenance JSON here")
    args = parser.parse_args()
    script = json.loads(Path(args.script).read_text(encoding="utf-8"))
    assets = retrieve_scenes(script, args.output_dir, args.manifest)
    _write_manifest(Path(args.manifest), assets)
    print(f"Retrieved {len(assets)} licensed Pexels clips; provenance written to {args.manifest}")


if __name__ == "__main__":
    main()
