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


def _rgba(value: str | None, fallback: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    """Read an optional storyboard colour without making gold a global rule."""
    if not value:
        return fallback
    code = value.lstrip("#")
    if len(code) != 6:
        raise ValueError(f"Invalid caption colour: {value}")
    return tuple(int(code[index:index + 2], 16) for index in range(0, 6, 2)) + (255,)


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


def _caption_png(tokens: list[str], active: int, destination: Path, accent: tuple[int, int, int, int], caption: tuple[int, int, int, int]) -> None:
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
            colour = accent if index == active else caption
            draw.text((x, y), token, font=font, fill=colour, stroke_width=8, stroke_fill=OUTLINE)
            x += token_width + space
        y += 110
    image.save(destination)


def _wrapped_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, maximum_width: int) -> str:
    words_in_text, lines, line = text.split(), [], ""
    for word in words_in_text:
        candidate = f"{line} {word}".strip()
        if line and draw.textlength(candidate, font=font) > maximum_width:
            lines.append(line)
            line = word
        else:
            line = candidate
    if line:
        lines.append(line)
    return "\n".join(lines)


def _scripture_png(verse: dict[str, str], destination: Path, accent: tuple[int, int, int, int]) -> None:
    """A persistent, source-visible verse card inspired by Bible app clarity."""
    image = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    panel = (38, 48, WIDTH - 38, 286)
    draw.rounded_rectangle(panel, radius=28, fill=(7, 12, 24, 190), outline=(*accent[:3], 185), width=2)
    label_font, verse_font = _font(34), _font(35)
    label = verse["reference"].upper()
    draw.text((72, 76), label, font=label_font, fill=accent, stroke_width=1, stroke_fill=(0, 0, 0, 170))
    body = _wrapped_text(draw, verse["text"], verse_font, 900)
    draw.multiline_text((72, 126), body, font=verse_font, fill=WHITE, spacing=5, stroke_width=2, stroke_fill=(0, 0, 0, 165))
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


def render(storyboard_path: str | Path, audio_path: str | Path, timing_path: str | Path, images_dir: str | Path, output_path: str | Path, music_path: str | Path | None = None) -> Path:
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
    # Devotionals use editorial cuts by default: crossfading two unrelated
    # images causes an unwanted double exposure and weakens each beat.
    segment_durations = [end - start for start, end in beat_times]

    palette = storyboard.get("caption_style", {})
    accent = _rgba(palette.get("accent_hex"), GOLD)
    caption_colour = _rgba(palette.get("caption_hex"), WHITE)
    output.parent.mkdir(parents=True, exist_ok=True)
    caption_dir = output.parent / "caption_overlays"
    caption_dir.mkdir(parents=True, exist_ok=True)
    caption_events = _caption_groups(timings)
    caption_files: list[Path] = []
    for index, event in enumerate(caption_events):
        path = caption_dir / f"word_{index:03d}.png"
        _caption_png(event["tokens"], event["active"], path, accent, caption_colour)
        caption_files.append(path)
    scripture_overlay = caption_dir / "scripture.png"
    _scripture_png(storyboard["evidence"]["verse"], scripture_overlay, accent)

    command = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]
    for image, segment_duration in zip(assets, segment_durations):
        command.extend(["-loop", "1", "-framerate", str(FPS), "-t", f"{segment_duration:.4f}", "-i", str(image)])
    for event, overlay in zip(caption_events, caption_files):
        command.extend(["-loop", "1", "-framerate", str(FPS), "-t", f"{event['end'] - event['start']:.4f}", "-i", str(overlay)])
    command.extend(["-loop", "1", "-framerate", str(FPS), "-t", f"{duration:.4f}", "-i", str(scripture_overlay), "-i", str(audio)])
    if music_path:
        command.extend(["-i", str(music_path)])

    filters: list[str] = []
    motion = {"push_in": "min(zoom+0.0008,1.10)", "pull_out": "max(zoom-0.0007,1.0)", "pan_left": "min(zoom+0.0005,1.06)", "pan_right": "min(zoom+0.0005,1.06)", "still": "1.02"}
    for index, (beat, segment_duration) in enumerate(zip(beats, segment_durations)):
        zoom = motion[beat["camera_motion"]]
        filters.append(f"[{index}:v]scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,crop={WIDTH}:{HEIGHT},zoompan=z='{zoom}':d=1:s={WIDTH}x{HEIGHT}:fps={FPS},trim=duration={segment_duration:.4f},setpts=PTS-STARTPTS[v{index}]")
    if len(beats) == 1:
        current = "v0"
    else:
        filters.append("".join(f"[v{index}]" for index in range(len(beats))) + f"concat=n={len(beats)}:v=1:a=0[vmain]")
        current = "vmain"
    for index, event in enumerate(caption_events):
        image_input = len(beats) + index
        label = "vcaptions" if index == len(caption_events) - 1 else f"cap{index}"
        filters.append(f"[{image_input}:v]setpts=PTS-STARTPTS+{event['start']:.4f}/TB[overlay{index}]")
        filters.append(f"[{current}][overlay{index}]overlay=0:0:eof_action=pass[{label}]")
        current = label
    scripture_input = len(beats) + len(caption_events)
    filters.append(f"[{scripture_input}:v]setpts=PTS-STARTPTS[scripture]")
    filters.append(f"[{current}][scripture]overlay=0:0:eof_action=pass[vscripture]")
    current = "vscripture"
    audio_input = scripture_input + 1
    # Xfade overlaps can shorten the visual stream by a few frames. Hold the
    # final image, then trim precisely to the measured narration duration.
    filters.append(f"[{current}]tpad=stop_mode=clone:stop_duration={duration:.4f},trim=duration={duration:.4f}[vout]")
    if music_path:
        music_input = audio_input + 1
        fade_start = max(0.0, duration - 2.5)
        filters.append(f"[{audio_input}:a]aresample=44100,atrim=duration={duration:.4f}[voice]")
        filters.append(f"[{music_input}:a]aresample=44100,volume=0.12,atrim=duration={duration:.4f},afade=t=in:st=0:d=1.5,afade=t=out:st={fade_start:.4f}:d=2.5[music]")
        filters.append("[voice][music]amix=inputs=2:duration=first:dropout_transition=0[aout]")
    else:
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
    parser.add_argument("--music", help="Optional original/licensed background music, mixed gently below narration")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    print(render(args.storyboard, args.audio, args.timings, args.images_dir, args.output, args.music))


if __name__ == "__main__":
    main()
