"""No-key Wikimedia Commons still-image retrieval with licence-aware provenance.

The module creates gentle motion clips from openly licensed stills. It is a
fallback for review candidates when licensed stock-video access is unavailable;
Pexels remains the preferred Faith Nexus production source.
"""

from __future__ import annotations

import argparse
import html
import json
import subprocess
from pathlib import Path
from typing import Any

import requests

API_URL = "https://commons.wikimedia.org/w/api.php"
ALLOWED_LICENCE_TOKENS = ("cc by", "cc0", "public domain")
DISALLOWED_LICENCE_TOKENS = ("noncommercial", "non-commercial", "no derivatives", "no-derivatives")


def _scene_query(scene: dict[str, Any]) -> str:
    query = scene.get("visual_query") or scene.get("description") or scene.get("visual_cue") or "peaceful morning landscape"
    # Search works better with a concise visual noun phrase than a full prompt.
    return " ".join(query.replace(",", " ").split()[:9])


def _metadata_text(item: dict[str, Any], name: str) -> str:
    return html.unescape(item.get("extmetadata", {}).get(name, {}).get("value", "")).strip()


def _is_allowed(item: dict[str, Any]) -> bool:
    licence = _metadata_text(item, "LicenseShortName").lower()
    return bool(licence) and any(token in licence for token in ALLOWED_LICENCE_TOKENS) and not any(token in licence for token in DISALLOWED_LICENCE_TOKENS)


def search_images(query: str, limit: int = 25) -> list[dict[str, Any]]:
    response = requests.get(
        API_URL,
        params={
            "action": "query", "format": "json", "generator": "search", "gsrsearch": query,
            "gsrnamespace": 6, "gsrlimit": limit, "prop": "imageinfo", "iiprop": "url|size|mime|extmetadata",
            "iiurlwidth": 1440,
        },
        timeout=30,
    )
    response.raise_for_status()
    pages = response.json().get("query", {}).get("pages", {})
    results = []
    for page in pages.values():
        info = (page.get("imageinfo") or [{}])[0]
        if info.get("mime") not in ("image/jpeg", "image/png") or not info.get("thumburl"):
            continue
        if _is_allowed(info):
            results.append({"page": page, "info": info})
    return results


def choose_image(results: list[dict[str, Any]]) -> dict[str, Any]:
    if not results:
        raise ValueError("No Commons image with an allowed reusable licence was found for this scene.")
    return max(results, key=lambda result: int(result["info"].get("width") or 0) * int(result["info"].get("height") or 0))


def _download(url: str, destination: Path) -> None:
    with requests.get(url, stream=True, timeout=120) as response:
        response.raise_for_status()
        with destination.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    handle.write(chunk)


def _render_motion_still(image: Path, output: Path, duration: float) -> None:
    # Editing motion is for presentation only and does not modify licensing terms.
    fps = 24
    frames = max(1, int(duration * fps))
    vf = f"zoompan=z='min(zoom+0.0007,1.08)':d={frames}:s=1080x1920:fps={fps},format=yuv420p"
    subprocess.run(
        ["ffmpeg", "-y", "-loop", "1", "-i", str(image), "-t", str(duration), "-vf", vf,
         "-r", str(fps), "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(output)],
        check=True, capture_output=True, text=True,
    )


def retrieve_scenes(script: dict[str, Any], destination: str | Path) -> list[dict[str, Any]]:
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    assets: list[dict[str, Any]] = []
    for index, scene in enumerate(script.get("scenes", []), start=1):
        query = _scene_query(scene)
        selected = choose_image(search_images(query))
        page, info = selected["page"], selected["info"]
        suffix = ".png" if info.get("mime") == "image/png" else ".jpg"
        image_path = destination / f"scene_{index:02d}_commons_{page['pageid']}{suffix}"
        clip_path = destination / f"scene_{index:02d}_commons_{page['pageid']}.mp4"
        _download(info["thumburl"], image_path)
        _render_motion_still(image_path, clip_path, float(scene.get("duration_seconds") or 6))
        assets.append({
            "scene_number": scene.get("scene_number", index), "provider": "Wikimedia Commons",
            "licence": _metadata_text(info, "LicenseShortName"), "licence_url": _metadata_text(info, "LicenseUrl"),
            "creator": _metadata_text(info, "Artist"), "attribution": _metadata_text(info, "AttributionRequired"),
            "asset_url": "https://commons.wikimedia.org/?curid=" + str(page["pageid"]),
            "query": query, "local_source_path": str(image_path), "local_path": str(clip_path),
        })
    return assets


def main() -> None:
    parser = argparse.ArgumentParser(description="Retrieve licence-verified Commons stills and render motion clips.")
    parser.add_argument("--script", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--manifest", required=True)
    args = parser.parse_args()
    script = json.loads(Path(args.script).read_text(encoding="utf-8"))
    assets = retrieve_scenes(script, args.output_dir)
    Path(args.manifest).write_text(json.dumps({"assets": assets}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Retrieved and rendered {len(assets)} Commons visual clips; provenance written to {args.manifest}")


if __name__ == "__main__":
    main()
