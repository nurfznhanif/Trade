#!/usr/bin/env bash
# auto_update.sh — dijalanin timer trade-update tiap 15 menit (user trade).
# Ada commit baru di GitHub main -> tarik, install library kalau requirements berubah, restart backend.
set -euo pipefail
cd /opt/trade
git fetch -q origin main
[ "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)" ] && exit 0
OLD_REQ=$(git rev-parse HEAD:requirements.txt)
git merge -q --ff-only origin/main
[ "$OLD_REQ" = "$(git rev-parse HEAD:requirements.txt)" ] || .venv/bin/pip install -q -r requirements.txt
sudo systemctl restart trade-api
echo "Trade diupdate ke $(git rev-parse --short HEAD)"
