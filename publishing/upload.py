#!/usr/bin/env python3
"""Dry-run-first CLI for the channel-scoped publishing router."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from publishing.router import PublishRequest, health, publish

parser = argparse.ArgumentParser()
parser.add_argument("--channel", required=True, choices=["christian", "soccer"])
parser.add_argument("--health", action="store_true")
parser.add_argument("--video")
parser.add_argument("--title")
parser.add_argument("--description", default="")
parser.add_argument("--tags", nargs="*", default=[])
parser.add_argument("--privacy", choices=["private", "unlisted", "public"], default="private")
parser.add_argument("--provider", choices=["auto", "youtube_api", "postiz", "studio"], default="auto")
parser.add_argument("--publish", action="store_true", help="Required to create an external upload")
args = parser.parse_args()
if args.health:
    print(json.dumps(health(args.channel), indent=2))
elif args.video and args.title:
    print(json.dumps(publish(PublishRequest(args.channel, args.video, args.title, args.description, args.tags, args.privacy), args.provider, args.publish), indent=2))
else:
    parser.error("use --health or provide --video and --title")
