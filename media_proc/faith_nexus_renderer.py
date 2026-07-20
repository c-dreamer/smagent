#!/usr/bin/env python3
"""Audio-led Faith Nexus image-film renderer with word-highlight captions."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

_PARENT = str(Path(__file__).resolve().parents[1])
if _PARENT not in sys.path:
    sys.path.insert(0, _PARENT)

from faith_nexus import load_storyboard, words

WIDTH, HEIGHT, FPS = 1080, 1920, 24
GOLD, WHITE, OUTLINE = (246, 201, 69, 255), (255, 255, 255, 255), (0, 0, 0, 235)
FONT_CANDIDATES = (Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"), Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"))


def _font(size: int) -> ImageFont.FreeTypeFont:
    path = next((item for item in FONT_CANDIDATES if item.exists()), None)
    if not path:
        raise FileNotFoundError("A bold TrueType font is required for Faith Nexus captions.")
    return ImageFont.truetype(path, size)


def _audio_duration(path: Path) -> float:
    result = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)], capture_output=True, text=True, check=True)
    return float(result.stdout.strip())


def _caption_groups(timings: dict[str, Any]) -> list[dict[str, Any]]:
    entries = timings.get("words", [])
    if not entries:
        raise ValueError("Word timing JSON has no words.")
    result: list[dict[str, Any]] = []
    for start in range(0, len(entries), 4):
        group = entries[start:start + 4]
        for active, item in enumerate(group):
            result.append({"start": item["start"], "end": max(item["end"], item["start"] + 0.08),
                           "tokens": [word["text"] for word in group], "active": active})
    return result


def _caption_png(tokens: list[str], active: int, destination: Path) -> None:
    image = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    font = _font(88)
    upper = [token.upper() for token in tokens]
    space = int(draw.textlength(" ", font=font))
    rows: list[list[tuple[int, str, int]]] = [[]]
    row_width = 0
    for index, token in enumerate(upper):
        width = int(draw.textlength(token, font=font))
        extra = width if not rows[-1] else width + space
        if rows[-1] and row_width + extra > 900:
            rows.append([])
            row_width = 0
            extra = width
        rows[-1].append((index, token, width))
        row_width += extra
    y = int(HEIGHT * 0.68)
    for row in rows:
        width = sum(item[2] for item in row) + space * (len(row) - 1)
        x = (WIDTH - width) // 2
        for index, token, token_width in row:
            colour = GOLD if index == active else WHITE
            draw.text((x, y), token, font=font, fill=colour, stroke_width=5, stroke_fill=OUTLINE)
            x += token_width + space
        y += 110
    image.save(destination)


def _asset_paths(images_dir: Path, beats: list[dict[str, Any]]) -> list[Path]:
    manifest = images_dir / "visual_asset_provenance.json"
    if not manifest.exists():
        raise FileNotFoundError("visual_asset_provenance.json is required for visual review.")
    assets = json.loads(manifest.read_text(encoding="utf-8")).get("assets", [])
    by_beat = {int(asset["beat_number"]): Path(asset["local_path"]) for asset in assets}
    paths = [by_beat.get(beat["beat_number"]) for beat in beats]
    if any(path is None or not path.exists() for path in paths):
        raise ValueError("Every storyboard beat must have an existing provenance-recorded image.")
    return [path for path in paths if path is not None]


def render(storyboard_path: str | Path, audio_path: str | Path, timing_path: str | Path, images_dir: str | Path, output_path: str | Path) -> Path:
    storyboard = load_storyboard(storyboard_path)
    audio, timing_file, images, output = Path(audio_path), Path(timing_path), Path(images_dir), Path(output_path)
    timings = json.loads(timing_file.read_text(encoding="utf-8"))
    narrated_words, timed_words = words(storyboard["narration"]), timings.get("words", [])
    if len(narrated_words) != len(timed_words):
        raise ValueError(f"Caption timing mismatch: narration has {len(narrated_words)} words, TTS supplied {len(timed_words)}.")
    beats, assets = storyboard["visual_beats"], _asset_paths(images, storyboard["visual_beats"])
    duration = _audio_duration(audio)
    beat_times = []
    for beat in beats:
        start = 0.0 if beat["start_word"] == 1 else float(timed_words[beat["start_word"] - 1]["start"])
        end = duration if beat["end_word"] == len(timed_words) else float(timed_words[beat["end_word"] - 1]["end"])
        beat_times.append((start, max(end, start + 0.5)))
    transition = 0.32
    segment_durations = [end - start + (transition if index < len(beats) - 1 else 0.0) for index, (start, end) in enumerate(beat_times)]

    output.parent.mkdir(parents=True, exist_ok=True)
    caption_dir = output.parent / "caption_overlays"
    caption_dir.mkdir(parents=True, exist_ok=True)
    caption_events = _caption_groups(timings)
    caption_files: list[Path] = []
    for index, event in enumerate(caption_events):
        path = caption_dir / f"word_{index:03d}.png"
        _caption_png(event["tokens"], event["active"], path)
        caption_files.append(path)

    command = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]
    for image, segment_duration in zip(assets, segment_durations):
        command.extend(["-loop", "1", "-framerate", str(FPS), "-t", f"{segment_duration:.4f}", "-i", str(image)])
    for event, overlay in zip(caption_events, caption_files):
        command.extend(["-loop", "1", "-framerate", str(FPS), "-t", f"{event['end'] - event['start']:.4f}", "-i", str(overlay)])
    command.extend(["-i", str(audio)])

    filters: list[str] = []
    motion = {"push_in": "min(zoom+0.0008,1.10)", "pull_out": "max(zoom-0.0007,1.0)", "pan_left": "min(zoom+0.0005,1.06)", "pan_right": "min(zoom+0.0005,1.06)", "still": "1.02"}
    for index, (beat, segment_duration) in enumerate(zip(beats, segment_durations)):
        zoom = motion[beat["camera_motion"]]
        filters.append(f"[{index}:v]scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,crop={WIDTH}:{HEIGHT},zoompan=z='{zoom}':d=1:s={WIDTH}x{HEIGHT}:fps={FPS},trim=duration={segment_duration:.4f},setpts=PTS-STARTPTS[v{index}]")
    current, elapsed = "v0", segment_durations[0]
    for index in range(1, len(beats)):
        label = "vmain" if index == len(beats) - 1 else f"x{index}"
        offset = max(0.0, elapsed - transition)
        filters.append(f"[{current}][v{index}]xfade=transition=fade:duration={transition}:offset={offset:.4f}[{label}]")
        elapsed += segment_durations[index] - transition
        current = label
    if len(beats) == 1:
        current = "v0"
    for index, event in enumerate(caption_events):
        image_input = len(beats) + index
        label = "vcaptions" if index == len(caption_events) - 1 else f"cap{index}"
        filters.append(f"[{image_input}:v]setpts=PTS-STARTPTS+{event['start']:.4f}/TB[overlay{index}]")
        filters.append(f"[{current}][overlay{index}]overlay=0:0:eof_action=pass[{label}]")
        current = label
    audio_input = len(beats) + len(caption_events)
    # Xfade overlaps can shorten the visual stream by a few frames. Hold the
    # final image, then trim precisely to the measured narration duration.
    filters.append(f"[{current}]tpad=stop_mode=clone:stop_duration={duration:.4f},trim=duration={duration:.4f}[vout]")
    filters.append(f"[{audio_input}:a]aresample=44100,atrim=duration={duration:.4f}[aout]")
    command.extend(["-filter_complex", ";".join(filters), "-map", "[vout]", "-map", "[aout]", "-c:v", "libx264", "-crf", "19", "-preset", "medium", "-pix_fmt", "yuv420p", "-r", str(FPS), "-c:a", "aac", "-b:a", "160k", "-t", f"{duration:.4f}", "-movflags", "+faststart", str(output)])
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr[-4000:])
    (output.with_suffix(".caption_manifest.json")).write_text(json.dumps({"timing_source": str(timing_file), "events": caption_events, "audio_duration": duration}, indent=2), encoding="utf-8")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a Faith Nexus cinematic devotional image-film.")
    parser.add_argument("--storyboard", required=True)
    parser.add_argument("--audio", required=True)
    parser.add_argument("--timings", required=True)
    parser.add_argument("--images-dir", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    print(render(args.storyboard, args.audio, args.timings, args.images_dir, args.output))


if __name__ == "__main__":
    main()
