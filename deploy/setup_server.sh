#!/usr/bin/env bash
# setup_server.sh — pasang Trade IDX di VPS Ubuntu yang UDAH ada aplikasi lain di nginx.
# Aman buat aplikasi lain di server itu:
#   - jalan sebagai user sendiri `trade` (bukan root), folder /opt/trade, port DALAM 127.0.0.1:8000
#   - cuma NAMBAH 1 site nginx (site lain gak disentuh; dicek `nginx -t` dulu sebelum reload)
#   - zona waktu WIB cuma buat service Trade (zona waktu server gak diubah)
#   - firewall (ufw) gak diubah
#   - auto-update: tiap 15 menit narik kode terbaru dari GitHub (gak butuh SSH)
#
# Jalanin SEKALI sebagai root (Alibaba: tab Command Assistant, Timeout 1800 detik):
#   curl -fsSL https://raw.githubusercontent.com/nurfznhanif/Trade/main/deploy/setup_server.sh | bash -s -- "<kunci publik SSH PC>"
# Argumen ke-2 opsional: domain sendiri. Default: <ip-publik>.sslip.io
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo "[!] Jalanin sebagai root"; exit 1; }

PUBKEY=${1:-}
APP=/opt/trade
REPO=https://github.com/nurfznhanif/Trade.git
U=trade
PORT=8000
IP=$(curl -fsS https://api.ipify.org)
DOMAIN=${2:-${IP//./-}.sslip.io}
as_trade() { sudo -u "$U" -H "$@"; }

if ss -tln | awk '{print $4}' | grep -qE "[:.]$PORT\$" && ! systemctl is-active -q trade-api; then
  echo "[!] Port $PORT udah dipakai aplikasi lain. Batal (gak ada yang diubah)."; exit 1
fi

echo "==> [1/7] Paket sistem"
apt-get update -y -q
DEBIAN_FRONTEND=noninteractive apt-get install -y -q python3-venv python3-pip git sqlite3
command -v certbot >/dev/null || DEBIAN_FRONTEND=noninteractive apt-get install -y -q certbot python3-certbot-nginx

echo "==> [2/7] User '$U' (tanpa password, cuma boleh restart service-nya sendiri)"
id "$U" >/dev/null 2>&1 || useradd --create-home --shell /bin/bash "$U"
usermod -p '*' "$U"   # gak bisa login pakai password; login SSH cuma pakai kunci
if [ -n "$PUBKEY" ]; then
  install -d -m 700 -o "$U" -g "$U" "/home/$U/.ssh"
  touch "/home/$U/.ssh/authorized_keys"
  grep -qF "$PUBKEY" "/home/$U/.ssh/authorized_keys" || echo "$PUBKEY" >> "/home/$U/.ssh/authorized_keys"
  chown "$U:$U" "/home/$U/.ssh/authorized_keys" && chmod 600 "/home/$U/.ssh/authorized_keys"
fi
cat > /etc/sudoers.d/trade <<EOF
$U ALL=(root) NOPASSWD: /usr/bin/systemctl restart trade-api, /usr/bin/systemctl stop trade-api, /usr/bin/systemctl start trade-api
EOF
chmod 440 /etc/sudoers.d/trade && visudo -cqf /etc/sudoers.d/trade

echo "==> [3/7] Kode dari GitHub + Python venv (beberapa menit)"
install -d -o "$U" -g "$U" "$APP"
if [ -d "$APP/.git" ]; then as_trade git -C "$APP" pull -q --ff-only; else as_trade git clone -q "$REPO" "$APP"; fi
as_trade mkdir -p "$APP/data"
[ -d "$APP/.venv" ] || as_trade python3 -m venv "$APP/.venv"
as_trade "$APP/.venv/bin/pip" install -q --upgrade pip
as_trade "$APP/.venv/bin/pip" install -q -r "$APP/requirements.txt"

echo "==> [4/7] Kunci akses"
as_trade touch "$APP/.env" && chmod 600 "$APP/.env"
grep -q '^TRADE_API_TOKEN=' "$APP/.env" || echo "TRADE_API_TOKEN=$(openssl rand -hex 24)" >> "$APP/.env"
TOKEN=$(grep '^TRADE_API_TOKEN=' "$APP/.env" | cut -d= -f2)

echo "==> [5/7] Service: backend 24 jam + jadwal harian + auto-update"
cat > /etc/systemd/system/trade-api.service <<EOF
[Unit]
Description=Trade IDX API
After=network-online.target

[Service]
User=$U
WorkingDirectory=$APP
Environment=TZ=Asia/Jakarta
ExecStart=$APP/.venv/bin/uvicorn backend.api:app --host 127.0.0.1 --port $PORT
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
cat > /etc/systemd/system/trade-daily.service <<EOF
[Unit]
Description=Trade IDX refresh data harian + analisa LLM

[Service]
Type=oneshot
User=$U
WorkingDirectory=$APP
Environment=TZ=Asia/Jakarta
ExecStart=$APP/.venv/bin/python scripts/daily.py
ExecStart=$APP/.venv/bin/python scripts/auto_analisa.py --out $APP/data/analysis.json
EOF
cat > /etc/systemd/system/trade-daily.timer <<EOF
[Unit]
Description=Jadwal refresh data Trade IDX (Senin-Jumat 17:30 WIB, habis bursa tutup)

[Timer]
OnCalendar=Mon..Fri 17:30 Asia/Jakarta
Persistent=true

[Install]
WantedBy=timers.target
EOF
cat > /etc/systemd/system/trade-update.service <<EOF
[Unit]
Description=Trade IDX tarik kode terbaru dari GitHub

[Service]
Type=oneshot
User=$U
WorkingDirectory=$APP
ExecStart=/bin/bash $APP/deploy/auto_update.sh
EOF
cat > /etc/systemd/system/trade-update.timer <<EOF
[Unit]
Description=Cek update kode Trade IDX tiap 15 menit

[Timer]
OnBootSec=5min
OnUnitActiveSec=15min

[Install]
WantedBy=timers.target
EOF
systemctl daemon-reload
systemctl enable -q --now trade-api trade-daily.timer trade-update.timer
systemctl restart trade-api

echo "==> [6/7] Site nginx baru: $DOMAIN (site lain gak disentuh)"
SITE=/etc/nginx/sites-available/trade
if [ ! -f "$SITE" ]; then
  cat > "$SITE" <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN;
    location / {
        proxy_pass http://127.0.0.1:$PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 600s;   # POST /analisa bisa 1-2 menit
    }
}
EOF
fi
ln -sf "$SITE" /etc/nginx/sites-enabled/trade
if ! nginx -t 2>/dev/null; then
  rm -f /etc/nginx/sites-enabled/trade
  echo "[!] Config nginx gak valid -> site Trade DIBATALKAN, nginx gak di-reload (Dashboard aman)."; exit 1
fi
systemctl reload nginx

echo "==> [7/7] HTTPS (certbot, cuma buat $DOMAIN)"
SCHEME=https
certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --register-unsafely-without-email --redirect -q \
  || { SCHEME=http; echo "[!] Sertifikat HTTPS gagal (kuota sslip.io kadang habis). Sementara pakai http://, jalanin ulang script nanti."; }

sleep 2
echo
echo "============================================================"
echo "  SERVER TRADE JADI"
echo "  Alamat Server : $SCHEME://$DOMAIN"
echo "  Kunci Akses   : $TOKEN"
echo "  Cek backend   : $(curl -fsS http://127.0.0.1:$PORT/health || echo 'belum nyaut')"
echo "============================================================"
