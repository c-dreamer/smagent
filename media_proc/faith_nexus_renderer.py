#!/usr/bin/env python3
"""Portable Faith Nexus renderer using Pillow captions and standard FFmpeg filters.

Unlike the general assemblers this never needs MoviePy, libass, or FFmpeg's
optional drawtext filter. It is the default high-style renderer for Faith Nexus.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT, FPS = 1080, 1920, 24
GOLD, OUTLINE, WHITE = (246, 201, 69, 255), (0, 0, 0, 235), (255, 255, 255, 210)
FONT_CANDIDATES = (
    Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
)


def _font(size: int) -> ImageFont.FreeTypeFont:
    path = next((candidate for candidate in FONT_CANDIDATES if candidate.exists()), None)
    if path is None:
        raise FileNotFoundError("Arial Bold or DejaVu Sans Bold is required for Faith Nexus captions.")
    return ImageFont.truetype(path, size)


def _fit_caption(draw: ImageDraw.ImageDraw, text: str, maximum_width: int = 900) -> tuple[ImageFont.FreeTypeFont, tuple[int, int, int, int]]:
    for size in range(92, 40, -4):
        font = _font(size)
        bounds = draw.multiline_textbbox((0, 0), text, font=font, align="center", spacing=10, stroke_width=4)
        if bounds[2] - bounds[0] <= maximum_width:
            return font, bounds
    return _font(40), draw.multiline_textbbox((0, 0), text, font=_font(40), align="center", spacing=10, stroke_width=4)


def caption_overlay(text: str, destination: Path, handle: str = "@Faith_Nexus") -> None:
    image = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    font, bounds = _fit_caption(draw, text)
    caption_width, caption_height = bounds[2] - bounds[0], bounds[3] - bounds[1]
    x, y = (WIDTH - caption_width) / 2, HEIGHT * 0.61
    draw.multiline_text((x, y), text, font=font, fill=GOLD, align="center", spacing=10,
                        stroke_width=4, stroke_fill=OUTLINE)
    small = _font(27)
    draw.text((48, 52), handle, font=small, fill=WHITE, stroke_width=2, stroke_fill=OUTLINE)
    image.save(destination)


def cta_overlay(destination: Path, text: str = "Save this for tomorrow") -> None:
    image = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    font, bounds = _fit_caption(draw, text)
    x = (WIDTH - (bounds[2] - bounds[0])) / 2
    y = (HEIGHT - (bounds[3] - bounds[1])) / 2
    draw.multiline_text((x, y), text, font=font, fill=GOLD, align="center", spacing=10,
                        stroke_width=4, stroke_fill=OUTLINE)
    image.save(destination)


def render(script_path: str | Path, audio_path: str | Path, clips_dir: str | Path, output_path: str | Path) -> Path:
    script = json.loads(Path(script_path).read_text(encoding="utf-8"))
    scenes = script.get("scenes", [])
    if not scenes:
        raise ValueError("No scenes in script")
    clips = sorted(Path(clips_dir).glob("*.mp4"))
    if len(clips) < len(scenes):
        raise ValueError(f"Need {len(scenes)} visual clips, found {len(clips)}")

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    overlay_dir = output.parent / "caption_overlays"
    overlay_dir.mkdir(parents=True, exist_ok=True)
    overlays: list[Path] = []
    for index, scene in enumerate(scenes, start=1):
        overlay = overlay_dir / f"scene_{index:02d}.png"
        caption_overlay(scene.get("on_screen_text") or scene.get("voiceover_text", ""), overlay)
        overlays.append(overlay)
    cta = overlay_dir / "cta.png"
    cta_overlay(cta)

    command = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]
    for clip in clips[:len(scenes)]:
        command.extend(["-i", str(clip)])
    for scene, overlay in zip(scenes, overlays):
        command.extend(["-loop", "1", "-t", str(scene["duration_seconds"]), "-i", str(overlay)])
    command.extend(["-f", "lavfi", "-t", "2.5", "-i", f"color=c=0x0a0a0a:s={WIDTH}x{HEIGHT}:r={FPS}"])
    command.extend(["-loop", "1", "-t", "2.5", "-i", str(cta), "-i", str(audio_path)])

    parts: list[str] = []
    scene_count = len(scenes)
    for index, scene in enumerate(scenes):
        duration = float(scene["duration_seconds"])
        parts.append(
            f"[{index}:v]trim=duration={duration},setpts=PTS-STARTPTS,"
            f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,crop={WIDTH}:{HEIGHT},fps={FPS}[base{index}]"
        )
        parts.append(f"[{scene_count + index}:v]setpts=PTS-STARTPTS[caption{index}]")
        parts.append(f"[base{index}][caption{index}]overlay=0:0:shortest=1,format=yuv420p[v{index}]")

    transition, cursor = 0.55, 0.0
    current = "v0"
    for index in range(scene_count - 1):
        offset = cursor + float(scenes[index]["duration_seconds"]) - transition
        label = f"xf{index}" if index < scene_count - 2 else "vmain"
        parts.append(f"[{current}][v{index + 1}]xfade=transition=fade:duration={transition}:offset={offset}[{label}]")
        current, cursor = label, offset + transition
    if scene_count == 1:
        current = "v0"

    cta_base_index, cta_overlay_index = scene_count * 2, scene_count * 2 + 1
    parts.append(f"[{cta_base_index}:v][{cta_overlay_index}:v]overlay=0:0:shortest=1,format=yuv420p[vcta]")
    parts.append(f"[{current}][vcta]concat=n=2:v=1:a=0[vout]")
    total_duration = sum(float(scene["duration_seconds"]) for scene in scenes) - transition * (scene_count - 1) + 2.5
    audio_index = scene_count * 2 + 2
    parts.append(f"[{audio_index}:a]aresample=44100,apad=pad_dur={total_duration},atrim=duration={total_duration}[aout]")

    command.extend([
        "-filter_complex", ";".join(parts), "-map", "[vout]", "-map", "[aout]",
        "-c:v", "libx264", "-crf", "20", "-preset", "medium", "-pix_fmt", "yuv420p",
        "-r", str(FPS), "-c:a", "aac", "-b:a", "160k", "-t", str(total_duration), "-movflags", "+faststart", str(output),
    ])
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr[-3000:])
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a Faith Nexus Short without MoviePy or drawtext.")
    parser.add_argument("--script", required=True)
    parser.add_argument("--audio", required=True)
    parser.add_argument("--clips-dir", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    print(render(args.script, args.audio, args.clips_dir, args.output))


if __name__ == "__main__":
    main()
