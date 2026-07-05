#!/usr/bin/env python3
"""
Analytics collector — fetches YouTube channel and video metrics via Data API v3.

Stores results in a local JSON file for dashboard rendering.
Designed to run as a daily cron job.
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

_PARENT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PARENT not in sys.path:
    sys.path.insert(0, _PARENT)

from youtube.auth import get_authenticated_service

# Store analytics in the Obsidian vault for easy viewing
ANALYTICS_DIR = Path.home() / "obsidian-vault" / "knowledge" / "docs" / "social-media" / "analytics"
ANALYTICS_FILE = ANALYTICS_DIR / "channel_data.json"


def collect_channel_stats(channel_key: str) -> dict:
    """Fetch channel statistics from YouTube API."""
    try:
        service = get_authenticated_service(channel_key)
        channels = service.channels().list(
            part="snippet,statistics",
            mine=True
        ).execute()
        
        if not channels.get("items"):
            return {"error": "No channel found"}
        
        ch = channels["items"][0]
        stats = ch["statistics"]
        return {
            "channel": ch["snippet"]["title"],
            "subscribers": int(stats.get("subscriberCount", 0)),
            "views": int(stats.get("viewCount", 0)),
            "videos": int(stats.get("videoCount", 0)),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        return {"error": str(e), "channel_key": channel_key}


def collect_video_stats(channel_key: str, max_results: int = 20) -> list[dict]:
    """Fetch recent video stats from a channel."""
    try:
        service = get_authenticated_service(channel_key)
        channels = service.channels().list(part="id", mine=True).execute()
        if not channels.get("items"):
            return []
        channel_id = channels["items"][0]["id"]
        
        videos = []
        request = service.search().list(
            channelId=channel_id,
            part="id",
            order="date",
            maxResults=max_results,
            type="video"
        )
        response = request.execute()
        
        video_ids = [item["id"]["videoId"] for item in response.get("items", []) if item["id"]["kind"] == "youtube#video"]
        
        if video_ids:
            stats_response = service.videos().list(
                part="snippet,statistics,contentDetails",
                id=",".join(video_ids)
            ).execute()
            
            for item in stats_response.get("items", []):
                sn = item["snippet"]
                st = item["statistics"]
                videos.append({
                    "video_id": item["id"],
                    "title": sn["title"],
                    "published": sn["publishedAt"][:10],
                    "views": int(st.get("viewCount", 0)),
                    "likes": int(st.get("likeCount", 0)),
                    "comments": int(st.get("commentCount", 0)),
                    "duration": item["contentDetails"]["duration"],
                })
        
        return videos
    except Exception as e:
        return [{"error": str(e)}]


def collect_all(channel_keys: list[str] = None):
    """Collect analytics for all or specified channels."""
    if channel_keys is None:
        channel_keys = ["soccer", "faithnexus"]
    
    ANALYTICS_DIR.mkdir(parents=True, exist_ok=True)
    
    report = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "channels": {},
    }
    
    for ch in channel_keys:
        print(f"Fetching {ch}...")
        stats = collect_channel_stats(ch)
        videos = collect_video_stats(ch, max_results=10)
        report["channels"][ch] = {
            "stats": stats,
            "recent_videos": videos,
        }
    
    with open(ANALYTICS_FILE, "w") as f:
        json.dump(report, f, indent=2)
    
    # Also write a readable markdown version
    md_path = ANALYTICS_DIR / "dashboard.md"
    with open(md_path, "w") as f:
        f.write("# Social Media Analytics Dashboard\n\n")
        f.write(f"*Last updated: {report['fetched_at'][:19]}*\n\n")
        
        for ch, data in report["channels"].items():
            f.write(f"## {ch}\n\n")
            stats = data.get("stats", {})
            if "error" in stats:
                f.write(f"⚠️ {stats['error']}\n\n")
                continue
            f.write(f"| Metric | Value |\n|---|---|\n")
            f.write(f"| Subscribers | {stats.get('subscribers', 'N/A')} |\n")
            f.write(f"| Total Views | {stats.get('views', 'N/A')} |\n")
            f.write(f"| Total Videos | {stats.get('videos', 'N/A')} |\n\n")
            
            videos = data.get("recent_videos", [])
            if videos:
                f.write("| Video | Views | Likes | Published |\n|---|---|---|---|\n")
                for v in videos:
                    f.write(f"| {v['title'][:50]} | {v['views']} | {v['likes']} | {v['published']} |\n")
                f.write("\n")
    
    print(f"Analytics saved to {ANALYTICS_FILE}")
    print(f"Dashboard updated: {md_path}")
    return report


if __name__ == "__main__":
    collect_all()
