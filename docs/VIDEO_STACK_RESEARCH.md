# Faith Nexus video-stack decision record

Updated 2026-07-20. This is a production decision record, not an endorsement of
every repository listed below.

## Decision

Use a **licensed-stock first** recipe for Faith Nexus until one reviewed short is
approved:

1. Source-bound NVIDIA NIM script.
2. Pexels portrait clips with a saved creator, URL and licence record.
3. Local/OpenCode FFmpeg render and Edge TTS voiceover.
4. Quality rubric, human approval, then upload.

This is the quickest path to a high-quality, publishable short on the existing
M1 Mac and CPU-only VPS. It contains no Codex runtime dependency.

If a Pexels key is not available, use `--asset-provider commons` to make a
review candidate from licence-verified Wikimedia Commons stills with gentle
motion. It is a practical no-key fallback, not the preferred final visual style.

Use generative video only for a deliberately chosen 3–6 second motion insert
after the stock-first version earns approval. Keep each model workflow and seed
in the output manifest.

## Host roles

| Host | Run here | Do not run here |
| --- | --- | --- |
| M1 MacBook Air (8 GB) | OpenCode control, script review, Pexels retrieval, FFmpeg renders, small LTX experiments | A dependable high-resolution diffusion/video production queue |
| CPU-only Oracle VPS | scheduling, manifests, FFmpeg, uploads, n8n triggers | Flux, Wan, OpenSora, HunyuanVideo or LTX inference |
| Temporary NVIDIA GPU worker | ComfyUI job server, Wan/LTX image-to-video experiments, WhisperX captions | publishing credentials or the source-of-truth database |

## Candidate projects

| Project | Fit | Decision |
| --- | --- | --- |
| [LTX-Video](https://github.com/Lightricks/LTX-Video) | Image-to-video, keyframes and ComfyUI. Its repository documents MPS support and a commercial-use licence for current models. | **Best optional motion experiment.** Start with a 2B distilled workflow or remote GPU worker; preserve its ComfyUI API JSON. |
| [Wan2.1](https://github.com/Wan-Video/Wan2.1) | Strong open video stack with ComfyUI/Diffusers integration. The 1.3B model is lighter but its own documentation recommends 480p for stable output. | **GPU worker only.** Use I2V, not unconstrained T2V, for a 3–6 second ambient insert. |
| [Open-Sora](https://github.com/hpcaitech/Open-Sora) | Research-oriented I2V/T2V. Published figures show roughly 52.5 GB at 256px and 60.3 GB at 768px on H100/H800-class tests. | **Do not deploy for Faith Nexus now.** Keep as a later research benchmark. |
| [HunyuanVideo](https://github.com/Tencent-Hunyuan/HunyuanVideo) | Good research quality, but the official requirements specify 45–60 GB minimum and recommend 80 GB GPU, Linux/CUDA. | **Not viable** for the Mac or current VPS. |
| [WhisperX](https://github.com/m-bain/whisperX) | Word-level timestamps, useful for a later caption quality pass. | **Optional GPU-worker post-process.** Add after visual recipe approval; do not make it a first-short blocker. |
| [n8n](https://github.com/n8n-io/n8n) | Self-hostable workflow coordination. | **Use only as a trigger/status layer.** Keep all content decisions in `smagent` Python and manifests. |

## NVIDIA API strategy

| Capability | Use | Constraint |
| --- | --- | --- |
| Nemotron/NIM text | Evidence-bound script candidates and optionally title/metadata alternatives | Use JSON schema plus the current source and generic-copy rejection checks. |
| FLUX.1 dev/kontext dev | Private visual prototyping only | NVIDIA’s current documentation describes these endpoints as non-commercial. Do not place their output in a monetised production recipe without separate rights. |
| Cosmos3 Nano | Track as a future open-model experiment | The model card says hosted preview output receives SynthID watermarking; the public endpoint has not been reliably available. Do not make it a pipeline dependency. |
| NVIDIA visual-language models | Optional visual quality checks on candidate frames | Informative only. A human still makes the publish decision. |

## Source policy

`yt-dlp` is an acquisition tool, not a rights grant. Use it only for channel-owned
media, media with an explicit compatible licence, or footage with written
permission. Store source URL, creator, licence/permission proof, and used
timecodes. Never alter footage to evade Content ID or use transformation as a
substitute for permission.

`yt-dlp` can mark/remove SponsorBlock segments; that is useful to clean up a
lawfully acquired long source before an editor selects a clip, but must not be
used to conceal reuse.

## First approved recipe

```sh
python3 pipeline/orchestrator.py \
  --channel christian \
  --topic "When tomorrow feels heavy" \
  --script-provider nvidia \
  --evidence-file examples/faith_nexus_matthew_6_34_evidence.json \
  --asset-provider pexels \
  --output-dir ./media_output/faith-nexus-matthew-6-34
```

Before running it, provide `NVIDIA_API_KEY`, `NVIDIA_TEXT_MODEL`, and
`PEXELS_API_KEY` to the OpenCode environment or the local ignored `.env`. The
result remains `pending_approval` until a completed quality review is attached.

## Evidence

- [LTX-Video repository](https://github.com/Lightricks/LTX-Video)
- [Wan2.1 repository](https://github.com/Wan-Video/Wan2.1)
- [Open-Sora repository](https://github.com/hpcaitech/Open-Sora)
- [HunyuanVideo repository](https://github.com/Tencent-Hunyuan/HunyuanVideo)
- [Pexels API documentation](https://www.pexels.com/api/documentation/)
- [yt-dlp repository](https://github.com/yt-dlp/yt-dlp)
- [WhisperX repository](https://github.com/m-bain/whisperX)
- [n8n repository](https://github.com/n8n-io/n8n)
