#!/usr/bin/env python3
"""
Transition library — configurable scene transitions for all channels.

Uses ffmpeg xfade filter for smooth transitions between scenes.
Channels can customize: christian=gentle fade, soccer=dynamic wipe, trading=dissolve.
"""

import subprocess
from typing import Optional

TRANSITION_MAP = {
    "soccer": {
        "transition": "slideleft",
        "duration": 0.3,
    },
    "christian": {
        "transition": "fade",
        "duration": 0.6,
    },
    "trading": {
        "transition": "dissolve",
        "duration": 0.5,
    },
    "default": {
        "transition": "fade",
        "duration": 0.4,
    },
}


def get_transition(channel: str) -> tuple[str, float]:
    """Get (transition_type, duration) for a channel."""
    cfg = TRANSITION_MAP.get(channel, TRANSITION_MAP["default"])
    return cfg["transition"], cfg["duration"]


def build_xfade_chain(
    scene_count: int,
    scene_durations: list[float],
    channel: str = "default",
    start_label: str = "v0",
) -> str:
    """
    Build an ffmpeg xfade filter chain for concatenating scenes with transitions.
    
    Args:
        scene_count: Number of scenes
        scene_durations: List of scene durations in seconds
        channel: Channel key for transition style
        start_label: Label of the first scene stream
        
    Returns:
        (filter_string, last_label) — the filter graph fragment and output label
        
    Example usage in filter_complex:
        filter_str, out_label = build_xfade_chain(3, [10, 12, 10], "soccer")
        full_fc = f"[0:v]{scene0_filters}[v0];[1:v]{scene1_filters}[v1];...;{filter_str}"
    """
    if scene_count <= 1:
        return f"", start_label
    
    t_type, t_dur = get_transition(channel)
    parts = []
    current = start_label
    cursor = 0.0
    
    for i in range(scene_count - 1):
        next_in = f"v{i+1}"
        offset = cursor + scene_durations[i] - t_dur
        out_label = f"x{i}" if i < scene_count - 2 else "vfinal"
        
        parts.append(
            f"[{current}][{next_in}]xfade=transition={t_type}:duration={t_dur}:offset={offset}[{out_label}]"
        )
        current = out_label
        cursor = offset + t_dur
    
    return ";\n".join(parts), current


def apply_fade_in(clip_label: str, duration: float = 0.3) -> str:
    """Apply fade-in effect at the start of a clip."""
    return f"[{clip_label}]fade=t=in:d={duration}:alpha=1[ff{clip_label}]"


def apply_fade_out(clip_label: str, duration: float = 0.3) -> str:
    """Apply fade-out effect at the end of a clip."""
    return f"[{clip_label}]fade=t=out:d={duration}:alpha=1[ff{clip_label}]"


if __name__ == "__main__":
    # Test
    for ch in ["soccer", "christian", "trading"]:
        chain, last = build_xfade_chain(4, [10, 12, 10, 12], ch)
        print(f"\n{ch} ({TRANSITION_MAP[ch]['transition']}):")
        print(f"  Last label: {last}")
        for line in chain.split(";\n"):
            print(f"  {line}")
