# Channel-specific YouTube publishing

`python3 publishing/upload.py --channel christian --health` performs only
read-only checks. Publishing is impossible unless `--publish` is passed.

## Required one-time setup

1. Authorize each YouTube channel separately:

   ```sh
   python3 -m youtube.auth authorize --channel faithnexus
   python3 -m youtube.auth authorize --channel soccer
   ```

2. Configure Postiz Cloud or a self-hosted Postiz Public API. Create a Public
   API key, connect each YouTube channel in Postiz, list integrations, and put
   the two YouTube integration IDs in the protected process environment:

   ```sh
   POSTIZ_BASE_URL=https://api.postiz.com/public/v1
   POSTIZ_API_KEY=...
   SMAGENT_CHRISTIAN_POSTIZ_INTEGRATION_ID=...
   SMAGENT_SOCCER_POSTIZ_INTEGRATION_ID=...
   ```

3. Open each authenticated YouTube Studio channel in the CDP-controlled
   Chromium profile and set the matching immutable channel IDs:

   ```sh
   SMAGENT_STUDIO_CDP_URL=http://127.0.0.1:9222
   SMAGENT_CHRISTIAN_STUDIO_CHANNEL_ID=UC...
   SMAGENT_SOCCER_STUDIO_CHANNEL_ID=UC...
   ```

The Postiz flow follows the official sequence: upload media to `/upload`, then
create a YouTube post through `/posts` using the connected integration. The
router keeps channel IDs separate and never accepts an arbitrary integration
ID on a command line.

## Safe operation

```sh
# Inspect all providers without publishing.
python3 publishing/upload.py --channel christian --health

# Validate route choice and file/title without publishing.
python3 publishing/upload.py --channel christian --video /path/video.mp4 \
  --title "When Tomorrow Feels Heavy" --privacy private

# Explicitly permit a publish after approval.
python3 publishing/upload.py --channel christian --video /path/video.mp4 \
  --title "When Tomorrow Feels Heavy" --privacy private --publish
```

The router selects YouTube API, then Postiz, then Studio only when that
channel's provider health check passes. Upload attempts are recorded in
`~/.local/state/smagent/publish-ledger.json`; a started or published video
cannot be blindly retried.
