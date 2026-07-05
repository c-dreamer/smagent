#!/usr/bin/env python3
"""
Clip assembler — composes videos from real video clips using moviepy.

Features:
  - Multi-clip support: different clips per scene, auto-segmentation of single clip
  - Channel watermark/logo overlay (text-based watermarks)
  - Copyright-safe transforms: mirror flip, slight speed change, color tweak
  - Scene text overlays per scene
  - Voiceover TTS audio overlay
  - Scale/fit to channel orientation (landscape 16:9 or portrait 9:16)
"""

import argparse
import json
import os
import random
import subprocess
import sys
import hashlib
from pathlib import Path
from typing import Optional

_PARENT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PARENT not in sys.path:
    sys.path.insert(0, _PARENT)

from channel_configs import get_channel_config, ChannelVideoConfig  # noqa: E402

try:
    from moviepy import (
        VideoFileClip, AudioFileClip, TextClip, ColorClip,
        CompositeVideoClip, concatenate_videoclips,
    )
    from moviepy import concatenate_audioclips
    from moviepy.video.fx import MultiplySpeed, MirrorX, MultiplyColor
    HAS_MOVIEPY = True
except ImportError:
    HAS_MOVIEPY = False

# ── Copyright-safe transforms ───────────────────────────────────────────────
# These subtle transforms help avoid YouTube Content ID automatic flagging.
# They're applied deterministically based on the video hash so the same clip
# always gets the same transform.

COPYRIGHT_TRANSFORMS = {
    0: "speed_up_5pct",
    1: "mirror_flip",
    2: "saturate_10pct",
    3: "speed_down_3pct",
    4: "mirror_flip_speed_up",
    5: "no_transform",  # 1 in 6 chance of no transform
}

def _get_clip_hash_int(path: str) -> int:
    """Get a deterministic int from the clip path for consistent transforms."""
    h = hashlib.md5(path.encode()).hexdigest()
    return int(h[:8], 16) % len(COPYRIGHT_TRANSFORMS)

def apply_copyright_safe(clip: "VideoFileClip", clip_path: str) -> "VideoFileClip":
    """
    Apply a subtle copyright-safe transform to a clip.
    These transforms are designed to avoid YouTube Content ID while
    being barely perceptible to humans.
    """
    transform_idx = _get_clip_hash_int(clip_path)
    transform_name = COPYRIGHT_TRANSFORMS[transform_idx]
    
    if transform_name == "mirror_flip":
        clip = clip.with_effects([MirrorX()])
    elif transform_name == "mirror_flip_speed_up":
        clip = clip.with_effects([MirrorX(), MultiplySpeed(1.05)])
    elif transform_name == "speed_up_5pct":
        clip = clip.with_effects([MultiplySpeed(1.05)])
    elif transform_name == "speed_down_3pct":
        clip = clip.with_effects([MultiplySpeed(0.97)])
    elif transform_name == "saturate_10pct":
        clip = clip.with_effects([MultiplyColor(1.12)])
    # "no_transform" — no change
    
    return clip


# ── Helpers ─────────────────────────────────────────────────────────────────

def get_media_duration(filepath: str) -> float:
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", filepath],
            capture_output=True, text=True, check=True,
        )
        return float(result.stdout.strip())
    except Exception:
        return 0.0

def resolve_clip_path(clip_ref: str, channel_config: ChannelVideoConfig) -> Optional[str]:
    if os.path.isfile(clip_ref):
        return clip_ref
    if channel_config.stock_dir:
        candidate = os.path.join(channel_config.stock_dir, clip_ref)
        if os.path.isfile(candidate):
            return candidate
    source_dir = "/home/yahweh1_2025/videos/source"
    if os.path.isdir(source_dir):
        candidate = os.path.join(source_dir, clip_ref)
        if os.path.isfile(candidate):
            return candidate
    channel_video_dir = f"/home/yahweh1_2025/videos/{channel_config.channel_key}"
    if os.path.isdir(channel_video_dir):
        for root, _dirs, files in os.walk(channel_video_dir):
            if clip_ref in files:
                return os.path.join(root, clip_ref)
    return None

def load_clip(path: str, trim_start: float = 0, trim_end: Optional[float] = None,
              target_resolution: Optional[tuple[int, int]] = None) -> "VideoFileClip":
    # target_resolution in the constructor is much faster than .resized() in
    # moviepy 2.x — it avoids Pillow resample on every frame (issue #2395)
    if target_resolution is not None:
        clip = VideoFileClip(path, target_resolution=target_resolution)
    else:
        clip = VideoFileClip(path)
    if trim_start > 0 or trim_end is not None:
        end = trim_end if trim_end is not None else clip.duration
        # Guard against subclip end == clip duration (moviepy 2.x requires <)
        if end >= clip.duration:
            end = clip.duration - 0.01
        if trim_start >= end:
            trim_start = max(0, end - 0.5)
        clip = clip.subclipped(trim_start, end)
    return clip

def fit_clip_to_frame(clip: "VideoFileClip", target_w: int, target_h: int) -> "VideoFileClip":
    clip_w, clip_h = clip.size
    if clip_w == 0 or clip_h == 0:
        return clip
    # If clip is already at target size (from target_resolution), just position it
    if clip_w == target_w and clip_h == target_h:
        return clip.with_position(("center", "center"))
    scale = min(target_w / clip_w, target_h / clip_h)
    new_w = int(clip_w * scale)
    new_h = int(clip_h * scale)
    if scale != 1.0:
        clip = clip.resized(new_size=(new_w, new_h))
    return clip.with_position(("center", "center"))


# ── Watermark ───────────────────────────────────────────────────────────────

def make_watermark_clip(channel_handle: str, config: ChannelVideoConfig, video_duration: float) -> "CompositeVideoClip":
    """
    Create a subtle semi-transparent watermark for the channel.
    Uses the channel handle as text, positioned in bottom-right corner.
    """
    label = channel_handle or f"@{config.channel_key}"
    
    txt = TextClip(
        text=label,
        font_size=28,
        color="white",
        font=config.font_name,
        stroke_color="black",
        stroke_width=2,
    )
    txt = txt.with_opacity(0.5).with_position(
        ("right", "bottom")
    ).with_duration(video_duration)
    
    return txt


# ── Multi-clip segment manager ──────────────────────────────────────────────

class ClipSegmentManager:
    """
    Manages clip-to-scene assignment with smart segmentation.
    
    If clips_dir has N clips and M scenes:
      - N >= M: each scene gets a different clip
      - N < M and N > 0: clips are auto-segmented — each clip sliced into 
        (M/N) segments, each segment goes to a different scene
      - N == 0: fall back to text cards
    """
    
    def __init__(self, clips_dir: str):
        self.clips = sorted([
            os.path.join(clips_dir, f)
            for f in os.listdir(clips_dir)
            if f.lower().endswith((".mp4", ".mov", ".avi", ".mkv", ".webm"))
        ]) if clips_dir and os.path.isdir(clips_dir) else []
    
    def get_clip_for_scene(self, scene_num: int, scene_duration: float) -> Optional[dict]:
        """
        Return clip info for a scene: {path, start, end} or None.
        
        Strategy:
        - If enough clips, assign clip scene_num % len(clips)
        - If only 1 clip, auto-segment: split into equal chunks across all scenes
        """
        if not self.clips:
            return None
        
        if len(self.clips) == 1:
            # Single clip — auto-segment it
            return self._segment_single_clip(scene_num, scene_duration)
        else:
            # Multiple clips — assign different clips
            idx = (scene_num - 1) % len(self.clips)
            clip_path = self.clips[idx]
            clip_dur = get_media_duration(clip_path)
            return {
                "path": clip_path,
                "start": 0,
                "end": min(clip_dur, scene_duration),
            }
    
    def _segment_single_clip(self, scene_num: int, scene_duration: float) -> Optional[dict]:
        """Auto-segment a single clip into equal parts across all scenes.
        
        The total number of scenes is estimated at 4 by default (can be overridden).
        For scene N: uses segment from (N-1)*chunk to N*chunk of the clip.
        """
        clip_path = self.clips[0]
        total_dur = get_media_duration(clip_path)
        if total_dur <= 0:
            return None
        
        # We need to know the total scenes to segment properly.
        # Use a heuristic: typical script has 4 scenes, chunk_size ≈ total_dur/4
        # But we don't know total scenes here — so use scene_duration as chunk.
        # Each scene gets a unique segment. Scene 1 gets 0..scene_duration,
        # scene 2 gets scene_duration..2*scene_duration, etc.
        start = (scene_num - 1) * scene_duration
        end = min(scene_num * scene_duration, total_dur)
        
        if start >= total_dur:
            # Wraparound: start from beginning again
            wrap_start = start % total_dur
            end = min(wrap_start + scene_duration, total_dur)
            start = wrap_start
        
        if start >= end:
            return None
        
        return {"path": clip_path, "start": start, "end": end}
    
    def clip_count(self) -> int:
        return len(self.clips)


# ── Scene assembly ──────────────────────────────────────────────────────────

def make_text_overlay(scene: dict, config: ChannelVideoConfig, clip_dur: float) -> "TextClip":
    """Create a scene title text overlay."""
    voiceover = scene.get("voiceover_text", "")
    description = scene.get("description", "")
    
    # Use first sentence of voiceover or description as the overlay
    text = voiceover.split(".")[0].strip() if voiceover else description
    if not text:
        text = f"Scene {scene.get('scene_number', '?')}"
    
    # Shorten long text for overlay
    if len(text) > 80:
        text = text[:77] + "..."
    
    txt = TextClip(
        text=text,
        font_size=config.subtitle_fontsize,
        color=config.font_color,
        font=config.font_name,
        stroke_color="black",
        stroke_width=3,
        size=(config.width - 160, None),
        method="caption",
        text_align="center",
    )
    txt = txt.with_position(("center", config.height - txt.h - 80))
    txt = txt.with_duration(min(clip_dur, 8.0))  # Show for 8s max
    # Fade in/out
    txt = txt.with_start(0.3)
    
    return txt


def make_scene_clip(
    scene: dict,
    config: ChannelVideoConfig,
    segment_manager: "ClipSegmentManager",
    apply_copyright: bool = True,
) -> "VideoFileClip":
    """
    Build a scene clip with real video footage, text overlay, and transforms.
    
    Returns a single VideoFileClip for this scene.
    """
    scene_num = scene.get("scene_number", 1)
    duration = scene.get("duration_seconds", 30)
    description = scene.get("description", "Scene")
    clip_file = scene.get("clip_file")
    clip_start = scene.get("clip_start", 0)
    clip_end = scene.get("clip_end")
    
    clip_path = None
    start_time = 0.0
    end_time = duration
    
    # ── Resolve clip ──────────────────────────────────────────────────────
    if clip_file:
        clip_path = resolve_clip_path(clip_file, config)
    
    if not clip_path:
        seg = segment_manager.get_clip_for_scene(scene_num, duration)
        if seg:
            clip_path = seg["path"]
            start_time = seg.get("start", 0)
            end_time = seg.get("end", duration)
    
    # ── Build clip ────────────────────────────────────────────────────────
    if clip_path and os.path.isfile(clip_path):
        try:
            # Use target_resolution for fast native decode (avoids Pillow resample per-frame)
            target_res = (config.width, config.height)
            clip = load_clip(clip_path, start_time, end_time, target_resolution=target_res)

            # Copyright-safe transform
            if apply_copyright:
                clip = apply_copyright_safe(clip, clip_path)

            # Set exact duration
            clip = clip.with_duration(duration)
            
            # Add scene text overlay
            txt = make_text_overlay(scene, config, duration)
            clip = CompositeVideoClip([clip, txt])
            
            return clip
        except Exception as e:
            print(f"  Warning: Failed to load clip '{clip_path}': {e}")
    
    # ── Fallback: text card ──────────────────────────────────────────────
    print(f"  Scene {scene_num}: No clip — creating text card")
    bg = ColorClip(size=(config.width, config.height), color=(25, 30, 40))
    bg = bg.with_duration(duration)
    
    txt = TextClip(
        text=description or f"Scene {scene_num}",
        font_size=config.title_fontsize,
        color=config.font_color,
        font=config.font_name,
        size=(config.width - 120, None),
        method="caption",
        text_align="center",
    )
    txt = txt.with_position("center").with_duration(duration)
    
    return CompositeVideoClip([bg, txt])


# ── Main assembly ───────────────────────────────────────────────────────────

def _generate_cta_tts_sync(output_path: str) -> None:
    python_code = f"""
import asyncio, edge_tts
async def _main():
    communicate = edge_tts.Communicate(
        "Please like and subscribe!",
        "en-US-ChristopherNeural",
        rate="+10%"
    )
    await communicate.save("{output_path}")
asyncio.run(_main())
"""
    result = subprocess.run(
        ["python3", "-c", python_code],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"CTA TTS failed: {result.stderr}")


def assemble_video(
    script_path: str,
    audio_path: Optional[str],
    channel: str,
    output_path: str,
    clips_dir: Optional[str] = None,
    apply_copyright_safe: bool = True,
    channel_handle: Optional[str] = None,
) -> str:
    """
    Assemble a video from script JSON with real clips, watermark, and transforms.
    
    Args:
        script_path: Path to script JSON with scenes
        audio_path: Path to TTS voiceover audio
        channel: Channel key
        output_path: Output video path
        clips_dir: Directory with video clips
        apply_copyright_safe: Apply subtle transforms to avoid Content ID
        channel_handle: Watermark text (e.g. @Goal_HubPro)
    """
    if not HAS_MOVIEPY:
        raise ImportError("moviepy is required: pip install moviepy")
    
    with open(script_path, "r") as f:
        script = json.load(f)
    scenes = script.get("scenes", [])
    if not scenes:
        raise ValueError("No scenes in script")
    
    config = get_channel_config(channel)
    print(f"Assembling {channel} video: {config.width}x{config.height} "
          f"({config.orientation}), {len(scenes)} scenes")
    
    # ── Multi-clip segment manager ──────────────────────────────────────
    segment_mgr = ClipSegmentManager(clips_dir or "")
    print(f"  Clips available: {segment_mgr.clip_count()}")
    if segment_mgr.clip_count() == 1:
        print(f"  Single clip mode — auto-segmenting across {len(scenes)} scenes")
    
    # ── Build scene clips ───────────────────────────────────────────────
    print("Building scene clips...")
    scene_clips = []
    for i, scene in enumerate(scenes):
        clip = make_scene_clip(scene, config, segment_mgr, apply_copyright_safe)
        scene_clips.append(clip)
        print(f"  Scene {i + 1}: {clip.duration:.1f}s — {'clip' if clip_path_used(scene, segment_mgr) else 'text card'}")
    
    # ── Concatenate with crossfade ──────────────────────────────────────
    print("Concatenating with crossfade transitions...")
    if len(scene_clips) > 1:
        video = concatenate_videoclips(
            scene_clips,
            method="compose",
            padding=-config.transition_duration,
        )
    else:
        video = scene_clips[0]
    
    # ── Add watermark ───────────────────────────────────────────────────
    actual_handle = channel_handle or config.display_name
    watermark = make_watermark_clip(actual_handle, config, video.duration)
    video = CompositeVideoClip([video, watermark])
    print(f"  Watermark: {actual_handle}")
    
    # ── Add voiceover audio ─────────────────────────────────────────────
    if audio_path and os.path.isfile(audio_path):
        print(f"Adding voiceover: {audio_path}")
        audio_clip = AudioFileClip(audio_path)
        video_dur = video.duration
        audio_dur = audio_clip.duration
        
        if audio_dur < video_dur:
            from moviepy import AudioClip as _AudioClip
            silence = _AudioClip(lambda t: [0, 0], duration=video_dur - audio_dur, fps=44100)
            final_audio = audio_clip.with_duration(audio_dur)
            final_audio = concatenate_audioclips([final_audio, silence])
        else:
            final_audio = audio_clip.with_duration(video_dur)
        
        video = video.with_audio(final_audio)
    else:
        print("No voiceover — using clip audio")
    
    # ── Add "LIKE AND SUBSCRIBE" CTA at end ───────────────────────────────
    cta_duration = 5.0
    cta_start = video.duration
    cta_text = TextClip(
        text="LIKE AND SUBSCRIBE",
        font_size=config.title_fontsize + 10,
        color="white",
        font=config.font_name,
        stroke_color="red",
        stroke_width=4,
        size=(config.width - 100, None),
        method="caption",
        text_align="center",
    )
    cta_text = cta_text.with_position("center").with_duration(cta_duration)
    cta_clip = CompositeVideoClip([cta_text]).with_start(cta_start)
    video = CompositeVideoClip([video, cta_clip])
    print(f"  CTA: 'LIKE AND SUBSCRIBE' text overlay at end ({cta_duration}s)")
    
    try:
        cta_tts_path = output_path.replace(".mp4", "_cta.mp3")
        _generate_cta_tts_sync(cta_tts_path)
        if os.path.exists(cta_tts_path):
            from moviepy import AudioClip as _AudioClip
            cta_audio = AudioFileClip(cta_tts_path)
            cta_audio_dur = cta_audio.duration
            silence_needed = cta_duration - cta_audio_dur
            if silence_needed > 0:
                silence = _AudioClip(lambda t: [0, 0], duration=silence_needed, fps=44100)
                cta_audio = concatenate_audioclips([cta_audio, silence])
            cta_audio = cta_audio.with_start(cta_start)
            current_audio = video.audio if video.audio else None
            if current_audio:
                final_audio = concatenate_audioclips([current_audio, cta_audio])
            else:
                final_audio = cta_audio
            video = video.with_audio(final_audio)
            print(f"  CTA: TTS 'please like and subscribe' added at {cta_start:.1f}s")
    except Exception as e:
        print(f"  CTA TTS skipped: {e}")
    
    # ── Write output ────────────────────────────────────────────────────
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    print(f"Rendering video to: {output_path}")
    print(f"  Source duration: {video.duration:.1f}s @ {config.width}x{config.height} {config.fps}fps")
    print(f"  This will take ~{int(video.duration * 0.4)}-{int(video.duration * 0.8)}s on 4-core CPU")

    video.write_videofile(
        output_path,
        codec="libx264",
        audio_codec="aac",
        fps=config.fps,
        preset="ultrafast",
        bitrate="2000k" if config.width >= 1920 else "1000k",
        threads=4,
        temp_audiofile_path="/tmp/moviepy_audio.m4a",
        logger="bar",
    )
    
    final_dur = get_media_duration(output_path)
    if final_dur <= 0:
        raise ValueError("Output video has zero duration")
    
    print(f"Video assembled: {output_path}")
    print(f"Duration: {final_dur:.1f}s")
    print(f"Size: {os.path.getsize(output_path):,} bytes")
    
    return output_path


def clip_path_used(scene: dict, segment_mgr: "ClipSegmentManager") -> bool:
    """Check if a scene actually used a real clip."""
    clip_file = scene.get("clip_file")
    if clip_file:
        return True
    return segment_mgr.clip_count() > 0


# ── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Assemble video from script + clips using moviepy")
    parser.add_argument("--script", required=True, help="Path to script JSON")
    parser.add_argument("--audio", help="Path to TTS voiceover audio")
    parser.add_argument("--channel", required=True, help="Channel key")
    parser.add_argument("--output", required=True, help="Output video path")
    parser.add_argument("--clips-dir", help="Directory with source video clips")
    parser.add_argument("--no-copyright-safe", action="store_true",
                        help="Disable copyright-safe transforms")
    parser.add_argument("--watermark", help="Watermark text (default: channel handle)")
    args = parser.parse_args()
    
    try:
        assemble_video(
            script_path=args.script,
            audio_path=args.audio,
            channel=args.channel,
            output_path=args.output,
            clips_dir=args.clips_dir,
            apply_copyright_safe=not args.no_copyright_safe,
            channel_handle=args.watermark,
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()