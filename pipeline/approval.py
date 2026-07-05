#!/usr/bin/env python3
"""Approval gate for video content — review artifacts before marking ready for upload."""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

_PARENT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PARENT not in sys.path:
    sys.path.insert(0, _PARENT)

from config import CHANNELS  # noqa: E402


def create_review_manifest(channel: str, topic: str, artifacts: dict,
                           output_dir: str) -> str:
    """Generate a review manifest JSON for human approval."""
    manifest = {
        "channel": channel,
        "topic": topic,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending_approval",
        "artifacts": artifacts,
        "channel_info": {
            "name": CHANNELS[channel].name,
            "handle": CHANNELS[channel].handle,
            "niche": CHANNELS[channel].niche,
        },
    }
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, "review_manifest.json")
    with open(path, "w") as f:
        json.dump(manifest, f, indent=2, default=str)
    return path


def approve(manifest_path: str) -> dict:
    """Mark a review manifest as approved."""
    if not os.path.exists(manifest_path):
        print(f"Error: manifest not found: {manifest_path}", file=sys.stderr)
        sys.exit(1)
    with open(manifest_path, "r") as f:
        manifest = json.load(f)
    if manifest.get("status") == "approved":
        print("Already approved.")
        return manifest
    manifest["status"] = "approved"
    manifest["approved_at"] = datetime.now(timezone.utc).isoformat()
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2, default=str)
    print(f"Approved. Manifest updated: {manifest_path}")
    return manifest


def reject(manifest_path: str, reason: str = "") -> dict:
    """Mark a review manifest as rejected."""
    if not os.path.exists(manifest_path):
        print(f"Error: manifest not found: {manifest_path}", file=sys.stderr)
        sys.exit(1)
    with open(manifest_path, "r") as f:
        manifest = json.load(f)
    manifest["status"] = "rejected"
    manifest["rejected_at"] = datetime.now(timezone.utc).isoformat()
    if reason:
        manifest["rejection_reason"] = reason
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2, default=str)
    print(f"Rejected. Manifest updated: {manifest_path}")
    return manifest


def show_review(manifest_path: str):
    """Print a human-readable summary of the review manifest."""
    if not os.path.exists(manifest_path):
        print(f"Error: manifest not found: {manifest_path}", file=sys.stderr)
        sys.exit(1)
    with open(manifest_path, "r") as f:
        m = json.load(f)
    print(f"Channel:     {m['channel']} ({m['channel_info']['name']})")
    print(f"Topic:       {m['topic']}")
    print(f"Status:      {m['status']}")
    print(f"Created:     {m['created_at']}")
    print(f"\nArtifacts:")
    for label, path in m.get("artifacts", {}).items():
        size = os.path.getsize(path) if os.path.exists(path) else 0
        print(f"  {label:12s}  {path}  ({size:,} bytes)")
    if m.get("approved_at"):
        print(f"\nApproved at: {m['approved_at']}")
    if m.get("rejected_at"):
        print(f"\nRejected at: {m['rejected_at']}")
        if m.get("rejection_reason"):
            print(f"Reason: {m['rejection_reason']}")


def main():
    parser = argparse.ArgumentParser(description="Video approval gate")
    sub = parser.add_subparsers(dest="command", required=True)

    p_review = sub.add_parser("review", help="Show review manifest")
    p_review.add_argument("--manifest", required=True)

    p_approve = sub.add_parser("approve", help="Approve video for upload")
    p_approve.add_argument("--manifest", required=True)

    p_reject = sub.add_parser("reject", help="Reject video")
    p_reject.add_argument("--manifest", required=True)
    p_reject.add_argument("--reason", default="")

    args = parser.parse_args()
    if args.command == "review":
        show_review(args.manifest)
    elif args.command == "approve":
        approve(args.manifest)
    elif args.command == "reject":
        reject(args.manifest, args.reason)


if __name__ == "__main__":
    main()
