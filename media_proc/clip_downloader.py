#!/usr/bin/env python3
"""Download video clips from YouTube, TikTok, and other sources using yt-dlp."""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

_PARENT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PARENT not in sys.path:
    sys.path.insert(0, _PARENT)

from config import CHANNELS  # noqa: E402


# ── URL detection ──────────────────────────────────────────────────────────

TIKTOK_PATTERNS = [
    r"tiktok\.com/.*?video/\d+",
    r"vm\.tiktok\.com/\w+",
]

YOUTUBE_PATTERNS = [
    r"youtube\.com/watch\?v=",
    r"youtu\.be/",
    r"youtube\.com/shorts/",
    r"youtube\.com/clip/",
    r"m\.youtube\.com/",
]

INSTAGRAM_PATTERNS = [
    r"instagram\.com/reel/",
    r"instagram\.com/p/",
]


def detect_source(url: str) -> str:
    """Detect whether a URL is YouTube, TikTok, Instagram, or unknown."""
    for pat in TIKTOK_PATTERNS:
        if re.search(pat, url):
            return "tiktok"
    for pat in YOUTUBE_PATTERNS:
        if re.search(pat, url):
            return "youtube"
    for pat in INSTAGRAM_PATTERNS:
        if re.search(pat, url):
            return "instagram"
    return "unknown"


# ── yt-dlp helpers ─────────────────────────────────────────────────────────

def _ytdlp(args: list[str], description: str = "") -> subprocess.CompletedProcess:
    """Run yt-dlp with given args and return result."""
    cmd = ["yt-dlp", "--no-warnings"] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"yt-dlp failed{' (' + description + ')' if description else ''}:\n"
            f"{result.stderr.strip()}"
        )
    return result


def list_formats(url: str) -> list[dict]:
    """List available formats for a URL. Returns list of format dicts."""
    result = _ytdlp(["-J", url], "list formats")
    info = json.loads(result.stdout)
    return info.get("formats", [])


def get_video_info(url: str) -> dict:
    """Get video metadata without downloading."""
    result = _ytdlp(
        ["-J", "--no-download", url],
        "get video info",
    )
    return json.loads(result.stdout)


# ── Download functions ──────────────────────────────────────────────────────

def download_youtube(
    url: str,
    output_path: str,
    start_time: str | None = None,
    end_time: str | None = None,
    quality: str = "best",
) -> str:
    """
    Download a YouTube video (or clip) to the given path.

    Args:
        url: YouTube URL (video, shorts, or clip)
        output_path: Where to save the downloaded file
        start_time: Optional start timestamp (e.g. "0:15", "1:30")
        end_time: Optional end timestamp (e.g. "2:00")
        quality: "best" (default), "720p", "480p", or "audio_only"

    Returns:
        Path to the downloaded file
    """
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    args = [
        "-f", _format_selector(quality),
        "--merge-output-format", "mp4",
        "--remux-video", "mp4",
        "-o", output_path,
    ]

    if start_time or end_time:
        if start_time and end_time:
            section = f"*{start_time}-{end_time}"
        elif start_time:
            section = f"*{start_time}-"
        elif end_time:
            section = f"*-{end_time}"
        args.extend(["--download-sections", section])

    args.append(url)

    _ytdlp(args, f"download youtube {url}")
    return output_path


def download_tiktok(url: str, output_path: str) -> str:
    """
    Download a TikTok video/reel.

    Args:
        url: TikTok video URL
        output_path: Where to save

    Returns:
        Path to downloaded file
    """
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    args = [
        "-f", "bestvideo+bestaudio/best",
        "--merge-output-format", "mp4",
        "--remux-video", "mp4",
        "-o", output_path,
        "--no-playlist",
        url,
    ]
    _ytdlp(args, f"download tiktok {url}")
    return output_path


def download_instagram(url: str, output_path: str) -> str:
    """Download an Instagram Reel or post."""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    args = [
        "-f", "bestvideo+bestaudio/best",
        "--merge-output-format", "mp4",
        "--remux-video", "mp4",
        "-o", output_path,
        "--no-playlist",
        url,
    ]
    _ytdlp(args, f"download instagram {url}")
    return output_path


def download_audio(url: str, output_path: str) -> str:
    """
    Download audio-only from a video URL.

    Args:
        url: Video URL (YouTube, TikTok, etc.)
        output_path: Where to save the audio file (.mp3 or .m4a)

    Returns:
        Path to downloaded audio file
    """
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    # Determine output format from extension
    ext = os.path.splitext(output_path)[1].lower()
    audio_format = ext.lstrip(".") if ext else "mp3"

    args = [
        "-f", "bestaudio/best",
        "--extract-audio",
        "--audio-format", audio_format,
        "--audio-quality", "0",  # best quality
        "-o", output_path,
        url,
    ]
    _ytdlp(args, f"download audio {url}")
    return output_path


# ── Format selection helper ─────────────────────────────────────────────────

def _format_selector(quality: str) -> str:
    """Map quality string to yt-dlp format filter."""
    quality_map = {
        "best": "bv*+ba/b",
        "1080p": "bv*[height<=1080]+ba/b[height<=1080]",
        "720p": "bv*[height<=720]+ba/b[height<=720]",
        "480p": "bv*[height<=480]+ba/b[height<=480]",
        "audio_only": "bestaudio/best",
    }
    return quality_map.get(quality, quality_map["best"])


# ── Smart download (auto-detect source) ────────────────────────────────────

def smart_download(
    url: str,
    output_path: str,
    start_time: str | None = None,
    end_time: str | None = None,
    quality: str = "best",
) -> str:
    """
    Auto-detect the source platform and download accordingly.
    """
    source = detect_source(url)
    if source == "youtube":
        return download_youtube(url, output_path, start_time, end_time, quality)
    elif source == "tiktok":
        return download_tiktok(url, output_path)
    elif source == "instagram":
        return download_instagram(url, output_path)
    else:
        # Fallback: try yt-dlp generic extractor
        _ytdlp([
            "-f", _format_selector(quality),
            "--merge-output-format", "mp4",
            "-o", output_path,
            url,
        ], f"smart download {url}")
        return output_path


# ── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Download video/audio clips from YouTube, TikTok, Instagram"
    )
    parser.add_argument("url", help="Video URL to download")
    parser.add_argument("--output", "-o", required=True, help="Output file path")
    parser.add_argument("--start", help="Start timestamp (e.g. '0:15')")
    parser.add_argument("--end", help="End timestamp (e.g. '2:00')")
    parser.add_argument("--quality", default="best",
                        choices=["best", "1080p", "720p", "480p", "audio_only"],
                        help="Video quality")
    parser.add_argument("--audio-only", action="store_true",
                        help="Download audio only")
    parser.add_argument("--info", action="store_true",
                        help="Print video info and exit")
    parser.add_argument("--list-formats", action="store_true",
                        help="List available formats and exit")

    args = parser.parse_args()

    if args.info:
        info = get_video_info(args.url)
        print(json.dumps(info, indent=2, default=str))
        return

    if args.list_formats:
        formats = list_formats(args.url)
        for fmt in formats:
            print(f"{fmt.get('format_id', '?'):10s} "
                  f"{fmt.get('height', 'audio'):>5} "
                  f"{fmt.get('ext', '?'):5s} "
                  f"{fmt.get('tbr', 0):>6.0f}kbps "
                  f"{fmt.get('fps', ''):>4}")
        return

    if args.audio_only:
        result = download_audio(args.url, args.output)
    else:
        source = detect_source(args.url)
        if source == "youtube":
            result = download_youtube(
                args.url, args.output, args.start, args.end, args.quality
            )
        elif source == "tiktok":
            result = download_tiktok(args.url, args.output)
        elif source == "instagram":
            result = download_instagram(args.url, args.output)
        else:
            result = smart_download(args.url, args.output, args.start, args.end, args.quality)

    size = os.path.getsize(result)
    dur = _get_duration(result)
    print(f"Downloaded: {result}")
    print(f"Size: {size:,} bytes")
    if dur:
        print(f"Duration: {dur:.1f}s")


def _get_duration(filepath: str) -> float | None:
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", filepath],
            capture_output=True, text=True, check=True,
        )
        return float(result.stdout.strip())
    except Exception:
        return None


if __name__ == "__main__":
    main()
