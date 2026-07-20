# Faith Nexus cinematic devotional pipeline

The new Faith Nexus route is an audio-led image-film: it creates word timings
with TTS, acquires one visual for every storyboard beat, then renders animated
images with word-highlight captions and a persistent exact Scripture card. It creates review artifacts only; it never
uploads or approves a video.

Each devotional can generate an original, low-level ambient bed from synthesis.
The generated WAV and its provenance JSON are preserved in the review bundle;
use a separately recorded licence manifest if replacing it with external music.

`caption_style` belongs in each storyboard. Set `accent_hex` and `caption_hex`
per video to match its emotional palette; gold is only the warm-dawn default,
not a channel-wide brand requirement. Captions are uppercase, large, and black
outlined. A five-word phrase stays continuously visible between spoken words;
only the active word changes to the palette accent, preventing a blinking or
flashing subtitle effect.

## Workflow references adopted deliberately

[MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo) usefully
reinforces configurable vertical output, material pacing, caption styling, and
gentle background-music control. smagent keeps the Scripture-first storyboard,
provenance checks, and review-only publishing policy rather than adopting its
generic auto-video path. [WhisperX](https://github.com/m-bain/whisperX) is the
optional post-TTS verification route: its forced alignment can validate
word-level caption timing on a capable GPU worker. Edge TTS boundaries remain
the production timing source, so the pipeline works without a WhisperX runtime
dependency on this Mac.

## Run the Matthew 6:34 candidate

```sh
python3 pipeline/orchestrator.py \
  --channel christian \
  --topic "When Tomorrow Feels Too Heavy" \
  --faith-storyboard examples/faith_nexus_matthew_6_34_storyboard.json \
  --faith-image-provider comfyui \
  --comfy-workflow-template workflows/faith_nexus_sd35.api.json
```

The default `comfyui` provider needs `COMFYUI_URL` and a ComfyUI API workflow
whose positive prompt includes `{{PROMPT}}`. Every generated asset records its
prompt and workflow. `pexels` is a licensed fallback only and is recorded as
non-generated in `visual_asset_provenance.json`.

The official ComfyUI source checkout is kept alongside this repository at
`AI/Github Repos/ComfyUI`; it is intentionally not vendored into `smagent`.
Install its macOS/Apple Silicon dependencies and start its server separately,
then set `COMFYUI_URL`, for example `http://127.0.0.1:8188`. The included
`workflows/faith_nexus_sd35.api.json` expects an authorised
`sd3.5_large.safetensors` checkpoint on a capable GPU worker. Do not attempt
this 8 GB M1 as the production generator; it is intended for a remote GPU.

## Approval requirements

The storyboard validator requires a full exact WEB verse, 85–105 narration
words, and 10–18 consecutive image beats. The bundle preflight checks verse
fidelity, word timing, one generated visual per beat, captions, and audio duration. A
human still completes `examples/faith_nexus_review_template.json` and records
the passing review before approval is possible.
