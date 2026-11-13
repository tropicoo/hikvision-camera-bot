#!/usr/bin/env bash
# Update the bot to the latest version from git and restart containers.
# Your configs (configs/*.json) and .env are kept as is.
#
# Usage: ./update.sh
set -euo pipefail

cd "$(dirname "$0")"

if docker compose version >/dev/null 2>&1; then
    COMPOSE="docker compose"
else
    COMPOSE="docker-compose"
fi

STASHED=0
if ! git diff --quiet || ! git diff --cached --quiet; then
    # e.g. edited volume paths in docker-compose.yml or TZ in .env
    echo ">>> Saving your local changes of tracked files (git stash)"
    git stash push -m "update.sh $(date '+%Y-%m-%d %H:%M:%S')"
    STASHED=1
fi

echo ">>> Pulling latest code"
git pull --ff-only

if [ "$STASHED" -eq 1 ]; then
    echo ">>> Restoring your local changes"
    if ! git stash pop; then
        echo "!!! Your local changes conflict with the update."
        echo "!!! Resolve conflicts in the files above (git status), then run: git stash drop"
        exit 1
    fi
fi

echo ">>> Building images (may take a few minutes on Raspberry Pi)"
$COMPOSE build --pull

echo ">>> Restarting containers"
$COMPOSE up -d --remove-orphans

echo ">>> Removing old unused images to free disk space"
docker image prune -f

echo ">>> Done. Status:"
$COMPOSE ps
echo "Logs: $COMPOSE logs -f --tail 200 hikvision-camera-bot"
