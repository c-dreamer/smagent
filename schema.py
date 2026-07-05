"""
Pydantic models for social media agent configuration and data.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
import re


class ChannelConfigModel(BaseModel):
    """Pydantic model for ChannelConfig."""
    name: str
    handle: str
    channel_id: Optional[str] = None
    niche: str
    tone: str
    content_folder: Optional[str] = None
    gdrive_path: Optional[str] = None
    category_id: Optional[int] = None
    playlist_id: Optional[str] = None


class VideoMetadataModel(BaseModel):
    """Pydantic model for VideoMetadata with validation."""
    title: str = Field(..., min_length=30, max_length=100)
    description: str = Field(..., max_length=5000)
    tags: List[str] = Field(default_factory=list)
    category_id: int
    publish_at: Optional[str] = None  # ISO format string
    language: str = "en"
    made_for_kids: bool = False

    @validator('tags')
    def check_tags_length(cls, v):
        """Validate that the total length of tags (including commas and spaces) is <= 500."""
        # Join tags with commas and spaces as they would appear in a tag string
        tags_string = ', '.join(v)
        if len(tags_string) > 500:
            raise ValueError('Total length of tags must be <= 500 characters')
        return v


class PipelineStateModel(BaseModel):
    """Pydantic model for PipelineState."""
    stage: str
    status: str  # pending|running|completed|failed
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None
    artifacts: Optional[Dict[str, Any]] = None


class ContentQueueItemModel(BaseModel):
    """Pydantic model for ContentQueueItem."""
    id: Optional[int] = None
    channel: str = ""
    topic: str = ""
    script_path: Optional[str] = None
    video_path: Optional[str] = None
    metadata_path: Optional[str] = None
    status: str = "queued"  # queued|in_progress|completed|failed
    created_at: Optional[str] = None