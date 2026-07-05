"""
Channel configuration system for the social media agent.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class ChannelConfig:
    """Configuration for a social media channel."""
    name: str
    handle: str
    channel_id: Optional[str] = None
    niche: str = ""
    tone: str = ""
    content_folder: Optional[str] = None
    gdrive_path: Optional[str] = None
    category_id: Optional[int] = None
    playlist_id: Optional[str] = None


@dataclass
class VideoMetadata:
    """Metadata for a video to be published."""
    title: str
    description: str
    tags: List[str]
    category_id: int
    publish_at: Optional[str] = None  # ISO format string
    language: str = "en"
    made_for_kids: bool = False


@dataclass
class PipelineState:
    """State of a pipeline stage."""
    stage: str
    status: str  # pending|running|completed|failed
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None
    artifacts: Optional[Dict[str, Any]] = None


@dataclass
class ContentQueueItem:
    """Item in the content queue."""
    id: Optional[int] = None
    channel: str = ""
    topic: str = ""
    script_path: Optional[str] = None
    video_path: Optional[str] = None
    metadata_path: Optional[str] = None
    status: str = "queued"  # queued|in_progress|completed|failed
    created_at: Optional[str] = None


# Channel configurations
CHANNELS: Dict[str, ChannelConfig] = {
    "soccer": ChannelConfig(
        name="GoalHubPro",
        handle="@Goal_HubPro",
        niche="soccer analysis and highlights",
        tone="energetic and exciting"
    ),
    "christian": ChannelConfig(
        name="Faith Nexus",
        handle="@Faith_Nexus",
        niche="faith and Bible study",
        tone="warm and reverent"
    ),
    "trading": ChannelConfig(
        name="Trading",
        handle="TBD",
        niche="market analysis and trading strategies",
        tone="professional and analytical"
    )
}