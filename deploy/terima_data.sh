#!/usr/bin/env bash
# terima_data.sh — jalan di SERVER, dipanggil deploy\kirim_data.bat:
# pasang trade.db + analysis.json kiriman PC, gabung .env PC (kunci LLM) TANPA nimpa kunci akses server.
set -euo pipefail
APP=/opt/trade

sudo systemctl stop trade-api
if [ -f /tmp/trade_kirim.db ]; then mv /tmp/trade_kirim.db "$APP/data/trade.db"; fi
if [ -f /tmp/analysis.json ]; then mv /tmp/analysis.json "$APP/data/analysis.json"; fi

if [ -f /tmp/pc.env ]; then
  TOKEN_LINE=$(grep '^TRADE_API_TOKEN=' "$APP/.env" || true)
  tr -d '\r' < /tmp/pc.env | grep -v '^TRADE_API_TOKEN=' > "$APP/.env.new" || true
  if [ -n "$TOKEN_LINE" ]; then echo "$TOKEN_LINE" >> "$APP/.env.new"; fi
  mv "$APP/.env.new" "$APP/.env" && chmod 600 "$APP/.env" && rm -f /tmp/pc.env
fi
sudo systemctl start trade-api

echo "Data terpasang: trade.db $(du -h "$APP/data/trade.db" | cut -f1)"
