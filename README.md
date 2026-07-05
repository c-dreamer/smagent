# smagent — Social Media Agent

Automated social media content pipeline — script generation, video assembly, thumbnail creation, YouTube upload, scheduling, and analytics.

Originally extracted from the `human-ai` monorepo.

## Features

- **Script Generation** — Per-channel template-based script generation
- **Video Assembly** — Compose videos from clips with transitions, voiceover, overlays, watermarks (moviepy or ffmpeg backend)
- **Thumbnail Creation** — Channel-branded YouTube thumbnail generator
- **YouTube Upload** — OAuth-authenticated upload with metadata, thumbnails, playlist assignment, and quota management
- **Content Queue** — Supabase-backed queue for scheduling and tracking content pipeline runs
- **Scheduler** — Interval-based scheduler (APScheduler) for automated pipeline runs
- **Analytics** — YouTube channel and video analytics collector
- **Audit Logging** — Pipeline run audit trail to Supabase and local JSON logs

## Project Structure

```
smagent/
├── analytics/          # YouTube analytics collector
├── content_queue/      # Supabase-backed content queue
├── media_proc/         # Video processing (clips, ffmpeg, voiceover, overlays, transitions)
├── metadata/           # SEO metadata optimizer
├── pipeline/           # Orchestrator and approval gate
├── scheduler/          # Interval-based queue scheduler
├── script_gen/         # Script generation engine and templates
├── thumbnail/          # Thumbnail image generator
├── youtube/            # YouTube API auth and uploader
├── config.py           # Channel configurations
├── channel_configs.py  # Per-channel video generation configs
├── channels.yaml       # Channel definitions
├── log_utils.py        # Logging setup
├── observability.py    # Audit logging and quota tracking
└── schema.py           # Pydantic data models
```

## Supported Channels

| Key | Name | Niche | Orientation |
|-----|------|-------|-------------|
| `soccer` | GoalHubPro | Soccer analysis | Landscape (1920×1080) |
| `christian` | Faith Nexus | Faith & Bible study | Portrait (1080×1920) |
| `trading` | Trading Ed | Market analysis | Landscape (1920×1080) |

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set up YouTube OAuth (place client_secrets.json in youtube/)
python auth.py authorize --channel <channel_name>

# Run the full pipeline
python pipeline/orchestrator.py --channel soccer --topic "Match Analysis"
```

## Requirements

- Python 3.11+
- ffmpeg (for video assembly)
- Supabase instance (for content queue, optional)
- YouTube Data API v3 credentials

See [`requirements.txt`](requirements.txt) for Python dependencies.
