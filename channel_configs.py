"""
Per-channel video generation configuration.

Each channel has its own orientation, style, default clip sources,
and compositing preferences. These configs drive the clip_assembler.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ChannelVideoConfig:
    """Configuration for a channel's video generation pipeline."""

    # ── Identity ───────────────────────────────────────────────────────────
    channel_key: str          # e.g. "soccer", "christian"
    display_name: str         # Friendly name

    # ── Output format ──────────────────────────────────────────────────────
    orientation: str          # "landscape" (16:9) or "portrait" (9:16)
    width: int
    height: int
    fps: int = 24

    # ── Default clip sources (URLs or local paths) ─────────────────────────
    default_sources: list[str] = field(default_factory=list)

    # ── Scene styling ──────────────────────────────────────────────────────
    title_fontsize: int = 48
    subtitle_fontsize: int = 32
    caption_fontsize: int = 28
    font_color: str = "white"
    font_bg_color: str = "black@0.5"
    font_name: str = "DejaVuSans-Bold"

    # ── Transition ─────────────────────────────────────────────────────────
    transition_duration: float = 0.5     # seconds for crossfade

    # ── Audio ──────────────────────────────────────────────────────────────
    tts_volume: float = 1.0              # TTS voiceover volume (0-1)
    background_music_volume: float = 0.0  # Background music volume (0-1)
    extract_audio_from_clips: bool = False  # Use clip audio instead of TTS

    # ── Clip sourcing strategy ─────────────────────────────────────────────
    prefer_yt_download: bool = True       # Download from YouTube?
    use_stock_clips: bool = False          # Use local stock footage?
    stock_dir: Optional[str] = None       # Path to stock footage directory

    # ── Logo / watermark ───────────────────────────────────────────────────
    logo_path: Optional[str] = None
    logo_position: str = "top-right"      # top-left, top-right, bottom-left, bottom-right


# ── Per-channel configs ─────────────────────────────────────────────────────

CHANNEL_VIDEO_CONFIGS: dict[str, ChannelVideoConfig] = {
    "soccer": ChannelVideoConfig(
        channel_key="soccer",
        display_name="Soccer Analysis",
        orientation="landscape",
        width=1920,
        height=1080,
        fps=24,
        title_fontsize=52,
        subtitle_fontsize=36,
        caption_fontsize=30,
        transition_duration=0.5,
        tts_volume=1.0,
        extract_audio_from_clips=False,
        prefer_yt_download=True,
        stock_dir=None,
    ),
    "christian": ChannelVideoConfig(
        channel_key="christian",
        display_name="Christian Devotional",
        orientation="portrait",
        width=1080,
        height=1920,
        fps=24,
        title_fontsize=56,
        subtitle_fontsize=38,
        caption_fontsize=32,
        font_color="white",
        font_bg_color="black@0.4",
        transition_duration=0.8,
        tts_volume=1.0,
        extract_audio_from_clips=False,
        prefer_yt_download=False,
        use_stock_clips=True,
        stock_dir="/home/yahweh1_2025/videos/source",
    ),
    "trading": ChannelVideoConfig(
        channel_key="trading",
        display_name="Trading Education",
        orientation="landscape",
        width=1920,
        height=1080,
        fps=24,
        title_fontsize=48,
        subtitle_fontsize=32,
        caption_fontsize=28,
        font_name="DejaVuSans-Bold",
        font_color="white",
        transition_duration=0.5,
        tts_volume=1.0,
        extract_audio_from_clips=False,
        prefer_yt_download=True,
        stock_dir=None,
    ),
}


def get_channel_config(channel_key: str) -> ChannelVideoConfig:
    """Get video config for a channel, falling back to soccer defaults."""
    return CHANNEL_VIDEO_CONFIGS.get(
        channel_key,
        CHANNEL_VIDEO_CONFIGS["soccer"],
    )
