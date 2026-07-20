# OpenCode production path

`smagent` is the source of truth and must run without Codex tooling.

## Runtime split

| Host | Work |
| --- | --- |
| macOS M1 | OpenCode control, review, small renders and approvals |
| Linux CPU VPS | scheduling, evidence packs, manifests, assets, FFmpeg rendering and uploads |
| NVIDIA API or optional Linux GPU worker | NIM script generation; high-quality image/video generation through an API or ComfyUI |

The Oracle VPS is CPU-only. Do not run Flux, Wan, Open-Sora or HunyuanVideo on it.

## Required environment

```sh
export NVIDIA_API_KEY='…'
export NVIDIA_TEXT_MODEL='…'
export NVIDIA_NIM_URL='https://integrate.api.nvidia.com/v1/chat/completions'
```

Never commit keys, OAuth credentials, model weights, source media, or private manifests.

Your current OpenCode configuration supplies NVIDIA credentials only to the
memory service, not to arbitrary `smagent` commands. Give the OpenCode task an
explicit `NVIDIA_API_KEY` and `NVIDIA_TEXT_MODEL` environment (or load a local
untracked `.env` from `.env.example`) before using the NVIDIA provider.

## Quality gate

1. Create an evidence pack with quotations, translation, licence and URLs.
2. Generate with `script_gen.nvidia_writer.generate_faith_script`.
3. Record model/workflow, prompt, seed, source URL and licence for every visual.
4. Render using FFmpeg/Pillow; captions are rasterised so `libass` is not required.
5. Review reference and candidate frames. Codex may compare quality when available, but is never a dependency.
6. Complete `examples/faith_nexus_review_template.json`, attach it with `pipeline/approval.py record-quality`, then have a human approve the manifest. Codex may supply comparison notes in that review, but its availability never affects rendering or publishing.

## Asset policy

Use ComfyUI API with Flux for keyframes and Wan/LTX for short motion shots, a hosted NVIDIA provider, or licensed stock. `yt-dlp` is a downloader, not a licence: restrict it to your own work, explicitly licensed assets, or written permission. Preserve URL, creator, licence and used timecodes in the manifest.

For Faith Nexus, the recommended first production recipe is Pexels video clips (`visual_gen/pexels.py`) plus source-bound Scripture, rather than a model whose commercial terms are unclear. It downloads one portrait clip per scene and writes the creator, Pexels URL, selected resolution and licence reminder to a provenance JSON file. A Pexels key is free but must be requested separately and stored only in `PEXELS_API_KEY`.

For a local or GPU-worker ComfyUI server, `visual_gen.comfyui.ComfyUIClient` queues an exported API workflow, waits for it, and retrieves its outputs. This keeps the exact workflow JSON under version control and makes OpenCode—not an interactive UI—the orchestrator.
