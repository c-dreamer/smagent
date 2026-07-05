#!/usr/bin/env python3
"""
Meme/text overlay system for social media videos.

Generates meme-style text cards, reaction overlays, and callout graphics
using Pillow, then composites them onto video frames via ffmpeg overlay.

Key features:
- Meme text cards with red stroke outline (Impact-style)
- Reaction emoji overlays (🔥, 😱, 💀)
- Stat callouts ("GOAL!", "RECORD!", "UNBELIEVABLE")
- Channel watermark integration
- Copyright-breaking visual layers for soccer clips
"""

import json
import os
import random
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

MEME_TEMPLATES = {
    "goal": {"text": "GOAL!", "emoji": "⚽🔥", "style": "meme"},
    "technique": {"text": "INCREDIBLE TECHNIQUE", "emoji": "🎯", "style": "bold"},
    "unreal": {"text": "UNREAL!", "emoji": "😱🔥", "style": "meme"},
    "record": {"text": "NEW RECORD!", "emoji": "📊💀", "style": "meme"},
    "class": {"text": "PURE CLASS", "emoji": "👏✨", "style": "bold"},
    "crazy": {"text": "THIS IS CRAZY", "emoji": "🤯", "style": "meme"},
    "subscribe": {"text": "LIKE & SUBSCRIBE", "emoji": "🔔", "style": "cta"},
    # Christian channel
    "amen": {"text": "AMEN! 🙏", "emoji": "", "style": "gentle"},
    "godloves": {"text": "GOD LOVES YOU ❤️", "emoji": "", "style": "gentle"},
    "blessed": {"text": "STAY BLESSED 🙏", "emoji": "", "style": "gentle"},
}


def render_meme_card(
    text: str,
    output_path: str,
    width: int = 1920,
    height: int = 300,
    style: str = "meme",
    emoji: str = "",
    font_size: Optional[int] = None,
) -> str:
    """Render a meme-style text card as a transparent PNG for overlay."""
    if not HAS_PIL:
        raise ImportError("Pillow required: pip install Pillow")
    
    # Create transparent canvas
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    if style == "meme":
        # Full-width colored bar
        bar_height = height
        draw.rectangle([0, 0, width, bar_height], fill=(0, 0, 0, 180))
        
        # Large white text with red stroke
        fs = font_size or 80
        try:
            font = ImageFont.truetype(FONT_BOLD, fs)
        except:
            font = ImageFont.load_default()
        
        full_text = f"{emoji} {text}" if emoji else text
        bbox = draw.textbbox((0, 0), full_text, font=font)
        text_x = (width - (bbox[2] - bbox[0])) // 2
        text_y = (height - (bbox[3] - bbox[1])) // 2
        
        # Red stroke
        for dx, dy in [(-3,-3),(-3,3),(3,-3),(3,3)]:
            draw.text((text_x+dx, text_y+dy), full_text, font=font, fill=(255, 0, 0, 220))
        draw.text((text_x, text_y), full_text, font=font, fill=(255, 255, 255, 255))
        
    elif style == "bold":
        fs = font_size or 64
        try:
            font = ImageFont.truetype(FONT_BOLD, fs)
        except:
            font = ImageFont.load_default()
        
        full_text = f"{emoji} {text}" if emoji else text
        bbox = draw.textbbox((0, 0), full_text, font=font)
        text_x = (width - (bbox[2] - bbox[0])) // 2
        text_y = (height - (bbox[3] - bbox[1])) // 2
        
        # Yellow stroke
        for dx, dy in [(-2,-2),(-2,2),(2,-2),(2,2)]:
            draw.text((text_x+dx, text_y+dy), full_text, font=font, fill=(255, 200, 0, 220))
        draw.text((text_x, text_y), full_text, font=font, fill=(255, 255, 255, 255))
        
    elif style == "gentle":
        fs = font_size or 56
        try:
            font = ImageFont.truetype(FONT_BOLD, fs)
        except:
            font = ImageFont.load_default()
        
        bbox = draw.textbbox((0, 0), text, font=font)
        text_x = (width - (bbox[2] - bbox[0])) // 2
        text_y = (height - (bbox[3] - bbox[1])) // 2
        
        draw.text((text_x, text_y), text, font=font, fill=(255, 255, 255, 255))
    
    elif style == "cta":
        fs = font_size or 72
        try:
            font = ImageFont.truetype(FONT_BOLD, fs)
        except:
            font = ImageFont.load_default()
        
        draw.rectangle([0, 0, width, height], fill=(0, 0, 0, 200))
        full_text = text
        bbox = draw.textbbox((0, 0), full_text, font=font)
        text_x = (width - (bbox[2] - bbox[0])) // 2
        text_y = (height - (bbox[3] - bbox[1])) // 2
        
        for dx, dy in [(-3,-3),(-3,3),(3,-3),(3,3)]:
            draw.text((text_x+dx, text_y+dy), full_text, font=font, fill=(255, 0, 0, 220))
        draw.text((text_x, text_y), full_text, font=font, fill=(255, 255, 255, 255))
        
        # Bell emoji
        if emoji:
            try:
                emoji_font = ImageFont.truetype(FONT_REGULAR, 48)
            except:
                emoji_font = ImageFont.load_default()
            draw.text((text_x - 60, text_y - 60), emoji, font=emoji_font, fill=(255, 255, 255, 255))
    
    img.save(output_path, "PNG")
    return output_path


def generate_match_overlays(timestamp_pairs: list[tuple[float, str, str]]) -> list[str]:
    """Generate multiple meme cards timed to specific video timestamps.
    
    Args:
        timestamp_pairs: List of (timestamp_seconds, text_key, style) tuples
        
    Returns:
        List of overlay PNG paths
    """
    overlays = []
    for ts, key, style in timestamp_pairs:
        template = MEME_TEMPLATES.get(key, {"text": key, "emoji": "", "style": "meme"})
        out = f"/tmp/overlay_{int(ts)}_{random.randint(100,999)}.png"
        render_meme_card(
            text=template["text"],
            output_path=out,
            style=style or template["style"],
            emoji=template.get("emoji", ""),
        )
        overlays.append(out)
    return overlays


def build_overlay_filter_chain(
    overlay_paths: list[str],
    timestamps: list[float],
    durations: list[float],
    input_label: str = "vmain",
    output_label: str = "vover" 
) -> str:
    """Build an ffmpeg overlay filter chain for multiple timed overlays.
    
    Creates a filter_complex that overlays each PNG at the specified timestamp.
    """
    parts = []
    current = input_label
    for i, (ov_path, ts, dur) in enumerate(zip(overlay_paths, timestamps, durations)):
        label = f"o{i}" if i < len(overlay_paths) - 1 else output_label
        parts.append(
            f"[{current}][{i}:v]overlay=0:0:enable='between(t,{ts},{ts+dur})'[{label}]"
        )
        current = label
    return ";\n".join(parts)


if __name__ == "__main__":
    # Test: generate a meme card and print the overlay path
    out = render_meme_card("GOAL!", "/tmp/test_meme.png", style="meme", emoji="⚽🔥")
    print(f"Meme card: {out}")
    out2 = render_meme_card("GOD LOVES YOU ❤️", "/tmp/test_gentle.png", style="gentle")
    print(f"Gentle card: {out2}")
    out3 = render_meme_card("LIKE & SUBSCRIBE", "/tmp/test_cta.png", style="cta", emoji="🔔")
    print(f"CTA card: {out3}")
