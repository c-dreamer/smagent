#!/usr/bin/env python3
"""
YouTube uploader — uploads videos with thumbnails, metadata, and playlist assignment.

Integrated with pipeline orchestrator. Handles per-channel OAuth token routing,
quota management, and retry logic.
"""

import argparse
import json
import os
import sys
import time

_PARENT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PARENT not in sys.path:
    sys.path.insert(0, _PARENT)

from youtube.auth import get_authenticated_service, check_token_validity
from googleapiclient.http import MediaFileUpload


# YouTube quota: 10,000 units/day. An upload costs ~1600 units.
# Track in a local file to avoid exceeding.
QUOTA_FILE = os.path.join(os.path.dirname(__file__), "..", "youtube_quota.json")


def _read_quota() -> dict:
    if os.path.exists(QUOTA_FILE):
        with open(QUOTA_FILE) as f:
            return json.load(f)
    return {"used": 0, "date": time.strftime("%Y-%m-%d")}


def _write_quota(used: int):
    os.makedirs(os.path.dirname(QUOTA_FILE), exist_ok=True)
    with open(QUOTA_FILE, "w") as f:
        json.dump({"used": used, "date": time.strftime("%Y-%m-%d")}, f)


def upload_video(
    video_path: str,
    title: str,
    description: str,
    tags: list[str],
    channel_key: str,
    category_id: str = "22",
    privacy: str = "public",
    thumbnail_path: str | None = None,
    playlist_id: str | None = None,
    made_for_kids: bool = False,
    dry_run: bool = False,
) -> dict:
    """Upload a video to YouTube.
    
    Args:
        video_path: Path to MP4 file
        title: Video title
        description: Video description
        tags: List of tags
        channel_key: OAuth channel key (soccer/faithnexus)
        category_id: YouTube category ID
        privacy: public/unlisted/private
        thumbnail_path: Optional thumbnail image path
        playlist_id: Optional playlist to add video to
        made_for_kids: If True, mark as made for kids
        dry_run: If True, validate without uploading
        
    Returns:
        Dict with video_id, url, or error
    """
    # Check quota
    quota = _read_quota()
    today = time.strftime("%Y-%m-%d")
    if quota["date"] != today:
        quota = {"used": 0, "date": today}
    
    # Upload costs ~1600 units per video
    UPLOAD_COST = 1600
    if quota["used"] + UPLOAD_COST > 9500:
        return {"error": f"YouTube quota exhausted ({quota['used']}/10000). Try tomorrow."}
    
    if not os.path.isfile(video_path):
        return {"error": f"Video file not found: {video_path}"}
    
    if not check_token_validity(channel_key).get("valid"):
        return {"error": f"OAuth token invalid for channel: {channel_key}. Re-authorize with 'python -m youtube.auth authorize --channel {channel_key}'"}
    
    service = get_authenticated_service(channel_key)
    
    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": tags[:50],
            "categoryId": category_id,
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": made_for_kids,
        }
    }
    
    if dry_run:
        print(f"[DRY RUN] Would upload: {title}")
        print(f"  Channel: {channel_key}")
        print(f"  File: {video_path}")
        print(f"  Privacy: {privacy}")
        return {"dry_run": True, "title": title}
    
    print(f"Uploading to {channel_key}: {title}")
    media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
    
    request = service.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )
    response = request.execute()
    video_id = response["id"]
    video_url = f"https://youtu.be/{video_id}"
    
    # Track quota
    quota["used"] += UPLOAD_COST
    _write_quota(quota["used"])
    
    # Upload thumbnail if provided
    if thumbnail_path and os.path.isfile(thumbnail_path):
        try:
            thumb_media = MediaFileUpload(thumbnail_path)
            service.thumbnails().set(videoId=video_id, media_body=thumb_media).execute()
            print(f"  Thumbnail set: {thumbnail_path}")
        except Exception as e:
            print(f"  Thumbnail upload failed (needs phone-verified account): {e}")
    
    # Add to playlist if specified
    if playlist_id:
        try:
            service.playlistItems().insert(
                part="snippet",
                body={
                    "snippet": {
                        "playlistId": playlist_id,
                        "resourceId": {
                            "kind": "youtube#video",
                            "videoId": video_id,
                        }
                    }
                }
            ).execute()
            print(f"  Added to playlist: {playlist_id}")
        except Exception as e:
            print(f"  Playlist add failed: {e}")
    
    result = {
        "video_id": video_id,
        "url": video_url,
        "channel": channel_key,
        "quota_used": quota["used"],
    }
    print(f"  Published: {video_url}")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload video to YouTube")
    parser.add_argument("--video", required=True, help="Path to MP4 video file")
    parser.add_argument("--title", required=True, help="Video title")
    parser.add_argument("--description", default="", help="Video description")
    parser.add_argument("--tags", nargs="*", default=[], help="Video tags")
    parser.add_argument("--channel", required=True, help="OAuth channel key (soccer/faithnexus)")
    parser.add_argument("--category", default="22", help="YouTube category ID")
    parser.add_argument("--privacy", default="public", choices=["public", "unlisted", "private"])
    parser.add_argument("--thumbnail", help="Thumbnail image path")
    parser.add_argument("--playlist", help="Playlist ID to add video to")
    parser.add_argument("--made-for-kids", action="store_true", help="Mark video as made for kids")
    parser.add_argument("--dry-run", action="store_true", help="Validate without uploading")
    args = parser.parse_args()
    
    result = upload_video(
        video_path=args.video,
        title=args.title,
        description=args.description,
        tags=args.tags or [],
        channel_key=args.channel,
        category_id=args.category,
        privacy=args.privacy,
        thumbnail_path=args.thumbnail,
        playlist_id=args.playlist,
        made_for_kids=args.made_for_kids,
        dry_run=args.dry_run,
    )
    
    if "error" in result:
        print(f"Error: {result['error']}", file=sys.stderr)
        sys.exit(1)
    
    print(json.dumps(result, indent=2))
