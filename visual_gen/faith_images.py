#!/usr/bin/env python3
"""Acquire one traceable Faith Nexus image per storyboard beat.

ComfyUI is the production default. Pexels is deliberately an explicit fallback;
the provenance manifest states which route was used for every beat.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import sys
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

_PARENT = str(Path(__file__).resolve().parents[1])
if _PARENT not in sys.path:
    sys.path.insert(0, _PARENT)

from faith_nexus import load_storyboard
from visual_gen.comfyui import ComfyUIClient

load_dotenv(Path(__file__).resolve().parents[3] / "human-ai.env2")


def _write_manifest(destination: Path, provider: str, storyboard: dict[str, Any], assets: list[dict[str, Any]]) -> Path:
    path = destination / "visual_asset_provenance.json"
    path.write_text(json.dumps({
        "provider": provider,
        "generated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "storyboard_title": storyboard["title"],
        "assets": assets,
    }, indent=2), encoding="utf-8")
    return path


def _inject_prompt(value: Any, prompt: str) -> Any:
    if isinstance(value, str):
        return value.replace("{{PROMPT}}", prompt)
    if isinstance(value, list):
        return [_inject_prompt(item, prompt) for item in value]
    if isinstance(value, dict):
        return {key: _inject_prompt(item, prompt) for key, item in value.items()}
    return value


def acquire_comfyui(storyboard: dict[str, Any], destination: Path, workflow_template: Path) -> list[dict[str, Any]]:
    base_url = os.getenv("COMFYUI_URL")
    if not base_url:
        raise RuntimeError("COMFYUI_URL is required for generated Faith Nexus imagery.")
    template = json.loads(workflow_template.read_text(encoding="utf-8"))
    client = ComfyUIClient(base_url)
    assets: list[dict[str, Any]] = []
    for beat in storyboard["visual_beats"]:
        prompt = f"{beat['image_prompt']}. {storyboard['visual_style']}"
        job = client.wait(client.queue(_inject_prompt(copy.deepcopy(template), prompt)))
        outputs = client.download_outputs(job, destination)
        if not outputs:
            raise RuntimeError(f"ComfyUI returned no image for beat {beat['beat_number']}.")
        image = outputs[0]
        target = destination / f"beat_{beat['beat_number']:02d}{image.suffix.lower()}"
        if image != target:
            image.replace(target)
        assets.append({"beat_number": beat["beat_number"], "provider": "comfyui", "prompt": prompt,
                       "workflow": str(workflow_template), "local_path": str(target), "generated": True})
    return assets


def acquire_pexels(storyboard: dict[str, Any], destination: Path) -> list[dict[str, Any]]:
    key = os.getenv("PEXELS_API_KEY")
    if not key:
        raise RuntimeError("PEXELS_API_KEY is required for the licensed Pexels fallback.")
    headers = {"Authorization": key}
    assets: list[dict[str, Any]] = []
    for beat in storyboard["visual_beats"]:
        query = beat["image_prompt"][:180]
        response = requests.get("https://api.pexels.com/v1/search", headers=headers,
                                params={"query": query, "orientation": "portrait", "size": "large", "per_page": 1}, timeout=30)
        response.raise_for_status()
        photos = response.json().get("photos", [])
        if not photos:
            raise RuntimeError(f"Pexels found no portrait image for beat {beat['beat_number']}: {query}")
        photo = photos[0]
        source = photo["src"].get("large2x") or photo["src"]["large"]
        binary = requests.get(source, timeout=90)
        binary.raise_for_status()
        path = destination / f"beat_{beat['beat_number']:02d}.jpg"
        path.write_bytes(binary.content)
        assets.append({"beat_number": beat["beat_number"], "provider": "pexels", "prompt": query,
                       "generated": False, "license": "Pexels License; preserve attribution URL in manifest",
                       "asset_id": photo["id"], "creator": photo.get("photographer"),
                       "creator_url": photo.get("photographer_url"), "source_url": photo.get("url"), "local_path": str(path)})
    return assets


def main() -> None:
    parser = argparse.ArgumentParser(description="Acquire one Faith Nexus visual per storyboard beat.")
    parser.add_argument("--storyboard", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--provider", choices=("comfyui", "pexels"), default="comfyui")
    parser.add_argument("--workflow-template", type=Path, help="ComfyUI API workflow JSON containing {{PROMPT}}.")
    args = parser.parse_args()
    storyboard, destination = load_storyboard(args.storyboard), Path(args.output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    if args.provider == "comfyui":
        if not args.workflow_template:
            parser.error("--workflow-template is required for --provider comfyui")
        assets = acquire_comfyui(storyboard, destination, args.workflow_template)
    else:
        assets = acquire_pexels(storyboard, destination)
    print(_write_manifest(destination, args.provider, storyboard, assets))


if __name__ == "__main__":
    main()
