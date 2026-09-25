#!/usr/bin/env bash
# uninstall_server.sh — COPOT Trade dari server. Aplikasi lain (Dashboard, MySQL, site nginx lain) gak disentuh.
# Database Trade (jurnal dll) di-backup dulu ke /root/trade-backup-<tanggal>.db sebelum folder dihapus.
# Jalanin sebagai root:
#   curl -fsSL https://raw.githubusercontent.com/nurfznhanif/Trade/main/deploy/uninstall_server.sh | sudo bash
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo "[!] Jalanin sebagai root (pakai sudo)"; exit 1; }

systemctl disable --now trade-api trade-daily.timer trade-update.timer 2>/dev/null || true
rm -f /etc/systemd/system/trade-api.service /etc/systemd/system/trade-daily.service \
      /etc/systemd/system/trade-daily.timer /etc/systemd/system/trade-update.service \
      /etc/systemd/system/trade-update.timer
systemctl daemon-reload

if [ -e /etc/nginx/sites-enabled/trade ] || [ -e /etc/nginx/sites-available/trade ]; then
  rm -f /etc/nginx/sites-enabled/trade /etc/nginx/sites-available/trade
  nginx -t && systemctl reload nginx
fi

if [ -f /opt/trade/data/trade.db ]; then
  BK=/root/trade-backup-$(date +%Y%m%d-%H%M).db
  cp /opt/trade/data/trade.db "$BK" && echo "Backup database Trade: $BK"
fi
rm -f /etc/sudoers.d/trade
userdel -r trade 2>/dev/null || true
rm -rf /opt/trade

echo "Trade udah dicopot. Sertifikat HTTPS-nya (kalau ada) gak ganggu; hapus pakai: certbot delete"
