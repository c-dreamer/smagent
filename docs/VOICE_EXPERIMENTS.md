# Faith Nexus voice experiments

Use a named voice variant for future videos: `jenny_warm`, `aria_clear`,
`guy_calm`, or `andrew_steady`. The voice name and rate are retained in the
word-timing manifest for every render.

To learn which voice earns the strongest views, hold the Scripture, topic,
script, visual beats, caption palette, CTA, posting time, title, and thumbnail
constant. Change **only** the voice. Rotate one variant per comparable video,
then compare 7-day views, average percentage viewed, average view duration,
likes per 1,000 views, and subscriptions per 1,000 views. Do not declare a
winner from one upload; review at least five comparable videos per voice.

Example:

```sh
python3 pipeline/orchestrator.py --channel christian --topic "..." \
  --faith-storyboard examples/faith_nexus_matthew_6_34_storyboard.json \
  --faith-image-provider comfyui --faith-voice aria_clear
```
