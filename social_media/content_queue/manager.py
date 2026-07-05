import os
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, List, Dict, Any
from supabase import create_client, Client

# Supabase client setup
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")  # Using service role for backend

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


@dataclass
class QueueItem:
    id: Optional[int]
    channel: str
    topic: str
    status: str  # queued | in_progress | completed | failed
    script_path: Optional[str] = None
    video_path: Optional[str] = None
    metadata_path: Optional[str] = None
    thumbnail_path: Optional[str] = None
    error: Optional[str] = None
    created_at: str = ""
    updated_at: Optional[str] = None

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()
        if self.updated_at is None:
            self.updated_at = self.created_at


def _item_from_row(row: Dict[str, Any]) -> QueueItem:
    """Convert a Supabase row to a QueueItem dataclass."""
    return QueueItem(
        id=row.get("id"),
        channel=row.get("channel"),
        topic=row.get("topic"),
        status=row.get("status"),
        script_path=row.get("script_path"),
        video_path=row.get("video_path"),
        metadata_path=row.get("metadata_path"),
        thumbnail_path=row.get("thumbnail_path"),
        error=row.get("error"),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
    )


def add_item(channel: str, topic: str, **kwargs) -> int:
    """
    Add a new item to the queue.
    Returns the ID of the inserted item.
    """
    data = {
        "channel": channel,
        "topic": topic,
        "status": "queued",
        **kwargs,
    }
    # Ensure timestamps are set
    if "created_at" not in data:
        data["created_at"] = datetime.utcnow().isoformat()
    if "updated_at" not in data:
        data["updated_at"] = data["created_at"]

    try:
        result = supabase.table("social_media_queue").insert(data).execute()
        if result.data and len(result.data) > 0:
            return result.data[0]["id"]
        else:
            raise Exception("No data returned from insert")
    except Exception as e:
        # Handle Supabase connection failures gracefully
        print(f"Error adding item to queue: {e}")
        raise


def get_next(channel: str) -> Optional[QueueItem]:
    """
    Get the next queued item for a channel.
    Returns the oldest queued item (by created_at) or None if none available.
    """
    try:
        result = (
            supabase.table("social_media_queue")
            .select("*")
            .eq("channel", channel)
            .eq("status", "queued")
            .order("created_at", asc=True)
            .limit(1)
            .execute()
        )
        if result.data and len(result.data) > 0:
            return _item_from_row(result.data[0])
        return None
    except Exception as e:
        print(f"Error getting next item for channel {channel}: {e}")
        return None


def update_status(item_id: int, status: str, **kwargs) -> bool:
    """
    Update the status of a queue item and optional fields.
    Returns True if successful, False otherwise.
    """
    data = {
        "status": status,
        "updated_at": datetime.utcnow().isoformat(),
        **kwargs,
    }
    # Remove None values to avoid overwriting with NULL
    data = {k: v for k, v in data.items() if v is not None}

    try:
        result = (
            supabase.table("social_media_queue")
            .update(data)
            .eq("id", item_id)
            .execute()
        )
        return len(result.data) > 0
    except Exception as e:
        print(f"Error updating status for item {item_id}: {e}")
        return False


def retry_failed(channel: str) -> int:
    """
    Re-queue all failed items for a channel.
    Returns the count of items re-queued.
    """
    try:
        # First, get all failed items for the channel
        result = (
            supabase.table("social_media_queue")
            .select("id")
            .eq("channel", channel)
            .eq("status", "failed")
            .execute()
        )
        failed_ids = [item["id"] for item in result.data or []]

        if not failed_ids:
            return 0

        # Update each failed item to queued
        updated_count = 0
        for item_id in failed_ids:
            if update_status(item_id, "queued"):
                updated_count += 1

        return updated_count
    except Exception as e:
        print(f"Error retrying failed items for channel {channel}: {e}")
        return 0


def list_pending(channel: str) -> List[QueueItem]:
    """
    List all non-completed items for a channel.
    Returns items with status queued, in_progress, or failed.
    """
    try:
        result = (
            supabase.table("social_media_queue")
            .select("*")
            .eq("channel", channel)
            .in_("status", ["queued", "in_progress", "failed"])
            .order("created_at", asc=True)
            .execute()
        )
        return [_item_from_row(row) for row in result.data or []]
    except Exception as e:
        print(f"Error listing pending items for channel {channel}: {e}")
        return []


def get_stats(channel: str) -> Dict[str, int]:
    """
    Get counts per status for a channel.
    Returns a dictionary with status as key and count as value.
    """
    try:
        result = (
            supabase.table("social_media_queue")
            .select("status")
            .eq("channel", channel)
            .execute()
        )
        stats = {}
        for row in result.data or []:
            status = row["status"]
            stats[status] = stats.get(status, 0) + 1
        return stats
    except Exception as e:
        print(f"Error getting stats for channel {channel}: {e}")
        return {}