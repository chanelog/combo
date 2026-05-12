#!/bin/bash
# ============================================================
#   OGH-ZIV Multi-Server Installer (Enhanced)
#   Support: 1 Master + Unlimited Worker Server
#   GitHub : https://github.com/chanelog/combo
# ============================================================

R='\033[1;31m'; Y='\033[1;33m'; G='\033[1;32m'
C='\033[1;36m'; W='\033[1;37m'; N='\033[0m'
DIM='\033[2m'; B='\033[1m'

# ── Path ─────────────────────────────────────────────────────
BOT_STORE_CONF="/etc/zivpn/bot_store.conf"
BOT_PY="/usr/local/bin/zivpn-tgbot.py"
WORKER_PY="/usr/local/bin/zivpn-api-worker.py"
WORKER_CONF="/etc/zivpn/worker.conf"
BOT_SVC="/etc/systemd/system/zivpn-tgbot.service"
WORKER_SVC="/etc/systemd/system/zivpn-api-worker.service"
SERVERS_JSON="/etc/zivpn/servers.json"
SOCKSIP_WORKER_PY="/usr/local/bin/socksip-api-worker.py"
SOCKSIP_WORKER_SVC="/etc/systemd/system/socksip-api-worker.service"
SOCKSIP_WORKER_CONF="/etc/zivpn/socksip_worker.conf"
SOCKSIP_SERVERS_JSON="/etc/zivpn/socksip_servers.json"

# ── URL Script ────────────────────────────────────────────────
BOT_URL="https://github.com/chanelog/combo/raw/main/zivpn_bot_socksip.py"
WORKER_URL="https://raw.githubusercontent.com/chanelog/combo/main/zivpn_api_worker.py"

clear
echo ""
echo -e "${C}  ╔══════════════════════════════════════════════════════╗${N}"
echo -e "${C}  ║   🤖  OGH-ZIV MULTI-SERVER INSTALLER               ║${N}"
echo -e "${C}  ╠══════════════════════════════════════════════════════╣${N}"
echo -e "${C}  ║${N}  Support: 1 Master Bot + Unlimited Worker Server     ${C}║${N}"
echo -e "${C}  ╚══════════════════════════════════════════════════════╝${N}"
echo ""

# ── Cek root ─────────────────────────────────────────────────
[[ $EUID -ne 0 ]] && { echo -e "${R}  ✘ Jalankan sebagai root!${N}"; exit 1; }

# ── Pilih mode install ────────────────────────────────────────
echo -e "${C}  Pilih mode instalasi:${N}"
echo ""
echo -e "  ${W}[1]${N} 🖥  VPS Master   ${DIM}— Install Bot Telegram (satu saja)${N}"
echo -e "  ${W}[2]${N} 🔌  VPS Worker   ${DIM}— Install ZiVPN API Worker (VPS remote)${N}"
echo -e "  ${W}[3]${N} 📡  SocksIP Worker ${DIM}— Install SocksIP API Worker (VPS UDP)${N}"
echo -e "  ${W}[0]${N}     Keluar"
echo ""
read -rp "$(echo -e "  ${C}Pilih [0-3] : ${N}")" MODE

case "$MODE" in
  1) MODE_NAME="master" ;;
  2) MODE_NAME="worker" ;;
  3) MODE_NAME="socksip_worker" ;;
  0) echo -e "\n  ${Y}Dibatalkan.${N}\n"; exit 0 ;;
  *) echo -e "\n  ${R}✘ Pilihan tidak valid!${N}\n"; exit 1 ;;
esac

echo ""

# ════════════════════════════════════════════════════════════
#   MODE 1 — VPS MASTER (Bot Telegram)
# ════════════════════════════════════════════════════════════
install_master() {
  echo -e "${C}  ╔══════════════════════════════════════════════════════╗${N}"
  echo -e "${C}  ║   🖥  INSTALL BOT TELEGRAM — VPS MASTER              ║${N}"
  echo -e "${C}  ╚══════════════════════════════════════════════════════╝${N}"
  echo ""

  # ── Install dependencies ───────────────────────────────────
  echo -e "${Y}  ➜  Menginstall dependencies...${N}"
  apt-get update -qq 2>/dev/null
  apt-get install -y -qq python3 python3-pip curl wget 2>/dev/null
  echo -e "${G}  ✔  Dependencies selesai${N}"

  echo -e "${Y}  ➜  Menginstall python-telegram-bot...${N}"
  pip3 install python-telegram-bot --break-system-packages -q 2>/dev/null || \
  pip3 install python-telegram-bot -q 2>/dev/null

  echo -e "${Y}  ➜  Menginstall OCR (Tesseract)...${N}"
  apt-get install -y -qq tesseract-ocr tesseract-ocr-ind 2>/dev/null
  pip3 install pytesseract Pillow --break-system-packages -q 2>/dev/null || \
  pip3 install pytesseract Pillow -q 2>/dev/null

  # ── Download bot script ────────────────────────────────────
  echo -e "${Y}  ➜  Mengunduh bot script...${N}"
  mkdir -p /etc/zivpn
  curl -Ls "$BOT_URL" -o "$BOT_PY" 2>/dev/null || \
  wget -qO "$BOT_PY" "$BOT_URL" 2>/dev/null
  chmod +x "$BOT_PY" 2>/dev/null

  # Fix kompatibilitas Python lama
  sed -i '1s/^/from __future__ import annotations\n/' "$BOT_PY" 2>/dev/null
  echo -e "${G}  ✔  Script diunduh${N}"

  # ── Konfigurasi ────────────────────────────────────────────
  echo ""
  echo -e "${C}  ════════════════════════════════════════════════════${N}"
  echo -e "${C}  ⚙️   KONFIGURASI BOT${N}"
  echo -e "${C}  ════════════════════════════════════════════════════${N}"
  echo ""

  [[ -f "$BOT_STORE_CONF" ]] && source "$BOT_STORE_CONF" 2>/dev/null

  echo -ne "  ${C}Bot Token${N} (dari @BotFather) [${BOT_TOKEN:--}]: "
  read -r inp_token
  [[ -z "$inp_token" ]] && inp_token="${BOT_TOKEN:-}"
  [[ -z "$inp_token" ]] && { echo -e "${R}  ✘ Token tidak boleh kosong!${N}"; exit 1; }

  echo -ne "  ${C}No. DANA${N} [${DANA_NUMBER:-08xxxxxxxxxx}]: "
  read -r inp_dana_num
  [[ -z "$inp_dana_num" ]] && inp_dana_num="${DANA_NUMBER:-08xxxxxxxxxx}"

  echo -ne "  ${C}Nama Pemilik DANA${N} [${DANA_NAME:-Nama Pemilik}]: "
  read -r inp_dana_name
  [[ -z "$inp_dana_name" ]] && inp_dana_name="${DANA_NAME:-Nama Pemilik}"

  echo -ne "  ${C}Nama Brand${N} [${BRAND:-OGH-ZIV}]: "
  read -r inp_brand
  [[ -z "$inp_brand" ]] && inp_brand="${BRAND:-OGH-ZIV}"

  echo -ne "  ${C}Username Admin TG${N} [${ADMIN_TG:-@admin}]: "
  read -r inp_admin_tg
  [[ -z "$inp_admin_tg" ]] && inp_admin_tg="${ADMIN_TG:-@admin}"
  [[ "$inp_admin_tg" != @* ]] && inp_admin_tg="@${inp_admin_tg}"

  # ── Setup Server Remote (opsional, bisa tambah banyak) ─────
  echo ""
  echo -e "${C}  ════════════════════════════════════════════════════${N}"
  echo -e "${C}  🌍  KONFIGURASI SERVER REMOTE (Opsional)${N}"
  echo -e "${C}  ════════════════════════════════════════════════════${N}"
  echo -e "  ${DIM}Bisa dilewati dan ditambah nanti via bot Telegram.${N}"
  echo ""

  # Mulai dari server lokal (master)
  MY_IP=$(curl -s4 --max-time 5 ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
  MY_PORT=$(python3 -c "import json;d=json.load(open('/etc/zivpn/config.json'));print(d.get('listen',':5667').lstrip(':'))" 2>/dev/null || echo "5667")

  # Buat servers.json dengan server master dulu
  SERVERS_JSON_CONTENT=$(cat <<EOF
{
  "server1": {
    "label":   "🇮🇩 Indonesia",
    "enabled": true,
    "host":    "${MY_IP}",
    "port":    "${MY_PORT}",
    "api_url": "",
    "api_key": "",
    "note":    "Server Master — Lokal",
    "stock":   -1
  }
EOF
)

  # Loop tambah server remote
  SRV_INDEX=2
  while true; do
    echo -ne "  ${C}Tambah server remote ke-$((SRV_INDEX-1))?${N} [y/N]: "
    read -r add_more
    [[ "$add_more" != "y" && "$add_more" != "Y" ]] && break

    echo -ne "  ${C}Nama Region${N} (contoh: SG 01 / Japan / Germany): "
    read -r inp_srv_label
    [[ -z "$inp_srv_label" ]] && { echo -e "${R}  ✘ Nama tidak boleh kosong!${N}"; continue; }

    echo -ne "  ${C}IP/Domain VPS${N}: "
    read -r inp_srv_host
    [[ -z "$inp_srv_host" ]] && { echo -e "${R}  ✘ IP tidak boleh kosong!${N}"; continue; }

    echo -ne "  ${C}Port ZIVPN${N} [5667]: "
    read -r inp_srv_port
    [[ -z "$inp_srv_port" ]] && inp_srv_port="5667"

    echo -ne "  ${C}API URL${N} [http://${inp_srv_host}:8765]: "
    read -r inp_srv_api_url
    [[ -z "$inp_srv_api_url" ]] && inp_srv_api_url="http://${inp_srv_host}:8765"

    echo -ne "  ${C}API Key${N} (buat sendiri, catat untuk dipakai di VPS ini): "
    read -r inp_srv_api_key
    [[ -z "$inp_srv_api_key" ]] && inp_srv_api_key="ogh-ziv-$(openssl rand -hex 6)"
    echo -e "  ${G}  API Key: ${W}${inp_srv_api_key}${N}"

    # Buat server_id dari label
    SRV_ID=$(echo "$inp_srv_label" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/_/g' | sed 's/__*/_/g' | sed 's/^_//;s/_$//')_${SRV_INDEX}

    SERVERS_JSON_CONTENT+=",
  \"${SRV_ID}\": {
    \"label\":   \"${inp_srv_label}\",
    \"enabled\": true,
    \"host\":    \"${inp_srv_host}\",
    \"port\":    \"${inp_srv_port}\",
    \"api_url\": \"${inp_srv_api_url}\",
    \"api_key\": \"${inp_srv_api_key}\",
    \"note\":    \"Server Remote\",
    \"stock\":   -1
  }"

    echo -e "  ${G}  ✔ Server '${inp_srv_label}' ditambahkan.${N}"
    echo -e "  ${Y}  ⚠ Catat: install API Worker di VPS tersebut dengan API Key: ${W}${inp_srv_api_key}${N}"
    echo ""
    SRV_INDEX=$((SRV_INDEX + 1))
  done

  SERVERS_JSON_CONTENT+="
}"

  # ── Simpan konfigurasi ─────────────────────────────────────
  cat > "$BOT_STORE_CONF" <<EOF
# OGH-ZIV Bot Store Config
# Dibuat: $(date "+%Y-%m-%d %H:%M:%S")
BOT_TOKEN=${inp_token}
OWNER_ID=
ADMIN_IDS=
DANA_NUMBER=${inp_dana_num}
DANA_NAME=${inp_dana_name}
QRIS_ENABLED=0
BRAND=${inp_brand}
ADMIN_TG=${inp_admin_tg}
EOF

  echo "$SERVERS_JSON_CONTENT" > "$SERVERS_JSON"
  echo -e "${G}  ✔  Konfigurasi disimpan.${N}"

  # ── Buat systemd service ───────────────────────────────────
  cat > "$BOT_SVC" <<EOF
[Unit]
Description=OGH-ZIV Telegram Bot (Master)
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=root
ExecStart=/usr/bin/python3 ${BOT_PY}
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

  systemctl daemon-reload
  systemctl enable zivpn-tgbot.service &>/dev/null
  systemctl restart zivpn-tgbot.service
  sleep 2

  if systemctl is-active --quiet zivpn-tgbot; then
    STATUS="${G}● RUNNING${N}"
  else
    STATUS="${R}● FAILED — cek: journalctl -u zivpn-tgbot -n 20${N}"
  fi

  echo ""
  echo -e "${C}  ╔══════════════════════════════════════════════════════╗${N}"
  echo -e "${C}  ║   ✦  INSTALASI VPS MASTER SELESAI!                  ║${N}"
  echo -e "${C}  ╠══════════════════════════════════════════════════════╣${N}"
  printf  "  ${C}║${N}  %-20s : ${W}%s${N}\n" "Brand"    "${inp_brand}"
  printf  "  ${C}║${N}  %-20s : ${W}%s${N}\n" "No. DANA" "${inp_dana_num}"
  printf  "  ${C}║${N}  %-20s : ${W}%s${N}\n" "A/N DANA" "${inp_dana_name}"
  printf  "  ${C}║${N}  %-20s : ${W}%s${N}\n" "Admin TG" "${inp_admin_tg}"
  printf  "  ${C}║${N}  %-20s : ${W}%s${N}\n" "IP Master" "${MY_IP}"
  printf  "  ${C}║${N}  %-20s : ${W}%s server${N}\n" "Total Server" "$((SRV_INDEX-1))"
  echo -e "${C}  ╠══════════════════════════════════════════════════════╣${N}"
  echo -e "${C}  ║${N}  Status Bot : $STATUS"
  echo -e "${C}  ╠══════════════════════════════════════════════════════╣${N}"
  echo -e "${C}  ║${N}  Perintah :                                          ${C}║${N}"
  echo -e "${C}  ║${N}  ${DIM}systemctl status  zivpn-tgbot${N}                       ${C}║${N}"
  echo -e "${C}  ║${N}  ${DIM}systemctl restart zivpn-tgbot${N}                       ${C}║${N}"
  echo -e "${C}  ║${N}  ${DIM}journalctl -u zivpn-tgbot -f${N}                        ${C}║${N}"
  echo -e "${C}  ╚══════════════════════════════════════════════════════╝${N}"
  echo ""
  echo -e "  ${Y}⚠️  LANGKAH SELANJUTNYA:${N}"
  echo -e "  Untuk setiap VPS remote, login dan jalankan:"
  echo ""
  echo -e "  ${W}bash <(curl -Ls https://raw.githubusercontent.com/chanelog/combo/main/install-tgbot-multiserver.sh)${N}"
  echo ""
  echo -e "  Pilih ${W}[2] VPS Worker${N}, masukkan API Key yang sudah dicatat."
  echo ""
  echo -e "  ${G}✔  Buka Telegram → cari bot → kirim /start${N}"
  echo ""
}

# ════════════════════════════════════════════════════════════
#   MODE 2 — VPS WORKER (API Worker)
# ════════════════════════════════════════════════════════════
install_worker() {
  echo -e "${C}  ╔══════════════════════════════════════════════════════╗${N}"
  echo -e "${C}  ║   🔌  INSTALL API WORKER — VPS REMOTE                ║${N}"
  echo -e "${C}  ╚══════════════════════════════════════════════════════╝${N}"
  echo ""

  # ── Install dependencies ───────────────────────────────────
  echo -e "${Y}  ➜  Menginstall dependencies...${N}"
  apt-get update -qq 2>/dev/null
  apt-get install -y -qq python3 curl wget ufw 2>/dev/null
  echo -e "${G}  ✔  Dependencies selesai${N}"

  # ── Download worker script ─────────────────────────────────
  echo -e "${Y}  ➜  Mengunduh API Worker script...${N}"
  mkdir -p /etc/zivpn
  curl -Ls "$WORKER_URL" -o "$WORKER_PY" 2>/dev/null || \
  wget -qO "$WORKER_PY" "$WORKER_URL" 2>/dev/null
  chmod +x "$WORKER_PY" 2>/dev/null
  echo -e "${G}  ✔  Script diunduh${N}"

  # ── Konfigurasi ────────────────────────────────────────────
  echo ""
  echo -e "${C}  ════════════════════════════════════════════════════${N}"
  echo -e "${C}  ⚙️   KONFIGURASI API WORKER${N}"
  echo -e "${C}  ════════════════════════════════════════════════════${N}"
  echo -e "  ${DIM}API Key harus sama dengan yang dicatat saat install Master!${N}"
  echo ""

  [[ -f "$WORKER_CONF" ]] && source "$WORKER_CONF" 2>/dev/null

  echo -ne "  ${C}Nama Region VPS ini${N} (contoh: SG 01 / Japan): "
  read -r inp_region
  [[ -z "$inp_region" ]] && inp_region="Remote Server"

  echo -ne "  ${C}API Key${N} (dari VPS Master) [${API_KEY:--}]: "
  read -r inp_api_key
  [[ -z "$inp_api_key" ]] && inp_api_key="${API_KEY:-}"
  [[ -z "$inp_api_key" ]] && { echo -e "${R}  ✘ API Key tidak boleh kosong!${N}"; exit 1; }

  echo -ne "  ${C}Port API Worker${N} [8765]: "
  read -r inp_api_port
  [[ -z "$inp_api_port" ]] && inp_api_port="8765"

  # ── Simpan konfigurasi worker ──────────────────────────────
  cat > "$WORKER_CONF" <<EOF
# OGH-ZIV API Worker Config
# Region : ${inp_region}
# Dibuat : $(date "+%Y-%m-%d %H:%M:%S")
API_KEY=${inp_api_key}
API_PORT=${inp_api_port}
REGION=${inp_region}
EOF

  sed -i "s|API_KEY.*=.*\"GANTI_API_KEY_RAHASIA_INI\"|API_KEY     = \"${inp_api_key}\"|g" "$WORKER_PY"
  sed -i "s|LISTEN_PORT.*=.*8765|LISTEN_PORT = ${inp_api_port}|g" "$WORKER_PY"
  echo -e "${G}  ✔  Konfigurasi disimpan${N}"

  # ── Buka port firewall ─────────────────────────────────────
  echo -e "${Y}  ➜  Membuka port ${inp_api_port} di firewall...${N}"
  ufw allow "${inp_api_port}" &>/dev/null
  echo -e "${G}  ✔  Port ${inp_api_port} dibuka${N}"

  # ── Buat systemd service worker ────────────────────────────
  cat > "$WORKER_SVC" <<EOF
[Unit]
Description=OGH-ZIV API Worker (${inp_region})
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=root
ExecStart=/usr/bin/python3 ${WORKER_PY}
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

  systemctl daemon-reload
  systemctl enable zivpn-api-worker.service &>/dev/null
  systemctl restart zivpn-api-worker.service
  sleep 2

  if systemctl is-active --quiet zivpn-api-worker; then
    STATUS="${G}● RUNNING${N}"
  else
    STATUS="${R}● FAILED — cek: journalctl -u zivpn-api-worker -n 20${N}"
  fi

  MY_IP=$(curl -s4 --max-time 5 ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')

  echo ""
  echo -e "${C}  ╔══════════════════════════════════════════════════════╗${N}"
  echo -e "${C}  ║   ✦  INSTALASI API WORKER SELESAI!                  ║${N}"
  echo -e "${C}  ╠══════════════════════════════════════════════════════╣${N}"
  printf  "  ${C}║${N}  %-20s : ${W}%s${N}\n" "Region"       "${inp_region}"
  printf  "  ${C}║${N}  %-20s : ${W}%s${N}\n" "IP Publik"    "${MY_IP}"
  printf  "  ${C}║${N}  %-20s : ${W}%s${N}\n" "API Port"     "${inp_api_port}"
  printf  "  ${C}║${N}  %-20s : ${W}%s${N}\n" "API Key"      "${inp_api_key}"
  printf  "  ${C}║${N}  %-20s : ${W}http://%s:%s${N}\n" "API URL" "${MY_IP}" "${inp_api_port}"
  echo -e "${C}  ╠══════════════════════════════════════════════════════╣${N}"
  echo -e "${C}  ║${N}  Status Worker : $STATUS"
  echo -e "${C}  ╠══════════════════════════════════════════════════════╣${N}"
  echo -e "${C}  ║${N}  Perintah :                                          ${C}║${N}"
  echo -e "${C}  ║${N}  ${DIM}systemctl status  zivpn-api-worker${N}                 ${C}║${N}"
  echo -e "${C}  ║${N}  ${DIM}systemctl restart zivpn-api-worker${N}                 ${C}║${N}"
  echo -e "${C}  ║${N}  ${DIM}journalctl -u zivpn-api-worker -f${N}                  ${C}║${N}"
  echo -e "${C}  ╚══════════════════════════════════════════════════════╝${N}"
  echo ""
  echo -e "${Y}  ⚠️  DAFTARKAN DI BOT TELEGRAM (VPS Master):${N}"
  echo -e "  Admin Panel → Kelola Server → ➕ Tambah Server"
  echo ""
  echo -e "  Isi data berikut:"
  echo -e "  • Nama Region  : ${W}${inp_region}${N}"
  echo -e "  • Host/IP      : ${W}${MY_IP}${N}"
  echo -e "  • API URL      : ${W}http://${MY_IP}:${inp_api_port}${N}"
  echo -e "  • API Key      : ${W}${inp_api_key}${N}"
  echo -e "  • Aktifkan     : ✅"
  echo ""
  echo -e "  ${G}✔  VPS ${inp_region} siap menerima perintah dari Bot!${N}"
  echo ""
}

# ════════════════════════════════════════════════════════════
#   MODE 3 — VPS SOCKSIP WORKER (UDP Server)
# ════════════════════════════════════════════════════════════
install_socksip_worker() {
  echo -e "${C}  ╔══════════════════════════════════════════════════════╗${N}"
  echo -e "${C}  ║   📡  INSTALL SOCKSIP API WORKER — VPS UDP           ║${N}"
  echo -e "${C}  ╚══════════════════════════════════════════════════════╝${N}"
  echo ""

  # ── Install dependencies ───────────────────────────────────
  echo -e "${Y}  ➜  Menginstall dependencies...${N}"
  apt-get update -qq 2>/dev/null
  apt-get install -y -qq python3 curl wget ufw openssl 2>/dev/null
  echo -e "${G}  ✔  Dependencies selesai${N}"

  # ── Konfigurasi ────────────────────────────────────────────
  echo ""
  echo -e "${C}  ════════════════════════════════════════════════════${N}"
  echo -e "${C}  ⚙️   KONFIGURASI SOCKSIP API WORKER${N}"
  echo -e "${C}  ════════════════════════════════════════════════════${N}"
  echo -e "  ${DIM}API Key harus sama dengan api_key di socksip_servers.json VPS Master!${N}"
  echo ""

  [[ -f "$SOCKSIP_WORKER_CONF" ]] && source "$SOCKSIP_WORKER_CONF" 2>/dev/null

  echo -ne "  ${C}Nama Region VPS ini${N} (contoh: Indonesia UDP / SG UDP): "
  read -r inp_region
  [[ -z "$inp_region" ]] && inp_region="UDP Server"

  echo -ne "  ${C}API Key${N} (dari socksip_servers.json VPS Master) [${API_KEY:--}]: "
  read -r inp_api_key
  [[ -z "$inp_api_key" ]] && inp_api_key="${API_KEY:-}"
  [[ -z "$inp_api_key" ]] && inp_api_key="socksip-$(openssl rand -hex 8)"
  echo -e "  ${G}  API Key: ${W}${inp_api_key}${N}"

  echo -ne "  ${C}Port API Worker${N} [8766]: "
  read -r inp_api_port
  [[ -z "$inp_api_port" ]] && inp_api_port="8766"

  # ── Buat file socksip_api_worker.py langsung ───────────────
  echo -e "${Y}  ➜  Membuat SocksIP API Worker script...${N}"
  mkdir -p /etc/zivpn

  cat > "$SOCKSIP_WORKER_PY" << 'WORKER_SCRIPT'
#!/usr/bin/env python3
# ============================================================
#   SocksIP API Worker — VPS UDP (UDPserver)
#   Bot Telegram (VPS Master) mengirim perintah ke sini
#   via HTTP POST
# ============================================================

import json
import subprocess
import string
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler

_WIB_OFFSET = timezone(timedelta(hours=7))
def now_wib():
    return datetime.now(_WIB_OFFSET).replace(tzinfo=None)

# ── Konfigurasi (diisi otomatis saat install) ─────────────────
LISTEN_HOST = "0.0.0.0"
LISTEN_PORT = 8766
API_KEY     = "GANTI_API_KEY_SOCKSIP_INI"

# ── Helper ────────────────────────────────────────────────────
def get_ip():
    try:
        import urllib.request
        return urllib.request.urlopen("https://api.ipify.org", timeout=5).read().decode().strip()
    except:
        import socket
        return socket.gethostbyname(socket.gethostname())

def get_udp_port():
    for cfg in ["/etc/udpserver/config.json", "/etc/udp/config.json", "/root/udpserver/config.json"]:
        if Path(cfg).exists():
            try:
                data = json.loads(Path(cfg).read_text())
                return str(data.get("port", data.get("listen", "1-65535"))).lstrip(":")
            except: pass
    return "1-65535"

def hash_password(password):
    try:
        ver = subprocess.check_output(["openssl","version"], stderr=subprocess.DEVNULL).decode().split()[1]
        algo = "-6" if (ver.startswith("3") or ver.startswith("1.1.1")) else "-1"
        return subprocess.check_output(["openssl","passwd",algo,password], stderr=subprocess.DEVNULL).decode().strip()
    except:
        import crypt
        return crypt.crypt(password, crypt.mksalt(crypt.METHOD_SHA512))

def user_exists(username):
    return subprocess.run(["id", username], capture_output=True).returncode == 0

# ── Fungsi akun ───────────────────────────────────────────────
def create_account(username, password, days, maxlogin, note="-"):
    if user_exists(username):
        raise Exception(f"Username '{username}' sudah ada di sistem")
    exp_date = (now_wib() + timedelta(days=days)).strftime("%Y-%m-%d")
    pw_hash  = hash_password(password)
    cmd = ["useradd", "-M", "-s", "/bin/false", "-e", exp_date,
           "-K", f"PASS_MAX_DAYS={days}", "-p", pw_hash,
           "-c", f"{maxlogin},{password}", username]
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        raise Exception(f"useradd gagal: {r.stderr.decode().strip() or r.stdout.decode().strip()}")
    return {
        "username": username, "password": password, "exp": exp_date,
        "maxlogin": maxlogin, "ip": get_ip(), "host": get_ip(),
        "udp_port": get_udp_port(), "note": note,
    }

def delete_account(username):
    if not user_exists(username): return False
    subprocess.run(["pkill", "-u", username], capture_output=True)
    import time; time.sleep(0.5)
    return subprocess.run(["userdel","--force",username], capture_output=True).returncode == 0

def list_accounts():
    result = []
    try:
        for line in Path("/etc/passwd").read_text().splitlines():
            parts = line.split(":")
            if len(parts) < 7: continue
            username, shell, home = parts[0], parts[6], parts[5]
            if shell != "/bin/false" or not home.startswith("/home/"): continue
            if username in ("syslog","hwid","token"): continue
            exp_str, status = "?", "aktif"
            try:
                chage = subprocess.check_output(["chage","-l",username], stderr=subprocess.DEVNULL).decode()
                for cl in chage.splitlines():
                    if "Account expires" in cl:
                        exp_raw = cl.split(": ",1)[-1].strip()
                        if exp_raw.lower() not in ("never","password must be changed"):
                            try:
                                exp_dt  = datetime.strptime(exp_raw, "%b %d, %Y")
                                exp_str = exp_dt.strftime("%Y-%m-%d")
                                status  = "expired" if exp_dt < now_wib() else "aktif"
                            except: exp_str = exp_raw
                        else: exp_str = "Unlimited"
                        break
            except: pass
            result.append({"username": username, "exp": exp_str, "status": status})
    except: pass
    return result

def delete_expired():
    deleted = []
    for u in list_accounts():
        if u["status"] == "expired":
            if delete_account(u["username"]):
                deleted.append(u["username"])
    return deleted

def get_info():
    users  = list_accounts()
    aktif  = sum(1 for u in users if u["status"] == "aktif")
    return {
        "ok": True, "ip": get_ip(), "host": get_ip(),
        "udp_port": get_udp_port(),
        "total_akun": len(users), "aktif_akun": aktif,
        "expired": len(users) - aktif,
    }

# ── HTTP Handler ──────────────────────────────────────────────
class SocksIPHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"[{now_wib().strftime('%H:%M:%S')}] {args[0]} {args[1]}")

    def do_POST(self):
        if self.path != "/api":
            self._send(404, {"ok": False, "error": "Not found"}); return
        try:
            length = int(self.headers.get("Content-Length", 0))
            data   = json.loads(self.rfile.read(length))
        except:
            self._send(400, {"ok": False, "error": "Invalid JSON"}); return
        if data.get("key") != API_KEY:
            self._send(403, {"ok": False, "error": "API key salah"}); return
        action = data.get("action", "")
        print(f"[API] action={action}")
        try:
            if action == "create_account":
                akun = create_account(
                    data["username"], data["password"],
                    int(data.get("days", 30)),
                    int(data.get("maxlogin", 2)),
                    data.get("note", "-")
                )
                self._send(200, {"ok": True, "akun": akun})
            elif action == "delete_account":
                ok = delete_account(data["username"])
                self._send(200, {"ok": ok, "error": "" if ok else "User tidak ditemukan"})
            elif action == "list_accounts":
                self._send(200, {"ok": True, "accounts": list_accounts()})
            elif action == "delete_expired":
                deleted = delete_expired()
                self._send(200, {"ok": True, "count": len(deleted), "deleted": deleted})
            elif action == "get_info":
                self._send(200, get_info())
            else:
                self._send(400, {"ok": False, "error": f"Action tidak dikenal: {action}"})
        except Exception as e:
            self._send(500, {"ok": False, "error": str(e)})

    def _send(self, code, data):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

if __name__ == "__main__":
    print(f"""
╔══════════════════════════════════════════════════╗
║   SocksIP API Worker — VPS UDP                   ║
╠══════════════════════════════════════════════════╣
║  Listen   : {LISTEN_HOST}:{LISTEN_PORT}
║  UDP Port : {get_udp_port()}
║  IP       : {get_ip()}
║  API Key  : {API_KEY[:6]}... (rahasia!)
╚══════════════════════════════════════════════════╝
""")
    srv = HTTPServer((LISTEN_HOST, LISTEN_PORT), SocksIPHandler)
    print(f"[INFO] SocksIP API Worker berjalan di port {LISTEN_PORT}...")
    srv.serve_forever()
WORKER_SCRIPT

  chmod +x "$SOCKSIP_WORKER_PY"

  # ── Isi API Key & Port dari input ──────────────────────────
  sed -i "s|API_KEY     = "GANTI_API_KEY_SOCKSIP_INI"|API_KEY     = "${inp_api_key}"|g" "$SOCKSIP_WORKER_PY"
  sed -i "s|LISTEN_PORT = 8766|LISTEN_PORT = ${inp_api_port}|g" "$SOCKSIP_WORKER_PY"
  echo -e "${G}  ✔  Script worker dibuat${N}"

  # ── Simpan konfigurasi worker ──────────────────────────────
  cat > "$SOCKSIP_WORKER_CONF" << EOF
# SocksIP API Worker Config
# Region : ${inp_region}
# Dibuat : $(date "+%Y-%m-%d %H:%M:%S")
API_KEY=${inp_api_key}
API_PORT=${inp_api_port}
REGION=${inp_region}
EOF

  # ── Buka port firewall ─────────────────────────────────────
  echo -e "${Y}  ➜  Membuka port ${inp_api_port} di firewall...${N}"
  ufw allow "${inp_api_port}" &>/dev/null
  echo -e "${G}  ✔  Port ${inp_api_port} dibuka${N}"

  # ── Buat systemd service ───────────────────────────────────
  cat > "$SOCKSIP_WORKER_SVC" << EOF
[Unit]
Description=SocksIP API Worker (${inp_region})
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=root
ExecStart=/usr/bin/python3 ${SOCKSIP_WORKER_PY}
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

  systemctl daemon-reload
  systemctl enable socksip-api-worker.service &>/dev/null
  systemctl restart socksip-api-worker.service
  sleep 2

  if systemctl is-active --quiet socksip-api-worker; then
    STATUS="${G}● RUNNING${N}"
  else
    STATUS="${R}● FAILED — cek: journalctl -u socksip-api-worker -n 20${N}"
  fi

  MY_IP=$(curl -s4 --max-time 5 ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')

  echo ""
  echo -e "${C}  ╔══════════════════════════════════════════════════════╗${N}"
  echo -e "${C}  ║   ✦  INSTALASI SOCKSIP WORKER SELESAI!              ║${N}"
  echo -e "${C}  ╠══════════════════════════════════════════════════════╣${N}"
  printf  "  ${C}║${N}  %-20s : ${W}%s${N}
" "Region"    "${inp_region}"
  printf  "  ${C}║${N}  %-20s : ${W}%s${N}
" "IP Publik" "${MY_IP}"
  printf  "  ${C}║${N}  %-20s : ${W}%s${N}
" "API Port"  "${inp_api_port}"
  printf  "  ${C}║${N}  %-20s : ${W}%s${N}
" "API Key"   "${inp_api_key}"
  printf  "  ${C}║${N}  %-20s : ${W}http://%s:%s${N}
" "API URL" "${MY_IP}" "${inp_api_port}"
  echo -e "${C}  ╠══════════════════════════════════════════════════════╣${N}"
  echo -e "${C}  ║${N}  Status Worker : $STATUS"
  echo -e "${C}  ╠══════════════════════════════════════════════════════╣${N}"
  echo -e "${C}  ║${N}  Perintah :                                          ${C}║${N}"
  echo -e "${C}  ║${N}  ${DIM}systemctl status  socksip-api-worker${N}               ${C}║${N}"
  echo -e "${C}  ║${N}  ${DIM}systemctl restart socksip-api-worker${N}               ${C}║${N}"
  echo -e "${C}  ║${N}  ${DIM}journalctl -u socksip-api-worker -f${N}                ${C}║${N}"
  echo -e "${C}  ╚══════════════════════════════════════════════════════╝${N}"
  echo ""
  echo -e "${Y}  ⚠️  DAFTARKAN DI BOT TELEGRAM (VPS Master):${N}"
  echo -e "  Edit file: /etc/zivpn/socksip_servers.json"
  echo ""
  echo -e "  Isi dengan data berikut:"
  echo -e "  • host      : ${W}${MY_IP}${N}"
  echo -e "  • api_url   : ${W}http://${MY_IP}:${inp_api_port}${N}"
  echo -e "  • api_key   : ${W}${inp_api_key}${N}"
  echo -e "  • is_local  : ${W}false${N}"
  echo -e "  • enabled   : ${W}true${N}"
  echo ""
  echo -e "  ${G}✔  VPS ${inp_region} siap menerima perintah dari Bot!${N}"
  echo ""
}

# ════════════════════════════════════════════════════════════
#   JALANKAN SESUAI PILIHAN
# ════════════════════════════════════════════════════════════
case "$MODE_NAME" in
  master) install_master ;;
  worker) install_worker ;;
  socksip_worker) install_socksip_worker ;;
esac
