# Release 2.0.1

No config changes are needed: existing `config.json`, `livestream_templates.json`,
`encoding_templates.json` and `.env` work as is.

## New

1. `/menu` - control cameras with inline buttons (photo, full photo, video, rewound video,
   alerts, motion detection, infrared). Buttons respect `command_sections_visibility`.
2. `/status` - uptime, CPU temperature, load, RAM, free disk space for used storages and
   started services per camera.
3. Alerts to `alert_users` when free disk space is low (< 10% or < 2 GiB) and when CPU
   temperature is >= 80°C. Each alert is sent once and repeated only after recovery.
4. Bot commands are shown in Telegram "Menu" button.
5. `update.sh` - one command update: `git pull`, rebuild, restart, prune old images.

## Fixes

1. Passwords with special characters (`@ : / # % " $ { }` etc.) in camera credentials no longer
   break RTSP URLs and ffmpeg commands.
2. ffmpeg is started without a shell: config values can't be interpreted as shell commands.
3. Passwords are masked in logs (`rtsp://user:***@host`, `-password "***"`).
4. On video/thumbnail timeout the bot could send `SIGINT` to its own process group, i.e. stop
   itself. Now only the ffmpeg process is signalled, and it is killed with `SIGKILL` if it
   doesn't exit in 10 seconds (no more zombie/hanging ffmpeg).
5. Quick `alert_off` -> `alert_on` started a second alert monitoring task, so every alert was
   sent twice. The old task is now cancelled.
6. Alert from an NVR channel which is not in the config (or is hidden) broke and reconnected
   the whole NVR alert stream. Such alerts are now skipped.
7. Background tasks could be garbage collected by Python before they finished. Now strong
   references are kept.
8. Reconnects to cameras/NVR and stream restarts use exponential backoff (0.5s -> 30s) instead
   of retrying every 0.1-0.5 seconds forever, which flooded logs and loaded CPU when a camera
   was offline.
9. ffmpeg output reader could flood logs with empty lines; now it logs only non-empty lines.
10. Graceful shutdown on `docker stop`: ffmpeg gets `SIGINT` so DVR segment files are finalized
    (not corrupted), then Telegram client is stopped.
11. DVR "file is still written" check reads `/proc` instead of running `lsof` for the whole
    system every time (much lighter on Raspberry Pi). `lsof` is used as a fallback.
12. Fixed a circular import that broke importing configs in some import orders.

## Docker

1. Base image `python:3.13-alpine3.22` (Alpine 3.20 reached end of life), ffmpeg 6.1 as before.
2. Docker healthcheck (heartbeat file written by the bot).
3. `init: true`, `stop_grace_period: 30s`, log rotation (3 x 10 MB) for both containers.
4. `/tmp` of the bot container is in RAM (`tmpfs`, 512 MB) - video clips are recorded there
   before sending, which reduces SD card wear.
5. Image is built and checked for both `amd64` and `arm64` (Raspberry Pi) in CI.

## Development

1. Tests (`pytest`), GitHub Actions CI: ruff lint + format, tests, Docker build for amd64/arm64.
2. Dependabot for `uv`, Docker and GitHub Actions.
3. Fixed all ruff findings.
