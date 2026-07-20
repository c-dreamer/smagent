"""Minimal ComfyUI HTTP client for reproducible OpenCode-driven image/video jobs."""

from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import requests


class ComfyUIClient:
    def __init__(self, base_url: str, timeout_seconds: int = 900) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def queue(self, workflow: dict[str, Any]) -> str:
        response = requests.post(
            f"{self.base_url}/prompt",
            json={"prompt": workflow, "client_id": str(uuid.uuid4())},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["prompt_id"]

    def wait(self, prompt_id: str, poll_seconds: float = 2.0) -> dict[str, Any]:
        deadline = time.monotonic() + self.timeout_seconds
        while time.monotonic() < deadline:
            response = requests.get(f"{self.base_url}/history/{prompt_id}", timeout=30)
            response.raise_for_status()
            job = response.json().get(prompt_id)
            if job and job.get("status", {}).get("status_str") == "success":
                return job
            if job and job.get("status", {}).get("status_str") == "error":
                raise RuntimeError(f"ComfyUI job failed: {job.get('status')}")
            time.sleep(poll_seconds)
        raise TimeoutError(f"ComfyUI job did not finish within {self.timeout_seconds}s: {prompt_id}")

    def download_outputs(self, job: dict[str, Any], destination: str | Path) -> list[Path]:
        """Download each image/video output while preserving the ComfyUI filename."""
        destination = Path(destination)
        destination.mkdir(parents=True, exist_ok=True)
        downloaded: list[Path] = []
        for node in job.get("outputs", {}).values():
            for group in ("images", "gifs"):
                for asset in node.get(group, []):
                    query = urlencode({"filename": asset["filename"], "subfolder": asset.get("subfolder", ""), "type": asset.get("type", "output")})
                    response = requests.get(f"{self.base_url}/view?{query}", timeout=120)
                    response.raise_for_status()
                    path = destination / Path(asset["filename"]).name
                    path.write_bytes(response.content)
                    downloaded.append(path)
        return downloaded
