#!/usr/bin/env python3
"""Voiceover/TTS engine for social media agent.

Converts script text to speech audio using edge-tts.
"""

import argparse
import asyncio
import json
import os
import re
import sys
from typing import List

import edge_tts

_PARENT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PARENT not in sys.path:
    sys.path.insert(0, _PARENT)

from config import CHANNELS  # noqa: E402

# Keep experiments controlled: the same script, visuals, captions and music are
# rendered with one of these named variants. Never A/B test multiple changes at
# once, or view performance becomes uninterpretable.
FAITH_NEXUS_VOICE_VARIANTS = {
    "jenny_warm": ("en-US-JennyNeural", "-10%"),
    "aria_clear": ("en-US-AriaNeural", "-8%"),
    "guy_calm": ("en-US-GuyNeural", "-8%"),
    "andrew_steady": ("en-US-AndrewNeural", "-8%"),
}


def extract_text_from_script(script_path: str) -> str:
    """Load script JSON and extract voiceover_text from all scenes."""
    with open(script_path, 'r', encoding='utf-8') as f:
        script = json.load(f)
    
    scenes: List[dict] = script.get('scenes', [])
    if not scenes:
        raise ValueError('No scenes found in script')
    
    texts = []
    for scene in scenes:
        text = scene.get('voiceover_text', '').strip()
        if text:
            texts.append(text)
    
    if not texts:
        raise ValueError('No voiceover text found in any scene')
    
    # Join with a space to ensure separation between scenes
    return ' '.join(texts)


def get_voice_settings(channel: str) -> tuple[str, str]:
    """Return (voice, rate) for the given channel based on its tone."""
    channel_info = CHANNELS.get(channel)
    if not channel_info:
        raise ValueError(f'Unknown channel: {channel}')
    
    tone = channel_info.tone.lower() if channel_info.tone else ''
    
    if channel == 'soccer' or 'energetic' in tone:
        return 'en-US-ChristopherNeural', '+20%'
    elif channel == 'christian' or 'reverent' in tone:
        return 'en-US-JennyNeural', '-10%'
    elif channel == 'trading' or 'professional' in tone:
        return 'en-US-GuyNeural', '+0%'
    else:
        return 'en-US-GuyNeural', '+0%'


def resolve_voice_settings(channel: str, voice: str | None = None, rate: str | None = None) -> tuple[str, str]:
    """Resolve a named Faith Nexus test voice or an explicit Edge voice."""
    default_voice, default_rate = get_voice_settings(channel)
    if voice and voice in FAITH_NEXUS_VOICE_VARIANTS:
        default_voice, default_rate = FAITH_NEXUS_VOICE_VARIANTS[voice]
    elif voice:
        default_voice = voice
    return default_voice, rate or default_rate


async def generate_audio(text: str, voice: str, rate: str, output_path: str) -> list[dict]:
    """Generate audio and retain provider word boundaries for precise captions."""
    communicate = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
    boundaries: list[dict] = []
    with open(output_path, "wb") as audio:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                tokens = re.findall(r"[A-Za-z0-9]+(?:['’][A-Za-z0-9]+)?", chunk["text"])
                start = chunk["offset"] / 10_000_000
                duration = chunk["duration"] / 10_000_000
                for index, token in enumerate(tokens):
                    token_start = start + duration * index / len(tokens)
                    token_end = start + duration * (index + 1) / len(tokens)
                    boundaries.append({"text": token, "start": round(token_start, 4), "end": round(token_end, 4)})
    if not boundaries:
        raise RuntimeError("TTS returned no word boundaries; refusing to render unsynchronised captions.")
    return boundaries


def validate_audio_file(file_path: str) -> None:
    """Validate that the audio file exists and has duration > 0 using ffprobe."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f'Audio file not found: {file_path}')
    
    # Use ffprobe to get duration
    import subprocess
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
             '-of', 'default=noprint_wrappers=1:nokey=1', file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        duration = float(result.stdout.strip())
        if duration <= 0:
            raise ValueError(f'Audio file has zero or negative duration: {duration}')
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f'ffprobe failed: {e.stderr}') from e
    except ValueError as e:
        raise ValueError(f'Invalid duration output from ffprobe: {e}') from e


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Generate voiceover audio from script or text using edge-tts.'
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '--script',
        type=str,
        help='Path to script JSON file containing scenes with voiceover_text.'
    )
    group.add_argument(
        '--script-text',
        type=str,
        help='Raw text to convert to speech directly.'
    )
    parser.add_argument(
        '--channel',
        type=str,
        required=True,
        choices=['soccer', 'christian', 'trading'],
        help='Channel name to determine voice settings.'
    )
    parser.add_argument('--timings-output', help='JSON destination for exact TTS word boundaries.')
    parser.add_argument('--voice', help='Named Faith Nexus test variant or explicit Edge TTS voice.')
    parser.add_argument('--rate', help='Optional Edge TTS rate such as -8% or +0%.')
    parser.add_argument(
        '--output',
        type=str,
        required=True,
        help='Output audio file path (MP3).'
    )
    
    args = parser.parse_args()
    
    # Determine the text to convert
    if args.script_text is not None:
        text = args.script_text.strip()
        if not text:
            print('Error: --script-text cannot be empty.', file=sys.stderr)
            sys.exit(1)
    else:
        # args.script is provided
        try:
            text = extract_text_from_script(args.script)
        except Exception as e:
            print(f'Error loading script: {e}', file=sys.stderr)
            sys.exit(1)
    
    # Get voice settings for the channel
    try:
        voice, rate = resolve_voice_settings(args.channel, args.voice, args.rate)
    except ValueError as e:
        print(f'Error: {e}', file=sys.stderr)
        sys.exit(1)
    
    # Ensure output directory exists
    output_dir = os.path.dirname(args.output)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Generate audio
    try:
        boundaries = asyncio.run(generate_audio(text, voice, rate, args.output))
        timings_path = args.timings_output or os.path.splitext(args.output)[0] + '.words.json'
        with open(timings_path, 'w', encoding='utf-8') as timing_handle:
            json.dump({"provider": "edge-tts", "voice": voice, "rate": rate, "text": text, "words": boundaries}, timing_handle, indent=2)
    except Exception as e:
        print(f'Error generating audio: {e}', file=sys.stderr)
        sys.exit(1)
    
    # Validate the generated audio file
    try:
        validate_audio_file(args.output)
        print(f'Successfully generated audio: {args.output}')
    except Exception as e:
        print(f'Error validating audio file: {e}', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
