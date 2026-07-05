#!/usr/bin/env python3
"""
Thumbnail generator — creates channel-branded YouTube thumbnails using Pillow.

Extracts frames from video or uses existing images, overlays channel watermark,
text, and optional meme-style callouts. No API keys required.
"""

import argparse
import json
import os
import random
import subprocess
from pathlib import Path
from typing import Optional

try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def extract_frame(video_path: str, at_sec: float = 5.0, output_path: Optional[str] = None) -> Optional[str]:
    """Extract a single frame from a video file."""
    if output_path is None:
        output_path = f"/tmp/thumb_frame_{random.randint(1000,9999)}.jpg"
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-ss", str(at_sec),
        "-i", video_path,
        "-vframes", "1",
        "-q:v", "2",
        output_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0 and os.path.exists(output_path):
        return output_path
    return None


def create_channel_thumbnail(
    background_path: str,
    output_path: str,
    title_text: str,
    channel_name: str,
    width: int = 1280,
    height: int = 720,
    subtitle_text: Optional[str] = None,
    meme_style: bool = False,
) -> str:
    """
    Create a branded YouTube thumbnail.
    
    Args:
        background_path: Path to background image/video frame
        output_path: Where to save the thumbnail
        title_text: Main text (e.g. "GOAL OF THE SEASON")
        channel_name: Watermark text (e.g. "@Goal_HubPro")
        subtitle_text: Optional subtitle
        meme_style: If True, use bold meme-style text formatting
    """
    if not HAS_PIL:
        raise ImportError("Pillow required: pip install Pillow")
    
    img = Image.open(background_path).convert("RGB")
    img = img.resize((width, height), Image.LANCZOS)
    draw = ImageDraw.Draw(img)
    
    # Semi-transparent overlay at bottom
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rectangle([0, height-180, width, height], fill=(0, 0, 0, 160))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)
    
    # Title text
    font_size = 56 if not meme_style else 72
    try:
        font = ImageFont.truetype(FONT_BOLD, font_size)
    except:
        font = ImageFont.load_default()
    
    # Center title text
    bbox = draw.textbbox((0, 0), title_text, font=font)
    text_x = (width - (bbox[2] - bbox[0])) // 2
    text_y = height - 140
    
    if meme_style:
        # Red stroke outline (meme style)
        for dx, dy in [(-2,-2),(-2,2),(2,-2),(2,2)]:
            draw.text((text_x+dx, text_y+dy), title_text, font=font, fill="red")
    draw.text((text_x, text_y), title_text, font=font, fill="white")
    
    # Subtitle
    if subtitle_text:
        try:
            sub_font = ImageFont.truetype(FONT_REGULAR, 28)
        except:
            sub_font = ImageFont.load_default()
        bbox2 = draw.textbbox((0, 0), subtitle_text, font=sub_font)
        sub_x = (width - (bbox2[2] - bbox2[0])) // 2
        draw.text((sub_x, text_y - 40), subtitle_text, font=sub_font, fill="yellow")
    
    # Channel watermark
    try:
        wm_font = ImageFont.truetype(FONT_BOLD, 20)
    except:
        wm_font = ImageFont.load_default()
    draw.text((15, 15), channel_name, font=wm_font, fill="white")
    
    # Channel watermark bottom-right
    bbox3 = draw.textbbox((0, 0), channel_name, font=wm_font)
    draw.text((width - (bbox3[2] - bbox3[0]) - 15, height - 35), channel_name, font=wm_font, fill="white")
    
    img.save(output_path, "JPEG", quality=92)
    return output_path


def generate_from_video(
    video_path: str,
    output_path: str,
    title: str,
    channel: str,
    frame_time: float = 5.0,
    subtitle: Optional[str] = None,
    meme: bool = False,
) -> str:
    """Extract video frame and create thumbnail."""
    frame = extract_frame(video_path, at_sec=frame_time)
    if not frame:
        raise RuntimeError(f"Could not extract frame from {video_path}")
    
    channel_handles = {
        "soccer": "@Goal_HubPro",
        "christian": "@Faith_Nexus",
        "faithnexus": "@Faith_Nexus",
        "trading": "@TradingChannel",
    }
    handle = channel_handles.get(channel, channel)
    
    return create_channel_thumbnail(
        background_path=frame,
        output_path=output_path,
        title_text=title,
        channel_name=handle,
        subtitle_text=subtitle,
        meme_style=meme,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate YouTube thumbnail from video frame")
    parser.add_argument("--video", required=True, help="Source video path")
    parser.add_argument("--output", required=True, help="Output thumbnail JPG path")
    parser.add_argument("--title", required=True, help="Main title text")
    parser.add_argument("--channel", required=True, help="Channel key (soccer/christian/trading)")
    parser.add_argument("--subtitle", help="Optional subtitle text")
    parser.add_argument("--meme", action="store_true", help="Meme-style formatting")
    parser.add_argument("--frame-time", type=float, default=5.0, help="Frame extraction time (seconds)")
    args = parser.parse_args()
    
    result = generate_from_video(
        video_path=args.video,
        output_path=args.output,
        title=args.title,
        channel=args.channel,
        frame_time=args.frame_time,
        subtitle=args.subtitle,
        meme=args.meme,
    )
    print(f"Thumbnail saved: {result}")
