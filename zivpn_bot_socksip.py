from __future__ import annotations
#!/usr/bin/env python3
# ============================================================
#   OGH-ZIV PREMIUM — Telegram Bot Auto Create Akun
#   Terintegrasi dengan OGH-ZIV Panel (ogh-ziv.sh)
#   Pembayaran via DANA / QRIS — Cek Screenshot Otomatis
#   GitHub: https://github.com/chanelog/Cek-bot
#
#   SISTEM ADMIN:
#   - OWNER (Admin Utama) : Akses penuh semua fitur
#                           Atur pembayaran, kelola admin,
#                           pengaturan bot, dll
#   - RESELLER (Admin Biasa) : Hanya buat akun gratis,
#                              hapus akun, lihat list & statistik
# ============================================================

import os
import re
import json
import logging
import subprocess
import random
import string
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone

# ── Timezone Indonesia (WIB = UTC+7, tidak perlu library pytz) ──
_WIB_OFFSET = timezone(timedelta(hours=7))

def now_wib() -> datetime:
    """Waktu sekarang dalam WIB (UTC+7) tanpa library eksternal."""
    return datetime.now(_WIB_OFFSET).replace(tzinfo=None)
from pathlib import Path
from typing import Optional, Tuple

# ── Telegram Bot Library ─────────────────────────────────────
try:
    from telegram import (
        Update, InlineKeyboardButton, InlineKeyboardMarkup,
        ReplyKeyboardMarkup, KeyboardButton
    )
    from telegram.ext import (
        ApplicationBuilder, CommandHandler, MessageHandler,
        CallbackQueryHandler, ContextTypes, filters,
        ConversationHandler
    )
except ImportError:
    print("Install dulu: pip3 install python-telegram-bot --break-system-packages")
    exit(1)

# ── OCR Library ───────────────────────────────────────────────
try:
    from PIL import Image
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    print("[WARN] pytesseract/Pillow tidak tersedia. OCR tidak aktif.")

# ============================================================
#  KONFIGURASI — Lokasi file
# ============================================================
CONFIG_FILE = "/etc/zivpn/bot_store.conf"
USERS_DB    = "/etc/zivpn/users.db"
DOMAIN_CONF = "/etc/zivpn/domain.conf"
BOT_CONF    = "/etc/zivpn/bot.conf"
MLDB        = "/etc/zivpn/maxlogin.db"
QRIS_IMG    = "/etc/zivpn/qris.jpg"

# ============================================================
#  KONFIGURASI MULTI-SERVER (INDO & SG)
# ============================================================
SERVERS_FILE = "/etc/zivpn/servers.json"

# Template field untuk setiap server
SERVER_TEMPLATE = {
    "label":   "",
    "enabled": False,
    "host":    "",
    "port":    "5667",
    "api_url": "",
    "api_key": "",
    "note":    "",
    "stock":   -1,
}

# Server default (hanya dibuat jika servers.json belum ada)
DEFAULT_SERVERS = {
    "server1": {
        "label":   "🇮🇩 Indonesia",
        "enabled": True,
        "host":    "",
        "port":    "5667",
        "api_url": "",
        "api_key": "",
        "note":    "Server Indonesia (Lokal)",
        "stock":   -1,
    },
}

def load_servers() -> dict:
    p = Path(SERVERS_FILE)
    if p.exists():
        try:
            data = json.loads(p.read_text())
            if isinstance(data, dict) and data:
                for srv_id in data:
                    for k, v in SERVER_TEMPLATE.items():
                        data[srv_id].setdefault(k, v)
                return data
        except: pass
    Path(SERVERS_FILE).parent.mkdir(parents=True, exist_ok=True)
    Path(SERVERS_FILE).write_text(json.dumps(DEFAULT_SERVERS, indent=2))
    return DEFAULT_SERVERS.copy()

def make_server_id(label: str) -> str:
    """Buat server_id unik dari label. Contoh: 'SG 01' -> 'sg_01_1234'"""
    import time as _time
    base = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")[:20]
    suffix = str(int(_time.time()))[-4:]
    return f"{base}_{suffix}" if base else f"srv_{suffix}"

def save_servers(data: dict):
    Path(SERVERS_FILE).parent.mkdir(parents=True, exist_ok=True)
    Path(SERVERS_FILE).write_text(json.dumps(data, indent=2))

def get_active_servers() -> dict:
    """Kembalikan hanya server yang enabled dan ada host-nya."""
    srvs = load_servers()
    return {k: v for k, v in srvs.items() if v.get("enabled") and v.get("host")}

def get_server_info(srv_id: str) -> dict:
    return load_servers().get(srv_id, {})

# ── API ke VPS lain (SG atau server remote) ───────────────────
def api_call_remote(srv_id: str, action: str, payload: dict) -> dict:
    """
    Kirim perintah ke VPS remote via HTTP API sederhana.
    VPS remote harus menjalankan zivpn_api_worker.py

    action: create_account | delete_account | list_accounts | get_info | restart_service
    """
    srv = get_server_info(srv_id)
    api_url = srv.get("api_url", "").rstrip("/")
    api_key = srv.get("api_key", "")
    if not api_url:
        return {"ok": False, "error": "api_url tidak dikonfigurasi"}
    try:
        body = json.dumps({"action": action, "key": api_key, **payload}).encode()
        req  = urllib.request.Request(
            f"{api_url}/api",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"ok": False, "error": str(e)}

def is_local_server(srv_id: str) -> bool:
    """Cek apakah server ini adalah VPS lokal (bot berjalan di sini)."""
    srv = get_server_info(srv_id)
    return not srv.get("api_url", "").strip()

# ── Buat akun di server tertentu ─────────────────────────────
def create_account_on_server(srv_id: str, username: str, password: str,
                              days: int, kuota: int, maxlogin: int, note: str = "-") -> dict:
    if is_local_server(srv_id):
        return create_account(username, password, days, kuota, maxlogin, note)
    else:
        result = api_call_remote(srv_id, "create_account", {
            "username": username, "password": password,
            "days": days, "kuota": kuota, "maxlogin": maxlogin, "note": note
        })
        if result.get("ok"):
            return result.get("akun", {})
        else:
            raise Exception(result.get("error", "Gagal membuat akun di server remote"))

def delete_account_on_server(srv_id: str, username: str) -> bool:
    if is_local_server(srv_id):
        return delete_account(username)
    else:
        result = api_call_remote(srv_id, "delete_account", {"username": username})
        return result.get("ok", False)

def get_server_stat_remote(srv_id: str) -> dict:
    """Ambil statistik dari server remote."""
    result = api_call_remote(srv_id, "get_info", {})
    if result.get("ok"):
        return result
    return {}

# ── Ikon status server ────────────────────────────────────────
def server_status_icon(srv: dict) -> str:
    if not srv.get("enabled"):   return "⛔"
    if not srv.get("host"):      return "⚙️"
    stock = srv.get("stock", -1)
    if stock == 0:               return "🔴"
    return "🟢"

def server_stock_text(srv: dict) -> str:
    stock = srv.get("stock", -1)
    if stock == -1: return "Unlimited"
    if stock == 0:  return "Habis"
    return f"{stock} slot"

PAKET = {
    "1": {"nama": "7 Hari",  "hari": 7,  "harga": 3000,  "kuota": 0, "maxlogin": 2},
    "2": {"nama": "15 Hari", "hari": 15, "harga": 6000,  "kuota": 0, "maxlogin": 2},
    "3": {"nama": "30 Hari", "hari": 30, "harga": 10000, "kuota": 0, "maxlogin": 2},
}

TRIAL_MENIT = 120

logging.basicConfig(format="%(asctime)s [%(levelname)s] %(message)s", level=logging.INFO)
log = logging.getLogger(__name__)

# ============================================================
#  LOAD & SAVE KONFIGURASI
# ============================================================
def load_config() -> dict:
    cfg = {
        "BOT_TOKEN":    "",
        "OWNER_ID":     0,        # ← Admin Utama / Owner (1 orang)
        "ADMIN_IDS":    [],       # ← Semua admin (owner + reseller)
        "DANA_NUMBER":  "08xxxxxxxxxx",
        "DANA_NAME":    "Nama Pemilik",
        "QRIS_ENABLED": "0",
        "BRAND":        "OGH-ZIV",
        "ADMIN_TG":     "@admin",
    }
    if Path(CONFIG_FILE).exists():
        for line in Path(CONFIG_FILE).read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, _, v = line.partition("=")
                k = k.strip(); v = v.strip().strip('"').strip("'")
                if k == "BOT_TOKEN":
                    if v and v != "ISI_TOKEN_BOT_TELEGRAM_DI_SINI":
                        cfg["BOT_TOKEN"] = v
                if k == "OWNER_ID":
                    # Hanya parse jika angka valid, skip jika kosong/placeholder
                    v_clean = v.strip()
                    if v_clean and v_clean.isdigit():
                        cfg["OWNER_ID"] = int(v_clean)
                if k == "ADMIN_IDS":
                    try:
                        ids = [int(x.strip()) for x in v.split(",") if x.strip().isdigit()]
                        if ids:
                            cfg["ADMIN_IDS"] = ids
                    except: pass
                if k == "DANA_NUMBER":  cfg["DANA_NUMBER"]  = v
                if k == "DANA_NAME":    cfg["DANA_NAME"]    = v
                if k == "QRIS_ENABLED": cfg["QRIS_ENABLED"] = v
                if k == "BRAND":        cfg["BRAND"]        = v
                if k == "ADMIN_TG":     cfg["ADMIN_TG"]     = v

    # Pastikan owner selalu ada di ADMIN_IDS
    if cfg["OWNER_ID"] and cfg["OWNER_ID"] not in cfg["ADMIN_IDS"]:
        cfg["ADMIN_IDS"].insert(0, cfg["OWNER_ID"])

    # Fallback token
    if not cfg["BOT_TOKEN"] and Path(BOT_CONF).exists():
        for line in Path(BOT_CONF).read_text().splitlines():
            if line.startswith("BOT_TOKEN="):
                cfg["BOT_TOKEN"] = line.split("=", 1)[1].strip()
                break
    return cfg

CFG = load_config()

def save_config_key(key: str, value: str):
    """Update satu key di config file dan refresh CFG global."""
    global CFG
    p = Path(CONFIG_FILE)
    p.parent.mkdir(parents=True, exist_ok=True)
    lines  = p.read_text().splitlines() if p.exists() else []
    found  = False
    result = []
    for line in lines:
        if line.strip().startswith(f"{key}=") or line.strip().startswith(f"{key} ="):
            result.append(f"{key}={value}")
            found = True
        else:
            result.append(line)
    if not found:
        result.append(f"{key}={value}")
    p.write_text("\n".join(result) + "\n")
    # Sync ke CFG
    if key == "OWNER_ID":
        try:
            CFG["OWNER_ID"] = int(value)
            if CFG["OWNER_ID"] not in CFG["ADMIN_IDS"]:
                CFG["ADMIN_IDS"].insert(0, CFG["OWNER_ID"])
        except: pass
    elif key == "ADMIN_IDS":
        try:
            ids = [int(x) for x in value.split(",") if x.strip().isdigit()]
            # Pastikan owner tetap ada
            if CFG["OWNER_ID"] and CFG["OWNER_ID"] not in ids:
                ids.insert(0, CFG["OWNER_ID"])
            CFG["ADMIN_IDS"] = ids
        except: pass
    else:
        CFG[key] = value

# ============================================================
#  CEK PERAN ADMIN
# ============================================================
def is_owner(user_id: int) -> bool:
    """Cek apakah user adalah Owner (Admin Utama)."""
    owner = CFG.get("OWNER_ID", 0)
    # Jika OWNER_ID belum diset, admin pertama di ADMIN_IDS otomatis jadi owner
    if not owner:
        ids = CFG.get("ADMIN_IDS", [])
        return bool(ids) and user_id == ids[0]
    return user_id == owner

def is_admin(user_id: int) -> bool:
    """Cek apakah user adalah admin (owner ATAU reseller)."""
    return user_id in CFG.get("ADMIN_IDS", [])

def is_reseller(user_id: int) -> bool:
    """Cek apakah user adalah reseller (admin tapi bukan owner)."""
    return is_admin(user_id) and not is_owner(user_id)

def get_role_label(user_id: int) -> str:
    """Ambil label peran untuk ditampilkan."""
    if is_owner(user_id): return "👑 Owner"
    if is_admin(user_id): return "🏪 Reseller"
    return "👤 User"

# ============================================================
#  HELPERS — Panel OGH-ZIV
# ============================================================
def get_ip() -> str:
    try:
        r = subprocess.check_output(
            ["curl", "-s4", "--max-time", "5", "ifconfig.me"], stderr=subprocess.DEVNULL
        ).decode().strip()
        if re.match(r"^\d+\.\d+\.\d+\.\d+$", r): return r
    except: pass
    try:
        return subprocess.check_output(["hostname", "-I"], stderr=subprocess.DEVNULL).decode().split()[0]
    except: return "0.0.0.0"

def get_domain() -> str:
    if Path(DOMAIN_CONF).exists(): return Path(DOMAIN_CONF).read_text().strip()
    return get_ip()

def get_port() -> str:
    cfg_file = "/etc/zivpn/config.json"
    if Path(cfg_file).exists():
        try:
            data = json.loads(Path(cfg_file).read_text())
            return data.get("listen", ":5667").lstrip(":")
        except: pass
    return "5667"

def rand_pass(length: int = 12) -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))

def rand_user(prefix: str = "ziv") -> str:
    return f"{prefix}{''.join(random.choices(string.digits, k=5))}"

def user_exists(username: str) -> bool:
    if not Path(USERS_DB).exists(): return False
    for line in Path(USERS_DB).read_text().splitlines():
        if line.startswith(f"{username}|"): return True
    return False

def create_account(username: str, password: str, days: int, kuota: int,
                   maxlogin: int, note: str = "-", exp_override: str = None) -> dict:
    # exp_override: opsional, datetime string "YYYY-MM-DD HH:MM" untuk trial (agar tepat 120 menit)
    if exp_override:
        exp = exp_override
    else:
        exp = (now_wib() + timedelta(days=days)).strftime("%Y-%m-%d")
    Path(USERS_DB).parent.mkdir(parents=True, exist_ok=True)
    with open(USERS_DB, "a") as f:
        f.write(f"{username}|{password}|{exp}|{kuota}|{note}\n")
    mldb = Path(MLDB)
    mldb.parent.mkdir(parents=True, exist_ok=True)
    lines = mldb.read_text().splitlines() if mldb.exists() else []
    lines = [l for l in lines if not l.startswith(f"{username}|")]
    lines.append(f"{username}|{maxlogin}")
    mldb.write_text("\n".join(lines) + "\n")
    _reload_pw()
    return {
        "username": username, "password": password, "exp": exp,
        "ip": get_ip(), "domain": get_domain(), "port": get_port(),
        "kuota": "Unlimited" if kuota == 0 else f"{kuota} GB",
        "maxlogin": maxlogin, "note": note,
    }

def _reload_pw():
    cfg_file = "/etc/zivpn/config.json"
    if not Path(USERS_DB).exists() or not Path(cfg_file).exists(): return
    try:
        pws = []
        for line in Path(USERS_DB).read_text().splitlines():
            parts = line.split("|")
            if len(parts) >= 2: pws.append(f'"{parts[1]}"')
        data = json.loads(Path(cfg_file).read_text())
        data["auth"]["config"] = json.loads(f"[{','.join(pws)}]")
        Path(cfg_file).write_text(json.dumps(data, indent=2))
        subprocess.run(["systemctl", "restart", "zivpn"], capture_output=True, timeout=10)
    except Exception as e: log.warning(f"reload_pw error: {e}")

def delete_account(username: str) -> bool:
    if not Path(USERS_DB).exists(): return False
    lines     = Path(USERS_DB).read_text().splitlines()
    new_lines = [l for l in lines if not l.startswith(f"{username}|")]
    if len(new_lines) == len(lines): return False
    Path(USERS_DB).write_text("\n".join(new_lines) + "\n" if new_lines else "")
    if Path(MLDB).exists():
        ml = [l for l in Path(MLDB).read_text().splitlines() if not l.startswith(f"{username}|")]
        Path(MLDB).write_text("\n".join(ml) + "\n")
    _reload_pw()
    return True

# ── Helper: parse expired support 2 format ───────────────────
def parse_exp(exp_raw: str) -> datetime:
    """Parse string expired ke datetime.
    Support: 'YYYY-MM-DD HH:MM' (trial) dan 'YYYY-MM-DD' (akun biasa = akhir hari).
    """
    exp_raw = exp_raw.strip()
    if len(exp_raw) > 10:
        return datetime.strptime(exp_raw, "%Y-%m-%d %H:%M")
    return datetime.strptime(exp_raw, "%Y-%m-%d").replace(hour=23, minute=59, second=59)

def is_expired(exp_raw: str) -> bool:
    """Return True jika akun sudah expired berdasarkan waktu sekarang."""
    try:
        return parse_exp(exp_raw) < now_wib()
    except ValueError:
        return False  # format tidak dikenal, anggap masih aktif

def delete_expired_accounts() -> dict:
    """
    Hapus semua akun yang sudah expired dari USERS_DB dan MLDB lokal.
    Mendukung format expired: 'YYYY-MM-DD' maupun 'YYYY-MM-DD HH:MM'.
    Return: {"deleted": [list username], "count": int}
    """
    now_dt  = now_wib()
    deleted = []
    if not Path(USERS_DB).exists():
        return {"deleted": [], "count": 0}
    lines     = Path(USERS_DB).read_text().splitlines()
    keep      = []
    for line in lines:
        if not line.strip():
            continue
        parts = line.split("|")
        if len(parts) < 3:
            keep.append(line)
            continue
        exp_raw = parts[2].strip()
        try:
            # Support format datetime lengkap (trial) maupun tanggal saja
            if len(exp_raw) > 10:
                exp_dt = datetime.strptime(exp_raw, "%Y-%m-%d %H:%M")
            else:
                exp_dt = datetime.strptime(exp_raw, "%Y-%m-%d")
                # Anggap expired akhir hari
                exp_dt = exp_dt.replace(hour=23, minute=59, second=59)
            if exp_dt < now_dt:
                deleted.append(parts[0])
            else:
                keep.append(line)
        except ValueError:
            keep.append(line)  # format tidak dikenal, jangan hapus
    Path(USERS_DB).write_text("\n".join(keep) + "\n" if keep else "")
    # Hapus juga dari MLDB
    if deleted and Path(MLDB).exists():
        ml_lines = Path(MLDB).read_text().splitlines()
        ml_keep  = [l for l in ml_lines if l.split("|")[0] not in deleted]
        Path(MLDB).write_text("\n".join(ml_keep) + "\n")
    if deleted:
        _reload_pw()
    return {"deleted": deleted, "count": len(deleted)}

def get_account_info(username: str) -> Optional[dict]:
    if not Path(USERS_DB).exists(): return None
    for line in Path(USERS_DB).read_text().splitlines():
        parts = line.split("|")
        if len(parts) >= 5 and parts[0] == username:
            ml = "2"
            if Path(MLDB).exists():
                for ml_line in Path(MLDB).read_text().splitlines():
                    if ml_line.startswith(f"{username}|"): ml = ml_line.split("|")[1]
            return {"username": parts[0], "password": parts[1], "exp": parts[2],
                    "kuota": parts[3], "note": parts[4], "maxlogin": ml,
                    "ip": get_ip(), "domain": get_domain(), "port": get_port()}
    return None

def qris_aktif() -> bool:
    return CFG.get("QRIS_ENABLED", "0") == "1" and Path(QRIS_IMG).exists()

# ============================================================
#  OCR — Verifikasi Screenshot
# ============================================================
def verify_payment_screenshot(image_path: str, expected_amount: int) -> Tuple[bool, str]:
    if not OCR_AVAILABLE: return (None, "ocr_unavailable")
    try:
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img, lang="ind+eng")
        text_up = text.upper()
        log.info(f"OCR result: {text[:300]}")

        has_payment = any(kw in text_up for kw in [
            "DANA", "BERHASIL", "SUKSES", "TRANSFER", "SELESAI",
            "SUCCESS", "PEMBAYARAN", "QRIS", "GOPAY", "OVO", "SHOPEEPAY"
        ])
        dana_num   = CFG.get("DANA_NUMBER", "").replace("-", "").replace(" ", "")
        has_number = dana_num in text.replace(" ", "").replace("-", "")
        has_amount = False
        for amt_str in re.findall(r"[\d.,]+", text):
            try:
                amt = int(amt_str.replace(".", "").replace(",", ""))
                if amt == expected_amount: has_amount = True; break
            except: pass

        if has_payment and has_number and has_amount:
            return (True,  "✅ Pembayaran terverifikasi otomatis")
        elif has_payment and has_amount:
            return (True,  "✅ Pembayaran terverifikasi (nominal cocok)")
        elif has_payment and has_number:
            return (False, "❌ Nominal tidak cocok dengan paket")
        elif not has_payment:
            return (False, "❌ Screenshot bukan dari aplikasi pembayaran yang valid")
        else:
            return (False, "❌ Screenshot tidak dapat diverifikasi")
    except Exception as e:
        log.error(f"OCR error: {e}")
        return (None, f"OCR error: {e}")

# ============================================================
#  FORMAT PESAN
# ============================================================
def format_akun_message(akun: dict, srv_id: str = "indo") -> str:
    brand    = CFG.get("BRAND", "OGH-ZIV")
    admin_tg = CFG.get("ADMIN_TG", "@admin")
    srv      = get_server_info(srv_id)
    srv_label = srv.get("label", "🇮🇩 Indonesia")
    hari_sisa = ""
    try:
        sisa = (datetime.strptime(akun["exp"], "%Y-%m-%d") - now_wib()).days
        hari_sisa = f"({sisa} hari lagi)" if sisa >= 0 else "(EXPIRED)"
    except: pass
    kuota_str = "Unlimited" if str(akun.get("kuota", "0")) == "0" else akun["kuota"]
    return (
        f"🎉 <b>{brand} — Akun VPN Premium</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🌍 <b>Server</b>    : {srv_label}\n"
        f"🖥 <b>IP Publik</b>  : <code>{akun['ip']}</code>\n"
        f"🌐 <b>Host</b>      : <code>{akun['domain']}</code>\n"
        f"🔌 <b>Port</b>      : <code>{akun['port']}</code>\n"
        f"📡 <b>Obfs</b>      : <code>zivpn</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>Username</b>  : <code>{akun['username']}</code>\n"
        f"🔑 <b>Password</b>  : <code>{akun['password']}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 <b>Kuota</b>     : {kuota_str}\n"
        f"🔒 <b>Max Login</b> : {akun['maxlogin']} device\n"
        f"📅 <b>Expired</b>   : {akun['exp']} {hari_sisa}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📱 Download ZiVPN → Play Store / App Store\n"
        f"⚠️  Jangan share akun ini ke orang lain!\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💬 Keluhan & bantuan: {admin_tg}"
    )

def format_paket_list() -> str:
    brand    = CFG.get("BRAND", "OGH-ZIV")
    dana_num = CFG.get("DANA_NUMBER", "")
    dana_name= CFG.get("DANA_NAME", "")
    lines = [
        f"🛒 <b>{brand} — Daftar Paket UDP VPN</b>\n",
        "━━━━━━━━━━━━━━━━━━━━━━━",
        f"1️⃣  <b>7 Hari</b>   — Rp 3.000  | Unlimited | 2 device",
        f"2️⃣  <b>15 Hari</b>  — Rp 6.000  | Unlimited | 2 device",
        f"3️⃣  <b>30 Hari</b>  — Rp 10.000 | Unlimited | 2 device",
        "━━━━━━━━━━━━━━━━━━━━━━━",
        f"🎁  <b>Trial Gratis</b> — 120 Menit | 1 device",
        "━━━━━━━━━━━━━━━━━━━━━━━",
        f"💳 <b>Metode Pembayaran:</b>",
        f"📱 DANA : <code>{dana_num}</code>  |  A/N: <b>{dana_name}</b>",
    ]
    if qris_aktif():
        lines.append(f"🔲 QRIS : <b>Tersedia</b> (pilih saat checkout)")
    return "\n".join(lines)

# ============================================================
#  HANDLERS — USER
# ============================================================
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user     = update.effective_user
    brand    = CFG.get("BRAND", "OGH-ZIV")
    admin_tg = CFG.get("ADMIN_TG", "@admin")
    keyboard = [
        [InlineKeyboardButton("🛒 Beli Akun VPN",          callback_data="beli")],
        [InlineKeyboardButton("🎁 Trial Gratis 120 Menit", callback_data="trial")],
        [InlineKeyboardButton("📋 Cek Akun Saya",          callback_data="cek_akun")],
        [InlineKeyboardButton("📞 Hubungi Admin", url=f"https://t.me/{admin_tg.lstrip('@')}")],
    ]
    if is_admin(user.id):
        keyboard.append([InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin")])
    await update.message.reply_text(
        f"👋 Selamat datang di <b>{brand} VPN Bot</b>!\n\n"
        f"Bot ini membantu kamu membeli akun VPN premium dengan mudah.\n"
        f"Pembayaran via DANA / QRIS — otomatis diproses setelah konfirmasi.\n\n"
        f"Pilih menu di bawah:",
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML"
    )

async def cb_back_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query    = update.callback_query
    await query.answer()
    user     = update.effective_user
    brand    = CFG.get("BRAND", "OGH-ZIV")
    admin_tg = CFG.get("ADMIN_TG", "@admin")
    keyboard = [
        [InlineKeyboardButton("🛒 Beli Akun VPN",          callback_data="beli")],
        [InlineKeyboardButton("🎁 Trial Gratis 120 Menit", callback_data="trial")],
        [InlineKeyboardButton("📋 Cek Akun Saya",          callback_data="cek_akun")],
        [InlineKeyboardButton("📞 Hubungi Admin", url=f"https://t.me/{admin_tg.lstrip('@')}")],
    ]
    if is_admin(user.id):
        keyboard.append([InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin")])
    await query.edit_message_text(
        f"👋 Selamat datang di <b>{brand} VPN Bot</b>!\n\n"
        f"Bot ini membantu kamu membeli akun VPN premium dengan mudah.\n"
        f"Pembayaran via DANA / QRIS — otomatis diproses setelah konfirmasi.\n\n"
        f"Pilih menu di bawah:",
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML"
    )

async def cb_beli(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Tampilkan pilihan jenis VPN (ZiVPN atau SocksIP)."""
    await cb_beli_jenis(update, ctx)


async def cb_paket(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query    = update.callback_query
    await query.answer()
    paket_id = query.data.split("_")[1]
    if paket_id not in PAKET:
        await query.edit_message_text("❌ Paket tidak valid.")
        return
    p = PAKET[paket_id]
    ctx.user_data["paket_id"]    = paket_id
    ctx.user_data["paket_nama"]  = p["nama"]
    ctx.user_data["paket_harga"] = p["harga"]

    # ── Tampilkan pilihan server setelah pilih paket ───────────
    await _show_server_choice(query, paket_id, p)

async def _show_server_choice(query, paket_id: str, p: dict):
    """Tampilkan pilihan server Indo/SG kepada user."""
    active_srvs = get_active_servers()
    srvs_all    = load_servers()

    keyboard = []
    for srv_id, srv in srvs_all.items():
        icon  = server_status_icon(srv)
        label = srv.get("label", srv_id.upper())
        stock = server_stock_text(srv)

        if not srv.get("enabled") or not srv.get("host"):
            # Server belum aktif — tampilkan tapi tidak bisa dipilih
            keyboard.append([InlineKeyboardButton(
                f"{icon} {label} — Belum tersedia",
                callback_data="server_unavailable"
            )])
        elif srv.get("stock", -1) == 0:
            # Stok habis
            keyboard.append([InlineKeyboardButton(
                f"{icon} {label} — Stok Habis",
                callback_data="server_unavailable"
            )])
        else:
            keyboard.append([InlineKeyboardButton(
                f"{icon} {label} — {stock}",
                callback_data=f"srv_{srv_id}_paket_{paket_id}"
            )])

    keyboard.append([InlineKeyboardButton("🔙 Kembali", callback_data="beli")])

    srv_lines = []
    for srv_id, srv in srvs_all.items():
        icon  = server_status_icon(srv)
        label = srv.get("label", srv_id.upper())
        note  = srv.get("note", "")
        stock = server_stock_text(srv)
        srv_lines.append(f"{icon} <b>{label}</b> — {stock}\n   <i>{note}</i>")

    await query.edit_message_text(
        f"📦 <b>Paket {p['nama']} — Rp {p['harga']:,}</b>\n\n"
        f"🌍 <b>Pilih Server:</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        + "\n".join(srv_lines) +
        f"\n━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>Pilih server yang tersedia di bawah:</i>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def cb_server_unavailable(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("⛔ Server ini tidak tersedia saat ini.", show_alert=True)

async def cb_srv_paket(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """User sudah pilih server + paket → lanjut ke pilih metode bayar."""
    query = update.callback_query
    await query.answer()
    # Format: srv_<srv_id>_paket_<paket_id>
    parts    = query.data.split("_")  # ['srv','indo','paket','1']
    srv_id   = parts[1]
    paket_id = parts[3]

    if paket_id not in PAKET:
        await query.edit_message_text("❌ Paket tidak valid."); return

    p   = PAKET[paket_id]
    srv = get_server_info(srv_id)

    ctx.user_data["paket_id"]    = paket_id
    ctx.user_data["paket_nama"]  = p["nama"]
    ctx.user_data["paket_harga"] = p["harga"]
    ctx.user_data["server_id"]   = srv_id

    keyboard = [[InlineKeyboardButton("💳 Bayar via DANA", callback_data=f"bayar_dana_{paket_id}")]]
    if qris_aktif():
        keyboard.append([InlineKeyboardButton("🔲 Bayar via QRIS", callback_data=f"bayar_qris_{paket_id}")])
    keyboard.append([InlineKeyboardButton("🔙 Kembali", callback_data=f"paket_{paket_id}")])

    await query.edit_message_text(
        f"📦 <b>Paket {p['nama']} — Rp {p['harga']:,}</b>\n"
        f"🌍 <b>Server</b> : {srv.get('label','?')}\n\n"
        f"Pilih metode pembayaran:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def cb_bayar_dana(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query    = update.callback_query
    await query.answer()
    paket_id = query.data.split("_")[2]
    p        = PAKET.get(paket_id, PAKET["1"])
    ctx.user_data["paket_id"]     = paket_id
    ctx.user_data["metode_bayar"] = "dana"
    dana_num  = CFG.get("DANA_NUMBER", "")
    dana_name = CFG.get("DANA_NAME", "")
    await query.edit_message_text(
        f"💳 <b>Pembayaran via DANA</b>\n\n"
        f"📦 Paket    : {p['nama']}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📱 No. DANA : <code>{dana_num}</code>\n"
        f"👤 A/N      : <b>{dana_name}</b>\n"
        f"💰 Nominal  : <b>Rp {p['harga']:,}</b> (pas)\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📸 Setelah transfer, kirim <b>screenshot bukti bayar</b> ke chat ini.\n\n"
        f"⚠️ Pastikan nominal <b>pas</b> sesuai paket!",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Kembali", callback_data=f"paket_{paket_id}")]])
    )

async def cb_bayar_qris(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query    = update.callback_query
    await query.answer()
    paket_id = query.data.split("_")[2]
    p        = PAKET.get(paket_id, PAKET["1"])
    ctx.user_data["paket_id"]     = paket_id
    ctx.user_data["metode_bayar"] = "qris"
    caption = (
        f"🔲 <b>Pembayaran via QRIS</b>\n\n"
        f"📦 Paket   : {p['nama']}\n"
        f"💰 Nominal : <b>Rp {p['harga']:,}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Scan QR di atas dengan DANA, GoPay, OVO, ShopeePay, atau m-Banking.\n\n"
        f"📸 Setelah bayar, kirim <b>screenshot bukti bayar</b> ke chat ini."
    )
    try:
        await query.message.reply_photo(photo=open(QRIS_IMG, "rb"), caption=caption, parse_mode="HTML")
        await query.edit_message_text(
            f"🔲 QRIS dikirim di atas. Bayar Rp {p['harga']:,} lalu kirim screenshot.", parse_mode="HTML"
        )
    except Exception as e:
        await query.edit_message_text(f"❌ Gagal tampilkan QRIS: {e}\nHubungi admin.", parse_mode="HTML")

async def cb_trial(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Langkah 1 trial: cek kuota harian, lalu tampilkan pilihan server."""
    query    = update.callback_query
    await query.answer()
    user     = query.from_user
    trial_db = Path("/etc/zivpn/trial_used.db")
    today    = now_wib().strftime("%Y-%m-%d")
    uid_key  = f"{user.id}_{today}"

    if trial_db.exists() and uid_key in trial_db.read_text().splitlines():
        admin_tg = CFG.get("ADMIN_TG", "@admin")
        await query.edit_message_text(
            f"⛔ <b>Trial Sudah Digunakan</b>\n\nTrial hanya bisa digunakan <b>1x per hari</b>.\n\n"
            f"Beli paket mulai <b>Rp 3.000</b> atau hubungi: {admin_tg}",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛒 Beli Paket", callback_data="beli")],
                [InlineKeyboardButton("🔙 Kembali",    callback_data="back_start")],
            ])
        )
        return

    # ── Tampilkan pilihan server untuk trial ─────────────────
    await _show_trial_server_choice(query)

async def _show_trial_server_choice(query):
    """Tampilkan tombol pilihan server Indo/SG untuk trial."""
    srvs_all    = load_servers()
    active_srvs = {k: v for k, v in srvs_all.items() if v.get("enabled") and v.get("host")}

    keyboard = []
    srv_lines = []
    for srv_id, srv in srvs_all.items():
        icon  = server_status_icon(srv)
        label = srv.get("label", srv_id.upper())
        stock = server_stock_text(srv)
        note  = srv.get("note", "")
        srv_lines.append(f"{icon} <b>{label}</b> — {stock}\n   <i>{note}</i>")

        if not srv.get("enabled") or not srv.get("host"):
            keyboard.append([InlineKeyboardButton(
                f"{icon} {label} — Belum tersedia",
                callback_data="server_unavailable"
            )])
        elif srv.get("stock", -1) == 0:
            keyboard.append([InlineKeyboardButton(
                f"{icon} {label} — Stok Habis",
                callback_data="server_unavailable"
            )])
        else:
            keyboard.append([InlineKeyboardButton(
                f"{icon} {label} — {stock}",
                callback_data=f"trial_srv_{srv_id}"
            )])

    keyboard.append([InlineKeyboardButton("🔙 Kembali", callback_data="back_start")])

    await query.edit_message_text(
        f"🎁 <b>Trial Gratis — 120 Menit</b>\n\n"
        f"🌍 <b>Pilih Server Trial:</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        + "\n".join(srv_lines) +
        f"\n━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>Pilih server yang tersedia:</i>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def cb_trial_srv(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Langkah 2 trial: user sudah pilih server → buat akun trial di server itu."""
    query  = update.callback_query
    await query.answer()
    user   = query.from_user
    # Format: trial_srv_<srv_id>
    srv_id = query.data.replace("trial_srv_", "")
    srv    = get_server_info(srv_id)
    if not srv:
        await query.edit_message_text("❌ Server tidak ditemukan."); return

    trial_db = Path("/etc/zivpn/trial_used.db")
    today    = now_wib().strftime("%Y-%m-%d")
    uid_key  = f"{user.id}_{today}"

    # Double-check kuota (antisipasi race)
    if trial_db.exists() and uid_key in trial_db.read_text().splitlines():
        admin_tg = CFG.get("ADMIN_TG", "@admin")
        await query.edit_message_text(
            f"⛔ <b>Trial Sudah Digunakan</b>\n\nTrial hanya bisa digunakan <b>1x per hari</b>.\n\n"
            f"Beli paket mulai <b>Rp 3.000</b> atau hubungi: {admin_tg}",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛒 Beli Paket", callback_data="beli")],
                [InlineKeyboardButton("🔙 Kembali",    callback_data="back_start")],
            ])
        )
        return

    await query.edit_message_text("⏳ Membuat akun trial, mohon tunggu...")

    username  = f"trial{user.id % 99999:05d}"
    password  = rand_pass(8)
    now_dt    = now_wib()
    exp_dt    = now_dt + timedelta(minutes=TRIAL_MENIT)

    # ── PERBAIKAN: Simpan expired dengan format datetime lengkap (YYYY-MM-DD HH:MM)
    # agar VPS membaca waktu expire yang tepat, bukan akhir hari.
    exp_str   = exp_dt.strftime("%Y-%m-%d %H:%M")   # format datetime lengkap
    exp_clock = exp_dt.strftime("%H:%M")
    exp_date  = exp_dt.strftime("%d/%m/%Y")

    try:
        if is_local_server(srv_id):
            # Hapus trial lama jika ada di lokal
            if Path(USERS_DB).exists():
                lines = Path(USERS_DB).read_text().splitlines()
                lines = [l for l in lines if not l.startswith(f"{username}|")]
                Path(USERS_DB).write_text("\n".join(lines) + "\n" if lines else "")
            Path(USERS_DB).parent.mkdir(parents=True, exist_ok=True)
            with open(USERS_DB, "a") as f:
                # Simpan dengan datetime lengkap termasuk jam:menit
                f.write(f"{username}|{password}|{exp_str}|1|TRIAL-TG{user.id}\n")
            mldb     = Path(MLDB)
            ml_lines = mldb.read_text().splitlines() if mldb.exists() else []
            ml_lines = [l for l in ml_lines if not l.startswith(f"{username}|")]
            ml_lines.append(f"{username}|1")
            mldb.write_text("\n".join(ml_lines) + "\n")
            _reload_pw()
            host   = get_domain()
            port   = get_port()
            ip_pub = get_ip()
        else:
            # Hapus trial lama di remote jika ada (abaikan error)
            api_call_remote(srv_id, "delete_account", {"username": username})
            # Pakai action create_trial — kirim exp datetime EXACT, tanpa days
            result = api_call_remote(srv_id, "create_trial", {
                "username": username,
                "password": password,
                "exp":      exp_str,   # "YYYY-MM-DD HH:MM" tepat 120 menit dari sekarang
                "note":     f"TRIAL-TG{user.id}"
            })
            if not result.get("ok"):
                raise Exception(result.get("error", "Gagal membuat akun di server remote"))
            akun_r = result.get("akun", {})
            host   = akun_r.get("domain", srv.get("host", "?"))
            port   = akun_r.get("port",   srv.get("port", "5667"))
            ip_pub = akun_r.get("ip",     srv.get("host", "?"))
    except Exception as e:
        await query.edit_message_text(
            f"❌ <b>Gagal membuat akun trial.</b>\n\nError: {e}\nCoba server lain atau hubungi admin.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Coba Server Lain", callback_data="trial")],
                [InlineKeyboardButton("🔙 Menu Utama",       callback_data="back_start")],
            ])
        )
        return

    # Simpan catatan trial terpakai
    with open(trial_db, "a") as f: f.write(uid_key + "\n")

    # ── PERBAIKAN: Jadwalkan auto-delete akun trial tepat setelah 120 menit ──
    async def _auto_delete_trial(srv_id_: str, username_: str, user_id_: int):
        """Hapus akun trial otomatis setelah TRIAL_MENIT menit."""
        import asyncio
        await asyncio.sleep(TRIAL_MENIT * 60)
        try:
            if is_local_server(srv_id_):
                deleted = delete_account(username_)
            else:
                result_ = api_call_remote(srv_id_, "delete_account", {"username": username_})
                deleted = result_.get("ok", False)
            if deleted:
                log.info(f"[TRIAL] Akun {username_} (user TG {user_id_}) dihapus otomatis setelah {TRIAL_MENIT} menit.")
            else:
                log.warning(f"[TRIAL] Gagal hapus akun {username_} (mungkin sudah dihapus).")
        except Exception as ex:
            log.error(f"[TRIAL] Error hapus akun trial {username_}: {ex}")

    import asyncio as _asyncio
    _asyncio.ensure_future(_auto_delete_trial(srv_id, username, user.id))

    brand    = CFG.get("BRAND", "OGH-ZIV")
    admin_tg = CFG.get("ADMIN_TG", "@admin")
    srv_label = srv.get("label", srv_id.upper())

    await query.edit_message_text(
        f"🎁 <b>{brand} — Akun Trial Gratis</b>\n"
        f"🌍 <b>Server</b>    : {srv_label}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🖥 <b>IP Publik</b>  : <code>{ip_pub}</code>\n"
        f"🌐 <b>Host</b>      : <code>{host}</code>\n"
        f"🔌 <b>Port</b>      : <code>{port}</code>\n"
        f"📡 <b>Obfs</b>      : <code>zivpn</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>Username</b>  : <code>{username}</code>\n"
        f"🔑 <b>Password</b>  : <code>{password}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏱ <b>Durasi</b>    : 120 Menit\n"
        f"🔒 <b>Max Login</b> : 1 device\n"
        f"⏰ <b>Expired</b>   : {exp_date} pukul {exp_clock}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚠️  Trial 1x per hari  |  💬 Keluhan: {admin_tg}",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🛒 Beli Paket Berbayar", callback_data="beli")],
            [InlineKeyboardButton("🔙 Menu Utama",          callback_data="back_start")],
        ])
    )
    for admin_id in CFG.get("ADMIN_IDS", []):
        try:
            await ctx.bot.send_message(
                admin_id,
                f"🎁 <b>Trial Baru</b>\n"
                f"👤 {user.full_name} (@{user.username or '-'}) | ID: {user.id}\n"
                f"🌍 Server  : {srv_label}\n"
                f"🔑 {username} / {password}\n"
                f"⏰ Expired : {exp_date} {exp_clock}",
                parse_mode="HTML"
            )
        except: pass

async def cb_cek_akun(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    ctx.user_data["action"] = "cek_akun"
    await query.edit_message_text(
        "🔍 <b>Cek Akun</b>\n\nKirim username kamu:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Kembali", callback_data="back_start")]])
    )

# ============================================================
#  HANDLE FOTO
# ============================================================
async def handle_document(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handler untuk file dokumen — dipakai untuk restore backup dari Telegram."""
    user = update.effective_user
    doc  = update.message.document

    # Hanya Owner yang bisa restore via file
    if not is_owner(user.id):
        return

    # Cek apakah Owner sedang dalam mode restore dari file
    if ctx.user_data.get("admin_action") != "waiting_backup_file":
        return

    # Validasi nama file harus .tar.gz
    filename = doc.file_name or ""
    if not filename.endswith(".tar.gz"):
        await update.message.reply_text(
            "❌ <b>File tidak valid!</b>\n\n"
            "File backup harus berformat <code>.tar.gz</code>\n"
            "Cari file bernama <code>oghziv_backup_*.tar.gz</code> di chat kamu.",
            parse_mode="HTML"
        )
        return

    await update.message.reply_text(
        "⏳ <b>File diterima! Sedang memproses restore...</b>\n\n"
        "<i>Mohon tunggu...</i>",
        parse_mode="HTML"
    )

    ctx.user_data.pop("admin_action", None)

    # Download file backup dari Telegram
    os.makedirs(_BACKUP_DIR, exist_ok=True)
    ts_now      = now_wib().strftime("%Y%m%d_%H%M%S")
    tmp_file    = f"/tmp/oghziv_restore_{ts_now}.tar.gz"

    try:
        file_obj = await ctx.bot.get_file(doc.file_id)
        await file_obj.download_to_drive(tmp_file)
    except Exception as e:
        await update.message.reply_text(
            f"❌ <b>Gagal mengunduh file!</b>\n\nError: <code>{e}</code>",
            parse_mode="HTML"
        )
        return

    # Auto-backup konfigurasi aktif sebelum restore
    auto_bak = f"{_BACKUP_DIR}/oghziv_backup_pre-restore_{ts_now}.tar.gz"
    files_to_backup = [
        "/etc/zivpn/bot_store.conf", "/etc/zivpn/servers.json",
        "/etc/zivpn/worker.conf",    "/etc/zivpn/config.json",
        "/etc/zivpn/users.db",       "/etc/zivpn/maxlogin.db",
        "/usr/local/bin/zivpn-tgbot.py",
        "/usr/local/bin/zivpn-api-worker.py",
    ]
    try:
        with _tarfile.open(auto_bak, "w:gz") as tar:
            for fp in files_to_backup:
                if os.path.exists(fp): tar.add(fp)
    except:
        pass  # auto-backup gagal tidak menghalangi restore

    # Lakukan restore dari file yang diupload
    restored = []
    try:
        with _tarfile.open(tmp_file, "r:gz") as tar:
            members = tar.getmembers()
            for m in members:
                tar.extract(m, "/")
                if m.name:
                    restored.append(os.path.basename(m.name))

        # Hapus file temp
        try: os.remove(tmp_file)
        except: pass

        # Reload config global
        global CFG
        CFG = load_config()

        await update.message.reply_text(
            f"✅ <b>Restore Berhasil!</b>\n\n"
            f"📦 Dari file : <code>{filename}</code>\n"
            f"🗂️ Dipulihkan ({len(restored)} file) :\n"
            + "\n".join(f"   • {r}" for r in [x for x in restored if x][:10]) +
            f"\n\n⚠️ <b>Restart bot agar semua perubahan aktif:</b>\n"
            f"<code>systemctl restart zivpn-tgbot</code>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Kembali ke Menu Backup", callback_data="admin_backup_menu")]
            ])
        )

    except Exception as e:
        try: os.remove(tmp_file)
        except: pass
        await update.message.reply_text(
            f"❌ <b>Restore gagal!</b>\n\n"
            f"Error: <code>{e}</code>\n\n"
            f"Pastikan file yang dikirim adalah file backup OGH-ZIV yang valid.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Kembali", callback_data="admin_backup_menu")]
            ])
        )

async def handle_photo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    # Owner upload gambar QRIS
    if is_owner(user.id) and ctx.user_data.get("admin_action") == "upload_qris":
        photo    = update.message.photo[-1]
        file_obj = await ctx.bot.get_file(photo.file_id)
        Path(QRIS_IMG).parent.mkdir(parents=True, exist_ok=True)
        await file_obj.download_to_drive(QRIS_IMG)
        save_config_key("QRIS_ENABLED", "1")
        ctx.user_data.pop("admin_action", None)
        await update.message.reply_text(
            "✅ <b>Gambar QRIS berhasil disimpan & diaktifkan!</b>\n\n"
            "User sekarang bisa memilih bayar via QRIS saat checkout.",
            parse_mode="HTML"
        )
        return

    # ── SocksIP: cek foto untuk SocksIP ──
    if ctx.user_data.get("vpn_type") == "socksip" and "socksip_paket_id" in ctx.user_data:
        await _handle_socksip_photo(update, ctx)
        return

    if "paket_id" not in ctx.user_data:
        await update.message.reply_text("❓ Kamu belum memilih paket.\nKetik /start untuk memulai.")
        return
    if ctx.user_data.get("waiting_username"):
        await update.message.reply_text(
            "⏳ Pembayaran sudah diverifikasi!\nSilakan ketik <b>username</b> yang kamu inginkan:",
            parse_mode="HTML"
        )
        return

    paket_id   = ctx.user_data["paket_id"]
    paket_info = PAKET[paket_id]
    await update.message.reply_text("⏳ Memverifikasi screenshot pembayaran...")

    photo    = update.message.photo[-1]
    file_obj = await ctx.bot.get_file(photo.file_id)
    img_path = f"/tmp/ss_{user.id}_{photo.file_id[:8]}.jpg"
    await file_obj.download_to_drive(img_path)

    ok, reason = verify_payment_screenshot(img_path, paket_info["harga"])

    if ok is True:
        try: os.remove(img_path)
        except: pass
        ctx.user_data["waiting_username"] = True
        ctx.user_data["ss_verified"]      = True
        await update.message.reply_text(
            f"✅ <b>Pembayaran Terverifikasi!</b>\n\nKetik <b>username</b> yang kamu inginkan:\n"
            f"<i>(Huruf kecil, angka, minimal 4 karakter)</i>",
            parse_mode="HTML"
        )
    elif ok is None:
        ctx.user_data["waiting_username"] = False
        await update.message.reply_text("⏳ Screenshot diterima. Admin akan verifikasi dalam beberapa menit. Harap tunggu 🙏")
        for admin_id in CFG.get("ADMIN_IDS", []):
            try:
                await ctx.bot.send_photo(
                    chat_id=admin_id, photo=open(img_path, "rb"),
                    caption=(
                        f"🧾 <b>Verifikasi Manual</b>\n\n"
                        f"👤 Pembeli : {user.full_name} (@{user.username or '-'})\n"
                        f"🆔 User ID : <code>{user.id}</code>\n"
                        f"📦 Paket   : {paket_info['nama']}\n"
                        f"💰 Nominal : Rp {paket_info['harga']:,}\n\n"
                        f"✅ /konfirm_{user.id}   ❌ /tolak_{user.id}"
                    ),
                    parse_mode="HTML"
                )
            except: pass
        try: os.remove(img_path)
        except: pass
    else:
        admin_tg = CFG.get("ADMIN_TG", "@admin")
        await update.message.reply_text(
            f"❌ <b>Verifikasi Gagal</b>\n\n{reason}\n\n"
            f"Pastikan screenshot dari aplikasi pembayaran & nominal <b>Rp {paket_info['harga']:,}</b> pas.\n\n"
            f"Coba lagi atau hubungi: {admin_tg}",
            parse_mode="HTML"
        )
        try: os.remove(img_path)
        except: pass

# ============================================================
#  ADMIN: Konfirmasi Manual
# ============================================================
async def cmd_konfirm(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    try: target_uid = int(update.message.text.split("_")[1])
    except:
        await update.message.reply_text("Format: /konfirm_<user_id>")
        return
    pdata = ctx.bot_data.get(f"pending_{target_uid}")
    if not pdata:
        await update.message.reply_text("❌ Data pending tidak ditemukan.")
        return
    paket_id = pdata.get("paket_id", "2")
    ctx.bot_data.pop(f"pending_{target_uid}", None)
    try:
        ctx.bot_data[f"konfirm_{target_uid}"] = {"paket_id": paket_id, "ss_verified": True}
        await ctx.bot.send_message(
            chat_id=target_uid,
            text=(
                f"✅ <b>Pembayaran Dikonfirmasi!</b>\n\nKetik <b>username</b> yang kamu inginkan:\n"
                f"<i>(Huruf kecil, angka, minimal 4 karakter)</i>"
            ),
            parse_mode="HTML"
        )
        await update.message.reply_text("✅ Dikonfirmasi. Bot sudah minta user/pass ke pembeli.")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Tidak bisa kirim ke user: {e}")

async def cmd_tolak(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    try: target_uid = int(update.message.text.split("_")[1])
    except:
        await update.message.reply_text("Format: /tolak_<user_id>")
        return
    ctx.bot_data.pop(f"pending_{target_uid}", None)
    admin_tg = CFG.get("ADMIN_TG", "@admin")
    try:
        await ctx.bot.send_message(
            target_uid,
            f"❌ <b>Pembayaran Ditolak</b>\n\nScreenshot tidak berhasil diverifikasi.\nHubungi admin: {admin_tg}",
            parse_mode="HTML"
        )
    except: pass
    await update.message.reply_text("✅ Pesanan ditolak dan user telah diberitahu.")

# ============================================================
#  ADMIN PANEL — MENU UTAMA
#  Owner → semua menu tampil
#  Reseller → hanya menu reseller yang tampil
# ============================================================
async def cb_admin(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id

    if not is_admin(uid):
        await query.edit_message_text("⛔ Akses ditolak!")
        return

    brand = CFG.get("BRAND", "OGH-ZIV")
    role  = get_role_label(uid)

    # Menu yang bisa diakses SEMUA admin (owner + reseller)
    keyboard = [
        [InlineKeyboardButton("👤 Buat Akun ZiVPN Gratis",   callback_data="admin_buat_akun")],
        [InlineKeyboardButton("📡 Panel SocksIP (UDP)",       callback_data="admin_socksip")],
        [InlineKeyboardButton("🗑️ Hapus Akun ZiVPN",   callback_data="admin_del")],
        [InlineKeyboardButton("🧹 Hapus Semua Akun Expired",  callback_data="admin_del_expired")],
        [InlineKeyboardButton("📋 List Akun Per Server",      callback_data="admin_list_menu")],
        [InlineKeyboardButton("📊 Statistik Server",          callback_data="admin_stat")],
    ]

    # Menu KHUSUS OWNER
    if is_owner(uid):
        keyboard += [
            [InlineKeyboardButton("👥 Kelola Reseller",        callback_data="admin_kelola_admin")],
            [InlineKeyboardButton("🌍 Kelola Server Indo/SG",  callback_data="admin_kelola_server")],
            [InlineKeyboardButton("💳 Pengaturan Pembayaran",  callback_data="admin_pembayaran")],
            [InlineKeyboardButton("⚙️ Pengaturan Bot",         callback_data="admin_settings")],
            [InlineKeyboardButton("💾 Backup / Restore",       callback_data="admin_backup_menu")],
        ]

    keyboard.append([InlineKeyboardButton("🔙 Kembali", callback_data="back_start")])

    await query.edit_message_text(
        f"⚙️ <b>Admin Panel — {brand}</b>\n"
        f"Halo, <b>{query.from_user.first_name}</b>!  {role}\n\n"
        + ("🔓 Akses penuh sebagai Owner.\n" if is_owner(uid)
           else "🔒 Akses terbatas sebagai Reseller.\n    Hubungi Owner untuk ubah pembayaran/setting.\n"),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

# ─── Pesan penolakan akses reseller ──────────────────────────
async def _akses_ditolak(query, fitur: str):
    await query.edit_message_text(
        f"⛔ <b>Akses Ditolak</b>\n\n"
        f"Fitur <b>{fitur}</b> hanya bisa diakses oleh <b>👑 Owner</b>.\n\n"
        f"Kamu login sebagai <b>🏪 Reseller</b>.\n"
        f"Hubungi Owner untuk mengubah pengaturan ini.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Kembali", callback_data="admin")]])
    )

# ============================================================
#  ADMIN — BUAT AKUN GRATIS (Owner + Reseller)
# ============================================================
async def cb_admin_buat_akun(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Menu utama buat akun gratis — tampilkan pilihan cara buat."""
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id): return
    keyboard = [
        [InlineKeyboardButton("✏️ Manual (User & Pass sendiri)", callback_data="admin_akun_manual")],
        [InlineKeyboardButton("⚡ Generate Otomatis",             callback_data="admin_akun_auto")],
        [InlineKeyboardButton("🔙 Kembali",                       callback_data="admin")],
    ]
    await query.edit_message_text(
        "👤 <b>Buat Akun Gratis</b>\n\nPilih cara membuat akun:",
        parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard)
    )

def _build_admin_server_keyboard(back_cb: str) -> tuple[list, list]:
    """Bangun keyboard pilihan server untuk admin + teks info server.
    Return: (keyboard_rows, srv_info_lines)
    """
    srvs_all = load_servers()
    keyboard  = []
    srv_lines = []
    for srv_id, srv in srvs_all.items():
        icon  = server_status_icon(srv)
        label = srv.get("label", srv_id.upper())
        stock = server_stock_text(srv)
        note  = srv.get("note", "")
        srv_lines.append(f"{icon} <b>{label}</b> — {stock}\n   <i>{note}</i>")

        if not srv.get("enabled") or not srv.get("host"):
            keyboard.append([InlineKeyboardButton(
                f"{icon} {label} — Belum tersedia", callback_data="server_unavailable"
            )])
        elif srv.get("stock", -1) == 0:
            keyboard.append([InlineKeyboardButton(
                f"{icon} {label} — Stok Habis", callback_data="server_unavailable"
            )])
        else:
            keyboard.append([InlineKeyboardButton(
                f"{icon} {label} — {stock}", callback_data=f"admin_srv_akun_{srv_id}__{back_cb}"
            )])
    keyboard.append([InlineKeyboardButton("🔙 Batal", callback_data=back_cb)])
    return keyboard, srv_lines

async def cb_admin_akun_manual(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Buat akun manual — Langkah 0: pilih server."""
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id): return

    keyboard, srv_lines = _build_admin_server_keyboard("admin_buat_akun")
    await query.edit_message_text(
        "✏️ <b>Buat Akun Manual — Pilih Server</b>\n\n"
        "🌍 <b>Server tersedia:</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n"
        + "\n".join(srv_lines) +
        "\n━━━━━━━━━━━━━━━━━━━━━━━\n"
        "<i>Pilih server tujuan akun ini:</i>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def cb_admin_akun_auto(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Generate akun otomatis — Langkah 0: pilih server."""
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id): return

    keyboard, srv_lines = _build_admin_server_keyboard("admin_buat_akun")
    # Ganti teks tombol callback agar tahu ini flow auto
    new_keyboard = []
    for row in keyboard:
        new_row = []
        for btn in row:
            if btn.callback_data and btn.callback_data.startswith("admin_srv_akun_"):
                new_row.append(InlineKeyboardButton(
                    btn.text,
                    callback_data=btn.callback_data.replace("admin_srv_akun_", "admin_srv_akun_auto_")
                ))
            else:
                new_row.append(btn)
        new_keyboard.append(new_row)

    await query.edit_message_text(
        "⚡ <b>Generate Akun Otomatis — Pilih Server</b>\n\n"
        "🌍 <b>Server tersedia:</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n"
        + "\n".join(srv_lines) +
        "\n━━━━━━━━━━━━━━━━━━━━━━━\n"
        "<i>Pilih server tujuan akun ini:</i>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(new_keyboard)
    )

async def cb_admin_srv_akun(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    Admin sudah pilih server untuk akun manual.
    callback_data: admin_srv_akun_<srv_id>__<back_cb>
    """
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id): return

    # Parse: admin_srv_akun_<srv_id>__<back_cb>
    raw    = query.data.replace("admin_srv_akun_", "")   # "indo__admin_buat_akun"
    parts  = raw.split("__", 1)
    srv_id = parts[0]
    srv    = get_server_info(srv_id)

    ctx.user_data["admin_action"]          = "akun_manual_step1"
    ctx.user_data["akun_manual_data"]      = {}
    ctx.user_data["akun_manual_server_id"] = srv_id

    await query.edit_message_text(
        f"✏️ <b>Buat Akun Manual — Langkah 1/4</b>\n"
        f"🌍 Server: <b>{srv.get('label', srv_id.upper())}</b>\n\n"
        "Ketik <b>username</b> yang diinginkan:\n"
        "<i>(Huruf kecil, angka, underscore — minimal 4 karakter)</i>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Batal", callback_data="admin_buat_akun")]])
    )

async def cb_admin_srv_akun_auto(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    Admin sudah pilih server untuk akun auto → tampilkan pilihan hari.
    callback_data: admin_srv_akun_auto_<srv_id>__<back_cb>
    """
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id): return

    raw    = query.data.replace("admin_srv_akun_auto_", "")
    parts  = raw.split("__", 1)
    srv_id = parts[0]
    srv    = get_server_info(srv_id)

    ctx.user_data["akun_auto_server_id"] = srv_id

    keyboard = [
        [InlineKeyboardButton("3 Hari",   callback_data=f"admin_auto_hari_3_{srv_id}")],
        [InlineKeyboardButton("15 Hari",  callback_data=f"admin_auto_hari_15_{srv_id}")],
        [InlineKeyboardButton("30 Hari",  callback_data=f"admin_auto_hari_30_{srv_id}")],
        [InlineKeyboardButton("🔙 Batal", callback_data="admin_buat_akun")],
    ]
    await query.edit_message_text(
        f"⚡ <b>Generate Akun Otomatis</b>\n"
        f"🌍 Server: <b>{srv.get('label', srv_id.upper())}</b>\n\n"
        "Pilih durasi aktif:",
        parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def cb_admin_auto_hari(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    Admin pilih durasi hari untuk akun auto.
    callback_data baru: admin_auto_hari_<hari>_<srv_id>
    callback_data lama (fallback): admin_auto_hari_<hari>
    """
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id): return

    # Format baru: admin_auto_hari_30_indo
    # Format lama: admin_auto_hari_30
    raw   = query.data.replace("admin_auto_hari_", "")   # "30_indo" atau "30"
    parts = raw.split("_", 1)
    try:
        hari = int(parts[0])
    except:
        await query.edit_message_text("❌ Format tidak valid."); return

    # Ambil srv_id dari callback baru, atau dari user_data, fallback ke "indo"
    if len(parts) > 1 and parts[1]:
        srv_id = parts[1]
    else:
        srv_id = ctx.user_data.pop("akun_auto_server_id", "indo")

    srv      = get_server_info(srv_id)
    username = rand_user("ziv")
    password = rand_pass()

    await query.edit_message_text("⏳ Membuat akun otomatis...")

    try:
        akun = create_account_on_server(srv_id, username, password, hari, 0, 2, "ADMIN-FREE-AUTO")
    except Exception as e:
        await query.edit_message_text(
            f"❌ <b>Gagal membuat akun di {srv.get('label', srv_id)}.</b>\n\nError: {e}",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Admin Panel", callback_data="admin")]])
        )
        return

    await query.edit_message_text(
        f"✅ <b>Akun Otomatis Berhasil Dibuat!</b>\n"
        f"🌍 Server: <b>{srv.get('label', srv_id.upper())}</b>\n\n"
        + format_akun_message(akun, srv_id),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Admin Panel", callback_data="admin")]])
    )

# ============================================================
#  ADMIN — HAPUS AKUN VPN (Owner + Reseller)
# ============================================================
async def cb_admin_del(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id): return
    ctx.user_data["admin_action"] = "del_akun"
    await query.edit_message_text(
        "🗑️ <b>Hapus Akun</b>\n\nKirim username yang ingin dihapus:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Batal", callback_data="admin")]])
    )

# ============================================================
#  ADMIN — HAPUS SEMUA AKUN EXPIRED (Owner + Reseller)
# ============================================================
async def cb_admin_del_expired(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Tampilkan preview akun expired sebelum konfirmasi hapus."""
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id): return

    now_dt  = now_wib()
    expired_list = []
    if Path(USERS_DB).exists():
        for line in Path(USERS_DB).read_text().splitlines():
            if not line.strip(): continue
            parts = line.split("|")
            if len(parts) < 3: continue
            exp_raw = parts[2].strip()
            try:
                if len(exp_raw) > 10:
                    exp_dt = datetime.strptime(exp_raw, "%Y-%m-%d %H:%M")
                else:
                    exp_dt = datetime.strptime(exp_raw, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
                if exp_dt < now_dt:
                    expired_list.append((parts[0], exp_raw))
            except ValueError:
                pass

    if not expired_list:
        await query.edit_message_text(
            "✅ <b>Tidak Ada Akun Expired</b>\n\nSemua akun masih aktif.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Kembali", callback_data="admin")]])
        )
        return

    lines = [f"🗑️ <b>Hapus Semua Akun Expired</b>\n",
             f"Ditemukan <b>{len(expired_list)}</b> akun expired:\n",
             "━━━━━━━━━━━━━━━━━━━━━━━"]
    for i, (uname, exp) in enumerate(expired_list[:30], 1):
        lines.append(f"{i}. <code>{uname}</code> | Exp: {exp}")
    if len(expired_list) > 30:
        lines.append(f"... (+{len(expired_list) - 30} akun lainnya)")
    lines.append("\n━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("⚠️ Yakin ingin menghapus semua akun expired?")

    await query.edit_message_text(
        "\n".join(lines), parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Ya, Hapus Semua",  callback_data="admin_del_expired_confirm")],
            [InlineKeyboardButton("❌ Batal",             callback_data="admin")],
        ])
    )

async def cb_admin_del_expired_confirm(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Eksekusi hapus semua akun expired."""
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id): return

    await query.edit_message_text("⏳ Menghapus akun expired, mohon tunggu...")

    # Hapus lokal
    result_lokal = delete_expired_accounts()

    # Hapus di semua server remote
    result_remote = {}
    srvs = load_servers()
    for srv_id, srv in srvs.items():
        if srv.get("enabled") and not is_local_server(srv_id):
            try:
                r = api_call_remote(srv_id, "delete_expired", {})
                label = srv.get("label", srv_id)
                result_remote[label] = r.get("count", 0) if r.get("ok") else "Gagal"
            except Exception as ex:
                result_remote[srv.get("label", srv_id)] = f"Error: {ex}"

    lines = [
        f"✅ <b>Selesai! Akun Expired Dihapus</b>\n",
        f"━━━━━━━━━━━━━━━━━━━━━━━",
        f"🖥 <b>Server Lokal</b> : {result_lokal['count']} akun dihapus",
    ]
    if result_lokal["deleted"]:
        for uname in result_lokal["deleted"][:20]:
            lines.append(f"   • <code>{uname}</code>")
        if len(result_lokal["deleted"]) > 20:
            lines.append(f"   ... (+{len(result_lokal['deleted']) - 20} lainnya)")

    for srv_label, cnt in result_remote.items():
        lines.append(f"🌍 <b>{srv_label}</b> : {cnt} akun dihapus")

    total = result_lokal["count"] + sum(
        v for v in result_remote.values() if isinstance(v, int)
    )
    lines.append(f"\n━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"🗑️ Total dihapus: <b>{total}</b> akun")

    await query.edit_message_text(
        "\n".join(lines), parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Kembali ke Admin Panel", callback_data="admin")]
        ])
    )

async def handle_admin_del(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    username = update.message.text.strip()
    ctx.user_data.pop("admin_action", None)
    if delete_account(username):
        await update.message.reply_text(f"✅ Akun <code>{username}</code> berhasil dihapus.", parse_mode="HTML")
    else:
        await update.message.reply_text(f"❌ Akun <code>{username}</code> tidak ditemukan.", parse_mode="HTML")

# ============================================================
#  ADMIN — LIST & STATISTIK (Owner + Reseller)
# ============================================================
async def cb_admin_list_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Tampilkan pilihan server untuk list akun."""
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id): return

    srvs = load_servers()
    keyboard = []

    # Tombol "Semua Server" (gabungan)
    keyboard.append([InlineKeyboardButton("🌐 Semua Server (Indo + SG)", callback_data="admin_list_all")])

    # Tombol per server
    for srv_id, srv in srvs.items():
        if not srv.get("enabled"): continue
        label = srv.get("label", srv_id.upper())
        keyboard.append([InlineKeyboardButton(f"📋 {label}", callback_data=f"admin_list_{srv_id}")])

    keyboard.append([InlineKeyboardButton("🔙 Kembali", callback_data="admin")])

    await query.edit_message_text(
        "📋 <b>List Akun — Pilih Server</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n"
        "Pilih server yang ingin ditampilkan akunnya:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def cb_admin_list(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """List akun satu server spesifik (indo atau sg)."""
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id): return

    srv_id = query.data.replace("admin_list_", "")
    srv    = get_server_info(srv_id)
    label  = srv.get("label", srv_id.upper())
    today  = now_wib().strftime("%Y-%m-%d")

    out = [f"📋 <b>Akun Server {label}</b>\n━━━━━━━━━━━━━━━━━━━━━━━"]

    if is_local_server(srv_id):
        # Baca dari USERS_DB lokal
        count = 0
        aktif = 0
        exp   = 0
        if Path(USERS_DB).exists():
            for line in Path(USERS_DB).read_text().splitlines():
                if not line.strip(): continue
                parts = line.split("|")
                if len(parts) < 3: continue
                count += 1
                st = "❌" if is_expired(parts[2]) else "✅"
                if not is_expired(parts[2]): aktif += 1
                else: exp += 1
                if count <= 50:
                    out.append(f"{count}. {st} <code>{parts[0]}</code> | Exp: {parts[2]}")
        if count == 0:
            out.append("Belum ada akun.")
        else:
            if count > 50: out.append(f"... (+{count - 50} akun lainnya)")
            out.append(f"\n📊 Total: <b>{count}</b> | ✅ Aktif: <b>{aktif}</b> | ❌ Expired: <b>{exp}</b>")
    else:
        # Ambil dari API remote
        result = api_call_remote(srv_id, "list_accounts", {})
        if result.get("ok"):
            akuns = result.get("accounts", [])
            aktif = 0
            exp   = 0
            for i, a in enumerate(akuns[:50], 1):
                st = "❌" if is_expired(a.get("exp", "9999-12-31")) else "✅"
                if not is_expired(a.get("exp", "9999-12-31")): aktif += 1
                else: exp += 1
                out.append(f"{i}. {st} <code>{a.get('username','?')}</code> | Exp: {a.get('exp','?')}")
            if not akuns:
                out.append("Belum ada akun.")
            else:
                if len(akuns) > 50: out.append(f"... (+{len(akuns) - 50} akun lainnya)")
                out.append(f"\n📊 Total: <b>{len(akuns)}</b> | ✅ Aktif: <b>{aktif}</b> | ❌ Expired: <b>{exp}</b>")
        else:
            out.append(f"❌ Gagal ambil data:\n<code>{result.get('error','?')}</code>")

    await query.edit_message_text(
        "\n".join(out), parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Kembali", callback_data="admin_list_menu")]
        ])
    )


async def cb_admin_list_all(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """List akun SEMUA server (Indo + SG) digabung."""
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id): return

    srvs  = load_servers()
    today = now_wib().strftime("%Y-%m-%d")
    out   = ["🌐 <b>List Akun — Semua Server</b>\n━━━━━━━━━━━━━━━━━━━━━━━"]

    grand_total = 0
    grand_aktif = 0
    grand_exp   = 0

    for srv_id, srv in srvs.items():
        if not srv.get("enabled"): continue
        label = srv.get("label", srv_id.upper())
        out.append(f"\n{label}")
        out.append("─────────────────────")

        if is_local_server(srv_id):
            count = 0
            aktif = 0
            exp   = 0
            if Path(USERS_DB).exists():
                for line in Path(USERS_DB).read_text().splitlines():
                    if not line.strip(): continue
                    parts = line.split("|")
                    if len(parts) < 3: continue
                    count += 1
                    st = "❌" if is_expired(parts[2]) else "✅"
                    if not is_expired(parts[2]): aktif += 1
                    else: exp += 1
                    if count <= 30:
                        out.append(f"{count}. {st} <code>{parts[0]}</code> | Exp: {parts[2]}")
            if count == 0:
                out.append("  Belum ada akun.")
            else:
                if count > 30: out.append(f"  ... (+{count - 30} lainnya)")
                out.append(f"  📊 {count} akun | ✅ {aktif} aktif | ❌ {exp} expired")
                grand_total += count; grand_aktif += aktif; grand_exp += exp
        else:
            result = api_call_remote(srv_id, "list_accounts", {})
            if result.get("ok"):
                akuns = result.get("accounts", [])
                aktif = 0
                exp   = 0
                for i, a in enumerate(akuns[:30], 1):
                    st = "❌" if is_expired(a.get("exp", "9999-12-31")) else "✅"
                    if not is_expired(a.get("exp", "9999-12-31")): aktif += 1
                    else: exp += 1
                    out.append(f"{i}. {st} <code>{a.get('username','?')}</code> | Exp: {a.get('exp','?')}")
                if not akuns:
                    out.append("  Belum ada akun.")
                else:
                    if len(akuns) > 30: out.append(f"  ... (+{len(akuns) - 30} lainnya)")
                    out.append(f"  📊 {len(akuns)} akun | ✅ {aktif} aktif | ❌ {exp} expired")
                    grand_total += len(akuns); grand_aktif += aktif; grand_exp += exp
            else:
                out.append(f"  ❌ Gagal: <code>{result.get('error','?')}</code>")

    out.append("\n━━━━━━━━━━━━━━━━━━━━━━━")
    out.append(f"📊 <b>Grand Total: {grand_total} akun</b>")
    out.append(f"✅ Aktif: <b>{grand_aktif}</b>  |  ❌ Expired: <b>{grand_exp}</b>")

    await query.edit_message_text(
        "\n".join(out), parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Kembali", callback_data="admin_list_menu")]
        ])
    )

async def cb_admin_stat(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id): return
    today = now_wib().strftime("%Y-%m-%d")
    total = aktif = expired = 0
    if Path(USERS_DB).exists():
        for line in Path(USERS_DB).read_text().splitlines():
            if not line.strip(): continue
            parts = line.split("|")
            if len(parts) >= 3:
                total += 1
                if not is_expired(parts[2]): aktif += 1
                else: expired += 1
    brand     = CFG.get("BRAND", "OGH-ZIV")
    admin_ids = CFG.get("ADMIN_IDS", [])
    owner_id  = CFG.get("OWNER_ID", 0)
    reseller_count = len([x for x in admin_ids if x != owner_id])

    await query.edit_message_text(
        f"📊 <b>Statistik — {brand}</b>\n\n"
        f"🖥 IP     : <code>{get_ip()}</code>\n"
        f"🌐 Domain : <code>{get_domain()}</code>\n"
        f"🔌 Port   : <code>{get_port()}</code>\n\n"
        f"👥 Total Akun  : <b>{total}</b>\n"
        f"✅ Aktif       : <b>{aktif}</b>\n"
        f"❌ Expired     : <b>{expired}</b>\n\n"
        f"👑 Owner       : <b>1</b>\n"
        f"🏪 Reseller    : <b>{reseller_count}</b>\n"
        f"💳 DANA        : <code>{CFG.get('DANA_NUMBER', '-')}</code>\n"
        f"🔲 QRIS        : {'✅ Aktif' if qris_aktif() else '❌ Nonaktif'}",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Kembali", callback_data="admin")]])
    )

# ============================================================
#  OWNER ONLY — KELOLA SERVER INDO & SG
# ============================================================
async def cb_admin_kelola_server(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_owner(query.from_user.id):
        await _akses_ditolak(query, "Kelola Server"); return

    srvs  = load_servers()
    total = len(srvs)
    lines = [f"🌍 <b>Kelola Multi-Server</b>  (<b>{total}</b> server terdaftar)\n━━━━━━━━━━━━━━━━━━━━━━━"]
    for srv_id, srv in srvs.items():
        icon  = server_status_icon(srv)
        label = srv.get("label", srv_id.upper())
        host  = srv.get("host", "-") or "-"
        port  = srv.get("port", "5667")
        stock = server_stock_text(srv)
        mode  = "Lokal" if not srv.get("api_url") else "Remote"
        enabled_text = "✅ Aktif" if srv.get("enabled") else "❌ Nonaktif"
        lines.append(
            f"\n{icon} <b>{label}</b>\n"
            f"   Host  : <code>{host}:{port}</code>\n"
            f"   Status: {enabled_text}  |  Mode: {mode}\n"
            f"   Stok  : {stock}"
        )

    keyboard = []
    for srv_id, srv in srvs.items():
        label = srv.get("label", srv_id.upper())
        icon  = server_status_icon(srv)
        keyboard.append([InlineKeyboardButton(
            f"{icon} Edit {label}", callback_data=f"admin_srv_edit_{srv_id}"
        )])

    keyboard.append([
        InlineKeyboardButton("➕ Tambah Server", callback_data="admin_srv_tambah"),
        InlineKeyboardButton("🗑 Hapus Server",  callback_data="admin_srv_hapus_menu"),
    ])
    keyboard.append([InlineKeyboardButton("📊 Status Semua Server", callback_data="admin_srv_status")])
    keyboard.append([InlineKeyboardButton("🔙 Kembali",              callback_data="admin")])

    await query.edit_message_text(
        "\n".join(lines), parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def cb_admin_srv_tambah(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Langkah 1 — minta nama/region server baru."""
    query = update.callback_query
    await query.answer()
    if not is_owner(query.from_user.id): return

    ctx.user_data["admin_action"] = "srv_tambah_nama"
    await query.edit_message_text(
        "➕ <b>Tambah Server Baru</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Kirim <b>nama region</b> server baru.\n\n"
        "Contoh:\n"
        "• <code>SG 01</code>\n"
        "• <code>🇸🇬 Singapore 1</code>\n"
        "• <code>🇯🇵 Japan</code>\n"
        "• <code>🇩🇪 Germany</code>\n\n"
        "<i>Nama ini yang akan tampil di menu bot.</i>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Batal", callback_data="admin_kelola_server")
        ]])
    )


async def cb_admin_srv_hapus_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Tampilkan daftar server untuk dipilih dan dihapus."""
    query = update.callback_query
    await query.answer()
    if not is_owner(query.from_user.id): return

    srvs = load_servers()
    if len(srvs) <= 1:
        await query.answer("⚠️ Minimal harus ada 1 server!", show_alert=True)
        return

    keyboard = []
    for srv_id, srv in srvs.items():
        label = srv.get("label", srv_id.upper())
        icon  = server_status_icon(srv)
        keyboard.append([InlineKeyboardButton(
            f"🗑 Hapus {icon} {label}", callback_data=f"admin_srv_hapus_konfirm_{srv_id}"
        )])
    keyboard.append([InlineKeyboardButton("🔙 Batal", callback_data="admin_kelola_server")])

    await query.edit_message_text(
        "🗑 <b>Hapus Server</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "⚠️ Pilih server yang ingin dihapus:\n"
        "<i>(Data akun di server tersebut tidak ikut terhapus)</i>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def cb_admin_srv_hapus_konfirm(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Konfirmasi hapus server."""
    query  = update.callback_query
    await query.answer()
    if not is_owner(query.from_user.id): return

    srv_id = query.data.replace("admin_srv_hapus_konfirm_", "")
    srv    = get_server_info(srv_id)
    label  = srv.get("label", srv_id)

    await query.edit_message_text(
        f"⚠️ <b>Konfirmasi Hapus Server</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Yakin ingin menghapus server:\n"
        f"<b>{label}</b>  (<code>{srv.get('host','-')}</code>)\n\n"
        f"❗ Tindakan ini tidak bisa dibatalkan.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Ya, Hapus",  callback_data=f"admin_srv_hapus_do_{srv_id}"),
             InlineKeyboardButton("❌ Batal",       callback_data="admin_kelola_server")],
        ])
    )


async def cb_admin_srv_hapus_do(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Eksekusi hapus server."""
    query  = update.callback_query
    await query.answer()
    if not is_owner(query.from_user.id): return

    srv_id = query.data.replace("admin_srv_hapus_do_", "")
    srvs   = load_servers()

    if len(srvs) <= 1:
        await query.answer("⚠️ Tidak bisa hapus — minimal 1 server harus ada!", show_alert=True)
        return

    label = srvs.get(srv_id, {}).get("label", srv_id)
    if srv_id in srvs:
        del srvs[srv_id]
        save_servers(srvs)
        await query.answer(f"✅ Server {label} berhasil dihapus!", show_alert=True)

    # Kembali ke kelola server
    query.data = "admin_kelola_server"
    await cb_admin_kelola_server(update, ctx)

async def cb_admin_srv_edit(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Menu edit satu server."""
    query  = update.callback_query
    await query.answer()
    if not is_owner(query.from_user.id):
        await _akses_ditolak(query, "Edit Server"); return

    srv_id = query.data.replace("admin_srv_edit_", "")
    srv    = get_server_info(srv_id)
    label  = srv.get("label", srv_id.upper())
    host   = srv.get("host", "-") or "-"
    port   = srv.get("port", "5667")
    stock  = server_stock_text(srv)
    api    = srv.get("api_url", "") or "(Lokal — tidak perlu API URL)"
    enabled = srv.get("enabled", False)

    keyboard = [
        [InlineKeyboardButton(
            "❌ Nonaktifkan" if enabled else "✅ Aktifkan",
            callback_data=f"admin_srv_toggle_{srv_id}"
        )],
        [InlineKeyboardButton("✏️ Ubah Nama Region",    callback_data=f"admin_srv_rename_{srv_id}")],
        [InlineKeyboardButton("🖥 Set Host/IP",          callback_data=f"admin_srv_sethost_{srv_id}")],
        [InlineKeyboardButton("🔌 Set Port",             callback_data=f"admin_srv_setport_{srv_id}")],
        [InlineKeyboardButton("🔗 Set API URL (Remote)", callback_data=f"admin_srv_setapi_{srv_id}")],
        [InlineKeyboardButton("🔑 Set API Key",          callback_data=f"admin_srv_setkey_{srv_id}")],
        [InlineKeyboardButton("📦 Set Stok Slot",        callback_data=f"admin_srv_setstock_{srv_id}")],
        [InlineKeyboardButton("🔄 Restart Service",      callback_data=f"admin_srv_restart_{srv_id}")],
        [InlineKeyboardButton("📋 Lihat Akun Server",    callback_data=f"admin_srv_list_{srv_id}")],
        [InlineKeyboardButton("🔙 Kembali",               callback_data="admin_kelola_server")],
    ]

    await query.edit_message_text(
        f"⚙️ <b>Edit Server — {label}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🖥 Host   : <code>{host}:{port}</code>\n"
        f"📡 Mode   : {'Remote API' if srv.get('api_url') else 'Lokal (bot berjalan di VPS ini)'}\n"
        f"🔗 API URL: <code>{api}</code>\n"
        f"📦 Stok   : {stock}\n"
        f"Status    : {'✅ Aktif' if enabled else '❌ Nonaktif'}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>Pilih pengaturan yang ingin diubah:</i>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def cb_admin_srv_toggle(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query  = update.callback_query
    await query.answer()
    if not is_owner(query.from_user.id): return
    srv_id = query.data.replace("admin_srv_toggle_", "")
    srvs   = load_servers()
    if srv_id not in srvs: return
    srvs[srv_id]["enabled"] = not srvs[srv_id].get("enabled", False)
    save_servers(srvs)
    status = "✅ Diaktifkan" if srvs[srv_id]["enabled"] else "❌ Dinonaktifkan"
    await query.answer(f"Server {status}", show_alert=True)
    # Refresh halaman edit
    query.data = f"admin_srv_edit_{srv_id}"
    await cb_admin_srv_edit(update, ctx)

async def cb_admin_srv_rename(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Ubah nama/label region server."""
    query  = update.callback_query
    await query.answer()
    if not is_owner(query.from_user.id): return
    srv_id = query.data.replace("admin_srv_rename_", "")
    srv    = get_server_info(srv_id)
    ctx.user_data["admin_action"] = f"srv_rename_{srv_id}"
    await query.edit_message_text(
        f"✏️ <b>Ubah Nama Region — {srv.get('label', srv_id)}</b>\n\n"
        f"Nama saat ini: <b>{srv.get('label', srv_id)}</b>\n\n"
        f"Kirim nama region baru:\n"
        f"<i>Contoh: 🇸🇬 Singapore 1 / 🇯🇵 Japan / ID-JKT</i>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Batal", callback_data=f"admin_srv_edit_{srv_id}")
        ]])
    )

async def cb_admin_srv_sethost(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query  = update.callback_query
    await query.answer()
    if not is_owner(query.from_user.id): return
    srv_id = query.data.replace("admin_srv_sethost_", "")
    srv    = get_server_info(srv_id)
    ctx.user_data["admin_action"] = f"srv_sethost_{srv_id}"
    await query.edit_message_text(
        f"🖥 <b>Set Host/IP — {srv.get('label',srv_id)}</b>\n\n"
        f"Host saat ini: <code>{srv.get('host','-') or '-'}</code>\n\n"
        f"Kirim IP atau domain VPS {srv.get('label',srv_id)}:\n"
        f"<i>Contoh: 103.x.x.x atau vpn.domain.com</i>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Batal", callback_data=f"admin_srv_edit_{srv_id}")]])
    )

async def cb_admin_srv_setport(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query  = update.callback_query
    await query.answer()
    if not is_owner(query.from_user.id): return
    srv_id = query.data.replace("admin_srv_setport_", "")
    srv    = get_server_info(srv_id)
    ctx.user_data["admin_action"] = f"srv_setport_{srv_id}"
    await query.edit_message_text(
        f"🔌 <b>Set Port — {srv.get('label',srv_id)}</b>\n\n"
        f"Port saat ini: <code>{srv.get('port','5667')}</code>\n\n"
        f"Kirim nomor port ZIVPN di server ini:\n<i>Contoh: 5667</i>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Batal", callback_data=f"admin_srv_edit_{srv_id}")]])
    )

async def cb_admin_srv_setapi(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query  = update.callback_query
    await query.answer()
    if not is_owner(query.from_user.id): return
    srv_id = query.data.replace("admin_srv_setapi_", "")
    srv    = get_server_info(srv_id)
    ctx.user_data["admin_action"] = f"srv_setapi_{srv_id}"
    await query.edit_message_text(
        f"🔗 <b>Set API URL — {srv.get('label',srv_id)}</b>\n\n"
        f"API URL saat ini: <code>{srv.get('api_url','-') or 'Lokal'}</code>\n\n"
        f"Kirim URL API worker di VPS {srv.get('label',srv_id)}:\n"
        f"<i>Contoh: http://103.x.x.x:8765</i>\n\n"
        f"ℹ️ Kosongkan (ketik <code>-</code>) jika bot berjalan di VPS ini (mode lokal).",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Batal", callback_data=f"admin_srv_edit_{srv_id}")]])
    )

async def cb_admin_srv_setkey(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query  = update.callback_query
    await query.answer()
    if not is_owner(query.from_user.id): return
    srv_id = query.data.replace("admin_srv_setkey_", "")
    srv    = get_server_info(srv_id)
    ctx.user_data["admin_action"] = f"srv_setkey_{srv_id}"
    await query.edit_message_text(
        f"🔑 <b>Set API Key — {srv.get('label',srv_id)}</b>\n\n"
        f"API Key digunakan untuk autentikasi antar VPS.\n"
        f"Harus sama dengan API_KEY di file <code>zivpn_api_worker.py</code> di VPS tersebut.\n\n"
        f"Kirim API Key baru:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Batal", callback_data=f"admin_srv_edit_{srv_id}")]])
    )

async def cb_admin_srv_setstock(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query  = update.callback_query
    await query.answer()
    if not is_owner(query.from_user.id): return
    srv_id = query.data.replace("admin_srv_setstock_", "")
    srv    = get_server_info(srv_id)
    ctx.user_data["admin_action"] = f"srv_setstock_{srv_id}"
    await query.edit_message_text(
        f"📦 <b>Set Stok Slot — {srv.get('label',srv_id)}</b>\n\n"
        f"Stok saat ini: <b>{server_stock_text(srv)}</b>\n\n"
        f"Kirim jumlah stok slot:\n"
        f"• <code>-1</code> = Unlimited\n"
        f"• <code>0</code>  = Habis (tidak tampil)\n"
        f"• <code>10</code> = 10 slot tersisa",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Batal", callback_data=f"admin_srv_edit_{srv_id}")]])
    )

async def cb_admin_srv_restart(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query  = update.callback_query
    await query.answer()
    if not is_owner(query.from_user.id): return
    srv_id = query.data.replace("admin_srv_restart_", "")
    srv    = get_server_info(srv_id)
    label  = srv.get("label", srv_id)
    await query.edit_message_text(f"⏳ Me-restart service ZIVPN di {label}...", parse_mode="HTML")

    if is_local_server(srv_id):
        try:
            subprocess.run(["systemctl", "restart", "zivpn"], timeout=15, capture_output=True)
            msg = f"✅ Service ZIVPN di {label} berhasil di-restart."
        except Exception as e:
            msg = f"❌ Gagal restart: {e}"
    else:
        result = api_call_remote(srv_id, "restart_service", {})
        msg = f"✅ Restart {label} berhasil." if result.get("ok") else f"❌ Gagal: {result.get('error','?')}"

    await query.edit_message_text(
        msg, parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Kembali", callback_data=f"admin_srv_edit_{srv_id}")]])
    )

async def cb_admin_srv_list(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query  = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id): return
    srv_id = query.data.replace("admin_srv_list_", "")
    srv    = get_server_info(srv_id)
    label  = srv.get("label", srv_id)

    if is_local_server(srv_id):
        today = now_wib().strftime("%Y-%m-%d")
        out   = [f"📋 <b>Akun Server {label}</b>\n━━━━━━━━━━━━━━━━━━━━━━━"]
        count = 0
        if Path(USERS_DB).exists():
            for i, line in enumerate(Path(USERS_DB).read_text().splitlines(), 1):
                if not line.strip(): continue
                parts = line.split("|")
                if len(parts) < 3: continue
                status = "❌" if is_expired(parts[2]) else "✅"
                out.append(f"{i}. {status} <code>{parts[0]}</code> | Exp: {parts[2]}")
                count += 1
                if count >= 30: out.append("... (max 30)"); break
        if count == 0: out.append("Belum ada akun.")
    else:
        result = api_call_remote(srv_id, "list_accounts", {})
        if result.get("ok"):
            out   = [f"📋 <b>Akun Server {label}</b>\n━━━━━━━━━━━━━━━━━━━━━━━"]
            akuns = result.get("accounts", [])
            for i, a in enumerate(akuns[:30], 1):
                out.append(f"{i}. <code>{a.get('username','?')}</code> | Exp: {a.get('exp','?')}")
            if not akuns: out.append("Belum ada akun.")
        else:
            out = [f"❌ Gagal ambil data dari {label}:\n{result.get('error','?')}"]

    await query.edit_message_text(
        "\n".join(out), parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Kembali", callback_data=f"admin_srv_edit_{srv_id}")]])
    )

async def cb_admin_srv_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Cek status semua server sekaligus."""
    query = update.callback_query
    await query.answer()
    if not is_owner(query.from_user.id): return
    await query.edit_message_text("⏳ Memeriksa status semua server...", parse_mode="HTML")

    srvs  = load_servers()
    lines = ["📊 <b>Status Semua Server</b>\n━━━━━━━━━━━━━━━━━━━━━━━"]
    for srv_id, srv in srvs.items():
        icon  = server_status_icon(srv)
        label = srv.get("label", srv_id.upper())
        if not srv.get("enabled") or not srv.get("host"):
            lines.append(f"\n{icon} <b>{label}</b>\n   ⛔ Belum dikonfigurasi")
            continue
        if is_local_server(srv_id):
            # Cek service lokal
            result = subprocess.run(
                ["systemctl", "is-active", "zivpn"],
                capture_output=True, text=True
            )
            status = "🟢 AKTIF" if result.stdout.strip() == "active" else "🔴 MATI"
            total  = 0
            aktif  = 0
            today  = now_wib().strftime("%Y-%m-%d")
            if Path(USERS_DB).exists():
                for line in Path(USERS_DB).read_text().splitlines():
                    if not line.strip(): continue
                    parts = line.split("|")
                    if len(parts) >= 3:
                        total += 1
                        if not is_expired(parts[2]): aktif += 1
            lines.append(
                f"\n{icon} <b>{label}</b> — {status}\n"
                f"   Akun: {total} total, {aktif} aktif\n"
                f"   Host: <code>{srv.get('host','-')}:{srv.get('port','5667')}</code>"
            )
        else:
            result = api_call_remote(srv_id, "get_info", {})
            if result.get("ok"):
                lines.append(
                    f"\n{icon} <b>{label}</b> — 🟢 ONLINE\n"
                    f"   Akun: {result.get('total_akun','?')} total, {result.get('aktif_akun','?')} aktif\n"
                    f"   Host: <code>{srv.get('host','-')}:{srv.get('port','5667')}</code>"
                )
            else:
                lines.append(
                    f"\n{icon} <b>{label}</b> — 🔴 OFFLINE\n"
                    f"   Error: {result.get('error','?')}\n"
                    f"   Host: <code>{srv.get('host','-')}:{srv.get('port','5667')}</code>"
                )

    await query.edit_message_text(
        "\n".join(lines), parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Kembali", callback_data="admin_kelola_server")]
        ])
    )

# ============================================================
#  OWNER ONLY — KELOLA RESELLER
# ============================================================
async def cb_admin_kelola_admin(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_owner(query.from_user.id):
        await _akses_ditolak(query, "Kelola Reseller"); return

    admin_ids = CFG.get("ADMIN_IDS", [])
    owner_id  = CFG.get("OWNER_ID", 0)
    lines = ["👥 <b>Kelola Reseller Bot</b>\n━━━━━━━━━━━━━━━━━━━━━━━"]
    lines.append(f"👑 <b>Owner</b>")
    lines.append(f"   <code>{owner_id}</code> ← Kamu\n")
    resellers = [x for x in admin_ids if x != owner_id]
    if resellers:
        lines.append(f"🏪 <b>Reseller ({len(resellers)} orang)</b>")
        for i, aid in enumerate(resellers, 1):
            lines.append(f"   {i}. <code>{aid}</code>")
    else:
        lines.append("🏪 <b>Reseller</b> : Belum ada")
    lines.append(f"\n━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("💡 Reseller hanya bisa buat/hapus akun & lihat statistik.")

    keyboard = [
        [InlineKeyboardButton("➕ Tambah Reseller",  callback_data="admin_tambah_reseller")],
        [InlineKeyboardButton("➖ Hapus Reseller",   callback_data="admin_hapus_reseller")],
        [InlineKeyboardButton("🔙 Kembali",          callback_data="admin")],
    ]
    await query.edit_message_text(
        "\n".join(lines), parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def cb_admin_tambah_reseller(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_owner(query.from_user.id):
        await _akses_ditolak(query, "Tambah Reseller"); return
    ctx.user_data["admin_action"] = "tambah_reseller"
    await query.edit_message_text(
        "➕ <b>Tambah Reseller</b>\n\n"
        "Kirim <b>Chat ID Telegram</b> orang yang ingin dijadikan reseller:\n"
        "<i>(Angka, contoh: 123456789)</i>\n\n"
        "💡 Cara cari Chat ID: suruh dia kirim pesan ke @userinfobot\n\n"
        "📋 <b>Hak akses reseller:</b>\n"
        "✅ Buat akun gratis (manual & auto)\n"
        "✅ Hapus akun VPN\n"
        "✅ Lihat list & statistik akun\n"
        "✅ Konfirmasi pembayaran manual\n"
        "❌ Tidak bisa ubah pembayaran/DANA/QRIS\n"
        "❌ Tidak bisa tambah/hapus reseller lain\n"
        "❌ Tidak bisa ubah pengaturan bot",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Batal", callback_data="admin_kelola_admin")]])
    )

async def cb_admin_hapus_reseller(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query    = update.callback_query
    await query.answer()
    if not is_owner(query.from_user.id):
        await _akses_ditolak(query, "Hapus Reseller"); return

    admin_ids = CFG.get("ADMIN_IDS", [])
    owner_id  = CFG.get("OWNER_ID", 0)
    resellers = [x for x in admin_ids if x != owner_id]

    if not resellers:
        await query.edit_message_text(
            "⚠️ Belum ada reseller yang terdaftar.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Kembali", callback_data="admin_kelola_admin")]])
        )
        return

    ctx.user_data["admin_action"] = "hapus_reseller"
    lines = ["➖ <b>Hapus Reseller</b>\n\nDaftar reseller saat ini:"]
    for i, aid in enumerate(resellers, 1):
        lines.append(f"{i}. <code>{aid}</code>")
    lines.append("\nKirim <b>Chat ID</b> reseller yang ingin dihapus:")
    await query.edit_message_text(
        "\n".join(lines), parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Batal", callback_data="admin_kelola_admin")]])
    )

# ============================================================
#  OWNER ONLY — PENGATURAN PEMBAYARAN
# ============================================================
async def cb_admin_pembayaran(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_owner(query.from_user.id):
        await _akses_ditolak(query, "Pengaturan Pembayaran"); return

    dana_num  = CFG.get("DANA_NUMBER", "-")
    dana_name = CFG.get("DANA_NAME", "-")
    qris_on   = qris_aktif()
    keyboard = [
        [InlineKeyboardButton("📱 Ubah Nomor DANA",     callback_data="admin_ubah_dana_num")],
        [InlineKeyboardButton("👤 Ubah Nama A/N DANA",  callback_data="admin_ubah_dana_name")],
        [InlineKeyboardButton("🔲 Upload / Ganti QRIS", callback_data="admin_upload_qris")],
        [InlineKeyboardButton("❌ Nonaktifkan QRIS" if qris_on else "✅ Aktifkan QRIS",
                              callback_data="admin_qris_off" if qris_on else "admin_qris_on")],
        [InlineKeyboardButton("🔙 Kembali", callback_data="admin")],
    ]
    await query.edit_message_text(
        f"💳 <b>Pengaturan Pembayaran</b>\n"
        f"<i>Hanya Owner yang dapat mengubah ini</i>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📱 No. DANA : <code>{dana_num}</code>\n"
        f"👤 A/N DANA : <b>{dana_name}</b>\n"
        f"🔲 QRIS     : {'✅ Aktif' if qris_on else '❌ Nonaktif'}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n\nPilih yang ingin diubah:",
        parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def cb_admin_ubah_dana_num(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    if not is_owner(query.from_user.id):
        await _akses_ditolak(query, "Ubah Nomor DANA"); return
    ctx.user_data["admin_action"] = "ubah_dana_num"
    await query.edit_message_text(
        f"📱 <b>Ubah Nomor DANA</b>\n\nNomor saat ini: <code>{CFG.get('DANA_NUMBER', '-')}</code>\n\nKirim nomor DANA baru:\n<i>(Contoh: 08123456789)</i>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Batal", callback_data="admin_pembayaran")]])
    )

async def cb_admin_ubah_dana_name(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    if not is_owner(query.from_user.id):
        await _akses_ditolak(query, "Ubah Nama A/N DANA"); return
    ctx.user_data["admin_action"] = "ubah_dana_name"
    await query.edit_message_text(
        f"👤 <b>Ubah Nama A/N DANA</b>\n\nNama saat ini: <b>{CFG.get('DANA_NAME', '-')}</b>\n\nKirim nama pemilik rekening DANA yang baru:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Batal", callback_data="admin_pembayaran")]])
    )

async def cb_admin_upload_qris(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    if not is_owner(query.from_user.id):
        await _akses_ditolak(query, "Upload QRIS"); return
    ctx.user_data["admin_action"] = "upload_qris"
    await query.edit_message_text(
        "🔲 <b>Upload Gambar QRIS</b>\n\n"
        "Kirim <b>foto gambar QRIS</b> kamu ke chat ini sekarang.\n\n"
        "💡 Tips:\n"
        "• Gunakan gambar QRIS yang jelas\n"
        "• Format JPG atau PNG\n"
        "• Setelah diupload, QRIS langsung aktif",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Batal", callback_data="admin_pembayaran")]])
    )

async def cb_admin_qris_toggle(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    if not is_owner(query.from_user.id):
        await _akses_ditolak(query, "Toggle QRIS"); return
    if query.data == "admin_qris_on":
        if not Path(QRIS_IMG).exists():
            await query.edit_message_text(
                "⚠️ Belum ada gambar QRIS!\n\nUpload dulu melalui menu <b>Upload / Ganti QRIS</b>.",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Kembali", callback_data="admin_pembayaran")]])
            )
            return
        save_config_key("QRIS_ENABLED", "1")
        msg = "✅ QRIS <b>diaktifkan!</b>"
    else:
        save_config_key("QRIS_ENABLED", "0")
        msg = "❌ QRIS <b>dinonaktifkan.</b>"
    await query.edit_message_text(
        msg, parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Pengaturan Pembayaran", callback_data="admin_pembayaran")]])
    )

# ============================================================
#  OWNER ONLY — PENGATURAN BOT
# ============================================================
async def cb_admin_settings(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    if not is_owner(query.from_user.id):
        await _akses_ditolak(query, "Pengaturan Bot"); return
    keyboard = [
        [InlineKeyboardButton("🏷️ Ubah Nama Brand",       callback_data="admin_ubah_brand")],
        [InlineKeyboardButton("📣 Ubah Username Admin TG", callback_data="admin_ubah_admintg")],
        [InlineKeyboardButton("🔑 Ganti Token Bot",         callback_data="admin_ganti_token")],
        [InlineKeyboardButton("🔙 Kembali",                 callback_data="admin")],
    ]
    await query.edit_message_text(
        f"⚙️ <b>Pengaturan Bot</b>\n"
        f"<i>Hanya Owner yang dapat mengubah ini</i>\n\n"
        f"🏷️ Brand    : <b>{CFG.get('BRAND', '-')}</b>\n"
        f"📣 Admin TG : <b>{CFG.get('ADMIN_TG', '-')}</b>\n\n"
        f"Pilih yang ingin diubah:",
        parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def cb_admin_ubah_brand(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    if not is_owner(query.from_user.id):
        await _akses_ditolak(query, "Ubah Brand"); return
    ctx.user_data["admin_action"] = "ubah_brand"
    await query.edit_message_text(
        f"🏷️ <b>Ubah Nama Brand</b>\n\nBrand saat ini: <b>{CFG.get('BRAND', '-')}</b>\n\nKirim nama brand baru:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Batal", callback_data="admin_settings")]])
    )

async def cb_admin_ubah_admintg(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    if not is_owner(query.from_user.id):
        await _akses_ditolak(query, "Ubah Admin TG"); return
    ctx.user_data["admin_action"] = "ubah_admintg"
    await query.edit_message_text(
        f"📣 <b>Ubah Username Admin TG</b>\n\nSaat ini: <b>{CFG.get('ADMIN_TG', '-')}</b>\n\nKirim username Telegram admin (dengan @):\n<i>Contoh: @namaadmin</i>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Batal", callback_data="admin_settings")]])
    )

async def cb_admin_ganti_token(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    if not is_owner(query.from_user.id):
        await _akses_ditolak(query, "Ganti Token Bot"); return
    ctx.user_data["admin_action"] = "ganti_token"
    await query.edit_message_text(
        "🔑 <b>Ganti Token Bot</b>\n\n"
        "⚠️ Bot perlu di-<b>restart</b> setelah token diganti.\n\n"
        "Cara dapat token baru:\n"
        "1. Buka @BotFather di Telegram\n"
        "2. Ketik /mybots → pilih bot kamu\n"
        "3. API Token → Revoke current token\n"
        "4. Copy token baru dan kirim ke sini",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Batal", callback_data="admin_settings")]])
    )

# ============================================================
#  HANDLE TEXT — Semua Input Teks
# ============================================================
async def handle_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user         = update.effective_user
    text         = update.message.text.strip()
    action       = ctx.user_data.get("action")
    admin_action = ctx.user_data.get("admin_action")

    # ── Sync state konfirm SocksIP dari admin ──
    konfirm_socksip = ctx.bot_data.get(f"konfirm_socksip_{user.id}")
    if konfirm_socksip and not ctx.user_data.get("socksip_ss_verified"):
        ctx.user_data["socksip_ss_verified"]      = True
        ctx.user_data["socksip_waiting_username"] = True
        ctx.user_data["socksip_paket_id"]         = konfirm_socksip.get("paket_id", "1")
        ctx.user_data["socksip_server_id"]        = konfirm_socksip.get("server_id", "udp_server1")
        ctx.user_data["vpn_type"]                 = "socksip"
        ctx.bot_data.pop(f"konfirm_socksip_{user.id}", None)

    # Sync state dari konfirm manual admin
    konfirm_data = ctx.bot_data.get(f"konfirm_{user.id}")
    if konfirm_data and not ctx.user_data.get("ss_verified"):
        ctx.user_data["ss_verified"]      = True
        ctx.user_data["waiting_username"] = True
        ctx.user_data["paket_id"]         = konfirm_data.get("paket_id", "1")
        ctx.bot_data.pop(f"konfirm_{user.id}", None)

    # Routing admin actions
    if is_admin(user.id) and admin_action:
        await _handle_admin_input(update, ctx, admin_action, text)
        return

    # ── Routing SocksIP user flow ──
    if ctx.user_data.get("vpn_type") == "socksip":
        if await _handle_socksip_user_text(update, ctx, text):
            return

    # Flow: input username setelah bayar
    if ctx.user_data.get("waiting_username") and ctx.user_data.get("ss_verified"):
        username = text.lower().strip()
        if len(username) < 4:
            await update.message.reply_text("❌ Username minimal <b>4 karakter</b>. Coba lagi:", parse_mode="HTML"); return
        if not re.match(r"^[a-z0-9_]+$", username):
            await update.message.reply_text("❌ Username hanya huruf kecil, angka, underscore. Coba lagi:", parse_mode="HTML"); return
        if user_exists(username):
            await update.message.reply_text(f"❌ Username <code>{username}</code> sudah dipakai. Pilih lain:", parse_mode="HTML"); return
        ctx.user_data["req_username"]     = username
        ctx.user_data["waiting_username"] = False
        ctx.user_data["waiting_password"] = True
        await update.message.reply_text(
            f"✅ Username <code>{username}</code> tersedia!\n\nKetik <b>password</b> yang kamu inginkan:\n<i>(Minimal 6 karakter)</i>",
            parse_mode="HTML"
        )
        return

    # Flow: input password setelah username
    if ctx.user_data.get("waiting_password") and ctx.user_data.get("ss_verified"):
        if len(text) < 6:
            await update.message.reply_text("❌ Password minimal <b>6 karakter</b>. Coba lagi:", parse_mode="HTML"); return
        username   = ctx.user_data.get("req_username")
        paket_id   = ctx.user_data.get("paket_id")
        srv_id     = ctx.user_data.get("server_id", "indo")
        paket_info = PAKET.get(paket_id, PAKET["1"])
        try:
            akun = create_account_on_server(
                srv_id, username, text,
                paket_info["hari"], paket_info["kuota"],
                paket_info["maxlogin"], f"TG:{user.username or user.first_name}"
            )
        except Exception as e:
            await update.message.reply_text(
                f"❌ <b>Gagal membuat akun di server.</b>\n\nError: {e}\nHubungi admin.",
                parse_mode="HTML"
            )
            ctx.user_data.clear()
            return
        ctx.user_data.clear()
        await update.message.reply_text(
            f"🎉 <b>Akun UDP Berhasil Dibuat!</b>\n\n" + format_akun_message(akun, srv_id),
            parse_mode="HTML"
        )
        brand = CFG.get("BRAND", "OGH-ZIV")
        srv   = get_server_info(srv_id)
        for admin_id in CFG.get("ADMIN_IDS", []):
            try:
                await ctx.bot.send_message(
                    admin_id,
                    f"💰 <b>Pesanan Baru — {brand}</b>\n━━━━━━━━━━━━━━━━━━━\n"
                    f"👤 Pembeli  : {user.full_name} (@{user.username or '-'})\n"
                    f"🌍 Server   : {srv.get('label','?')}\n"
                    f"📦 Paket    : {paket_info['nama']}\n"
                    f"💰 Nominal  : Rp {paket_info['harga']:,}\n"
                    f"🔑 Username : <code>{username}</code>\n"
                    f"📅 Expired  : {akun['exp']}",
                    parse_mode="HTML"
                )
            except: pass
        return

    # Cek akun user biasa
    if action == "cek_akun":
        info = get_account_info(text)
        ctx.user_data.pop("action", None)
        if not info:
            await update.message.reply_text(f"❌ Akun <code>{text}</code> tidak ditemukan.", parse_mode="HTML")
        else:
            await update.message.reply_text(format_akun_message(info), parse_mode="HTML")
        return

    await update.message.reply_text("Ketik /start untuk memulai.")

async def _handle_admin_input(update: Update, ctx: ContextTypes.DEFAULT_TYPE, admin_action: str, text: str):
    """Routing semua input teks dari admin (owner & reseller)"""

    # ── SOCKSIP: buat akun manual step 1 ──
    if admin_action == "socksip_manual_step1":
        username = text.lower().strip()
        if len(username) < 4 or len(username) > 16:
            await update.message.reply_text("❌ Username 4-16 karakter. Coba lagi:"); return
        if not re.match(r"^[a-z0-9_]+$", username):
            await update.message.reply_text("❌ Hanya huruf kecil, angka, underscore. Coba lagi:"); return
        if socksip_user_in_system(username):
            await update.message.reply_text(f"❌ Username <code>{username}</code> sudah ada. Kirim lain:", parse_mode="HTML"); return
        ctx.user_data.setdefault("socksip_manual_data", {})["username"] = username
        ctx.user_data["admin_action"] = "socksip_manual_step2"
        await update.message.reply_text(
            f"✅ Username: <code>{username}</code>\n\n✏️ <b>Langkah 2/3</b> — Ketik <b>password</b>:\n<i>(6-20 karakter)</i>",
            parse_mode="HTML"
        ); return

    # ── SOCKSIP: buat akun manual step 2 ──
    if admin_action == "socksip_manual_step2":
        if len(text) < 6 or len(text) > 20:
            await update.message.reply_text("❌ Password 6-20 karakter. Coba lagi:"); return
        ctx.user_data.setdefault("socksip_manual_data", {})["password"] = text
        ctx.user_data["admin_action"] = "socksip_manual_step3"
        await update.message.reply_text(
            "✅ Password disimpan.\n\n✏️ <b>Langkah 3/3</b> — Ketik <b>jumlah hari</b> aktif:\n<i>(1-360)</i>",
            parse_mode="HTML"
        ); return

    # ── SOCKSIP: buat akun manual step 3 → selesai ──
    if admin_action == "socksip_manual_step3":
        try:
            hari = int(text)
            if hari < 1 or hari > 360: raise ValueError
        except:
            await update.message.reply_text("❌ Hari harus angka 1-360. Coba lagi:"); return
        data     = ctx.user_data.get("socksip_manual_data", {})
        username = data.get("username")
        password = data.get("password")
        srv_id   = ctx.user_data.pop("socksip_manual_server_id", "udp_server1")
        srv      = get_socksip_server_info(srv_id)
        if not username or not password:
            await update.message.reply_text("❌ Data tidak lengkap. Mulai ulang.")
            ctx.user_data.pop("admin_action", None); return
        await update.message.reply_text(
            f"⏳ Membuat akun SocksIP di <b>{srv.get("label", srv_id)}</b>...", parse_mode="HTML"
        )
        try:
            akun = socksip_create_on_server(srv_id, username, password, hari, 2, "ADMIN-FREE-MANUAL")
        except Exception as e:
            ctx.user_data.pop("admin_action", None)
            ctx.user_data.pop("socksip_manual_data", None)
            await update.message.reply_text(f"❌ <b>Gagal membuat akun SocksIP.</b>\n\nError: {e}", parse_mode="HTML"); return
        ctx.user_data.pop("admin_action", None)
        ctx.user_data.pop("socksip_manual_data", None)
        await update.message.reply_text(
            f"🎉 <b>Akun SocksIP Berhasil Dibuat!</b>\n🌍 Server: <b>{srv.get("label", srv_id)}</b>\n\n"
            + format_socksip_akun(akun, srv_id), parse_mode="HTML"
        ); return

    # ── SOCKSIP: hapus akun ──
    if admin_action == "socksip_del":
        username = text.strip()
        ctx.user_data.pop("admin_action", None)
        deleted = False
        for sid in load_socksip_servers():
            try:
                if socksip_delete_on_server(sid, username): deleted = True; break
            except: pass
        if deleted:
            await update.message.reply_text(f"✅ Akun SocksIP <code>{username}</code> berhasil dihapus.", parse_mode="HTML")
        else:
            await update.message.reply_text(f"❌ Akun SocksIP <code>{username}</code> tidak ditemukan.", parse_mode="HTML")
        return

    # ── BUAT AKUN MANUAL — step 1: username ──────────────────
    if admin_action == "akun_manual_step1":
        username = text.lower().strip()
        if len(username) < 4 or not re.match(r"^[a-z0-9_]+$", username):
            await update.message.reply_text("❌ Username minimal 4 karakter (huruf kecil/angka/underscore). Coba lagi:"); return
        if user_exists(username):
            await update.message.reply_text(f"❌ Username <code>{username}</code> sudah ada. Kirim lain:", parse_mode="HTML"); return
        ctx.user_data["akun_manual_data"]["username"] = username
        ctx.user_data["admin_action"] = "akun_manual_step2"
        await update.message.reply_text(
            f"✅ Username: <code>{username}</code>\n\n✏️ <b>Langkah 2/4</b> — Ketik <b>password</b>:\n<i>(Minimal 6 karakter)</i>",
            parse_mode="HTML"
        ); return

    # ── BUAT AKUN MANUAL — step 2: password ──────────────────
    if admin_action == "akun_manual_step2":
        if len(text) < 6:
            await update.message.reply_text("❌ Password minimal 6 karakter. Coba lagi:"); return
        ctx.user_data["akun_manual_data"]["password"] = text
        ctx.user_data["admin_action"] = "akun_manual_step3"
        await update.message.reply_text(
            f"✅ Password disimpan.\n\n✏️ <b>Langkah 3/4</b> — Ketik <b>jumlah hari</b> aktif:\n<i>(Contoh: 30)</i>",
            parse_mode="HTML"
        ); return

    # ── BUAT AKUN MANUAL — step 3: hari ──────────────────────
    if admin_action == "akun_manual_step3":
        try:
            hari = int(text)
            if hari < 1: raise ValueError
        except:
            await update.message.reply_text("❌ Jumlah hari harus angka positif. Coba lagi:"); return
        ctx.user_data["akun_manual_data"]["hari"] = hari
        ctx.user_data["admin_action"] = "akun_manual_step4"
        await update.message.reply_text(
            f"✅ Durasi: <b>{hari} hari</b>\n\n✏️ <b>Langkah 4/4</b> — Ketik <b>max login device</b>:\n<i>(Contoh: 2)</i>",
            parse_mode="HTML"
        ); return

    # ── BUAT AKUN MANUAL — step 4: maxlogin → selesai ────────
    if admin_action == "akun_manual_step4":
        try:
            maxlogin = int(text)
            if maxlogin < 1: raise ValueError
        except:
            await update.message.reply_text("❌ Max login harus angka positif. Coba lagi:"); return
        data     = ctx.user_data.get("akun_manual_data", {})
        username = data.get("username")
        password = data.get("password")
        hari     = data.get("hari", 30)
        srv_id   = ctx.user_data.pop("akun_manual_server_id", "indo")
        if not username or not password:
            await update.message.reply_text("❌ Data tidak lengkap. Mulai ulang.")
            ctx.user_data.pop("admin_action", None); return
        srv = get_server_info(srv_id)
        await update.message.reply_text(
            f"⏳ Membuat akun di server <b>{srv.get('label', srv_id.upper())}</b>...",
            parse_mode="HTML"
        )
        try:
            akun = create_account_on_server(srv_id, username, password, hari, 0, maxlogin, "ADMIN-FREE-MANUAL")
        except Exception as e:
            ctx.user_data.pop("admin_action", None)
            ctx.user_data.pop("akun_manual_data", None)
            await update.message.reply_text(
                f"❌ <b>Gagal membuat akun di {srv.get('label', srv_id)}.</b>\n\nError: {e}",
                parse_mode="HTML"
            ); return
        ctx.user_data.pop("admin_action", None)
        ctx.user_data.pop("akun_manual_data", None)
        await update.message.reply_text(
            f"🎉 <b>Akun Berhasil Dibuat!</b>\n"
            f"🌍 Server: <b>{srv.get('label', srv_id.upper())}</b>\n\n"
            + format_akun_message(akun, srv_id), parse_mode="HTML"
        ); return

    # ── OWNER: TAMBAH RESELLER ────────────────────────────────
    if admin_action == "tambah_reseller":
        if not is_owner(update.effective_user.id):
            await update.message.reply_text("⛔ Hanya Owner yang bisa menambah reseller!"); return
        try: new_id = int(text)
        except ValueError:
            await update.message.reply_text("❌ Chat ID harus angka! Contoh: <code>123456789</code>", parse_mode="HTML"); return
        owner_id  = CFG.get("OWNER_ID", 0)
        if new_id == owner_id:
            await update.message.reply_text("⚠️ ID tersebut adalah Owner, tidak perlu ditambah lagi.", parse_mode="HTML")
            ctx.user_data.pop("admin_action", None); return
        admin_ids = CFG.get("ADMIN_IDS", [])
        if new_id in admin_ids:
            await update.message.reply_text(f"⚠️ ID <code>{new_id}</code> sudah terdaftar sebagai reseller.", parse_mode="HTML")
        else:
            admin_ids.append(new_id)
            save_config_key("ADMIN_IDS", ",".join(str(x) for x in admin_ids))
            await update.message.reply_text(
                f"✅ Reseller <code>{new_id}</code> berhasil ditambahkan!\n"
                f"Total reseller: <b>{len([x for x in admin_ids if x != owner_id])}</b>",
                parse_mode="HTML"
            )
            try:
                brand = CFG.get("BRAND", "OGH-ZIV")
                await ctx.bot.send_message(
                    new_id,
                    f"🎉 Kamu telah ditambahkan sebagai <b>Reseller {brand}</b>!\n\n"
                    f"Ketik /start untuk mengakses panel reseller.\n\n"
                    f"📋 <b>Kamu bisa:</b>\n"
                    f"✅ Buat akun gratis untuk pelanggan\n"
                    f"✅ Hapus akun VPN\n"
                    f"✅ Lihat list & statistik akun\n\n"
                    f"❌ Pengaturan pembayaran & bot hanya bisa diubah Owner.",
                    parse_mode="HTML"
                )
            except: pass
        ctx.user_data.pop("admin_action", None); return

    # ── OWNER: HAPUS RESELLER ─────────────────────────────────
    if admin_action == "hapus_reseller":
        if not is_owner(update.effective_user.id):
            await update.message.reply_text("⛔ Hanya Owner yang bisa menghapus reseller!"); return
        try: del_id = int(text)
        except ValueError:
            await update.message.reply_text("❌ Chat ID harus angka!", parse_mode="HTML"); return
        owner_id  = CFG.get("OWNER_ID", 0)
        admin_ids = CFG.get("ADMIN_IDS", [])
        if del_id == owner_id:
            await update.message.reply_text("⚠️ Tidak bisa menghapus Owner!", parse_mode="HTML")
        elif del_id not in admin_ids:
            await update.message.reply_text(f"❌ ID <code>{del_id}</code> tidak ditemukan di daftar reseller.", parse_mode="HTML")
        else:
            admin_ids.remove(del_id)
            save_config_key("ADMIN_IDS", ",".join(str(x) for x in admin_ids))
            await update.message.reply_text(
                f"✅ Reseller <code>{del_id}</code> berhasil dihapus.\n"
                f"Total reseller: <b>{len([x for x in admin_ids if x != owner_id])}</b>",
                parse_mode="HTML"
            )
            try:
                await ctx.bot.send_message(
                    del_id,
                    f"⚠️ Akses reseller kamu telah <b>dicabut</b> oleh Owner.\nHubungi Owner jika ada pertanyaan.",
                    parse_mode="HTML"
                )
            except: pass
        ctx.user_data.pop("admin_action", None); return

    # ── HAPUS AKUN VPN ───────────────────────────────────────
    if admin_action == "del_akun":
        await handle_admin_del(update, ctx); return

    # ── OWNER ONLY: Ubah nomor DANA ──────────────────────────
    if admin_action == "ubah_dana_num":
        if not is_owner(update.effective_user.id):
            await update.message.reply_text("⛔ Hanya Owner!"); return
        nomor = text.replace(" ", "").replace("-", "")
        if not re.match(r"^0\d{9,12}$", nomor):
            await update.message.reply_text("❌ Format tidak valid. Contoh: <code>08123456789</code>", parse_mode="HTML"); return
        save_config_key("DANA_NUMBER", nomor)
        ctx.user_data.pop("admin_action", None)
        await update.message.reply_text(f"✅ Nomor DANA diubah ke: <code>{nomor}</code>", parse_mode="HTML"); return

    # ── OWNER ONLY: Ubah nama A/N DANA ───────────────────────
    if admin_action == "ubah_dana_name":
        if not is_owner(update.effective_user.id):
            await update.message.reply_text("⛔ Hanya Owner!"); return
        if len(text) < 3:
            await update.message.reply_text("❌ Nama terlalu pendek. Coba lagi:"); return
        save_config_key("DANA_NAME", text)
        ctx.user_data.pop("admin_action", None)
        await update.message.reply_text(f"✅ Nama A/N DANA diubah ke: <b>{text}</b>", parse_mode="HTML"); return

    # ── OWNER ONLY: Ubah brand ────────────────────────────────
    if admin_action == "ubah_brand":
        if not is_owner(update.effective_user.id):
            await update.message.reply_text("⛔ Hanya Owner!"); return
        if len(text) < 2:
            await update.message.reply_text("❌ Nama brand terlalu pendek. Coba lagi:"); return
        save_config_key("BRAND", text)
        ctx.user_data.pop("admin_action", None)
        await update.message.reply_text(f"✅ Nama brand diubah ke: <b>{text}</b>", parse_mode="HTML"); return

    # ── OWNER ONLY: Ubah admin TG ─────────────────────────────
    if admin_action == "ubah_admintg":
        if not is_owner(update.effective_user.id):
            await update.message.reply_text("⛔ Hanya Owner!"); return
        username_tg = text if text.startswith("@") else f"@{text}"
        save_config_key("ADMIN_TG", username_tg)
        ctx.user_data.pop("admin_action", None)
        await update.message.reply_text(f"✅ Username admin TG diubah ke: <b>{username_tg}</b>", parse_mode="HTML"); return

    # ── OWNER ONLY: Ganti token bot ───────────────────────────
    if admin_action == "ganti_token":
        if not is_owner(update.effective_user.id):
            await update.message.reply_text("⛔ Hanya Owner!"); return
        token = text.strip()
        if not re.match(r"^\d{8,12}:[A-Za-z0-9_-]{35,}$", token):
            await update.message.reply_text(
                "❌ Format token tidak valid.\nToken harus seperti: <code>1234567890:ABCdef...</code>",
                parse_mode="HTML"
            ); return
        save_config_key("BOT_TOKEN", token)
        ctx.user_data.pop("admin_action", None)
        await update.message.reply_text(
            "✅ <b>Token Bot berhasil disimpan!</b>\n\n"
            "⚠️ Restart bot agar token baru berlaku:\n"
            "<code>systemctl restart zivpn-tgbot</code>",
            parse_mode="HTML"
        ); return

    # ── OWNER ONLY: Tambah server baru — input nama region ───
    if admin_action == "srv_tambah_nama":
        if not is_owner(update.effective_user.id):
            await update.message.reply_text("⛔ Hanya Owner!"); return
        nama = text.strip()
        if len(nama) < 2:
            await update.message.reply_text("❌ Nama region terlalu pendek. Coba lagi:"); return
        srv_id = make_server_id(nama)
        srvs   = load_servers()
        srvs[srv_id] = {**SERVER_TEMPLATE, "label": nama, "enabled": False}
        save_servers(srvs)
        ctx.user_data.pop("admin_action", None)
        await update.message.reply_text(
            f"✅ <b>Server baru ditambahkan!</b>\n\n"
            f"🌐 Nama   : <b>{nama}</b>\n"
            f"🆔 ID     : <code>{srv_id}</code>\n\n"
            f"Sekarang pergi ke <b>Kelola Server</b> → Edit server ini untuk mengisi:\n"
            f"• Host/IP VPS\n"
            f"• API URL & API Key (jika remote)\n"
            f"• Lalu aktifkan servernya ✅",
            parse_mode="HTML"
        ); return

    # ── OWNER ONLY: Rename label server ──────────────────────
    if admin_action and admin_action.startswith("srv_rename_"):
        if not is_owner(update.effective_user.id):
            await update.message.reply_text("⛔ Hanya Owner!"); return
        srv_id = admin_action.replace("srv_rename_", "")
        nama   = text.strip()
        if len(nama) < 2:
            await update.message.reply_text("❌ Nama terlalu pendek. Coba lagi:"); return
        srvs = load_servers()
        if srv_id in srvs:
            old_label = srvs[srv_id].get("label", srv_id)
            srvs[srv_id]["label"] = nama
            save_servers(srvs)
            ctx.user_data.pop("admin_action", None)
            await update.message.reply_text(
                f"✅ Nama server diubah:\n<b>{old_label}</b> → <b>{nama}</b>",
                parse_mode="HTML"
            )
        return

    # ── OWNER ONLY: Set Host/IP server ───────────────────────
    if admin_action and admin_action.startswith("srv_sethost_"):
        if not is_owner(update.effective_user.id):
            await update.message.reply_text("⛔ Hanya Owner!"); return
        srv_id = admin_action.replace("srv_sethost_", "")
        host   = text.strip()
        srvs   = load_servers()
        if srv_id in srvs:
            srvs[srv_id]["host"] = host
            save_servers(srvs)
            ctx.user_data.pop("admin_action", None)
            await update.message.reply_text(
                f"✅ Host server <b>{srvs[srv_id].get('label',srv_id)}</b> diubah ke: <code>{host}</code>",
                parse_mode="HTML"
            )
        return

    # ── OWNER ONLY: Set Port server ───────────────────────────
    if admin_action and admin_action.startswith("srv_setport_"):
        if not is_owner(update.effective_user.id):
            await update.message.reply_text("⛔ Hanya Owner!"); return
        srv_id = admin_action.replace("srv_setport_", "")
        port   = text.strip()
        if not port.isdigit():
            await update.message.reply_text("❌ Port harus angka!"); return
        srvs = load_servers()
        if srv_id in srvs:
            srvs[srv_id]["port"] = port
            save_servers(srvs)
            ctx.user_data.pop("admin_action", None)
            await update.message.reply_text(
                f"✅ Port server <b>{srvs[srv_id].get('label',srv_id)}</b> diubah ke: <code>{port}</code>",
                parse_mode="HTML"
            )
        return

    # ── OWNER ONLY: Set API URL server ────────────────────────
    if admin_action and admin_action.startswith("srv_setapi_"):
        if not is_owner(update.effective_user.id):
            await update.message.reply_text("⛔ Hanya Owner!"); return
        srv_id  = admin_action.replace("srv_setapi_", "")
        api_url = "" if text.strip() == "-" else text.strip()
        srvs    = load_servers()
        if srv_id in srvs:
            srvs[srv_id]["api_url"] = api_url
            save_servers(srvs)
            ctx.user_data.pop("admin_action", None)
            mode = "Lokal" if not api_url else f"Remote: <code>{api_url}</code>"
            await update.message.reply_text(
                f"✅ Mode server <b>{srvs[srv_id].get('label',srv_id)}</b>: {mode}",
                parse_mode="HTML"
            )
        return

    # ── OWNER ONLY: Set API Key server ────────────────────────
    if admin_action and admin_action.startswith("srv_setkey_"):
        if not is_owner(update.effective_user.id):
            await update.message.reply_text("⛔ Hanya Owner!"); return
        srv_id  = admin_action.replace("srv_setkey_", "")
        api_key = text.strip()
        srvs    = load_servers()
        if srv_id in srvs:
            srvs[srv_id]["api_key"] = api_key
            save_servers(srvs)
            ctx.user_data.pop("admin_action", None)
            await update.message.reply_text(
                f"✅ API Key server <b>{srvs[srv_id].get('label',srv_id)}</b> berhasil disimpan.",
                parse_mode="HTML"
            )
        return

    # ── OWNER ONLY: Set Stok server ───────────────────────────
    if admin_action and admin_action.startswith("srv_setstock_"):
        if not is_owner(update.effective_user.id):
            await update.message.reply_text("⛔ Hanya Owner!"); return
        srv_id = admin_action.replace("srv_setstock_", "")
        try:
            stock = int(text.strip())
        except:
            await update.message.reply_text("❌ Stok harus angka! (-1=unlimited, 0=habis, >0=jumlah slot)"); return
        srvs = load_servers()
        if srv_id in srvs:
            srvs[srv_id]["stock"] = stock
            save_servers(srvs)
            ctx.user_data.pop("admin_action", None)
            await update.message.reply_text(
                f"✅ Stok server <b>{srvs[srv_id].get('label',srv_id)}</b>: <b>{server_stock_text(srvs[srv_id])}</b>",
                parse_mode="HTML"
            )
        return

# ============================================================
#  SETUP & RUN
# ============================================================
# ============================================================
#  SETUP WIZARD — Pertama Kali Install
# ============================================================
SETUP_FLAG = "/etc/zivpn/.bot_setup_done"

def is_first_run() -> bool:
    """Cek apakah owner belum diset (butuh setup wizard)."""
    # Jika setup flag sudah ada, cek apakah owner valid di config
    cfg   = load_config()
    token = cfg.get("BOT_TOKEN", "")
    owner = cfg.get("OWNER_ID",  0)
    # First run jika token belum ada
    if not token:
        return True
    # First run jika owner belum diset (0 atau kosong)
    if not owner:
        return True
    return False

def write_default_config():
    p = Path(CONFIG_FILE)
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        p.write_text(
            "# OGH-ZIV Bot Store Config\n"
            "BOT_TOKEN=ISI_TOKEN_BOT_TELEGRAM_DI_SINI\n\n"
            "OWNER_ID=ISI_CHAT_ID_OWNER\n"
            "ADMIN_IDS=ISI_CHAT_ID_OWNER\n\n"
            "DANA_NUMBER=08xxxxxxxxxx\n"
            "DANA_NAME=Nama Pemilik Dana\n"
            "QRIS_ENABLED=0\n"
            "BRAND=OGH-ZIV\n"
            "ADMIN_TG=@namaadmin\n"
        )

async def setup_wizard_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handler /start saat owner belum diset — user pertama otomatis jadi Owner."""
    global CFG
    user = update.effective_user
    cfg  = load_config()

    token = cfg.get("BOT_TOKEN", "")
    owner = cfg.get("OWNER_ID",  0)

    # ── Token belum ada — arahkan ke setup console ─────────────
    if not token:
        await update.message.reply_text(
            f"⚙️ <b>Bot belum dikonfigurasi.</b>\n\n"
            f"Jalankan setup di VPS:\n"
            f"<code>python3 /usr/local/bin/zivpn-bot.py</code>\n\n"
            f"Ikuti langkah setup yang muncul di terminal.",
            parse_mode="HTML"
        )
        return

    # ── Owner belum diset — user pertama yang /start jadi Owner ─
    if not owner:
        # Simpan owner ke config
        save_config_key("OWNER_ID",   str(user.id))
        save_config_key("ADMIN_IDS",  str(user.id))
        # Tandai setup selesai
        Path(SETUP_FLAG).parent.mkdir(parents=True, exist_ok=True)
        Path(SETUP_FLAG).write_text(
            f"setup_done|owner={user.id}|{now_wib().strftime('%Y-%m-%d %H:%M:%S')}\n"
        )
        # Reload CFG global agar is_owner() langsung benar
        CFG = load_config()
        log.info(f"[SETUP] Owner terdaftar: {user.full_name} (ID: {user.id})")

        brand = CFG.get("BRAND", "OGH-ZIV")
        # Kirim pesan selamat datang owner + langsung tampilkan menu admin
        keyboard = [
            [InlineKeyboardButton("👤 Beli Akun VPN",           callback_data="beli")],
            [InlineKeyboardButton("🎁 Trial Gratis 120 Menit",  callback_data="trial")],
            [InlineKeyboardButton("📋 Cek Akun Saya",           callback_data="cek_akun")],
            [InlineKeyboardButton("⚙️ Admin Panel (Owner)",      callback_data="admin")],
        ]
        await update.message.reply_text(
            f"👑 <b>Selamat datang, Owner!</b>\n\n"
            f"✅ Kamu otomatis terdaftar sebagai <b>Owner / Admin Utama</b>.\n\n"
            f"📋 <b>Data Owner:</b>\n"
            f"👤 Nama    : <b>{user.full_name}</b>\n"
            f"🆔 Chat ID : <code>{user.id}</code>\n"
            f"🏷 Brand   : <b>{brand}</b>\n\n"
            f"Sekarang kamu bisa akses semua fitur panel di bawah 👇",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
        return

    # ── Owner sudah ada tapi handler ini masih dipanggil — redirect ke menu normal ─
    CFG = load_config()
    await cmd_start(update, ctx)

def run_setup_wizard_console():
    """Setup interaktif via console saat pertama kali dijalankan."""
    print("\n" + "="*55)
    print("  OGH-ZIV BOT — SETUP PERTAMA KALI")
    print("="*55)
    print("Bot belum dikonfigurasi. Ikuti langkah berikut:\n")

    # Minta token
    while True:
        token = input("  [1] Masukkan BOT TOKEN dari @BotFather:\n  > ").strip()
        if re.match(r"^\d{8,12}:[A-Za-z0-9_-]{35,}$", token):
            break
        print("  ❌ Format token tidak valid. Contoh: 1234567890:ABCdef...\n")

    # Minta DANA number
    while True:
        dana_num = input("\n  [2] Masukkan Nomor DANA kamu (contoh: 08123456789):\n  > ").strip()
        if re.match(r"^0\d{9,12}$", dana_num):
            break
        print("  ❌ Format nomor tidak valid.\n")

    # Minta nama A/N DANA
    dana_name = input("\n  [3] Masukkan Nama A/N DANA kamu:\n  > ").strip()
    if not dana_name:
        dana_name = "Pemilik Bot"

    # Minta brand name
    brand = input("\n  [4] Nama Brand Bot (default: OGH-ZIV):\n  > ").strip()
    if not brand:
        brand = "OGH-ZIV"

    # Minta admin TG username
    admin_tg = input("\n  [5] Username Telegram Admin (contoh: @namaadmin):\n  > ").strip()
    if not admin_tg:
        admin_tg = "@admin"
    if not admin_tg.startswith("@"):
        admin_tg = f"@{admin_tg}"

    # Simpan semua config
    p = Path(CONFIG_FILE)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        f"# OGH-ZIV Bot Store Config\n"
        f"# Setup: {now_wib().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"BOT_TOKEN={token}\n\n"
        f"# OWNER_ID akan otomatis diset saat user pertama /start ke bot\n"
        f"OWNER_ID=\n"
        f"ADMIN_IDS=\n\n"
        f"DANA_NUMBER={dana_num}\n"
        f"DANA_NAME={dana_name}\n"
        f"QRIS_ENABLED=0\n"
        f"BRAND={brand}\n"
        f"ADMIN_TG={admin_tg}\n"
    )

    print("\n" + "="*55)
    print("  ✅ KONFIGURASI TERSIMPAN!")
    print("="*55)
    print(f"  Token    : {token[:20]}...")
    print(f"  DANA     : {dana_num} a/n {dana_name}")
    print(f"  Brand    : {brand}")
    print(f"  Admin TG : {admin_tg}")
    print("\n  📌 LANGKAH SELANJUTNYA:")
    print("  1. Bot akan mulai berjalan sekarang")
    print("  2. Buka Telegram, cari bot kamu")
    print("  3. Kirim /start ke bot")
    print("  4. Kamu otomatis terdaftar sebagai OWNER 👑")
    print("="*55 + "\n")

    return token


# ============================================================
#  OWNER ONLY — BACKUP / RESTORE KONFIGURASI
# ============================================================
import tarfile as _tarfile
import glob as _glob
import datetime as _dt

_BACKUP_DIR = "/etc/zivpn/backups"

async def cb_admin_backup_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_owner(query.from_user.id):
        await _akses_ditolak(query, "Backup / Restore"); return

    os.makedirs(_BACKUP_DIR, exist_ok=True)
    total = len(_glob.glob(f"{_BACKUP_DIR}/oghziv_backup_*.tar.gz"))

    keyboard = [
        [InlineKeyboardButton("💾 Buat Backup Sekarang",        callback_data="admin_backup_do")],
        [InlineKeyboardButton("📤 Backup & Kirim ke Telegram",  callback_data="admin_backup_send")],
        [InlineKeyboardButton("📥 Restore dari File Telegram",  callback_data="admin_restore_file")],
        [InlineKeyboardButton("🔄 Restore dari Backup Lokal",   callback_data="admin_restore_list")],
        [InlineKeyboardButton("🗂️ Lihat Daftar Backup Lokal",   callback_data="admin_backup_list")],
        [InlineKeyboardButton("🔙 Kembali",                     callback_data="admin")],
    ]
    await query.edit_message_text(
        f"💾 <b>Backup / Restore Konfigurasi</b>\n"
        f"<i>Hanya Owner yang dapat menggunakan fitur ini</i>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📂 Backup Lokal  : <code>{_BACKUP_DIR}</code>\n"
        f"📦 Total Backup  : <b>{total} file</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💡 <b>Tips:</b> Gunakan <b>Backup &amp; Kirim ke Telegram</b>\n"
        f"agar backup tersimpan di HP kamu, aman meski VPS mati!\n\n"
        f"Pilih aksi:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def cb_admin_backup_do(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_owner(query.from_user.id):
        await _akses_ditolak(query, "Buat Backup"); return

    await query.edit_message_text("⏳ <b>Sedang membuat backup...</b>", parse_mode="HTML")

    os.makedirs(_BACKUP_DIR, exist_ok=True)
    ts          = now_wib().strftime("%Y%m%d_%H%M%S")
    backup_file = f"{_BACKUP_DIR}/oghziv_backup_{ts}.tar.gz"

    files_to_backup = [
        "/etc/zivpn/bot_store.conf",
        "/etc/zivpn/servers.json",
        "/etc/zivpn/worker.conf",
        "/etc/zivpn/config.json",
        "/etc/zivpn/users.db",
        "/etc/zivpn/maxlogin.db",
        "/usr/local/bin/zivpn-tgbot.py",
        "/usr/local/bin/zivpn-api-worker.py",
    ]

    backed = []
    try:
        with _tarfile.open(backup_file, "w:gz") as tar:
            for fp in files_to_backup:
                if os.path.exists(fp):
                    tar.add(fp)
                    backed.append(os.path.basename(fp))
        size = os.path.getsize(backup_file)
        sstr = f"{size/1024:.1f} KB" if size < 1048576 else f"{size/1048576:.1f} MB"
        lines = [
            "✅ <b>Backup Berhasil Dibuat!</b>\n",
            f"📦 File   : <code>oghziv_backup_{ts}.tar.gz</code>",
            f"📁 Ukuran : <b>{sstr}</b>",
            f"🗂️ Isi backup ({len(backed)} file) :",
        ]
        for b in backed:
            lines.append(f"   • {b}")
        lines.append(f"\n📅 Waktu : {now_wib().strftime('%Y-%m-%d %H:%M:%S')}")
    except Exception as e:
        lines = [f"❌ <b>Backup gagal!</b>\n\nError: <code>{e}</code>"]

    await query.edit_message_text(
        "\n".join(lines), parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💾 Backup Lagi",  callback_data="admin_backup_do")],
            [InlineKeyboardButton("🔙 Kembali",      callback_data="admin_backup_menu")],
        ])
    )

async def cb_admin_backup_send(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Buat backup lalu kirim file .tar.gz langsung ke chat Owner di Telegram."""
    query = update.callback_query
    await query.answer()
    if not is_owner(query.from_user.id):
        await _akses_ditolak(query, "Backup & Kirim ke Telegram"); return

    await query.edit_message_text(
        "⏳ <b>Sedang membuat & mengirim backup ke Telegram...</b>\n\n"
        "<i>Mohon tunggu, file akan dikirim sebentar lagi...</i>",
        parse_mode="HTML"
    )

    os.makedirs(_BACKUP_DIR, exist_ok=True)
    ts          = now_wib().strftime("%Y%m%d_%H%M%S")
    backup_file = f"{_BACKUP_DIR}/oghziv_backup_{ts}.tar.gz"

    files_to_backup = [
        "/etc/zivpn/bot_store.conf",
        "/etc/zivpn/servers.json",
        "/etc/zivpn/worker.conf",
        "/etc/zivpn/config.json",
        "/etc/zivpn/users.db",
        "/etc/zivpn/maxlogin.db",
        "/usr/local/bin/zivpn-tgbot.py",
        "/usr/local/bin/zivpn-api-worker.py",
    ]

    backed = []
    try:
        with _tarfile.open(backup_file, "w:gz") as tar:
            for fp in files_to_backup:
                if os.path.exists(fp):
                    tar.add(fp)
                    backed.append(os.path.basename(fp))

        size = os.path.getsize(backup_file)
        sstr = f"{size/1024:.1f} KB" if size < 1048576 else f"{size/1048576:.1f} MB"

        caption = (
            f"💾 <b>Backup OGH-ZIV</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📅 Waktu  : {now_wib().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"📁 Ukuran : <b>{sstr}</b>\n"
            f"🗂️ Isi ({len(backed)} file) :\n"
            + "\n".join(f"   • {b}" for b in backed) +
            f"\n━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ <b>Simpan file ini baik-baik!</b>\n"
            f"Kirim balik ke bot untuk restore jika VPS mati."
        )

        # Kirim file ke Owner
        with open(backup_file, "rb") as f:
            await ctx.bot.send_document(
                chat_id=query.from_user.id,
                document=f,
                filename=f"oghziv_backup_{ts}.tar.gz",
                caption=caption,
                parse_mode="HTML"
            )

        await query.edit_message_text(
            f"✅ <b>Backup Berhasil Dikirim!</b>\n\n"
            f"📦 File <code>oghziv_backup_{ts}.tar.gz</code>\n"
            f"📁 Ukuran : <b>{sstr}</b>\n"
            f"🗂️ {len(backed)} file ter-backup\n\n"
            f"📲 File sudah dikirim ke chat kamu!\n"
            f"Simpan file itu di HP/PC sebagai cadangan.\n\n"
            f"💡 Cara restore jika VPS mati:\n"
            f"1. Install ulang VPS + bot\n"
            f"2. Buka Admin Panel → Backup/Restore\n"
            f"3. Pilih <b>📥 Restore dari File Telegram</b>\n"
            f"4. Kirim/forward file backup ke bot",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📤 Kirim Backup Lagi",  callback_data="admin_backup_send")],
                [InlineKeyboardButton("🔙 Kembali",            callback_data="admin_backup_menu")],
            ])
        )

    except Exception as e:
        await query.edit_message_text(
            f"❌ <b>Gagal membuat/mengirim backup!</b>\n\nError: <code>{e}</code>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Kembali", callback_data="admin_backup_menu")]
            ])
        )

async def cb_admin_restore_file(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Minta Owner kirim file backup .tar.gz ke chat bot untuk di-restore."""
    query = update.callback_query
    await query.answer()
    if not is_owner(query.from_user.id):
        await _akses_ditolak(query, "Restore dari File Telegram"); return

    ctx.user_data["admin_action"] = "waiting_backup_file"

    await query.edit_message_text(
        "📥 <b>Restore dari File Telegram</b>\n\n"
        "Kirim file backup <code>.tar.gz</code> ke chat ini sekarang.\n\n"
        "📌 <b>Cara mendapatkan file backup:</b>\n"
        "• Cari di chat bot kamu, file yang pernah dikirim bot\n"
        "• File bernama <code>oghziv_backup_*.tar.gz</code>\n"
        "• Forward atau kirim ulang file itu ke sini\n\n"
        "⚠️ <b>Peringatan:</b> Semua konfigurasi aktif akan ditimpa!\n"
        "Bot akan auto-backup dulu sebelum restore.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Batal", callback_data="admin_backup_menu")]
        ])
    )


    query = update.callback_query
    await query.answer()
    if not is_owner(query.from_user.id):
        await _akses_ditolak(query, "Daftar Backup"); return

    backups = sorted(_glob.glob(f"{_BACKUP_DIR}/oghziv_backup_*.tar.gz"), reverse=True)

    if not backups:
        await query.edit_message_text(
            "📂 <b>Belum ada backup.</b>\n\n"
            "Gunakan <b>💾 Buat Backup Sekarang</b> untuk membuat backup pertama.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💾 Buat Backup Sekarang", callback_data="admin_backup_do")],
                [InlineKeyboardButton("🔙 Kembali",              callback_data="admin_backup_menu")],
            ])
        )
        return

    lines = [f"🗂️ <b>Daftar Backup</b> ({len(backups)} file)\n━━━━━━━━━━━━━━━━━━━━━━━"]
    for i, fp in enumerate(backups[:10], 1):
        size = os.path.getsize(fp)
        sstr = f"{size/1024:.1f} KB" if size < 1048576 else f"{size/1048576:.1f} MB"
        name = os.path.basename(fp)
        ts   = name.replace("oghziv_backup_", "").replace(".tar.gz", "")
        try:
            dt = f"{ts[:4]}-{ts[4:6]}-{ts[6:8]} {ts[9:11]}:{ts[11:13]}:{ts[13:15]}"
        except:
            dt = ts
        lines.append(f"\n{i}. 📦 <code>{name}</code>\n    📅 {dt}  |  📁 {sstr}")

    if len(backups) > 10:
        lines.append(f"\n<i>... dan {len(backups)-10} file lainnya</i>")

    await query.edit_message_text(
        "\n".join(lines), parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Restore dari Backup", callback_data="admin_restore_list")],
            [InlineKeyboardButton("🔙 Kembali",             callback_data="admin_backup_menu")],
        ])
    )

async def cb_admin_backup_list(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Tampilkan daftar backup lokal yang tersedia (hanya lihat, tanpa restore)."""
    query = update.callback_query
    await query.answer()
    if not is_owner(query.from_user.id):
        await _akses_ditolak(query, "Daftar Backup"); return

    backups = sorted(_glob.glob(f"{_BACKUP_DIR}/oghziv_backup_*.tar.gz"), reverse=True)

    if not backups:
        await query.edit_message_text(
            "⚠️ <b>Belum ada backup lokal yang tersedia.</b>\n\n"
            "Buat backup terlebih dahulu.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💾 Buat Backup Sekarang", callback_data="admin_backup_do")],
                [InlineKeyboardButton("🔙 Kembali",              callback_data="admin_backup_menu")],
            ])
        )
        return

    total_size = sum(os.path.getsize(f) for f in backups)
    total_sstr = f"{total_size/1024:.1f} KB" if total_size < 1048576 else f"{total_size/1048576:.1f} MB"

    lines = [
        "🗂️ <b>Daftar Backup Lokal</b>\n",
        f"📦 Total : <b>{len(backups)} file</b>  |  💽 {total_sstr}",
        f"📂 Lokasi : <code>{_BACKUP_DIR}</code>\n",
        "━━━━━━━━━━━━━━━━━━━━━━━",
    ]
    for i, fp in enumerate(backups[:10], 1):
        name = os.path.basename(fp)
        ts   = name.replace("oghziv_backup_", "").replace(".tar.gz", "")
        size = os.path.getsize(fp)
        sstr = f"{size/1024:.1f} KB" if size < 1048576 else f"{size/1048576:.1f} MB"
        try:
            dt = f"{ts[:4]}-{ts[4:6]}-{ts[6:8]} {ts[9:11]}:{ts[11:13]}"
        except:
            dt = ts
        lines.append(f"\n{i}. 📦 <code>{dt}</code>\n    💽 {sstr}")

    if len(backups) > 10:
        lines.append(f"\n<i>... dan {len(backups)-10} backup lainnya</i>")

    await query.edit_message_text(
        "\n".join(lines), parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💾 Buat Backup Baru",        callback_data="admin_backup_do")],
            [InlineKeyboardButton("🔄 Restore Backup",          callback_data="admin_restore_list")],
            [InlineKeyboardButton("🔙 Kembali",                 callback_data="admin_backup_menu")],
        ])
    )


async def cb_admin_restore_list(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_owner(query.from_user.id):
        await _akses_ditolak(query, "Restore Backup"); return

    backups = sorted(_glob.glob(f"{_BACKUP_DIR}/oghziv_backup_*.tar.gz"), reverse=True)[:8]

    if not backups:
        await query.edit_message_text(
            "⚠️ <b>Belum ada backup yang tersedia.</b>\n\n"
            "Buat backup terlebih dahulu.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💾 Buat Backup Sekarang", callback_data="admin_backup_do")],
                [InlineKeyboardButton("🔙 Kembali",              callback_data="admin_backup_menu")],
            ])
        )
        return

    lines = [
        "🔄 <b>Pilih Backup untuk di-Restore</b>\n",
        "⚠️ <i>Konfigurasi aktif akan ditimpa!</i>\n",
        "━━━━━━━━━━━━━━━━━━━━━━━",
    ]
    keyboard = []
    for i, fp in enumerate(backups, 1):
        name = os.path.basename(fp)
        ts   = name.replace("oghziv_backup_", "").replace(".tar.gz", "")
        size = os.path.getsize(fp)
        sstr = f"{size/1024:.1f} KB" if size < 1048576 else f"{size/1048576:.1f} MB"
        try:
            dt = f"{ts[:4]}-{ts[4:6]}-{ts[6:8]} {ts[9:11]}:{ts[11:13]}"
        except:
            dt = ts
        lines.append(f"\n{i}. 📦 {dt}  |  {sstr}")
        keyboard.append([InlineKeyboardButton(
            f"🔄 Restore #{i} — {dt}", callback_data=f"admin_restore_do_{i-1}"
        )])

    keyboard.append([InlineKeyboardButton("🔙 Batal", callback_data="admin_backup_menu")])

    # Simpan list backup ke user_data agar bisa diakses saat restore
    ctx.user_data["restore_list"] = backups

    await query.edit_message_text(
        "\n".join(lines), parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def cb_admin_restore_do(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_owner(query.from_user.id):
        await _akses_ditolak(query, "Restore Backup"); return

    idx     = int(query.data.replace("admin_restore_do_", ""))
    backups = ctx.user_data.get("restore_list", [])

    if not backups or idx >= len(backups):
        await query.edit_message_text(
            "❌ Sesi restore habis. Silakan ulangi dari menu.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Kembali", callback_data="admin_backup_menu")]
            ])
        )
        return

    selected = backups[idx]
    await query.edit_message_text(
        f"⏳ <b>Sedang restore backup...</b>\n\n"
        f"📦 <code>{os.path.basename(selected)}</code>",
        parse_mode="HTML"
    )

    # Auto-backup konfigurasi aktif sebelum restore
    ts_now   = now_wib().strftime("%Y%m%d_%H%M%S")
    auto_bak = f"{_BACKUP_DIR}/oghziv_backup_pre-restore_{ts_now}.tar.gz"
    files_to_backup = [
        "/etc/zivpn/bot_store.conf", "/etc/zivpn/servers.json",
        "/etc/zivpn/worker.conf",    "/etc/zivpn/config.json",
        "/etc/zivpn/users.db",       "/etc/zivpn/maxlogin.db",
        "/usr/local/bin/zivpn-tgbot.py",
        "/usr/local/bin/zivpn-api-worker.py",
    ]
    try:
        with _tarfile.open(auto_bak, "w:gz") as tar:
            for fp in files_to_backup:
                if os.path.exists(fp): tar.add(fp)
    except:
        pass  # auto-backup gagal tidak menghalangi restore

    # Lakukan restore
    restored = []
    try:
        with _tarfile.open(selected, "r:gz") as tar:
            members = tar.getmembers()
            for m in members:
                # Pastikan extract ke path absolut yang benar
                tar.extract(m, "/")
                if m.name:
                    restored.append(os.path.basename(m.name))

        # Reload config setelah restore
        global CFG
        CFG = load_config()

        lines = [
            "✅ <b>Restore Berhasil!</b>\n",
            f"📦 Dari    : <code>{os.path.basename(selected)}</code>",
            f"🗂️ Dipulihkan ({len(restored)} file) :",
        ]
        for r in [x for x in restored if x][:10]:
            lines.append(f"   • {r}")
        lines.append(
            f"\n⚠️ <b>Restart bot agar semua perubahan aktif:</b>\n"
            f"<code>systemctl restart zivpn-tgbot</code>"
        )
    except Exception as e:
        lines = [
            f"❌ <b>Restore gagal!</b>\n",
            f"Error: <code>{e}</code>\n",
            f"ℹ️ Auto-backup sebelum restore tersimpan di:",
            f"<code>{auto_bak}</code>",
        ]

    await query.edit_message_text(
        "\n".join(lines), parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Kembali ke Backup Menu", callback_data="admin_backup_menu")]
        ])
    )

def main():
    global CFG
    write_default_config()
    CFG = load_config()

    token = CFG.get("BOT_TOKEN", "")

    # ── Jalankan setup wizard console jika token belum ada ────────
    if not token or token == "ISI_TOKEN_BOT_TELEGRAM_DI_SINI":
        token = run_setup_wizard_console()
        CFG = load_config()

    if not token:
        print("[ERROR] Token tidak valid. Keluar.")
        return

    owner_id   = CFG.get("OWNER_ID", 0)
    admin_list = CFG.get("ADMIN_IDS", [])
    resellers  = [x for x in admin_list if x != owner_id]

    print(f"[INFO] OGH-ZIV Bot starting...")
    print(f"[INFO] Brand     : {CFG.get('BRAND')}")
    print(f"[INFO] DANA      : {CFG.get('DANA_NUMBER')}")
    print(f"[INFO] QRIS      : {'Aktif' if qris_aktif() else 'Nonaktif'}")
    print(f"[INFO] Owner     : {owner_id if owner_id else '⚠️  Belum diset — kirim /start ke bot!'}")
    print(f"[INFO] Reseller  : {resellers} ({len(resellers)} orang)")
    print(f"[INFO] OCR       : {'Aktif' if OCR_AVAILABLE else 'Tidak aktif (manual mode)'}")

    app = ApplicationBuilder().token(token).build()

    # ── Pakai setup_wizard_start jika owner belum diset ──────────
    if not CFG.get("OWNER_ID", 0):
        app.add_handler(CommandHandler("start", setup_wizard_start))
        print("[INFO] MODE      : SETUP — Kirim /start ke bot untuk daftar sebagai Owner 👑")
    else:
        app.add_handler(CommandHandler("start", cmd_start))

    app.add_handler(MessageHandler(filters.Regex(r"^/konfirm_\d+$"), cmd_konfirm))
    app.add_handler(MessageHandler(filters.Regex(r"^/tolak_\d+$"),   cmd_tolak))

    # Callback — User
    app.add_handler(CallbackQueryHandler(cb_beli,                 pattern="^beli$"))
    app.add_handler(CallbackQueryHandler(cb_trial,                pattern="^trial$"))
    app.add_handler(CallbackQueryHandler(cb_trial_srv,            pattern="^trial_srv_"))
    app.add_handler(CallbackQueryHandler(cb_paket,                pattern="^paket_"))
    app.add_handler(CallbackQueryHandler(cb_server_unavailable,   pattern="^server_unavailable$"))
    app.add_handler(CallbackQueryHandler(cb_srv_paket,            pattern="^srv_(?!akun_)"))
    app.add_handler(CallbackQueryHandler(cb_bayar_dana,           pattern="^bayar_dana_"))
    app.add_handler(CallbackQueryHandler(cb_bayar_qris,           pattern="^bayar_qris_"))
    app.add_handler(CallbackQueryHandler(cb_cek_akun,             pattern="^cek_akun$"))
    app.add_handler(CallbackQueryHandler(cb_back_start,           pattern="^back_start$"))

    # ── SocksIP handlers ───────────────────────────────────
    app.add_handler(MessageHandler(filters.Regex(r"^/konfirm_socksip_\d+$"), cmd_konfirm_socksip))
    app.add_handler(CallbackQueryHandler(cb_beli_jenis,                pattern="^beli_jenis$"))
    app.add_handler(CallbackQueryHandler(cb_beli_jenis_zivpn,          pattern="^beli_jenis_zivpn$"))
    app.add_handler(CallbackQueryHandler(cb_beli_jenis_socksip,        pattern="^beli_jenis_socksip$"))
    app.add_handler(CallbackQueryHandler(cb_socksip_paket,             pattern="^socksip_paket_"))
    app.add_handler(CallbackQueryHandler(cb_socksip_srv_paket,         pattern="^socksip_srv_"))
    app.add_handler(CallbackQueryHandler(cb_socksip_bayar_dana,        pattern="^socksip_bayar_dana_"))
    app.add_handler(CallbackQueryHandler(cb_socksip_bayar_qris,        pattern="^socksip_bayar_qris_"))
    app.add_handler(CallbackQueryHandler(cb_admin_socksip,             pattern="^admin_socksip$"))
    app.add_handler(CallbackQueryHandler(cb_admin_socksip_buat_manual, pattern="^admin_socksip_buat_manual$"))
    app.add_handler(CallbackQueryHandler(cb_admin_socksip_buat_auto,   pattern="^admin_socksip_buat_auto$"))
    app.add_handler(CallbackQueryHandler(cb_admin_socksip_srv,         pattern="^admin_socksip_srv_"))
    app.add_handler(CallbackQueryHandler(cb_admin_socksip_auto_hari,   pattern="^admin_socksip_auto_"))
    app.add_handler(CallbackQueryHandler(cb_admin_socksip_del,         pattern="^admin_socksip_del$"))
    app.add_handler(CallbackQueryHandler(cb_admin_socksip_list,        pattern="^admin_socksip_list$"))

    # Callback — Admin Panel (semua admin)
    app.add_handler(CallbackQueryHandler(cb_admin,                pattern="^admin$"))
    app.add_handler(CallbackQueryHandler(cb_admin_buat_akun,      pattern="^admin_buat_akun$"))
    app.add_handler(CallbackQueryHandler(cb_admin_akun_manual,    pattern="^admin_akun_manual$"))
    app.add_handler(CallbackQueryHandler(cb_admin_akun_auto,      pattern="^admin_akun_auto$"))
    app.add_handler(CallbackQueryHandler(cb_admin_srv_akun,       pattern="^admin_srv_akun_(?!auto_)"))
    app.add_handler(CallbackQueryHandler(cb_admin_srv_akun_auto,  pattern="^admin_srv_akun_auto_"))
    app.add_handler(CallbackQueryHandler(cb_admin_auto_hari,      pattern="^admin_auto_hari_"))
    app.add_handler(CallbackQueryHandler(cb_admin_del,                 pattern="^admin_del$"))
    app.add_handler(CallbackQueryHandler(cb_admin_del_expired,         pattern="^admin_del_expired$"))
    app.add_handler(CallbackQueryHandler(cb_admin_del_expired_confirm, pattern="^admin_del_expired_confirm$"))
    app.add_handler(CallbackQueryHandler(cb_admin_list_menu,      pattern="^admin_list_menu$"))
    app.add_handler(CallbackQueryHandler(cb_admin_list_all,       pattern="^admin_list_all$"))
    app.add_handler(CallbackQueryHandler(cb_admin_list,           pattern="^admin_list_(indo|sg)$"))
    app.add_handler(CallbackQueryHandler(cb_admin_stat,           pattern="^admin_stat$"))

    # Callback — Owner Only
    app.add_handler(CallbackQueryHandler(cb_admin_kelola_admin,   pattern="^admin_kelola_admin$"))
    app.add_handler(CallbackQueryHandler(cb_admin_tambah_reseller,pattern="^admin_tambah_reseller$"))
    app.add_handler(CallbackQueryHandler(cb_admin_hapus_reseller, pattern="^admin_hapus_reseller$"))
    app.add_handler(CallbackQueryHandler(cb_admin_kelola_server,       pattern="^admin_kelola_server$"))
    app.add_handler(CallbackQueryHandler(cb_admin_srv_tambah,          pattern="^admin_srv_tambah$"))
    app.add_handler(CallbackQueryHandler(cb_admin_srv_hapus_menu,      pattern="^admin_srv_hapus_menu$"))
    app.add_handler(CallbackQueryHandler(cb_admin_srv_hapus_konfirm,   pattern="^admin_srv_hapus_konfirm_"))
    app.add_handler(CallbackQueryHandler(cb_admin_srv_hapus_do,        pattern="^admin_srv_hapus_do_"))
    app.add_handler(CallbackQueryHandler(cb_admin_srv_edit,            pattern="^admin_srv_edit_"))
    app.add_handler(CallbackQueryHandler(cb_admin_srv_toggle,          pattern="^admin_srv_toggle_"))
    app.add_handler(CallbackQueryHandler(cb_admin_srv_rename,          pattern="^admin_srv_rename_"))
    app.add_handler(CallbackQueryHandler(cb_admin_srv_sethost,         pattern="^admin_srv_sethost_"))
    app.add_handler(CallbackQueryHandler(cb_admin_srv_setport,         pattern="^admin_srv_setport_"))
    app.add_handler(CallbackQueryHandler(cb_admin_srv_setapi,          pattern="^admin_srv_setapi_"))
    app.add_handler(CallbackQueryHandler(cb_admin_srv_setkey,          pattern="^admin_srv_setkey_"))
    app.add_handler(CallbackQueryHandler(cb_admin_srv_setstock,        pattern="^admin_srv_setstock_"))
    app.add_handler(CallbackQueryHandler(cb_admin_srv_restart,    pattern="^admin_srv_restart_"))
    app.add_handler(CallbackQueryHandler(cb_admin_srv_list,       pattern="^admin_srv_list_"))
    app.add_handler(CallbackQueryHandler(cb_admin_srv_status,     pattern="^admin_srv_status$"))
    app.add_handler(CallbackQueryHandler(cb_admin_pembayaran,     pattern="^admin_pembayaran$"))
    app.add_handler(CallbackQueryHandler(cb_admin_ubah_dana_num,  pattern="^admin_ubah_dana_num$"))
    app.add_handler(CallbackQueryHandler(cb_admin_ubah_dana_name, pattern="^admin_ubah_dana_name$"))
    app.add_handler(CallbackQueryHandler(cb_admin_upload_qris,    pattern="^admin_upload_qris$"))
    app.add_handler(CallbackQueryHandler(cb_admin_qris_toggle,    pattern="^admin_qris_o"))
    app.add_handler(CallbackQueryHandler(cb_admin_settings,       pattern="^admin_settings$"))
    app.add_handler(CallbackQueryHandler(cb_admin_ubah_brand,     pattern="^admin_ubah_brand$"))
    app.add_handler(CallbackQueryHandler(cb_admin_ubah_admintg,   pattern="^admin_ubah_admintg$"))
    app.add_handler(CallbackQueryHandler(cb_admin_ganti_token,    pattern="^admin_ganti_token$"))

    app.add_handler(CallbackQueryHandler(cb_admin_backup_menu,  pattern="^admin_backup_menu$"))
    app.add_handler(CallbackQueryHandler(cb_admin_backup_do,    pattern="^admin_backup_do$"))
    app.add_handler(CallbackQueryHandler(cb_admin_backup_send,  pattern="^admin_backup_send$"))
    app.add_handler(CallbackQueryHandler(cb_admin_restore_file, pattern="^admin_restore_file$"))
    app.add_handler(CallbackQueryHandler(cb_admin_backup_list,  pattern="^admin_backup_list$"))
    app.add_handler(CallbackQueryHandler(cb_admin_restore_list, pattern="^admin_restore_list$"))
    app.add_handler(CallbackQueryHandler(cb_admin_restore_do,   pattern="^admin_restore_do_"))

    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("[INFO] Bot berjalan... Tekan Ctrl+C untuk berhenti.\n")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()

# ============================================================
#  MODUL SOCKSIP — PATCH TAMBAHAN
#  Ditambahkan otomatis ke zivpn_bot_v2_fixed
# ============================================================

# ── Konstanta SocksIP ────────────────────────────────────────
PAKET_SOCKSIP = {
    "1": {"nama": "7 Hari",  "hari": 7,  "harga": 3000,  "maxlogin": 2},
    "2": {"nama": "15 Hari", "hari": 15, "harga": 6000,  "maxlogin": 2},
    "3": {"nama": "30 Hari", "hari": 30, "harga": 10000, "maxlogin": 2},
}
SOCKSIP_SERVERS_FILE = "/etc/zivpn/socksip_servers.json"
SOCKSIP_SERVER_TEMPLATE = {
    "label": "", "enabled": False, "host": "",
    "udp_port": "1-65535", "api_url": "", "api_key": "",
    "note": "", "stock": -1, "is_local": True,
}
DEFAULT_SOCKSIP_SERVERS = {
    "udp_server1": {
        "label": "\U0001f1ee\U0001f1e9 Indonesia UDP",
        "enabled": True, "host": "", "udp_port": "1-65535",
        "api_url": "", "api_key": "",
        "note": "Server UDP SocksIP Indonesia",
        "stock": -1, "is_local": True,
    },
}

# ── Helper fungsi SocksIP ────────────────────────────────────
def load_socksip_servers() -> dict:
    p = Path(SOCKSIP_SERVERS_FILE)
    if p.exists():
        try:
            data = json.loads(p.read_text())
            if isinstance(data, dict) and data:
                for sid in data:
                    for k, v in SOCKSIP_SERVER_TEMPLATE.items():
                        data[sid].setdefault(k, v)
                return data
        except: pass
    Path(SOCKSIP_SERVERS_FILE).parent.mkdir(parents=True, exist_ok=True)
    Path(SOCKSIP_SERVERS_FILE).write_text(json.dumps(DEFAULT_SOCKSIP_SERVERS, indent=2))
    return DEFAULT_SOCKSIP_SERVERS.copy()

def save_socksip_servers(data: dict):
    Path(SOCKSIP_SERVERS_FILE).parent.mkdir(parents=True, exist_ok=True)
    Path(SOCKSIP_SERVERS_FILE).write_text(json.dumps(data, indent=2))

def get_socksip_server_info(srv_id: str) -> dict:
    return load_socksip_servers().get(srv_id, {})

def socksip_is_local(srv_id: str) -> bool:
    srv = get_socksip_server_info(srv_id)
    return srv.get("is_local", True) or not srv.get("api_url", "").strip()

def socksip_server_stock_text(srv: dict) -> str:
    s = srv.get("stock", -1)
    return "Unlimited" if s == -1 else ("Habis" if s == 0 else f"{s} slot")

def socksip_server_status_icon(srv: dict) -> str:
    if not srv.get("enabled"):        return "\u26d4"
    if not srv.get("host"):           return "\u2699\ufe0f"
    if srv.get("stock", -1) == 0:     return "\U0001f534"
    return "\U0001f7e2"

def socksip_user_exists(username: str) -> bool:
    r = subprocess.run(["id", username], capture_output=True)
    return r.returncode == 0

def socksip_user_in_system(username: str) -> bool:
    return socksip_user_exists(username) or user_exists(username)

def socksip_create_user(username: str, password: str, days: int, maxlogin: int) -> dict:
    if socksip_user_exists(username):
        raise Exception(f"Username '{username}' sudah ada di sistem")
    exp_date = (now_wib() + timedelta(days=days)).strftime("%Y-%m-%d")
    try:
        ossl = subprocess.check_output(
            ["openssl", "version"], stderr=subprocess.DEVNULL
        ).decode().split()[1]
        algo = "-6" if (ossl.startswith("3") or ossl.startswith("1.1.1")) else "-1"
        pw_hash = subprocess.check_output(
            ["openssl", "passwd", algo, password], stderr=subprocess.DEVNULL
        ).decode().strip()
    except:
        import crypt
        pw_hash = crypt.crypt(password, crypt.mksalt(crypt.METHOD_SHA512))
    cmd = ["useradd", "-M", "-s", "/bin/false", "-e", exp_date,
           "-K", f"PASS_MAX_DAYS={days}", "-p", pw_hash,
           "-c", f"{maxlogin},{password}", username]
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        err = r.stderr.decode().strip() or r.stdout.decode().strip()
        raise Exception(f"useradd gagal: {err}")
    return {"username": username, "password": password, "exp": exp_date,
            "maxlogin": maxlogin, "ip": get_ip(), "host": get_ip(), "udp_port": "1-65535"}

def socksip_delete_user(username: str) -> bool:
    subprocess.run(["pkill", "-u", username], capture_output=True)
    import time; time.sleep(0.5)
    return subprocess.run(["userdel", "--force", username], capture_output=True).returncode == 0

def socksip_list_users() -> list:
    result = []
    try:
        for line in Path("/etc/passwd").read_text().splitlines():
            parts = line.split(":")
            if len(parts) < 7: continue
            username, shell, home = parts[0], parts[6], parts[5]
            if shell != "/bin/false" or not home.startswith("/home/"): continue
            if username in ("syslog", "hwid", "token"): continue
            exp_str, status = "?", "aktif"
            try:
                chage_out = subprocess.check_output(
                    ["chage", "-l", username], stderr=subprocess.DEVNULL
                ).decode()
                for cl in chage_out.splitlines():
                    if "Account expires" in cl:
                        exp_raw = cl.split(": ", 1)[-1].strip()
                        if exp_raw.lower() not in ("never", "password must be changed"):
                            try:
                                from datetime import datetime as _dt
                                exp_dt  = _dt.strptime(exp_raw, "%b %d, %Y")
                                exp_str = exp_dt.strftime("%Y-%m-%d")
                                status  = "expired" if exp_dt < now_wib() else "aktif"
                            except: exp_str = exp_raw
                        else: exp_str = "Unlimited"
                        break
            except: pass
            try:
                pw_st = subprocess.check_output(
                    ["passwd", "--status", username], stderr=subprocess.DEVNULL
                ).decode().split()
                if len(pw_st) > 1 and pw_st[1] == "L": status = "blokir"
            except: pass
            result.append({"username": username, "exp": exp_str, "status": status})
    except Exception as e:
        log.warning(f"socksip_list_users error: {e}")
    return result

def socksip_api_call(srv_id: str, action: str, payload: dict) -> dict:
    srv     = get_socksip_server_info(srv_id)
    api_url = srv.get("api_url", "").rstrip("/")
    api_key = srv.get("api_key", "")
    if not api_url: return {"ok": False, "error": "api_url tidak dikonfigurasi"}
    try:
        body = json.dumps({"action": action, "key": api_key, **payload}).encode()
        req  = urllib.request.Request(
            f"{api_url}/api", data=body,
            headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"ok": False, "error": str(e)}

def socksip_create_on_server(srv_id: str, username: str, password: str,
                              days: int, maxlogin: int, note: str = "-") -> dict:
    if socksip_is_local(srv_id):
        akun = socksip_create_user(username, password, days, maxlogin)
        srv  = get_socksip_server_info(srv_id)
        akun["host"]     = srv.get("host", "") or get_ip()
        akun["udp_port"] = srv.get("udp_port", "1-65535")
        return akun
    result = socksip_api_call(srv_id, "create_account", {
        "username": username, "password": password,
        "days": days, "maxlogin": maxlogin, "note": note
    })
    if result.get("ok"): return result.get("akun", {})
    raise Exception(result.get("error", "Gagal membuat akun di server remote"))

def socksip_delete_on_server(srv_id: str, username: str) -> bool:
    if socksip_is_local(srv_id): return socksip_delete_user(username)
    return socksip_api_call(srv_id, "delete_account", {"username": username}).get("ok", False)

def format_socksip_akun(akun: dict, srv_id: str = "udp_server1") -> str:
    brand    = CFG.get("BRAND", "OGH-ZIV")
    admin_tg = CFG.get("ADMIN_TG", "@admin")
    srv      = get_socksip_server_info(srv_id)
    label    = srv.get("label", "UDP Server")
    host     = akun.get("host", srv.get("host", get_ip()))
    udp_port = akun.get("udp_port", srv.get("udp_port", "1-65535"))
    exp      = akun.get("exp", "-")
    hari_sisa = ""
    try:
        sisa = (datetime.strptime(exp, "%Y-%m-%d") - now_wib()).days
        hari_sisa = f"({sisa} hari lagi)" if sisa >= 0 else "(EXPIRED)"
    except: pass
    sep = "\u2501" * 23
    return (
        f"\U0001f389 <b>{brand} \u2014 Akun SocksIP (UDP)</b>\n"
        f"{sep}\n"
        f"\U0001f30d <b>Server</b>    : {label}\n"
        f"\U0001f5a5 <b>IP Server</b> : <code>{host}</code>\n"
        f"\U0001f4e1 <b>UDP Port</b>  : <code>{udp_port}</code>\n"
        f"{sep}\n"
        f"\U0001f464 <b>Username</b>  : <code>{akun.get('username','-')}</code>\n"
        f"\U0001f511 <b>Password</b>  : <code>{akun.get('password','-')}</code>\n"
        f"{sep}\n"
        f"\U0001f512 <b>Max Login</b> : {akun.get('maxlogin',2)} device\n"
        f"\U0001f4c5 <b>Expired</b>   : {exp} {hari_sisa}\n"
        f"{sep}\n"
        f"\U0001f4f1 <b>Cara pakai:</b>\n"
        f"1. Download <b>SocksIP</b> di Play Store\n"
        f"2. Buka app \u2192 tap tombol \u2795\n"
        f"3. Masukkan: IP, Port (bebas 1-65535), User, Pass\n"
        f"{sep}\n"
        f"\u26a0\ufe0f Jangan share akun ke orang lain!\n"
        f"\U0001f4ac Bantuan: {admin_tg}"
    )

def format_socksip_paket_list() -> str:
    brand     = CFG.get("BRAND", "OGH-ZIV")
    dana_num  = CFG.get("DANA_NUMBER", "")
    dana_name = CFG.get("DANA_NAME", "")
    sep = "\u2501" * 23
    lines = [
        f"\U0001f4e1 <b>{brand} \u2014 Paket UDP SocksIP</b>\n",
        sep,
        f"1\ufe0f\u20e3  <b>7 Hari</b>   \u2014 Rp 3.000  | Unlimited | 2 device",
        f"2\ufe0f\u20e3  <b>15 Hari</b>  \u2014 Rp 6.000  | Unlimited | 2 device",
        f"3\ufe0f\u20e3  <b>30 Hari</b>  \u2014 Rp 10.000 | Unlimited | 2 device",
        sep,
        f"\U0001f4b3 <b>Metode Pembayaran:</b>",
        f"\U0001f4f1 DANA : <code>{dana_num}</code>  |  A/N: <b>{dana_name}</b>",
    ]
    if qris_aktif(): lines.append("\U0001f532 QRIS : <b>Tersedia</b>")
    return "\n".join(lines)

# ── Handler foto SocksIP ─────────────────────────────────────
async def _handle_socksip_photo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if ctx.user_data.get("socksip_waiting_username"):
        await update.message.reply_text(
            "\u23f3 Pembayaran sudah diverifikasi!\nSilakan ketik <b>username</b> yang kamu inginkan:",
            parse_mode="HTML"
        ); return
    paket_id   = ctx.user_data.get("socksip_paket_id", "1")
    paket_info = PAKET_SOCKSIP.get(paket_id, PAKET_SOCKSIP["1"])
    await update.message.reply_text("\u23f3 Memverifikasi screenshot pembayaran SocksIP...")
    photo    = update.message.photo[-1]
    file_obj = await ctx.bot.get_file(photo.file_id)
    img_path = f"/tmp/ss_socksip_{user.id}_{photo.file_id[:8]}.jpg"
    await file_obj.download_to_drive(img_path)
    ok, reason = verify_payment_screenshot(img_path, paket_info["harga"])
    if ok is True:
        try: os.remove(img_path)
        except: pass
        ctx.user_data["socksip_waiting_username"] = True
        ctx.user_data["socksip_ss_verified"]      = True
        await update.message.reply_text(
            "\u2705 <b>Pembayaran SocksIP Terverifikasi!</b>\n\n"
            "Ketik <b>username</b> yang kamu inginkan:\n"
            "<i>(Huruf kecil, angka, minimal 4 karakter)</i>",
            parse_mode="HTML"
        )
    elif ok is None:
        ctx.user_data["socksip_waiting_username"] = False
        srv_id  = ctx.user_data.get("socksip_server_id", "udp_server1")
        srv     = get_socksip_server_info(srv_id)
        ctx.bot_data[f"pending_socksip_{user.id}"] = {
            "paket_id": paket_id, "server_id": srv_id
        }
        await update.message.reply_text(
            "\u23f3 Screenshot diterima. Admin akan verifikasi dalam beberapa menit. Harap tunggu \U0001f64f"
        )
        for admin_id in CFG.get("ADMIN_IDS", []):
            try:
                caption = (
                    f"\U0001f9fe <b>Verifikasi Manual \u2014 SocksIP</b>\n\n"
                    f"\U0001f464 Pembeli : {user.full_name} (@{user.username or '-'})\n"
                    f"\U0001f194 User ID : <code>{user.id}</code>\n"
                    f"\U0001f4e1 Server  : {srv.get('label','?')}\n"
                    f"\U0001f4e6 Paket   : SocksIP {paket_info['nama']}\n"
                    f"\U0001f4b0 Nominal : Rp {paket_info['harga']:,}\n\n"
                    f"\u2705 /konfirm_socksip_{user.id}   \u274c /tolak_{user.id}"
                )
                await ctx.bot.send_photo(
                    chat_id=admin_id, photo=open(img_path, "rb"),
                    caption=caption, parse_mode="HTML"
                )
            except: pass
        try: os.remove(img_path)
        except: pass
    else:
        admin_tg = CFG.get("ADMIN_TG", "@admin")
        await update.message.reply_text(
            f"\u274c <b>Verifikasi Gagal</b>\n\n{reason}\n\n"
            f"Pastikan screenshot dari aplikasi pembayaran & nominal "
            f"<b>Rp {paket_info['harga']:,}</b> pas.\n\n"
            f"Coba lagi atau hubungi: {admin_tg}",
            parse_mode="HTML"
        )
        try: os.remove(img_path)
        except: pass

# ── Handler teks user SocksIP ────────────────────────────────
async def _handle_socksip_user_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE,
                                     text: str) -> bool:
    user = update.effective_user
    # Step 1: input username
    if ctx.user_data.get("socksip_waiting_username") and ctx.user_data.get("socksip_ss_verified"):
        username = text.lower().strip()
        if len(username) < 4:
            await update.message.reply_text(
                "\u274c Username minimal <b>4 karakter</b>. Coba lagi:", parse_mode="HTML"
            ); return True
        if len(username) > 16:
            await update.message.reply_text(
                "\u274c Username maksimal <b>16 karakter</b>. Coba lagi:", parse_mode="HTML"
            ); return True
        if not re.match(r"^[a-z0-9_]+$", username):
            await update.message.reply_text(
                "\u274c Hanya huruf kecil, angka, underscore. Coba lagi:", parse_mode="HTML"
            ); return True
        if socksip_user_in_system(username):
            await update.message.reply_text(
                f"\u274c Username <code>{username}</code> sudah dipakai. Pilih lain:",
                parse_mode="HTML"
            ); return True
        ctx.user_data["socksip_req_username"]     = username
        ctx.user_data["socksip_waiting_username"] = False
        ctx.user_data["socksip_waiting_password"] = True
        await update.message.reply_text(
            f"\u2705 Username <code>{username}</code> tersedia!\n\n"
            "Ketik <b>password</b> yang kamu inginkan:\n"
            "<i>(Minimal 6 karakter, maks 20 karakter)</i>",
            parse_mode="HTML"
        ); return True
    # Step 2: input password → buat akun
    if ctx.user_data.get("socksip_waiting_password") and ctx.user_data.get("socksip_ss_verified"):
        if len(text) < 6:
            await update.message.reply_text(
                "\u274c Password minimal <b>6 karakter</b>. Coba lagi:", parse_mode="HTML"
            ); return True
        if len(text) > 20:
            await update.message.reply_text(
                "\u274c Password maksimal <b>20 karakter</b>. Coba lagi:", parse_mode="HTML"
            ); return True
        username = ctx.user_data.get("socksip_req_username")
        paket_id = ctx.user_data.get("socksip_paket_id", "1")
        srv_id   = ctx.user_data.get("socksip_server_id", "udp_server1")
        p        = PAKET_SOCKSIP.get(paket_id, PAKET_SOCKSIP["1"])
        await update.message.reply_text("\u23f3 Membuat akun SocksIP, mohon tunggu...")
        try:
            akun = socksip_create_on_server(
                srv_id, username, text, p["hari"], p["maxlogin"],
                f"TG:{user.username or user.first_name}"
            )
        except Exception as e:
            await update.message.reply_text(
                f"\u274c <b>Gagal membuat akun SocksIP.</b>\n\nError: {e}\n\nHubungi admin.",
                parse_mode="HTML"
            )
            ctx.user_data.clear(); return True
        for k in list(ctx.user_data.keys()):
            if k.startswith("socksip_") or k == "vpn_type":
                ctx.user_data.pop(k, None)
        await update.message.reply_text(
            "\U0001f389 <b>Akun SocksIP Berhasil Dibuat!</b>\n\n" + format_socksip_akun(akun, srv_id),
            parse_mode="HTML"
        )
        brand = CFG.get("BRAND", "OGH-ZIV")
        srv   = get_socksip_server_info(srv_id)
        for admin_id in CFG.get("ADMIN_IDS", []):
            try:
                await ctx.bot.send_message(
                    admin_id,
                    f"\U0001f4b0 <b>Pesanan Baru \u2014 SocksIP ({brand})</b>\n"
                    f"\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
                    f"\U0001f464 Pembeli  : {user.full_name} (@{user.username or '-'})\n"
                    f"\U0001f30d Server   : {srv.get('label','?')}\n"
                    f"\U0001f4e1 Paket    : SocksIP {p['nama']}\n"
                    f"\U0001f4b0 Nominal  : Rp {p['harga']:,}\n"
                    f"\U0001f511 Username : <code>{username}</code>\n"
                    f"\U0001f4c5 Expired  : {akun.get('exp','-')}",
                    parse_mode="HTML"
                )
            except: pass
        return True
    return False

# ── Command konfirmasi SocksIP ───────────────────────────────
async def cmd_konfirm_socksip(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    try:
        target_uid = int(update.message.text.split("_")[2])
    except:
        await update.message.reply_text("Format: /konfirm_socksip_<user_id>"); return
    pdata = ctx.bot_data.get(f"pending_socksip_{target_uid}")
    if not pdata:
        await update.message.reply_text("\u274c Data pending SocksIP tidak ditemukan."); return
    ctx.bot_data.pop(f"pending_socksip_{target_uid}", None)
    try:
        ctx.bot_data[f"konfirm_socksip_{target_uid}"] = {
            "paket_id":  pdata.get("paket_id", "1"),
            "server_id": pdata.get("server_id", "udp_server1"),
        }
        await ctx.bot.send_message(
            chat_id=target_uid,
            text=(
                "\u2705 <b>Pembayaran SocksIP Dikonfirmasi!</b>\n\n"
                "Ketik <b>username</b> yang kamu inginkan:\n"
                "<i>(Huruf kecil, angka, minimal 4 karakter)</i>"
            ),
            parse_mode="HTML"
        )
        await update.message.reply_text("\u2705 Dikonfirmasi. Bot sudah minta username ke pembeli SocksIP.")
    except Exception as e:
        await update.message.reply_text(f"\u26a0\ufe0f Tidak bisa kirim ke user: {e}")

# ── Handler callback SocksIP (USER) ─────────────────────────

async def cb_beli_jenis(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    sep = "\u2501" * 23
    keyboard = [
        [InlineKeyboardButton("\U0001f535 UDP ZiVPN  (ZIVPN App)",    callback_data="beli_jenis_zivpn")],
        [InlineKeyboardButton("\U0001f7e2 UDP SocksIP (SocksIP App)",  callback_data="beli_jenis_socksip")],
        [InlineKeyboardButton("\U0001f381 Trial Gratis 120 Menit",     callback_data="trial")],
        [InlineKeyboardButton("\U0001f519 Kembali",                    callback_data="back_start")],
    ]
    await query.edit_message_text(
        f"\U0001f6d2 <b>Pilih Jenis VPN</b>\n\n{sep}\n"
        f"\U0001f535 <b>UDP ZiVPN</b>  \u2014 Pakai aplikasi ZIVPN\n"
        f"\U0001f7e2 <b>UDP SocksIP</b> \u2014 Pakai aplikasi SocksIP\n{sep}\n"
        f"<i>Pilih sesuai aplikasi yang kamu gunakan:</i>",
        parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def cb_beli_jenis_zivpn(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    ctx.user_data["vpn_type"] = "zivpn"
    keyboard = [
        [InlineKeyboardButton("1\ufe0f\u20e3  7 Hari  \u2014 Rp 3.000",    callback_data="paket_1")],
        [InlineKeyboardButton("2\ufe0f\u20e3  15 Hari \u2014 Rp 6.000",    callback_data="paket_2")],
        [InlineKeyboardButton("3\ufe0f\u20e3  30 Hari \u2014 Rp 10.000",   callback_data="paket_3")],
        [InlineKeyboardButton("\U0001f381 Trial Gratis 120 Menit",           callback_data="trial")],
        [InlineKeyboardButton("\U0001f519 Kembali",                          callback_data="beli_jenis")],
    ]
    await query.edit_message_text(
        format_paket_list(), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML"
    )

async def cb_beli_jenis_socksip(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    ctx.user_data["vpn_type"] = "socksip"
    keyboard = [
        [InlineKeyboardButton("1\ufe0f\u20e3  7 Hari  \u2014 Rp 3.000",  callback_data="socksip_paket_1")],
        [InlineKeyboardButton("2\ufe0f\u20e3  15 Hari \u2014 Rp 6.000",  callback_data="socksip_paket_2")],
        [InlineKeyboardButton("3\ufe0f\u20e3  30 Hari \u2014 Rp 10.000", callback_data="socksip_paket_3")],
        [InlineKeyboardButton("\U0001f519 Kembali",                        callback_data="beli_jenis")],
    ]
    await query.edit_message_text(
        format_socksip_paket_list(), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML"
    )

async def cb_socksip_paket(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query    = update.callback_query; await query.answer()
    paket_id = query.data.split("_")[2]
    if paket_id not in PAKET_SOCKSIP:
        await query.edit_message_text("\u274c Paket tidak valid."); return
    p = PAKET_SOCKSIP[paket_id]
    ctx.user_data["socksip_paket_id"]    = paket_id
    ctx.user_data["socksip_paket_harga"] = p["harga"]
    srvs_all  = load_socksip_servers()
    keyboard  = []; srv_lines = []
    for srv_id, srv in srvs_all.items():
        icon  = socksip_server_status_icon(srv)
        label = srv.get("label", srv_id.upper())
        stock = socksip_server_stock_text(srv)
        note  = srv.get("note", "")
        if not srv.get("enabled") or not srv.get("host"):
            keyboard.append([InlineKeyboardButton(
                f"{icon} {label} \u2014 Belum tersedia", callback_data="server_unavailable")])
        elif srv.get("stock", -1) == 0:
            keyboard.append([InlineKeyboardButton(
                f"{icon} {label} \u2014 Stok Habis", callback_data="server_unavailable")])
        else:
            keyboard.append([InlineKeyboardButton(
                f"{icon} {label} \u2014 {stock}",
                callback_data=f"socksip_srv_{srv_id}_paket_{paket_id}")])
        srv_lines.append(f"{icon} <b>{label}</b> \u2014 {stock}\n   <i>{note}</i>")
    keyboard.append([InlineKeyboardButton("\U0001f519 Kembali", callback_data="beli_jenis_socksip")])
    sep = "\u2501" * 23
    await query.edit_message_text(
        f"\U0001f4e1 <b>Paket SocksIP {p['nama']} \u2014 Rp {p['harga']:,}</b>\n\n"
        f"\U0001f30d <b>Pilih Server/Region:</b>\n{sep}\n"
        + "\n".join(srv_lines) + f"\n{sep}\n<i>Pilih server yang tersedia:</i>",
        parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def cb_socksip_srv_paket(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    raw      = query.data.replace("socksip_srv_", "")
    parts    = raw.split("_paket_")
    srv_id   = parts[0]
    paket_id = parts[1] if len(parts) > 1 else "1"
    if paket_id not in PAKET_SOCKSIP:
        await query.edit_message_text("\u274c Paket tidak valid."); return
    p   = PAKET_SOCKSIP[paket_id]
    srv = get_socksip_server_info(srv_id)
    ctx.user_data["socksip_paket_id"]    = paket_id
    ctx.user_data["socksip_paket_harga"] = p["harga"]
    ctx.user_data["socksip_server_id"]   = srv_id
    ctx.user_data["vpn_type"]            = "socksip"
    keyboard = [[InlineKeyboardButton(
        "\U0001f4b3 Bayar via DANA", callback_data=f"socksip_bayar_dana_{paket_id}")]]
    if qris_aktif():
        keyboard.append([InlineKeyboardButton(
            "\U0001f532 Bayar via QRIS", callback_data=f"socksip_bayar_qris_{paket_id}")])
    keyboard.append([InlineKeyboardButton(
        "\U0001f519 Kembali", callback_data=f"socksip_paket_{paket_id}")])
    await query.edit_message_text(
        f"\U0001f4e1 <b>SocksIP \u2014 Paket {p['nama']} \u2014 Rp {p['harga']:,}</b>\n"
        f"\U0001f30d <b>Server</b> : {srv.get('label','?')}\n\nPilih metode pembayaran:",
        parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def cb_socksip_bayar_dana(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query    = update.callback_query; await query.answer()
    paket_id = query.data.split("_")[3]
    p        = PAKET_SOCKSIP.get(paket_id, PAKET_SOCKSIP["1"])
    ctx.user_data["socksip_paket_id"] = paket_id
    ctx.user_data["vpn_type"]         = "socksip"
    dana_num  = CFG.get("DANA_NUMBER", "")
    dana_name = CFG.get("DANA_NAME", "")
    sep = "\u2501" * 23
    await query.edit_message_text(
        f"\U0001f4b3 <b>Pembayaran SocksIP via DANA</b>\n\n"
        f"\U0001f4e1 Paket    : SocksIP {p['nama']}\n{sep}\n"
        f"\U0001f4f1 No. DANA : <code>{dana_num}</code>\n"
        f"\U0001f464 A/N      : <b>{dana_name}</b>\n"
        f"\U0001f4b0 Nominal  : <b>Rp {p['harga']:,}</b> (pas)\n{sep}\n"
        f"\U0001f4f8 Setelah transfer, kirim <b>screenshot bukti bayar</b> ke chat ini.\n\n"
        f"\u26a0\ufe0f Pastikan nominal <b>pas</b> sesuai paket!",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(
            "\U0001f519 Kembali", callback_data=f"socksip_paket_{paket_id}")]])
    )

async def cb_socksip_bayar_qris(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query    = update.callback_query; await query.answer()
    paket_id = query.data.split("_")[3]
    p        = PAKET_SOCKSIP.get(paket_id, PAKET_SOCKSIP["1"])
    ctx.user_data["socksip_paket_id"] = paket_id
    ctx.user_data["vpn_type"]         = "socksip"
    if not Path(QRIS_IMG).exists():
        await query.edit_message_text(
            "\u274c Gambar QRIS belum tersedia. Hubungi admin.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(
                "\U0001f519 Kembali", callback_data=f"socksip_paket_{paket_id}")]])
        ); return
    sep = "\u2501" * 23
    await query.edit_message_text(
        f"\U0001f532 <b>Pembayaran SocksIP via QRIS</b>\n\n"
        f"\U0001f4e1 Paket   : SocksIP {p['nama']}\n"
        f"\U0001f4b0 Nominal : <b>Rp {p['harga']:,}</b>\n{sep}\n"
        f"Scan QRIS lalu kirim <b>screenshot bukti bayar</b>.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(
            "\U0001f519 Kembali", callback_data=f"socksip_paket_{paket_id}")]])
    )
    try:
        await query.message.reply_photo(
            photo=open(QRIS_IMG, "rb"),
            caption=f"\U0001f532 QRIS \u2014 Rp {p['harga']:,}\nKirim screenshot setelah bayar."
        )
    except: pass

# ── Handler callback Admin SocksIP ───────────────────────────

async def cb_admin_socksip(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    if not is_admin(query.from_user.id): return
    keyboard = [
        [InlineKeyboardButton("\U0001f464 Buat Akun Manual",   callback_data="admin_socksip_buat_manual")],
        [InlineKeyboardButton("\u26a1 Generate Otomatis",      callback_data="admin_socksip_buat_auto")],
        [InlineKeyboardButton("\U0001f5d1\ufe0f Hapus Akun",   callback_data="admin_socksip_del")],
        [InlineKeyboardButton("\U0001f4cb List Akun",          callback_data="admin_socksip_list")],
        [InlineKeyboardButton("\U0001f519 Kembali",            callback_data="admin")],
    ]
    await query.edit_message_text(
        "\U0001f4e1 <b>Panel Admin \u2014 SocksIP (UDP)</b>\n"
        "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
        "Kelola akun UDP SocksIP di sini.\n\n<i>Pilih aksi:</i>",
        parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def cb_admin_socksip_buat_manual(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    if not is_admin(query.from_user.id): return
    srvs = load_socksip_servers()
    keyboard = []; srv_lines = []
    for srv_id, srv in srvs.items():
        icon  = socksip_server_status_icon(srv)
        label = srv.get("label", srv_id.upper())
        if srv.get("enabled") and srv.get("host"):
            keyboard.append([InlineKeyboardButton(
                f"{icon} {label}", callback_data=f"admin_socksip_srv_{srv_id}__manual")])
        srv_lines.append(f"{icon} <b>{label}</b>\n   <i>{srv.get('note','')}</i>")
    keyboard.append([InlineKeyboardButton("\U0001f519 Kembali", callback_data="admin_socksip")])
    await query.edit_message_text(
        "\U0001f464 <b>Buat Akun SocksIP Manual</b>\n\n\U0001f30d Pilih Server:\n"
        "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
        + "\n".join(srv_lines),
        parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def cb_admin_socksip_buat_auto(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    if not is_admin(query.from_user.id): return
    srvs = load_socksip_servers()
    keyboard = []
    for srv_id, srv in srvs.items():
        icon  = socksip_server_status_icon(srv)
        label = srv.get("label", srv_id.upper())
        if srv.get("enabled") and srv.get("host"):
            keyboard.append([InlineKeyboardButton(
                f"{icon} {label}", callback_data=f"admin_socksip_srv_{srv_id}__auto")])
    keyboard.append([InlineKeyboardButton("\U0001f519 Kembali", callback_data="admin_socksip")])
    await query.edit_message_text(
        "\u26a1 <b>Generate Akun SocksIP Otomatis</b>\n\nPilih server:",
        parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def cb_admin_socksip_srv(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    if not is_admin(query.from_user.id): return
    raw    = query.data.replace("admin_socksip_srv_", "")
    parts  = raw.split("__", 1)
    srv_id = parts[0]; mode = parts[1] if len(parts) > 1 else "manual"
    srv    = get_socksip_server_info(srv_id)
    if mode == "auto":
        keyboard = [
            [InlineKeyboardButton("7 Hari",   callback_data=f"admin_socksip_auto_7_{srv_id}")],
            [InlineKeyboardButton("15 Hari",  callback_data=f"admin_socksip_auto_15_{srv_id}")],
            [InlineKeyboardButton("30 Hari",  callback_data=f"admin_socksip_auto_30_{srv_id}")],
            [InlineKeyboardButton("\U0001f519 Batal", callback_data="admin_socksip")],
        ]
        await query.edit_message_text(
            f"\u26a1 <b>Generate Akun SocksIP Otomatis</b>\n"
            f"\U0001f30d Server: <b>{srv.get('label', srv_id)}</b>\n\nPilih durasi:",
            parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        ctx.user_data["admin_action"]             = "socksip_manual_step1"
        ctx.user_data["socksip_manual_data"]      = {}
        ctx.user_data["socksip_manual_server_id"] = srv_id
        await query.edit_message_text(
            f"\u270f\ufe0f <b>Buat Akun SocksIP Manual \u2014 Langkah 1/3</b>\n"
            f"\U0001f30d Server: <b>{srv.get('label', srv_id)}</b>\n\n"
            "Ketik <b>username</b>:\n<i>(Huruf kecil, angka, underscore \u2014 4-16 karakter)</i>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("\U0001f519 Batal", callback_data="admin_socksip")]])
        )

async def cb_admin_socksip_auto_hari(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    if not is_admin(query.from_user.id): return
    raw   = query.data.replace("admin_socksip_auto_", "")
    parts = raw.split("_", 1)
    try: hari = int(parts[0])
    except:
        await query.edit_message_text("\u274c Format tidak valid."); return
    srv_id   = parts[1] if len(parts) > 1 else "udp_server1"
    srv      = get_socksip_server_info(srv_id)
    username = rand_user("udp")
    password = rand_pass(10)
    await query.edit_message_text("\u23f3 Membuat akun SocksIP otomatis...")
    try:
        akun = socksip_create_on_server(srv_id, username, password, hari, 2, "ADMIN-FREE-AUTO")
    except Exception as e:
        await query.edit_message_text(
            f"\u274c <b>Gagal membuat akun SocksIP.</b>\n\nError: {e}", parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(
                "\U0001f519 Admin SocksIP", callback_data="admin_socksip")]])
        ); return
    await query.edit_message_text(
        f"\u2705 <b>Akun SocksIP Otomatis Berhasil Dibuat!</b>\n"
        f"\U0001f30d Server: <b>{srv.get('label', srv_id)}</b>\n\n" + format_socksip_akun(akun, srv_id),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(
            "\U0001f519 Admin SocksIP", callback_data="admin_socksip")]])
    )

async def cb_admin_socksip_del(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    if not is_admin(query.from_user.id): return
    ctx.user_data["admin_action"] = "socksip_del"
    await query.edit_message_text(
        "\U0001f5d1\ufe0f <b>Hapus Akun SocksIP</b>\n\nKirim <b>username</b> yang ingin dihapus:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(
            "\U0001f519 Batal", callback_data="admin_socksip")]])
    )

async def cb_admin_socksip_list(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    if not is_admin(query.from_user.id): return
    await query.edit_message_text("\u23f3 Mengambil data akun SocksIP...")
    users = socksip_list_users()
    sep   = "\u2501" * 23
    out   = [f"\U0001f4cb <b>List Akun SocksIP (UDP)</b>\n{sep}"]
    if not users:
        out.append("Belum ada akun SocksIP.")
    else:
        aktif = expired = blokir = 0
        for i, u in enumerate(users[:50], 1):
            if u["status"] == "aktif":    st = "\u2705"; aktif   += 1
            elif u["status"] == "blokir": st = "\U0001f512"; blokir  += 1
            else:                         st = "\u274c"; expired += 1
            out.append(f"{i}. {st} <code>{u['username']}</code> | Exp: {u['exp']}")
        if len(users) > 50: out.append(f"... (+{len(users)-50} lainnya)")
        out.append(f"\n\U0001f4ca Total: <b>{len(users)}</b> | \u2705 {aktif} | \u274c {expired} | \U0001f512 {blokir}")
    await query.edit_message_text(
        "\n".join(out), parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(
            "\U0001f519 Kembali", callback_data="admin_socksip")]])
    )

