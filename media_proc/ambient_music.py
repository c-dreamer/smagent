#!/usr/bin/env python3
"""Create a light original ambient bed without external music licensing risk."""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import wave
from pathlib import Path

SAMPLE_RATE = 44_100


def audio_duration(path: Path) -> float:
    result = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)], capture_output=True, text=True, check=True)
    return float(result.stdout.strip())


def generate(duration: float, output: str | Path) -> Path:
    """Warm D-major pad with sparse bell tones; entirely generated from math."""
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    frames = int(duration * SAMPLE_RATE)
    chords = ((146.83, 185.00, 220.00), (110.00, 146.83, 164.81), (130.81, 164.81, 196.00), (98.00, 123.47, 146.83))
    with wave.open(str(destination), "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        for frame in range(frames):
            time = frame / SAMPLE_RATE
            chord = chords[min(len(chords) - 1, int(time / max(duration / len(chords), 1)))]
            pad = sum(math.sin(2 * math.pi * frequency * time) + 0.25 * math.sin(2 * math.pi * frequency * 2 * time) for frequency in chord) / (len(chord) * 1.25)
            bell = 0.0
            beat = time % 4.0
            if beat < 1.1:
                bell = math.sin(2 * math.pi * chord[1] * 2 * time) * math.exp(-3.2 * beat) * 0.22
            envelope = min(1.0, time / 1.5, max(0.0, (duration - time) / 2.5))
            sample = max(-1.0, min(1.0, (pad * 0.20 + bell) * envelope))
            pcm = int(sample * 32767)
            wav.writeframesraw(pcm.to_bytes(2, "little", signed=True) * 2)
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate original light ambient music for a devotional.")
    parser.add_argument("--audio", required=True, help="Narration file used to match duration")
    parser.add_argument("--output", required=True)
    parser.add_argument("--provenance", help="JSON record; defaults beside output")
    args = parser.parse_args()
    destination = generate(audio_duration(Path(args.audio)), args.output)
    provenance = Path(args.provenance) if args.provenance else destination.with_suffix(".provenance.json")
    provenance.write_text(json.dumps({"provider": "smagent-original-synthesis", "licence": "Original generated waveform; no external samples or recording", "mood": "reflective warm ambient", "source_audio": args.audio}, indent=2), encoding="utf-8")
    print(destination)


if __name__ == "__main__":
    main()
