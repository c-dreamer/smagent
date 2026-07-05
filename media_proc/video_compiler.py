#!/usr/bin/env python3
"""Video compiler for the social media agent. Uses FFmpeg to compose video from assets."""

import argparse
import json
import os
import subprocess
import sys
import tempfile

_PARENT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PARENT not in sys.path:
    sys.path.insert(0, _PARENT)

from config import CHANNELS  # noqa: E402


def get_media_duration(filepath: str) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", filepath],
        capture_output=True, text=True, check=True,
    )
    return float(result.stdout.strip())


def build_filter_complex(scenes: list, width: int, height: int,
                         audio_duration: float) -> str:
    """Build FFmpeg filter_complex for scene text overlays with timestamps."""
    filters = []
    base = f"[0:v]scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2[bg]"
    filters.append(base)
    last = "bg"
    cumulative = 0.0
    for i, scene in enumerate(scenes):
        dur = scene.get("duration_seconds", 30)
        desc = scene.get("description", "").replace("'", "\\'").replace(":", "\\:")
        label = f"Scene {i + 1}: {desc}"
        ts_in = cumulative
        ts_out = min(cumulative + dur, audio_duration)
        if ts_out <= ts_in:
            cumulative += dur
            continue
        overlay_name = f"v{i}"
        filters.append(
            f"{last}[0:v]overlay=0:0:enable='between(t,{ts_in},{ts_out})'[{overlay_name}]"
        )
        text_filter = (
            f"drawtext=text='{label}':fontcolor=white:fontsize=24:"
            f"x=(w-text_w)/2:y=h-60:box=1:boxcolor=black@0.5:boxborderw=8:"
            f"enable='between(t,{ts_in},{ts_out})'"
        )
        filters.append(f"[{overlay_name}]{text_filter}[t{i}]")
        last = f"t{i}"
        cumulative += dur
    return ";".join(filters)


def compile_video(script_path: str, audio_path: str, thumbnail_path: str,
                  output_path: str) -> str:
    with open(script_path, "r") as f:
        script = json.load(f)
    scenes = script.get("scenes", [])
    if not scenes:
        raise ValueError("No scenes in script")

    audio_duration = get_media_duration(audio_path)
    width, height = 1920, 1080
    filter_complex = build_filter_complex(scenes, width, height, audio_duration)

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", thumbnail_path,
        "-i", audio_path,
        "-c:v", "libx264", "-t", str(audio_duration),
        "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
        "-shortest",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg failed:\n{result.stderr}")

    actual_dur = get_media_duration(output_path)
    if actual_dur <= 0:
        raise ValueError("Output video has zero duration")

    return output_path


def main():
    parser = argparse.ArgumentParser(description="Compile video from script, audio and thumbnail")
    parser.add_argument("--script", required=True, help="Path to script JSON")
    parser.add_argument("--audio", required=True, help="Path to voiceover audio file")
    parser.add_argument("--thumbnail", required=True, help="Path to thumbnail image")
    parser.add_argument("--output", required=True, help="Output video file path")
    args = parser.parse_args()

    try:
        compile_video(args.script, args.audio, args.thumbnail, args.output)
        print(f"Video compiled: {args.output}")
        dur = get_media_duration(args.output)
        print(f"Duration: {dur:.1f}s")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
