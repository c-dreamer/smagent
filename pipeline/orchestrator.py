#!/usr/bin/env python3
"""Pipeline orchestrator — runs the full content generation pipeline with real video clips."""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

_PARENT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PARENT not in sys.path:
    sys.path.insert(0, _PARENT)

from config import CHANNELS  # noqa: E402
from schema import PipelineStateModel  # noqa: E402
from pipeline import approval  # noqa: E402
from channel_configs import get_channel_config  # noqa: E402

STAGES = ["script", "thumbnail", "voiceover", "metadata", "download_clips", "compile", "review"]
DEFAULT_OUTPUT_DIR = str(Path.home() / "Downloads" / "smagent_output")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run_module(module_path: str, args: list, stage: str) -> PipelineStateModel:
    state = PipelineStateModel(stage=stage, status="running", started_at=_now())
    try:
        result = subprocess.run(
            [sys.executable, module_path] + args,
            capture_output=True, text=True, check=True,
        )
        state.status = "completed"
        state.completed_at = _now()
        state.artifacts = {"stdout": result.stdout.strip()}
    except subprocess.CalledProcessError as e:
        state.status = "failed"
        state.error = e.stderr.strip() or str(e)
        state.completed_at = _now()
    return state


def run_pipeline(
    channel: str,
    topic: str,
    output_dir: str,
    youtube_url: str | None = None,
    tiktok_url: str | None = None,
    skip_download: bool = False,
    script_provider: str = "template",
    evidence_file: str | None = None,
    asset_provider: str = "none",
) -> dict:
    """
    Run the full content generation pipeline for a channel.

    Args:
        channel: Channel key (soccer, christian, trading, our_daily_bread)
        topic: Video topic
        output_dir: Output directory for all artifacts
        youtube_url: Optional YouTube URL to download as clip source
        tiktok_url: Optional TikTok URL to download as clip source
        skip_download: If True, skip the download stage (use existing clips)

    Returns:
        Pipeline report dict
    """
    os.makedirs(output_dir, exist_ok=True)
    base = os.path.join(output_dir, channel.replace(" ", "_"))
    states = {}
    artifacts = {}

    ch_config = get_channel_config(channel)

    # ── Stage 1: Script ────────────────────────────────────────────────────
    script_path = f"{base}_script.json"
    script_args = ["--channel", channel, "--topic", topic, "--output", script_path,
                   "--provider", script_provider]
    if evidence_file:
        script_args.extend(["--evidence-file", evidence_file])
    s1 = _run_module(
        os.path.join(_PARENT, "script_gen", "generator.py"),
        script_args,
        "script",
    )
    states["script"] = s1.model_dump() if hasattr(s1, "model_dump") else s1.dict()
    if s1.status != "completed":
        return {"channel": channel, "topic": topic, "status": "failed", "stages": states}
    artifacts["script"] = script_path

    # ── Stage 2: Thumbnail ─────────────────────────────────────────────────
    thumb_path = f"{base}_thumbnail.jpg"
    s2 = _run_module(
        os.path.join(_PARENT, "thumbnail", "generator.py"),
        ["--channel", channel, "--title", topic, "--output", thumb_path],
        "thumbnail",
    )
    states["thumbnail"] = s2.model_dump() if hasattr(s2, "model_dump") else s2.dict()
    if s2.status != "completed":
        return {"channel": channel, "topic": topic, "status": "failed", "stages": states}
    artifacts["thumbnail"] = thumb_path

    # ── Stage 3: Voiceover ─────────────────────────────────────────────────
    audio_path = f"{base}_audio.mp3"
    s3 = _run_module(
        os.path.join(_PARENT, "media_proc", "voiceover.py"),
        ["--channel", channel, "--script", script_path, "--output", audio_path],
        "voiceover",
    )
    states["voiceover"] = s3.model_dump() if hasattr(s3, "model_dump") else s3.dict()
    if s3.status != "completed":
        return {"channel": channel, "topic": topic, "status": "failed", "stages": states}
    artifacts["audio"] = audio_path

    # ── Stage 4: Metadata ─────────────────────────────────────────────────
    meta_path = f"{base}_metadata.json"
    s4 = _run_module(
        os.path.join(_PARENT, "metadata", "optimizer.py"),
        ["--channel", channel, "--topic", topic, "--script", script_path, "--output", meta_path],
        "metadata",
    )
    states["metadata"] = s4.model_dump() if hasattr(s4, "model_dump") else s4.dict()
    if s4.status != "completed":
        return {"channel": channel, "topic": topic, "status": "failed", "stages": states}
    artifacts["metadata"] = meta_path

    # ── Stage 5: Download video clips ──────────────────────────────────────
    clips_dir = os.path.join(output_dir, "clips")
    os.makedirs(clips_dir, exist_ok=True)
    download_results = []
    provenance_path = None

    if asset_provider in {"pexels", "commons"}:
        provenance_path = os.path.join(output_dir, "visual_asset_provenance.json")
        asset_module = "pexels.py" if asset_provider == "pexels" else "wikimedia_commons.py"
        visual_stage = _run_module(
            os.path.join(_PARENT, "visual_gen", asset_module),
            ["--script", script_path, "--output-dir", clips_dir, "--manifest", provenance_path],
            "download_clips",
        )
        if visual_stage.status != "completed":
            states["download_clips"] = visual_stage.model_dump() if hasattr(visual_stage, "model_dump") else visual_stage.dict()
            return {"channel": channel, "topic": topic, "status": "failed", "stages": states}
        download_results = [str(path) for path in sorted(Path(clips_dir).glob("*.mp4"))]
        artifacts["visual_provenance"] = provenance_path

    if not skip_download and asset_provider == "none":
        if youtube_url:
            print(f"\nDownloading YouTube video: {youtube_url}")
            dl_path = os.path.join(clips_dir, "yt_source.mp4")
            dl_module = os.path.join(_PARENT, "media_proc", "clip_downloader.py")
            dl_args = [youtube_url, "--output", dl_path, "--quality", "720p"]
            s5a = _run_module(dl_module, dl_args, "download_clips")
            if s5a.status == "completed":
                download_results.append(dl_path)
                artifacts["downloaded_youtube"] = dl_path
                print(f"  Downloaded: {dl_path}")
            else:
                print(f"  YouTube download failed: {s5a.error}")

        if tiktok_url:
            print(f"\nDownloading TikTok video: {tiktok_url}")
            dl_path = os.path.join(clips_dir, "tt_source.mp4")
            dl_module = os.path.join(_PARENT, "media_proc", "clip_downloader.py")
            dl_args = [tiktok_url, "--output", dl_path]
            s5b = _run_module(dl_module, dl_args, "download_clips")
            if s5b.status == "completed":
                download_results.append(dl_path)
                artifacts["downloaded_tiktok"] = dl_path
                print(f"  Downloaded: {dl_path}")
            else:
                print(f"  TikTok download failed: {s5b.error}")

    # Mark download stage as completed (or skipped)
    download_status = "skipped" if skip_download else ("completed" if download_results else "no_clips")
    states["download_clips"] = {
        "stage": "download_clips",
        "status": download_status,
        "started_at": _now(),
        "completed_at": _now(),
        "artifacts": {"clips_dir": clips_dir, "downloaded": download_results, "provenance": provenance_path},
    }

    # If we have source stock clips and no YouTube/TikTok download, copy them
    if not download_results and ch_config.stock_dir and os.path.isdir(ch_config.stock_dir):
        print(f"\nUsing stock clips from: {ch_config.stock_dir}")
        import shutil
        for f in sorted(os.listdir(ch_config.stock_dir)):
            if f.lower().endswith((".mp4", ".mov", ".avi", ".mkv", ".webm")):
                src = os.path.join(ch_config.stock_dir, f)
                dst = os.path.join(clips_dir, f)
                if not os.path.exists(dst):
                    shutil.copy2(src, dst)
                    download_results.append(dst)
                    print(f"  Copied stock clip: {f}")
        states["download_clips"]["artifacts"]["stock_clips"] = download_results

    # ── Stage 6: Compile video (clip assembler) ────────────────────────────
    video_path = f"{base}_video.mp4"
    compile_args = [
        "--script", script_path,
        "--channel", channel,
        "--output", video_path,
    ]
    if audio_path and os.path.isfile(audio_path):
        compile_args.extend(["--audio", audio_path])
    if os.path.isdir(clips_dir) and os.listdir(clips_dir):
        compile_args.extend(["--clips-dir", clips_dir])
    # Pass watermark (channel handle)
    ch_info = CHANNELS.get(channel)
    if ch_info and ch_info.handle:
        compile_args.extend(["--watermark", ch_info.handle])

    if channel == "christian":
        s6 = _run_module(
            os.path.join(_PARENT, "media_proc", "faith_nexus_renderer.py"),
            ["--script", script_path, "--audio", audio_path, "--clips-dir", clips_dir, "--output", video_path],
            "compile",
        )
    else:
        s6 = _run_module(
            os.path.join(_PARENT, "media_proc", "clip_assembler.py"),
            compile_args,
            "compile",
        )
    states["compile"] = s6.model_dump() if hasattr(s6, "model_dump") else s6.dict()
    if s6.status != "completed":
        return {"channel": channel, "topic": topic, "status": "failed", "stages": states}
    artifacts["video"] = video_path

    # ── Stage 7: Approval review ─────────────────────────────────────────
    manifest_path = approval.create_review_manifest(
        channel=channel, topic=topic, artifacts=artifacts,
        output_dir=output_dir,
    )
    states["review"] = PipelineStateModel(
        stage="review", status="pending_approval", started_at=_now(), completed_at=_now(),
        artifacts={"manifest": manifest_path},
    ).model_dump() if hasattr(PipelineStateModel, "model_dump") else {
        "stage": "review", "status": "pending_approval",
        "started_at": _now(), "completed_at": _now(),
        "artifacts": {"manifest": manifest_path},
    }
    states["review"] = states["review"] if isinstance(states["review"], dict) else states["review"].dict()

    return {
        "channel": channel,
        "topic": topic,
        "status": "pending_approval",
        "stages": states,
        "artifacts": artifacts,
        "review_manifest": manifest_path,
    }


def main():
    parser = argparse.ArgumentParser(description="Run the full content generation pipeline with real clips")
    parser.add_argument("--channel", required=True, choices=list(CHANNELS.keys()),
                        help="Channel key")
    parser.add_argument("--topic", required=True, help="Video topic")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR,
                        help="Directory for all generated artifacts")
    parser.add_argument("--report", help="Path to write pipeline report JSON")
    parser.add_argument("--youtube-url", help="YouTube URL to download and use as clip source")
    parser.add_argument("--tiktok-url", help="TikTok URL to download and use as clip source")
    parser.add_argument("--skip-download", action="store_true",
                        help="Skip download stage, use existing clips only")
    parser.add_argument("--script-provider", choices=["template", "nvidia"], default="template",
                        help="Use nvidia only with a source-bound evidence pack")
    parser.add_argument("--evidence-file", help="JSON evidence pack required by --script-provider nvidia")
    parser.add_argument("--asset-provider", choices=["none", "pexels", "commons"], default="none",
                        help="pexels or commons retrieves provenance-tracked clips; pexels is preferred for production")

    args = parser.parse_args()

    report = run_pipeline(
        channel=args.channel,
        topic=args.topic,
        output_dir=args.output_dir,
        youtube_url=args.youtube_url,
        tiktok_url=args.tiktok_url,
        skip_download=args.skip_download,
        script_provider=args.script_provider,
        evidence_file=args.evidence_file,
        asset_provider=args.asset_provider,
    )

    report_path = args.report or os.path.join(args.output_dir, "pipeline_report.json")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    if report["status"] == "pending_approval":
        print("\n" + "=" * 60)
        print("All generation stages completed successfully!")
        print("Pipeline is now waiting for your approval before upload.")
        print()
        print("To review the artifacts:")
        print(f"  python3 pipeline/approval.py review --manifest \\")
        print(f"      {report['review_manifest']}")
        print()
        print("To approve and mark ready for upload:")
        print(f"  python3 pipeline/approval.py approve --manifest \\")
        print(f"      {report['review_manifest']}")
        print()
        print("Artifacts:")
        for label, path in report.get("artifacts", {}).items():
            size = os.path.getsize(path) if os.path.exists(path) else 0
            print(f"  {label:20s}  {path}  ({size:,} bytes)")
    elif report["status"] == "failed":
        failed = [s for s, st in report["stages"].items() if isinstance(st, dict) and st.get("status") == "failed"]
        print(f"Pipeline failed at stage(s): {failed}", file=sys.stderr)
        for f_stage in failed:
            err = report["stages"][f_stage].get("error", "unknown")
            print(f"  {f_stage}: {err}", file=sys.stderr)
        sys.exit(1)
    else:
        print(f"Pipeline completed: {report['status']}")


if __name__ == "__main__":
    main()
