#!/bin/bash
# ============================================================
#   OGH-ZIV Premium Panel
#   Creator : OGH-ZIV Team
#   Ketik   : menu  untuk membuka panel
#   Support : Debian (all version) & Ubuntu (all version)
# ============================================================

# ════════════════════════════════════════════════════════════
#  CEK IZIN — IP ADA DI DAFTAR = LOLOS | TIDAK ADA = BLOK
# ════════════════════════════════════════════════════════════
check_izin() {
    local R='\033[1;31m' Y='\033[1;33m' W='\033[1;37m' N='\033[0m'
    local IZIN_URL="https://raw.githubusercontent.com/chanelog/izin/main/ip"

    # Ambil IP publik VPS
    local MY_IP=""
    for _src in \
        "curl -s4 --max-time 8 https://ifconfig.me" \
        "curl -s4 --max-time 8 https://icanhazip.com" \
        "curl -s4 --max-time 8 https://api.ipify.org"
    do
        MY_IP=$(eval "$_src" 2>/dev/null | tr -d '[:space:]')
        [[ "$MY_IP" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]] && break
        MY_IP=""
    done
    [[ -z "$MY_IP" ]] && MY_IP=$(hostname -I 2>/dev/null | awk '{print $1}')

    # Download daftar izin langsung tanpa cache
    local LIST
    LIST=$(curl -s --max-time 10 "$IZIN_URL" 2>/dev/null)
    [[ -z "$LIST" ]] && LIST=$(wget -qO- --timeout=10 "$IZIN_URL" 2>/dev/null)

    if [[ -z "$LIST" ]]; then
        clear; echo ""
        echo -e "${Y}  ──────────────────────────────────────────────────${N}"
        echo -e "  ⚠️   GAGAL CEK IZIN — PANEL DIBLOKIR"
        echo -e "${Y}  ──────────────────────────────────────────────────${N}"
        echo -e "  Tidak dapat terhubung ke server validasi."
        echo -e "  Periksa koneksi internet VPS kamu."
        echo -e "${Y}  ──────────────────────────────────────────────────${N}"
        echo ""; exit 1
    fi

    # Cari IP di daftar
    local TODAY; TODAY=$(date +%Y-%m-%d)
    local FOUND=0 M_LABEL="" M_EXP=""

    while IFS= read -r _line; do
        [[ -z "$_line" || "$_line" =~ ^[[:space:]]*# ]] && continue
        local a="" b="" c=""
        read -r a b c <<< "$_line"
        if [[ "$c" == "$MY_IP" ]]; then
            FOUND=1; M_LABEL="$a"; M_EXP="$b"; break
        fi
    done <<< "$LIST"

    # IP tidak ditemukan → BLOK
    if [[ $FOUND -eq 0 ]]; then
        clear; echo ""
        echo -e "${R}  ──────────────────────────────────────────────────${N}"
        echo -e "  🚫  AKSES DITOLAK — IP TIDAK TERDAFTAR"
        echo -e "${R}  ──────────────────────────────────────────────────${N}"
        printf  "  IP VPS  : ${Y}%s${N}\n" "$MY_IP"
        echo -e "${R}  ──────────────────────────────────────────────────${N}"
        echo -e "  Hubungi kami untuk mendaftarkan IP VPS kamu:"
        echo -e "  ${LG}  📱 WhatsApp : wa.me/6283825566891${NC}"
        echo -e "  ${LC}  ✈️  Telegram  : t.me/ArsyadF${NC}"
        echo -e "${R}  ──────────────────────────────────────────────────${N}"
        echo ""; exit 1
    fi

    # Cek expired
    if [[ "$M_EXP" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ && "$TODAY" > "$M_EXP" ]]; then
        clear; echo ""
        echo -e "${R}  ──────────────────────────────────────────────────${N}"
        echo -e "  ⛔  LISENSI HABIS — PANEL DIBLOKIR"
        echo -e "${R}  ──────────────────────────────────────────────────${N}"
        printf  "  IP VPS  : ${Y}%s${N}\n" "$MY_IP"
        printf  "  Label   : ${W}%s${N}\n" "$M_LABEL"
        printf  "  Expired : ${R}%s${N}\n" "$M_EXP"
        echo -e "${R}  ──────────────────────────────────────────────────${N}"
        echo -e "  Hubungi kami untuk perpanjangan lisensi:"
        echo -e "  ${LG}  📱 WhatsApp : wa.me/6283825566891${NC}"
        echo -e "  ${LC}  ✈️  Telegram  : t.me/ArsyadF${NC}"
        echo -e "${R}  ──────────────────────────────────────────────────${N}"
        echo ""; exit 1
    fi

    # LOLOS
    IZIN_IP="$MY_IP"
    IZIN_LABEL="$M_LABEL"
    IZIN_EXP="$M_EXP"
}

check_izin

# ── CEK OS — HANYA DEBIAN & UBUNTU ──────────────────────────────────────────────────
check_os() {
    if [[ ! -f /etc/os-release ]]; then
        echo -e "
[1;31m✘ OS tidak dikenali! Script ini hanya untuk Debian & Ubuntu.[0m
"
        exit 1
    fi
    source /etc/os-release 2>/dev/null
    local os_name; os_name=$(echo "${ID}" | tr '[:upper:]' '[:lower:]')
    local os_like; os_like=$(echo "${ID_LIKE:-}" | tr '[:upper:]' '[:lower:]')

    if [[ "$os_name" != "debian" && "$os_name" != "ubuntu" ]] \
       && [[ "$os_like" != *"debian"* && "$os_like" != *"ubuntu"* ]]; then
        echo ""
        echo -e "[1;31m  ──────────────────────────────────────────────────[0m"
        echo -e "  ✘  OS TIDAK DIDUKUNG!"
        echo -e "  OS kamu : [1;33m${PRETTY_NAME:-$ID}[0m"
        echo -e "  Script ini hanya mendukung:"
        echo -e "  [1;32m✔[0m  Debian (semua versi)"
        echo -e "  [1;32m✔[0m  Ubuntu (semua versi)"
        echo -e "[1;31m  ──────────────────────────────────────────────────[0m"
        echo ""
        exit 1
    fi

    # Simpan info OS untuk ditampilkan di panel
    OS_NAME="${PRETTY_NAME:-$ID $VERSION_ID}"
    OS_ID="$os_name"
}

# ── KONSTANTA & PATH ──────────────────────────────────────────────────
DIR="/etc/zivpn"
CFG="$DIR/config.json"
BIN="/usr/local/bin/zivpn-bin"
SVC="/etc/systemd/system/zivpn.service"
LOG="$DIR/zivpn.log"
UDB="$DIR/users.db"
DOMF="$DIR/domain.conf"
BOTF="$DIR/bot.conf"
STRF="$DIR/store.conf"
THEMEF="$DIR/theme.conf"
MLDB="$DIR/maxlogin.db"   # format: username|maxdevice
BINARY_URL="https://github.com/fauzanihanipah/ziv-udp/releases/download/udp-zivpn/udp-zivpn-linux-amd64"
CONFIG_URL="https://raw.githubusercontent.com/fauzanihanipah/ziv-udp/main/config.json"
SCRIPT_VERSION="1.1"
SCRIPT_URL="https://raw.githubusercontent.com/chanelog/combo/main/ogh-ziv.sh"
VERSION_URL="https://raw.githubusercontent.com/chanelog/combo/main/version.txt"

# ── UTILS ──────────────────────────────────────────────────
check_root() { [[ $EUID -ne 0 ]] && { echo -e "\n\033[1;31m✘ Jalankan sebagai root!\033[0m\n"; exit 1; }; }
ok()    { echo -e "  ${A2}✔${NC}  $*"; }
inf()   { echo -e "  ${A3}➜${NC}  $*"; }
warn()  { echo -e "  ${A4}⚠${NC}  $*"; }
err()   { echo -e "  \033[1;31m✘${NC}  $*"; }
pause() { echo ""; echo -ne "  ${DIM}╰─ [ Enter ] kembali ke menu...${NC}"; read -r; }

get_ip()     { curl -s4 --max-time 5 ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}'; }
get_port()   { grep -o '"listen":":[0-9]*"\|"listen": *":[0-9]*"' "$CFG" 2>/dev/null | grep -o '[0-9]*' || echo "5667"; }
get_domain() { cat "$DOMF" 2>/dev/null || get_ip; }
is_up()      { systemctl is-active --quiet zivpn 2>/dev/null; }
total_user() { [[ -f "$UDB" ]] && grep -c '' "$UDB" 2>/dev/null || echo 0; }
exp_count()  {
    local t; t=$(date +%Y-%m-%d)
    [[ -f "$UDB" ]] && awk -F'|' -v d="$t" '$3<d{c++}END{print c+0}' "$UDB" || echo 0
}
rand_pass()  { tr -dc 'A-Za-z0-9' </dev/urandom | head -c 12; }

# ── MAXLOGIN HELPERS ──────────────────────────────────────────────────
get_maxlogin() {
    local u="$1"
    grep "^${u}|" "$MLDB" 2>/dev/null | cut -d'|' -f2
}

set_maxlogin() {
    local u="$1" ml="$2"
    sed -i "/^${u}|/d" "$MLDB" 2>/dev/null
    echo "${u}|${ml}" >> "$MLDB"
}

del_maxlogin() {
    local u="$1"
    sed -i "/^${u}|/d" "$MLDB" 2>/dev/null
}

# Hitung koneksi aktif sebuah user (via ss UDP)
count_active_conn() {
    local u="$1"
    local port; port=$(get_port)
    ss -u -n -p 2>/dev/null | grep ":$port" | grep -c "$u" 2>/dev/null || echo 0
}

# Cek & enforce maxlogin – panggil dari cron atau saat buka menu
check_maxlogin_all() {
    [[ ! -f "$MLDB" || ! -f "$UDB" ]] && return
    local port; port=$(get_port)
    local today; today=$(date +%Y-%m-%d)
    while IFS='|' read -r uname maxdev; do
        [[ -z "$uname" || -z "$maxdev" ]] && continue
        # Hitung koneksi aktif berdasarkan auth log zivpn atau ss
        local conn
        conn=$(ss -u -n -p 2>/dev/null | grep -c ":$port" || echo 0)
        # Pakai pendekatan: cek dari log zivpn jika ada
        local active=0
        if [[ -f "$LOG" ]]; then
            active=$(grep -c "user=$uname" "$LOG" 2>/dev/null || echo 0)
        fi
        # Jika koneksi aktif melebihi maxdev, hapus akun
        if [[ "$active" -gt "$maxdev" ]]; then
            sed -i "/^${uname}|/d" "$UDB"
            del_maxlogin "$uname"
            _reload_pw
            _tg_send "🚫 <b>Auto-Delete MaxLogin</b>
👤 User: <code>$uname</code>
⚠️ Melebihi batas ${maxdev} device — akun otomatis dihapus!"
        fi
    done < "$MLDB"
}

# ════════════════════════════════════════════════════════════
#  TEMA WARNA  — 15 Tema Premium
# ════════════════════════════════════════════════════════════
load_theme() {
    local theme=1
    [[ -f "$THEMEF" ]] && theme=$(cat "$THEMEF" 2>/dev/null)

    case "$theme" in
        # ── Tema 2: ARCTIC CYAN — Neon biru dingin elegan ──
        2)  A1='\033[38;5;51m';  A2='\033[1;36m';        A3='\033[0;36m';
            A4='\033[38;5;123m'; AL='\033[38;5;87m';     AT='\033[1;37m'
            THEME_NAME="ARCTIC CYAN" ;;
        # ── Tema 3: MATRIX GREEN — Hijau hacker klasik ──
        3)  A1='\033[38;5;46m';  A2='\033[1;32m';        A3='\033[38;5;40m';
            A4='\033[38;5;118m'; AL='\033[38;5;82m';     AT='\033[1;37m'
            THEME_NAME="MATRIX GREEN" ;;
        # ── Tema 4: ROYAL GOLD — Emas mewah kerajaan ──
        4)  A1='\033[38;5;220m'; A2='\033[38;5;226m';    A3='\033[38;5;214m';
            A4='\033[38;5;208m'; AL='\033[38;5;228m';    AT='\033[1;37m'
            THEME_NAME="ROYAL GOLD" ;;
        # ── Tema 5: CRIMSON RED — Merah gagah berani ──
        5)  A1='\033[38;5;196m'; A2='\033[1;31m';        A3='\033[38;5;203m';
            A4='\033[38;5;197m'; AL='\033[38;5;204m';    AT='\033[1;37m'
            THEME_NAME="CRIMSON RED" ;;
        # ── Tema 6: SAKURA PINK — Pink cantik lembut ──
        6)  A1='\033[38;5;213m'; A2='\033[38;5;218m';    A3='\033[38;5;219m';
            A4='\033[38;5;211m'; AL='\033[38;5;225m';    AT='\033[1;37m'
            THEME_NAME="SAKURA PINK" ;;
        # ── Tema 7: RAINBOW — Pelangi ceria warna-warni ──
        7)  A1='\033[1;37m';     A2='\033[1;37m';        A3='\033[38;5;51m';
            A4='\033[1;33m';     AL='\033[38;5;196m';    AT='\033[1;37m'
            THEME_NAME="RAINBOW" ;;
        # ── Tema 8: OCEAN BLUE — Biru samudra dalam ──
        8)  A1='\033[38;5;27m';  A2='\033[38;5;33m';     A3='\033[38;5;39m';
            A4='\033[38;5;45m';  AL='\033[38;5;81m';     AT='\033[1;37m'
            THEME_NAME="OCEAN BLUE" ;;
        # ── Tema 9: SUNSET ORANGE — Oranye hangat senja ──
        9)  A1='\033[38;5;202m'; A2='\033[38;5;208m';    A3='\033[38;5;214m';
            A4='\033[38;5;220m'; AL='\033[38;5;215m';    AT='\033[1;37m'
            THEME_NAME="SUNSET ORANGE" ;;
        # ── Tema 10: MIDNIGHT — Gelap misterius premium ──
        10) A1='\033[38;5;239m'; A2='\033[38;5;245m';    A3='\033[38;5;250m';
            A4='\033[38;5;153m'; AL='\033[38;5;189m';    AT='\033[1;37m'
            THEME_NAME="MIDNIGHT" ;;
        # ── Tema 11: EMERALD — Hijau zamrud mewah ──
        11) A1='\033[38;5;35m';  A2='\033[38;5;41m';     A3='\033[38;5;48m';
            A4='\033[38;5;85m';  AL='\033[38;5;121m';    AT='\033[1;37m'
            THEME_NAME="EMERALD" ;;
        # ── Tema 12: LAVENDER — Ungu lavender anggun ──
        12) A1='\033[38;5;99m';  A2='\033[38;5;105m';    A3='\033[38;5;111m';
            A4='\033[38;5;183m'; AL='\033[38;5;189m';    AT='\033[1;37m'
            THEME_NAME="LAVENDER" ;;
        # ── Tema 13: ROSE GOLD — Pink keemasan ekslusif ──
        13) A1='\033[38;5;210m'; A2='\033[38;5;216m';    A3='\033[38;5;222m';
            A4='\033[38;5;217m'; AL='\033[38;5;224m';    AT='\033[1;37m'
            THEME_NAME="ROSE GOLD" ;;
        # ── Tema 14: ICE WHITE — Putih bersih minimalis ──
        14) A1='\033[38;5;195m'; A2='\033[38;5;231m';    A3='\033[38;5;159m';
            A4='\033[38;5;123m'; AL='\033[38;5;255m';    AT='\033[38;5;231m'
            THEME_NAME="ICE WHITE" ;;
        # ── Tema 15: NEON PURPLE — Ungu neon cyberpunk ──
        15) A1='\033[38;5;129m'; A2='\033[38;5;135m';    A3='\033[38;5;141m';
            A4='\033[38;5;201m'; AL='\033[38;5;171m';    AT='\033[1;37m'
            THEME_NAME="NEON PURPLE" ;;
        # ── Tema 1 (default): VIOLET — Ungu premium klasik ──
        *)  A1='\033[38;5;135m'; A2='\033[1;35m';        A3='\033[38;5;141m';
            A4='\033[1;33m';     AL='\033[38;5;141m';    AT='\033[38;5;231m'
            THEME_NAME="VIOLET" ;;
    esac

    NC='\033[0m'; BLD='\033[1m'; DIM='\033[2m'; IT='\033[3m'
    W='\033[1;37m'; LG='\033[1;32m'; LR='\033[1;31m'; LC='\033[1;36m'; Y='\033[1;33m'
}

# ════════════════════════════════════════════════════════════
#  MENU TEMA  — 15 Tema Premium
# ════════════════════════════════════════════════════════════
menu_tema() {
    while true; do
        clear; load_theme
        local cur_theme; cur_theme=$(cat "$THEMEF" 2>/dev/null || echo 1)
        echo ""
        echo -e "  \033[38;5;135m──────────────────────────────────────────────────\033[0m"
        echo -e "  \033[3m\033[38;5;141m  🎨  PILIH TEMA WARNA — 15 Tema Premium\033[0m"
        echo -e "  \033[38;5;135m──────────────────────────────────────────────────\033[0m"
        echo ""

        # Helper fungsi tampilkan baris tema dengan preview warna
        _tema_row() {
            local num="$1" icon="$2" name="$3" desc="$4"
            local c1="$5" c2="$6" c3="$7"   # warna preview
            local mark="  "
            [[ "$cur_theme" == "$num" ]] && mark="\033[1;32m▶\033[0m "
            printf "  %b%s  \033[2m[%2s]\033[0m  %b%-14s\033[0m  %b██\033[0m%b██\033[0m%b██\033[0m  \033[2m%s\033[0m\n" \
                "$mark" "$icon" "$num" "$c1" "$name" "$c1" "$c2" "$c3" "$desc"
        }

        _tema_row  1 "💜" "VIOLET"       "Ungu premium klasik"    '\033[38;5;135m' '\033[38;5;141m' '\033[1;35m'
        echo -e "  \033[38;5;239m──────────────────────────────────────────────────\033[0m"
        _tema_row  2 "🩵" "ARCTIC CYAN"  "Neon biru dingin elegan" '\033[38;5;51m'  '\033[38;5;87m'  '\033[1;36m'
        echo -e "  \033[38;5;239m──────────────────────────────────────────────────\033[0m"
        _tema_row  3 "💚" "MATRIX GREEN" "Hijau hacker klasik"     '\033[38;5;46m'  '\033[38;5;82m'  '\033[38;5;40m'
        echo -e "  \033[38;5;239m──────────────────────────────────────────────────\033[0m"
        _tema_row  4 "💛" "ROYAL GOLD"   "Emas mewah kerajaan"     '\033[38;5;220m' '\033[38;5;226m' '\033[38;5;214m'
        echo -e "  \033[38;5;239m──────────────────────────────────────────────────\033[0m"
        _tema_row  5 "❤️ " "CRIMSON RED"  "Merah gagah berani"      '\033[38;5;196m' '\033[38;5;203m' '\033[38;5;204m'
        echo -e "  \033[38;5;239m──────────────────────────────────────────────────\033[0m"
        _tema_row  6 "🩷" "SAKURA PINK"  "Pink cantik lembut"      '\033[38;5;213m' '\033[38;5;219m' '\033[38;5;218m'
        echo -e "  \033[38;5;239m──────────────────────────────────────────────────\033[0m"
        _tema_row  7 "🌈" "RAINBOW"      "Perisai warna-warni"     '\033[38;5;196m' '\033[38;5;82m'  '\033[38;5;51m'
        echo -e "  \033[38;5;239m──────────────────────────────────────────────────\033[0m"
        _tema_row  8 "🌊" "OCEAN BLUE"   "Biru samudra dalam"      '\033[38;5;27m'  '\033[38;5;33m'  '\033[38;5;45m'
        echo -e "  \033[38;5;239m──────────────────────────────────────────────────\033[0m"
        _tema_row  9 "🌅" "SUNSET ORANGE" "Oranye hangat senja"    '\033[38;5;202m' '\033[38;5;208m' '\033[38;5;214m'
        echo -e "  \033[38;5;239m──────────────────────────────────────────────────\033[0m"
        _tema_row 10 "🌑" "MIDNIGHT"     "Gelap misterius premium"  '\033[38;5;239m' '\033[38;5;245m' '\033[38;5;153m'
        echo -e "  \033[38;5;239m──────────────────────────────────────────────────\033[0m"
        _tema_row 11 "💎" "EMERALD"      "Hijau zamrud mewah"       '\033[38;5;35m'  '\033[38;5;41m'  '\033[38;5;85m'
        echo -e "  \033[38;5;239m──────────────────────────────────────────────────\033[0m"
        _tema_row 12 "🫧" "LAVENDER"     "Ungu lavender anggun"     '\033[38;5;99m'  '\033[38;5;105m' '\033[38;5;183m'
        echo -e "  \033[38;5;239m──────────────────────────────────────────────────\033[0m"
        _tema_row 13 "🌸" "ROSE GOLD"    "Pink keemasan eksklusif"  '\033[38;5;210m' '\033[38;5;216m' '\033[38;5;222m'
        echo -e "  \033[38;5;239m──────────────────────────────────────────────────\033[0m"
        _tema_row 14 "🧊" "ICE WHITE"    "Putih bersih minimalis"   '\033[38;5;195m' '\033[38;5;231m' '\033[38;5;159m'
        echo -e "  \033[38;5;239m──────────────────────────────────────────────────\033[0m"
        _tema_row 15 "⚡" "NEON PURPLE"  "Ungu neon cyberpunk"      '\033[38;5;129m' '\033[38;5;135m' '\033[38;5;201m'

        echo ""
        echo -e "  \033[38;5;135m──────────────────────────────────────────────────\033[0m"
        echo -e "  \033[2mTema aktif : \033[0m${AL}${THEME_NAME}${NC}"
        echo -e "  \033[38;5;135m──────────────────────────────────────────────────\033[0m"
        echo -e "  ${LR}[0]${NC}  ◀  Kembali ke menu utama"
        echo -e "  \033[38;5;135m──────────────────────────────────────────────────\033[0m"
        echo ""
        echo -ne "  ${A1}›${NC} Pilih tema [0-15]: "; read -r ch
        case $ch in
            [1-9]|1[0-5])
                echo "$ch" > "$THEMEF"; load_theme
                ok "Tema ${AT}${THEME_NAME}${NC} aktif! ✨"; sleep 0.8 ;;
            0) break ;;
            *) warn "Pilihan tidak valid! Masukkan angka 1-15"; sleep 0.5 ;;
        esac
    done
}

# ════════════════════════════════════════════════════════════
#  LOGO OGH-ZIV  — Premium Panel Style
# ════════════════════════════════════════════════════════════
draw_logo() {
    local cur_theme; cur_theme=$(cat "$THEMEF" 2>/dev/null || echo 1)
    local L1 L2 L3 L4 L5
    if [[ "$cur_theme" == "7" ]]; then
        L1='\033[38;5;196m'; L2='\033[38;5;214m'; L3='\033[38;5;226m'
        L4='\033[38;5;82m';  L5='\033[38;5;51m'
    else
        L1="$AL"; L2="$AL"; L3="$A3"; L4="$AL"; L5="$A3"
    fi

    # Logo tanpa bingkai
    echo ""
    echo -e "  ${A1}${_DASH}${NC}"
    echo -e "  ${L1}${BLD}  ██████╗  ██████╗ ██╗  ██╗    ███████╗██╗██╗   ██╗${NC}"
    echo -e "  ${L2}${BLD} ██╔═══██╗██╔════╝ ██║  ██║    ╚══███╔╝██║██║   ██║${NC}"
    echo -e "  ${L3}${BLD} ██║   ██║██║  ███╗███████║      ███╔╝ ██║██║   ██║${NC}"
    echo -e "  ${L4}${BLD} ██║   ██║██║   ██║██╔══██║     ███╔╝  ██║╚██╗ ██╔╝${NC}"
    echo -e "  ${L5}${BLD} ╚██████╔╝╚██████╔╝██║  ██║    ███████╗██║ ╚████╔╝ ${NC}"
    echo -e "  ${DIM}      ╚═════╝  ╚═════╝ ╚═╝  ╚═╝    ╚══════╝╚═╝  ╚═══╝  ${NC}"
    echo -e "  ${A1}${_DASH}${NC}"
    echo -e "  ${A4}         * SECURE VPN MANAGEMENT SYSTEM *         ${NC}"
    echo -e "  ${DIM}+----------------- ${A2}[ PREMIUM ]${DIM} -----------------+${NC}"
    echo -e "  ${A1}${_DASH}${NC}"
}

# ════════════════════════════════════════════════════════════
#  INFO VPS  — HTML Panel Style (2-column + stats bar)
# ════════════════════════════════════════════════════════════
draw_vps() {
    local ip;     ip=$(get_ip)
    local port;   port=$(get_port)
    local domain; domain=$(get_domain)
    local ram_u;  ram_u=$(free -m | awk '/^Mem/{print $3}')
    local ram_t;  ram_t=$(free -m | awk '/^Mem/{print $2}')
    local cpu;    cpu=$(top -bn1 2>/dev/null | grep "Cpu(s)" | awk '{printf "%.1f",$2}' || echo "0.0")
    local du;     du=$(df -h / | awk 'NR==2{print $3}')
    local dt;     dt=$(df -h / | awk 'NR==2{print $2}')
    local du_pct; du_pct=$(df / | awk 'NR==2{print $5}' | tr -d '%')
    local os;     os=$(. /etc/os-release 2>/dev/null && echo "$PRETTY_NAME" || echo "Linux")
    local hn;     hn=$(hostname)
    local total;  total=$(total_user)
    local expc;   expc=$(exp_count)
    local now_time; now_time=$(date "+%H:%M")
    local now_date; now_date=$(date "+%d/%m/%Y")

    # RAM percent
    local ram_pct=0
    [[ $ram_t -gt 0 ]] && ram_pct=$(( ram_u * 100 / ram_t ))

    local svc_ic svc_txt svc_col
    if is_up; then svc_col="${LG}"; svc_ic="●"; svc_txt="RUNNING"
    else           svc_col="${LR}"; svc_ic="●"; svc_txt="STOPPED"; fi

    local bot_txt="Belum setup"
    local bot_col="${LR}"
    if [[ -f "$BOTF" ]]; then
        source "$BOTF" 2>/dev/null
        if [[ -n "$BOT_TOKEN" ]]; then
            bot_txt="@${BOT_NAME:-?}"
            bot_col="${LG}"
        fi
    fi

    local brand="OGH-ZIV"
    [[ -f "$STRF" ]] && { source "$STRF" 2>/dev/null; brand="${BRAND:-OGH-ZIV}"; }

    local tema_display
    if [[ "$THEME_NAME" == "RAINBOW" ]]; then
        tema_display="\033[38;5;196mR\033[38;5;208mA\033[38;5;226mI\033[38;5;82mN\033[38;5;51mB\033[38;5;171mO\033[38;5;213mW\033[0m"
    else
        tema_display="${AL}${THEME_NAME}${NC}"
    fi

    # ── Header bar ──────────────────────────────────────────────────
    echo ""
    echo -e "  ${A1}${_DASH}${NC}"
    echo -e "  ${A4}◈${NC} ${BLD}${A4}INFO VPS${NC}  ${DIM}${now_time}  │  ${now_date}${NC}"
    echo -e "  ${A1}${_DASH}${NC}"

    # ── 2-column grid ──────────────────────────────────────────────────
    local os_short; os_short=$(echo "$os" | cut -c1-12)
    local domain_short; domain_short=$(echo "$domain" | cut -c1-14)

    # Row 1: HOST | OS
    _btn "  ${DIM}HOST    ${NC}${A1}│${NC} ${A3}$(printf '%-16s' "$hn")${NC}  ${DIM}OS      ${NC}${A1}│${NC} ${W}${os_short}${NC}"

    echo -e "  ${A1}${_DASH}${NC}"

    # Row 2: IP | DOMAIN
    _btn "  ${DIM}IP ADDR ${NC}${A1}│${NC} ${A3}$(printf '%-16s' "$ip")${NC}  ${DIM}DOMAIN  ${NC}${A1}│${NC} ${W}${domain_short}${NC}"

    echo -e "  ${A1}${_DASH}${NC}"

    # Row 3: PORT | BRAND
    _btn "  ${DIM}PORT    ${NC}${A1}│${NC} ${Y}$(printf '%-16s' "$port")${NC}  ${DIM}BRAND   ${NC}${A1}│${NC} ${A4}${brand}${NC}"

    echo -e "  ${A1}${_DASH}${NC}"

    # ── Stats bar: CPU | RAM ──────────────────────────────────────────────────
    # Build mini bar (12 chars wide)
    _mini_bar() {
        local pct=${1:-0}; local color="$2"
        local filled=$(( pct * 12 / 100 ))
        [[ $filled -gt 12 ]] && filled=12
        local empty=$(( 12 - filled ))
        printf "${color}"
        printf '█%.0s' $(seq 1 $filled 2>/dev/null) 2>/dev/null || printf '%0.s█' {1..1}
        [[ $filled -gt 0 ]] && printf '█%.0s' $(seq 2 $filled) 2>/dev/null
        printf "${DIM}"
        [[ $empty -gt 0 ]] && printf '░%.0s' $(seq 1 $empty) 2>/dev/null
        printf "${NC}"
    }

    local cpu_bar; cpu_bar=$(
        pct=${cpu%.*}; [[ -z "$pct" || "$pct" == "?" ]] && pct=0
        filled=$(( pct * 10 / 100 )); [[ $filled -gt 10 ]] && filled=10; empty=$(( 10 - filled ))
        bar=""; for ((i=0;i<filled;i++)); do bar+="█"; done
        for ((i=0;i<empty;i++)); do bar+="░"; done
        echo "$bar"
    )
    local ram_bar; ram_bar=$(
        pct=$ram_pct; filled=$(( pct * 10 / 100 )); [[ $filled -gt 10 ]] && filled=10; empty=$(( 10 - filled ))
        bar=""; for ((i=0;i<filled;i++)); do bar+="█"; done
        for ((i=0;i<empty;i++)); do bar+="░"; done
        echo "$bar"
    )
    local disk_bar; disk_bar=$(
        pct=${du_pct:-3}; filled=$(( pct * 10 / 100 )); [[ $filled -gt 10 ]] && filled=10; empty=$(( 10 - filled ))
        bar=""; for ((i=0;i<filled;i++)); do bar+="█"; done
        for ((i=0;i<empty;i++)); do bar+="░"; done
        echo "$bar"
    )

    # Row: CPU | RAM (tanpa DISK) — pakai _btn agar border selalu lurus
    _btn "  ${DIM}CPU${NC} ${LG}${cpu}%${NC}  ${LG}${cpu_bar}${NC}  ${A1}│${NC}  ${DIM}RAM${NC} ${A3}${ram_u}/${ram_t}MB${NC}  ${A3}${ram_bar}${NC}"

    echo -e "  ${A1}${_DASH}${NC}"

    # Row: DISK (baris tersendiri di bawah CPU/RAM)
    _btn "  ${DIM}DISK${NC} ${Y}${du}/${dt}${NC}  ${Y}${disk_bar}${NC}"

    echo -e "  ${A1}${_DASH}${NC}"

    # ── Status row ──────────────────────────────────────────────────
    _btn "  ${svc_col}${svc_ic} ${svc_txt}${NC}  ${A1}│${NC}  ${DIM}AKUN${NC} ${A3}${total}${NC}  ${A1}│${NC}  ${DIM}EXP${NC} ${LR}${expc}${NC}  ${A1}│${NC}  ${DIM}BOT${NC} ${bot_col}${bot_txt}${NC}"

    echo -e "  ${A1}${_DASH}${NC}"

    # Row: TEMA
    _btn "  ${DIM}TEMA${NC}  ${tema_display}"

    echo -e "  ${A1}${_DASH}${NC}"

    # Row: STATUS IZIN
    local _exp_col="${LG}"
    local _exp_disp="${IZIN_EXP:-unlimited}"
    [[ ! "$_exp_disp" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] && { _exp_disp="Unlimited"; _exp_col="${A3}"; }
    _btn "  ${LG}✔ IZIN${NC}  ${W}${IZIN_LABEL:--}${NC}  ${A1}│${NC}  ${DIM}EXP${NC} ${_exp_col}${_exp_disp}${NC}  ${A1}│${NC}  ${DIM}IP${NC} ${A3}${IZIN_IP:-?}${NC}"

    echo -e "  ${A1}${_DASH}${NC}"
    echo ""
}

show_header() {
    clear; load_theme; draw_logo; draw_vps
}

# ════════════════════════════════════════════════════════════
#  BINGKAI AKUN
# ════════════════════════════════════════════════════════════
show_akun_box() {
    local u="$1" p="$2" domain="$3" port="$4" ql="$5" exp="$6" note="$7" ip_pub="$8" maxl="${9:-2}"
    local exp_ts; exp_ts=$(date -d "${exp} 23:59:59" +%s 2>/dev/null || echo 0)
    local now_ts; now_ts=$(date +%s)
    local sisa_detik=$(( exp_ts - now_ts ))
    local sisa_str
    if [[ $sisa_detik -le 0 ]]; then
        sisa_str="${LR}Expired${NC}"
    else
        local sisa_hari=$(( sisa_detik / 86400 ))
        local sisa_jam=$(( (sisa_detik % 86400) / 3600 ))
        local sisa_menit=$(( (sisa_detik % 3600) / 60 ))
        if [[ $sisa_hari -gt 0 ]]; then
            sisa_str="${LG}${sisa_hari} hari ${sisa_jam} jam lagi${NC}"
        elif [[ $sisa_jam -gt 0 ]]; then
            sisa_str="${Y}${sisa_jam} jam ${sisa_menit} menit lagi${NC}"
        else
            sisa_str="${LR}${sisa_menit} menit lagi${NC}"
        fi
    fi
    local brand="OGH-ZIV"
    [[ -f "$STRF" ]] && { source "$STRF" 2>/dev/null; brand="${BRAND:-OGH-ZIV}"; }

    echo ""
    echo -e "  ${LG}✅ Akun Baru — ${brand}${NC}"
    echo -e "  ${A1}┌──────────────────────────────────────────────────${NC}"
    printf  "  ${A1}│${NC} 👤 ${DIM}Username${NC} : ${BLD}${W}%s${NC}\n" "$u"
    printf  "  ${A1}│${NC} 🔑 ${DIM}Password${NC} : ${BLD}${A3}%s${NC}\n" "$p"
    echo -e "  ${A1}├──────────────────────────────────────────────────${NC}"
    printf  "  ${A1}│${NC} 🖥  ${DIM}IP Publik${NC} : ${LG}%s${NC}\n" "${ip_pub:-$(get_ip)}"
    printf  "  ${A1}│${NC} 🌐 ${DIM}Host    ${NC} : ${W}%s${NC}\n" "$domain"
    printf  "  ${A1}│${NC} 🔌 ${DIM}Port    ${NC} : ${Y}%s${NC}\n" "$port"
    printf  "  ${A1}│${NC} 📡 ${DIM}Obfs    ${NC} : ${W}%s${NC}\n" "zivpn"
    echo -e "  ${A1}├──────────────────────────────────────────────────${NC}"
    printf  "  ${A1}│${NC} 📦 ${DIM}Kuota   ${NC} : ${LG}%s${NC}\n" "$ql"
    printf  "  ${A1}│${NC} 🔒 ${DIM}MaxLogin${NC} : ${Y}%s${NC}\n" "${maxl} device"
    printf  "  ${A1}│${NC} 📅 ${DIM}Expired ${NC} : ${Y}%s${NC}\n" "$exp"
    printf  "  ${A1}│${NC} ⏳ ${DIM}Sisa    ${NC} : %b\n" "$sisa_str"
    [[ "$note" != "-" ]] && \
    printf  "  ${A1}│${NC} 📝 ${DIM}Pembeli ${NC} : ${W}%s${NC}\n" "$note"
    echo -e "  ${A1}└──────────────────────────────────────────────────${NC}"
    echo -e "  ${DIM}📱 Download ZiVPN → Play Store / App Store${NC}"
    echo -e "  ${DIM}⚠  Jangan share akun ini ke orang lain!${NC}"
    echo ""
}

# ════════════════════════════════════════════════════════════
#  HELPERS
# ════════════════════════════════════════════════════════════
_reload_pw() {
    [[ ! -f "$UDB" || ! -f "$CFG" ]] && return
    local pws=()
    while IFS='|' read -r _ pw _ _ _; do pws+=("\"$pw\""); done < "$UDB"
    local pwl; pwl=$(IFS=','; echo "${pws[*]}")
    python3 - <<PYEOF 2>/dev/null
import json
with open('$CFG') as f: c=json.load(f)
c['auth']['config']=[${pwl}]
with open('$CFG','w') as f: json.dump(c,f,indent=2)
PYEOF
    systemctl restart zivpn &>/dev/null
}

_tg_send() {
    [[ ! -f "$BOTF" ]] && return
    source "$BOTF" 2>/dev/null
    local msg="$1"
    [[ -n "$BOT_TOKEN" && -n "$CHAT_ID" ]] && \
        curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
            -d "chat_id=${CHAT_ID}" -d "text=${msg}" -d "parse_mode=HTML" &>/dev/null
}

_tg_raw() {
    local tok="$1" cid="$2" msg="$3"
    curl -s -X POST "https://api.telegram.org/bot${tok}/sendMessage" \
        -d "chat_id=${cid}" -d "text=${msg}" -d "parse_mode=HTML" &>/dev/null
}

# ════════════════════════════════════════════════════════════
#  HELPER PANEL BUTTONS
# ════════════════════════════════════════════════════════════
# Lebar baris output (tanpa bingkai)
_DASH="──────────────────────────────────────────────────"

_top()  { echo -e "  ${A1}${_DASH}${NC}"; }
_bot()  { echo -e "  ${A1}${_DASH}${NC}"; }
_sep()  { echo -e "  ${A1}${_DASH}${NC}"; }
_sep0() { echo -e "  ${A1}${_DASH}${NC}"; }

# Hitung lebar tampilan string (strip ANSI, hitung unicode display width)
_displen() {
    local raw="$1"
    local clean; clean=$(printf '%b' "$raw" 2>/dev/null | \
        sed 's/\x1b\[[0-9;]*[mJKHfABCDsuhlp]//g; s/\x1b[()][AB012]//g; s/\x1b//g' 2>/dev/null)
    # Hitung via python3 (akurat untuk emoji & CJK)
    python3 -c "
import unicodedata, sys
s = sys.argv[1]
w = sum(2 if unicodedata.east_asian_width(c) in ('W','F') else 1 for c in s)
print(w)
" "$clean" 2>/dev/null || echo "${#clean}"
}

# _btn: cetak baris tanpa bingkai (garis patah-patah)
_btn() {
    local raw="$1"
    printf "  %b\n" "$raw"
}

# ════════════════════════════════════════════════════════════
#  INSTALL
# ════════════════════════════════════════════════════════════
do_install() {
    show_header
    _top; _btn "  ${IT}${AL}🚀  INSTALL ZIVPN${NC}"; _bot; echo ""

    # ── Hapus file lama otomatis setiap kali install dijalankan ──────
    inf "Membersihkan file lama (jika ada)..."
    systemctl stop    zivpn.service 2>/dev/null
    systemctl disable zivpn.service 2>/dev/null
    rm -f "$BIN"              # binary lama
    rm -f "$SVC"              # service lama
    rm -f "$DIR/zivpn.key"    # SSL key lama
    rm -f "$DIR/zivpn.crt"    # SSL cert lama
    rm -f "$DIR/config.json"  # config lama
    rm -f "$DIR/zivpn.log"    # log lama
    # ⚠ Data akun, domain, theme, bot, store TIDAK dihapus
    systemctl daemon-reload 2>/dev/null
    ok "File lama dibersihkan — data akun & konfigurasi dipertahankan"

    local sip; sip=$(get_ip)
    echo -ne "  ${A3}Domain / IP${NC}            : "; read -r inp_domain
    [[ -z "$inp_domain" ]] && inp_domain="$sip"
    echo -ne "  ${A3}Port${NC} [5667]             : "; read -r inp_port
    [[ -z "$inp_port" ]] && inp_port=5667
    echo -ne "  ${A3}Nama Brand / Toko${NC}       : "; read -r inp_brand
    [[ -z "$inp_brand" ]] && inp_brand="OGH-ZIV"
    echo -ne "  ${A3}Username Telegram Admin${NC}  : "; read -r inp_tg
    [[ -z "$inp_tg" ]] && inp_tg="-"

    echo ""
    echo -e "  ${A1}──────────────────────────────────────────────────${NC}"
    inf "Memulai instalasi ${AL}OGH-ZIV Premium${NC}..."
    echo -e "  ${A1}──────────────────────────────────────────────────${NC}"; echo ""

    # ── Dependensi ──────────────────────────────────────────────────
    inf "Menginstall dependensi..."
    apt-get update -qq &>/dev/null
    apt-get install -y -qq curl wget openssl python3 iptables \
        iptables-persistent netfilter-persistent &>/dev/null
    ok "Dependensi terpasang"

    # ── Direktori & file konfigurasi awal ──────────────────────────────────────────────────
    mkdir -p "$DIR"
    touch "$UDB" "$LOG"
    echo "$inp_domain" > "$DOMF"
    echo "rainbow"     > "$THEMEF"
    printf "BRAND=%s\nADMIN_TG=%s\n" "$inp_brand" "$inp_tg" > "$STRF"
    ok "Direktori & konfigurasi dibuat"

    # ── Download binary ZiVPN ──────────────────────────────────────────────────
    echo -e "\n  ${A1}──────────────────────────────────────────────────${NC}"
    inf "Downloading UDP Service..."
    wget "$BINARY_URL" -O "$BIN"
    if [[ ! -s "$BIN" ]]; then
        err "Gagal download binary ZiVPN!"
        echo -e "  ${Y}Coba jalankan manual:${NC}"
        echo -e "  ${W}wget $BINARY_URL -O $BIN${NC}"
        rm -f "$BIN"; pause; return 1
    fi
    chmod +x "$BIN"
    ok "Binary ZiVPN siap ($(du -sh "$BIN" 2>/dev/null | cut -f1))"

    # ── Download config.json resmi dari GitHub ───────────────────────
    inf "Mengunduh config.json..."
    wget "$CONFIG_URL" -O "$CFG"
    if [[ ! -s "$CFG" ]]; then
        warn "config.json tidak bisa diunduh, membuat manual..."
        cat > "$CFG" <<CFEOF
{
  "listen": ":${inp_port}",
  "cert": "/etc/zivpn/zivpn.crt",
  "key": "/etc/zivpn/zivpn.key",
  "obfs": "zivpn",
  "auth": {
    "mode": "passwords",
    "config": []
  }
}
CFEOF
    else
        # Update port di config.json yang didownload
        python3 - <<PYEOF 2>/dev/null
import json
try:
    with open('$CFG') as f: c = json.load(f)
    c['listen'] = ':${inp_port}'
    with open('$CFG','w') as f: json.dump(c, f, indent=2)
except: pass
PYEOF
    fi
    ok "config.json siap"

    # ── Generate SSL Certificate (RSA 4096, 1 tahun) ─────────────────
    echo -e "\n  ${A1}──────────────────────────────────────────────────${NC}"
    inf "Generating cert files..."
    openssl req -new -newkey rsa:4096 -days 365 -nodes -x509 \
        -subj "/C=US/ST=California/L=Los Angeles/O=Example Corp/OU=IT Department/CN=zivpn" \
        -keyout "$DIR/zivpn.key" \
        -out    "$DIR/zivpn.crt" &>/dev/null
    ok "SSL Certificate RSA-4096 (1 tahun) dibuat"

    # ── Optimasi kernel buffer UDP ──────────────────────────────────────────────────
    sysctl -w net.core.rmem_max=16777216 &>/dev/null
    sysctl -w net.core.wmem_max=16777216 &>/dev/null
    grep -q 'rmem_max' /etc/sysctl.conf 2>/dev/null || \
        printf "net.core.rmem_max=16777216\nnet.core.wmem_max=16777216\n" >> /etc/sysctl.conf
    ok "Buffer UDP dioptimasi (rmem/wmem 16MB)"

    # ── Optimasi Kernel Tambahan untuk Speed & Stabilitas UDP ──────────
    inf "Mengoptimasi kernel untuk performa & stabilitas UDP..."

    # Aktifkan BBR congestion control
    modprobe tcp_bbr 2>/dev/null
    grep -q 'tcp_bbr' /etc/modules-load.d/modules.conf 2>/dev/null || \
        echo "tcp_bbr" >> /etc/modules-load.d/modules.conf 2>/dev/null

    sysctl -w net.core.default_qdisc=fq              &>/dev/null
    sysctl -w net.ipv4.tcp_congestion_control=bbr     &>/dev/null
    sysctl -w net.ipv4.udp_rmem_min=8192              &>/dev/null
    sysctl -w net.ipv4.udp_wmem_min=8192              &>/dev/null
    sysctl -w net.core.netdev_max_backlog=16384        &>/dev/null
    sysctl -w net.ipv4.ip_forward=1                   &>/dev/null

    # Simpan permanen ke sysctl.conf (hindari duplikat)
    for _kv in \
        "net.core.default_qdisc=fq" \
        "net.ipv4.tcp_congestion_control=bbr" \
        "net.ipv4.udp_rmem_min=8192" \
        "net.ipv4.udp_wmem_min=8192" \
        "net.core.netdev_max_backlog=16384" \
        "net.ipv4.ip_forward=1"
    do
        _key="${_kv%%=*}"
        grep -q "$_key" /etc/sysctl.conf 2>/dev/null || echo "$_kv" >> /etc/sysctl.conf
    done

    sysctl -p &>/dev/null
    ok "BBR aktif — Fair Queue, UDP buffer min, backlog & IP forward dioptimasi"

    # ── Systemd service ──────────────────────────────────────────────────
    echo -e "\n  ${A1}──────────────────────────────────────────────────${NC}"
    inf "Membuat systemd service..."
    cat > "$SVC" <<SVEOF
[Unit]
Description=zivpn VPN Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$DIR
ExecStartPre=/bin/sh -c 'fuser -k ${inp_port}/udp 2>/dev/null; true'
ExecStart=$BIN server -c $CFG
Restart=always
RestartSec=3
Environment=ZIVPN_LOG_LEVEL=info
CapabilityBoundingSet=CAP_NET_ADMIN CAP_NET_BIND_SERVICE CAP_NET_RAW
AmbientCapabilities=CAP_NET_ADMIN CAP_NET_BIND_SERVICE CAP_NET_RAW
NoNewPrivileges=true
LimitNOFILE=1048576
StandardOutput=append:$LOG
StandardError=append:$LOG

[Install]
WantedBy=multi-user.target
SVEOF
    ok "Systemd service dibuat"

    # ── IPTables: UDP port forwarding 6000-19999 → port VPN ──────────
    echo -e "\n  ${A1}──────────────────────────────────────────────────${NC}"
    inf "Mengatur iptables & UDP port forwarding..."
    local IFACE
    IFACE=$(ip -4 route ls | grep default | grep -Po '(?<=dev )(\S+)' | head -1)

    # Bersihkan rules lama
    while iptables -t nat -D PREROUTING \
        -i "$IFACE" -p udp --dport 6000:19999 \
        -j DNAT --to-destination :${inp_port} 2>/dev/null; do :; done

    # Tambah rules baru
    iptables -t nat -A PREROUTING \
        -i "$IFACE" -p udp --dport 6000:19999 \
        -j DNAT --to-destination :${inp_port}
    iptables -A FORWARD -p udp -d 127.0.0.1 --dport "${inp_port}" -j ACCEPT
    iptables -t nat -A POSTROUTING -s 127.0.0.1/32 -o "$IFACE" -j MASQUERADE

    # Simpan permanen
    netfilter-persistent save &>/dev/null
    ok "IPTables: UDP 6000-19999 → ${inp_port} via $IFACE"

    # ── Firewall UFW ──────────────────────────────────────────────────
    if command -v ufw &>/dev/null; then
        ufw allow 6000:19999/udp &>/dev/null
        ufw allow "${inp_port}/udp" &>/dev/null
        ok "UFW: port 6000-19999/udp & ${inp_port}/udp dibuka"
    fi
    iptables -I INPUT -p udp --dport "${inp_port}" -j ACCEPT 2>/dev/null

    # ── Aktifkan & start service ──────────────────────────────────────────────────
    echo -e "\n  ${A1}──────────────────────────────────────────────────${NC}"
    inf "Mengaktifkan service ZiVPN..."
    systemctl daemon-reload
    systemctl enable zivpn.service &>/dev/null
    systemctl start  zivpn.service
    sleep 1
    if systemctl is-active --quiet zivpn; then
        ok "Service ZiVPN aktif & berjalan"
    else
        warn "Service gagal start — cek: journalctl -u zivpn -n 20"
    fi

    # ── Setup menu command ──────────────────────────────────────────────────
    setup_menu_cmd &>/dev/null

    # ── Ringkasan instalasi ──────────────────────────────────────────────────
    echo ""
    echo -e "  ${A1}${_DASH}${NC}"
    echo -e "  ${LG}${BLD}  ✦ OGH-ZIV PREMIUM BERHASIL DIINSTALL!${NC}"
    echo -e "  ${A1}${_DASH}${NC}"
    printf  "  ${DIM} Domain     :${NC}  ${W}%s${NC}\n" "$inp_domain"
    printf  "  ${DIM} Port       :${NC}  ${Y}%s${NC}\n" "$inp_port"
    printf  "  ${DIM} Brand      :${NC}  ${AL}%s${NC}\n" "$inp_brand"
    printf  "  ${DIM} Forwarding :${NC}  ${W}%s${NC}\n" "UDP 6000-19999 → ${inp_port}"
    printf  "  ${DIM} Interface  :${NC}  ${W}%s${NC}\n" "$IFACE"
    echo -e "  ${A1}${_DASH}${NC}"
    echo ""
    echo -e "  ${DIM}Ketik ${A1}menu${NC}${DIM} untuk membuka panel kapan saja.${NC}"
    echo ""
    pause
}

# ════════════════════════════════════════════════════════════
#  USER FUNCTIONS
# ════════════════════════════════════════════════════════════
u_add() {
    show_header
    _top; _btn "  ${IT}${AL}➕  TAMBAH AKUN BARU${NC}"; _bot; echo ""
    echo -ne "  ${A3}Username${NC}               : "; read -r un
    [[ -z "$un" ]] && { err "Username kosong!"; pause; return; }
    grep -q "^${un}|" "$UDB" 2>/dev/null && { err "Username sudah ada!"; pause; return; }
    echo -ne "  ${A3}Password${NC} [auto]         : "; read -r up
    [[ -z "$up" ]] && up=$(rand_pass)
    echo -ne "  ${A3}Masa aktif (hari)${NC} [30]  : "; read -r ud
    [[ -z "$ud" ]] && ud=30
    local ue; ue=$(date -d "+${ud} days" +"%Y-%m-%d")
    echo -ne "  ${A3}Kuota GB${NC} (0=unlimited)  : "; read -r uq
    [[ -z "$uq" ]] && uq=0
    echo -ne "  ${A3}Catatan / Nama Pembeli${NC}  : "; read -r note
    [[ -z "$note" ]] && note="-"
    echo -ne "  ${A3}Max Login Device${NC} [2]    : "; read -r uml
    [[ -z "$uml" || ! "$uml" =~ ^[0-9]+$ ]] && uml=2

    echo "${un}|${up}|${ue}|${uq}|${note}" >> "$UDB"
    set_maxlogin "$un" "$uml"
    _reload_pw

    local domain; domain=$(get_domain)
    local port;   port=$(get_port)
    local ip_pub; ip_pub=$(get_ip)
    local ql;     [[ "$uq" == "0" ]] && ql="Unlimited" || ql="${uq} GB"

    [[ -f "$STRF" ]] && source "$STRF" 2>/dev/null
    _tg_send "✅ <b>Akun Baru — ${BRAND:-OGH-ZIV}</b>
┌──────────────────────────────────────────────────
│ 👤 <b>Username</b> : <code>$un</code>
│ 🔑 <b>Password</b> : <code>$up</code>
├──────────────────────────────────────────────────
│ 🖥 <b>IP Publik</b> : <code>$ip_pub</code>
│ 🌐 <b>Host</b>     : <code>$domain</code>
│ 🔌 <b>Port</b>     : <code>$port</code>
│ 📡 <b>Obfs</b>     : <code>zivpn</code>
├──────────────────────────────────────────────────
│ 📦 <b>Kuota</b>    : $ql
│ 🔒 <b>MaxLogin</b> : ${uml} device
│ 📅 <b>Expired</b>  : $ue
│ 📝 <b>Pembeli</b>  : $note
└──────────────────────────────────────────────────"

    show_akun_box "$un" "$up" "$domain" "$port" "$ql" "$ue" "$note" "$ip_pub" "$uml"
    pause
}

u_list() {
    show_header
    _top; _btn "  ${IT}${AL}📋  LIST SEMUA AKUN${NC}"; _bot; echo ""
    [[ ! -s "$UDB" ]] && { warn "Belum ada akun terdaftar."; pause; return; }
    local today; today=$(date +"%Y-%m-%d")
    local now_ts; now_ts=$(date +%s)
    local n=1
    echo -e "  ${A1}${_DASH}${NC}"
    printf  "  ${BLD} %-2s  %-16s  %-10s  %-10s  %-8s  %-16s${NC}\n" \
        "#" "Username" "Password" "Expired" "Kuota" "Sisa Waktu"
    echo -e "  ${A1}${_DASH}${NC}"
    while IFS='|' read -r u p e q _; do
        local sc sisa_str
        local exp_ts; exp_ts=$(date -d "${e} 23:59:59" +%s 2>/dev/null || echo 0)
        local sisa_detik=$(( exp_ts - now_ts ))
        if [[ $sisa_detik -le 0 ]]; then
            sc="$LR"; sisa_str="Expired"
        else
            sc="$LG"
            local sd=$(( sisa_detik / 86400 ))
            local sj=$(( (sisa_detik % 86400) / 3600 ))
            if [[ $sd -gt 0 ]]; then
                sisa_str="${sd}h ${sj}j lagi"
            else
                local sm=$(( (sisa_detik % 3600) / 60 ))
                sisa_str="${sj}j ${sm}m lagi"
            fi
        fi
        local ql; [[ "$q" == "0" ]] && ql="Unlim   " || ql="${q}GB     "
        printf "   ${DIM}%-2s${NC}  ${W}%-16s${NC}  ${A3}%-10s${NC}  ${Y}%-10s${NC}  %-8s  ${sc}%-16s${NC}\n" \
            "$n" "$u" "$p" "$e" "$ql" "$sisa_str"
        ((n++))
    done < "$UDB"
    echo -e "  ${A1}${_DASH}${NC}"
    echo ""
    echo -e "  ${DIM}  Total: $((n-1)) akun  │  Expired: $(exp_count) akun${NC}"
    pause
}

u_info() {
    show_header
    _top; _btn "  ${IT}${AL}🔍  INFO DETAIL AKUN${NC}"; _bot; echo ""
    echo -ne "  ${A3}Username${NC}: "; read -r un
    local ln; ln=$(grep "^${un}|" "$UDB" 2>/dev/null)
    [[ -z "$ln" ]] && { err "User tidak ditemukan!"; pause; return; }
    IFS='|' read -r u p e q note <<< "$ln"
    local domain; domain=$(get_domain)
    local port;   port=$(get_port)
    local ip_pub; ip_pub=$(get_ip)
    local ql;     [[ "$q" == "0" ]] && ql="Unlimited" || ql="${q} GB"
    local maxl;   maxl=$(get_maxlogin "$un"); [[ -z "$maxl" ]] && maxl=2
    show_akun_box "$u" "$p" "$domain" "$port" "$ql" "$e" "$note" "$ip_pub" "$maxl"
    pause
}

u_del() {
    show_header
    _top; _btn "  ${IT}${AL}🗑️   HAPUS AKUN${NC}"; _bot; echo ""
    [[ ! -s "$UDB" ]] && { warn "Tidak ada akun."; pause; return; }
    local n=1
    while IFS='|' read -r u _ e _ _; do
        printf "  ${DIM}%3s.${NC}  ${W}%-22s${NC}  ${DIM}exp: %s${NC}\n" "$n" "$u" "$e"; ((n++))
    done < "$UDB"
    echo ""
    echo -ne "  ${A3}Username yang dihapus${NC}: "; read -r du
    grep -q "^${du}|" "$UDB" 2>/dev/null || { err "User tidak ditemukan!"; pause; return; }
    sed -i "/^${du}|/d" "$UDB"
    del_maxlogin "$du"
    _reload_pw
    _tg_send "🗑 <b>Akun Dihapus</b> : <code>$du</code>"
    ok "Akun '${W}$du${NC}' berhasil dihapus."
    pause
}

u_renew() {
    show_header
    _top; _btn "  ${IT}${AL}🔁  PERPANJANG AKUN${NC}"; _bot; echo ""
    echo -ne "  ${A3}Username${NC}    : "; read -r ru
    grep -q "^${ru}|" "$UDB" 2>/dev/null || { err "User tidak ditemukan!"; pause; return; }
    echo -ne "  ${A3}Tambah hari${NC} : "; read -r rd; [[ -z "$rd" ]] && rd=30
    local ce; ce=$(grep "^${ru}|" "$UDB" | cut -d'|' -f3)
    local today; today=$(date +%Y-%m-%d)
    [[ "$ce" < "$today" ]] && ce="$today"
    local ne; ne=$(date -d "${ce} +${rd} days" +"%Y-%m-%d")
    sed -i "s/^\(${ru}|[^|]*|\)[^|]*/\1${ne}/" "$UDB"
    _tg_send "🔁 <b>Akun Diperpanjang</b>
👤 User     : <code>$ru</code>
📅 Expired  : <b>$ne</b>  (+${rd} hari)"
    echo ""
    echo -e "  ${A1}${_DASH}${NC}"
    echo -e "  ${LG}✔  Akun berhasil diperpanjang!${NC}"
    echo -e "  ${A1}${_DASH}${NC}"
    printf  "  ${DIM} Username :${NC}  ${W}%s${NC}\n" "$ru"
    printf  "  ${DIM} Expired  :${NC}  ${Y}%s${NC}\n" "$ne"
    printf  "  ${DIM} Tambahan :${NC}  ${LG}+%s${NC}\n" "${rd} hari"
    echo -e "  ${A1}${_DASH}${NC}"
    pause
}

u_chpass() {
    show_header
    _top; _btn "  ${IT}${AL}🔑  GANTI PASSWORD${NC}"; _bot; echo ""
    echo -ne "  ${A3}Username${NC}           : "; read -r pu
    grep -q "^${pu}|" "$UDB" 2>/dev/null || { err "User tidak ditemukan!"; pause; return; }
    echo -ne "  ${A3}Password baru${NC} [auto]: "; read -r pp
    [[ -z "$pp" ]] && pp=$(rand_pass)
    sed -i "s/^${pu}|[^|]*/${pu}|${pp}/" "$UDB"
    _reload_pw
    echo ""
    echo -e "  ${A1}${_DASH}${NC}"
    echo -e "  ${LG}✔  Password berhasil diubah!${NC}"
    echo -e "  ${A1}${_DASH}${NC}"
    printf  "  ${DIM} Username :${NC}  ${W}%s${NC}\n" "$pu"
    printf  "  ${DIM} Password :${NC}  ${A3}%s${NC}\n" "$pp"
    echo -e "  ${A1}${_DASH}${NC}"
    pause
}

u_trial() {
    show_header
    _top; _btn "  ${IT}${AL}🎁  BUAT AKUN TRIAL${NC}"; _bot; echo ""
    local tu="trial$(tr -dc 'a-z0-9' </dev/urandom | head -c 6)"
    local tp; tp=$(rand_pass)
    local te; te=$(date -d "+1 day" +"%Y-%m-%d")
    local ip_pub; ip_pub=$(get_ip)
    echo "${tu}|${tp}|${te}|1|TRIAL" >> "$UDB"
    _reload_pw
    local domain; domain=$(get_domain); local port; port=$(get_port)
    _tg_send "🎁 <b>Akun Trial Dibuat</b>
👤 User  : <code>$tu</code>
🔑 Pass  : <code>$tp</code>
🖥 IP    : <code>$ip_pub</code>
📅 Exp   : $te  (1 hari / 1 GB)"
    show_akun_box "$tu" "$tp" "$domain" "$port" "1 GB" "$te" "TRIAL" "$ip_pub"
    pause
}

u_clean() {
    show_header
    _top; _btn "  ${IT}${AL}🧹  HAPUS AKUN EXPIRED${NC}"; _bot; echo ""
    local today; today=$(date +"%Y-%m-%d"); local cnt=0
    while IFS='|' read -r u _ e _ _; do
        if [[ "$e" < "$today" ]]; then
            sed -i "/^${u}|/d" "$UDB"
            del_maxlogin "$u"
            ok "Dihapus: ${W}$u${NC}  ${DIM}(exp: $e)${NC}"; ((cnt++))
        fi
    done < <(cat "$UDB" 2>/dev/null)
    echo ""
    [[ $cnt -gt 0 ]] && { _reload_pw; ok "Total ${W}$cnt${NC} akun expired dihapus."; } \
                     || inf "Tidak ada akun expired."
    pause
}

# ════════════════════════════════════════════════════════════
#  JUALAN
# ════════════════════════════════════════════════════════════
t_akun() {
    show_header
    _top; _btn "  ${IT}${AL}📨  TEMPLATE PESAN AKUN${NC}"; _bot; echo ""
    [[ -f "$STRF" ]] && source "$STRF" 2>/dev/null
    echo -ne "  ${A3}Username${NC}: "; read -r tu
    local ln; ln=$(grep "^${tu}|" "$UDB" 2>/dev/null)
    [[ -z "$ln" ]] && { err "User tidak ditemukan!"; pause; return; }
    IFS='|' read -r u p e q note <<< "$ln"
    local domain; domain=$(get_domain); local port; port=$(get_port)
    local ip_pub; ip_pub=$(get_ip)
    local ql; [[ "$q" == "0" ]] && ql="Unlimited" || ql="${q} GB"
    show_akun_box "$u" "$p" "$domain" "$port" "$ql" "$e" "$note" "$ip_pub"
    pause
}

set_store() {
    show_header
    _top; _btn "  ${IT}${AL}⚙️   PENGATURAN TOKO${NC}"; _bot; echo ""
    [[ -f "$STRF" ]] && source "$STRF" 2>/dev/null
    echo -ne "  ${A3}Nama Brand${NC} [${BRAND:-OGH-ZIV}]   : "; read -r ib
    echo -ne "  ${A3}Username TG Admin${NC} [${ADMIN_TG:--}]: "; read -r it
    printf "BRAND=%s\nADMIN_TG=%s\n" "${ib:-${BRAND:-OGH-ZIV}}" "${it:-${ADMIN_TG:--}}" > "$STRF"
    ok "Pengaturan toko disimpan!"
    pause
}

# ════════════════════════════════════════════════════════════
#  TELEGRAM BOT
# ════════════════════════════════════════════════════════════
tg_setup() {
    show_header
    _top; _btn "  ${IT}${AL}🤖  SETUP BOT TELEGRAM${NC}"; _bot; echo ""
    inf "Buka ${A3}@BotFather${NC} di Telegram → ketik /newbot → salin TOKEN"
    inf "Kirim /start ke bot → buka URL:"
    echo -e "  ${DIM}     api.telegram.org/bot<TOKEN>/getUpdates${NC}"
    echo ""

    # Load existing config
    [[ -f "$BOTF" ]] && source "$BOTF" 2>/dev/null

    # ── Bot Admin (Wajib) ──────────────────────────────────────────────────
    echo -e "  ${A4}────────── BOT ADMIN ────────────────────────────${NC}"
    echo -ne "  ${A3}Bot Token${NC}     [${BOT_TOKEN:--}]: "; read -r tok1
    [[ -z "$tok1" ]] && tok1="${BOT_TOKEN:-}"
    [[ -z "$tok1" ]] && { err "Token Bot kosong! Harus diisi."; pause; return; }
    echo -ne "  ${A3}Chat ID Admin${NC} [${CHAT_ID:--}]:  "; read -r cid1
    [[ -z "$cid1" ]] && cid1="${CHAT_ID:-}"
    [[ -z "$cid1" ]] && { err "Chat ID Admin kosong!"; pause; return; }

    echo ""
    inf "Memverifikasi bot..."

    # Verifikasi Bot
    local res1; res1=$(curl -s "https://api.telegram.org/bot${tok1}/getMe")
    if ! echo "$res1" | grep -q '"ok":true'; then
        err "Token Bot tidak valid atau tidak bisa terhubung!"; pause; return
    fi
    local bname1; bname1=$(echo "$res1" | python3 -c \
        "import sys,json;d=json.load(sys.stdin);print(d['result']['username'])" 2>/dev/null)

    # Simpan ke BOTF (hapus bot 2 & 3 jika ada)
    {
        printf "BOT_TOKEN=%s\nCHAT_ID=%s\nBOT_NAME=%s\n" "$tok1" "$cid1" "$bname1"
    } > "$BOTF"

    # Kirim notif
    _tg_raw "$tok1" "$cid1" "✅ <b>OGH-ZIV Premium</b> Bot Admin terhubung ke server VPS!"

    echo ""
    echo -e "  ${A1}${_DASH}${NC}"
    echo -e "  ${LG}✔  Bot Telegram berhasil dikonfigurasi!${NC}"
    echo -e "  ${A1}${_DASH}${NC}"
    printf  "  ${DIM} Bot      :${NC}  ${W}@%s${NC}\n" "$bname1"
    printf  "  ${DIM} Chat ID  :${NC}  ${Y}%s${NC}\n" "$cid1"
    echo -e "  ${A1}${_DASH}${NC}"
    pause
}

tg_status() {
    show_header
    _top; _btn "  ${IT}${AL}📡  STATUS BOT TELEGRAM${NC}"; _bot; echo ""
    if [[ ! -f "$BOTF" ]]; then
        warn "Bot belum dikonfigurasi."
        echo -ne "  Setup sekarang? [y/N]: "; read -r a
        [[ "$a" == [yY] ]] && tg_setup; return
    fi
    source "$BOTF" 2>/dev/null
    echo ""
    echo -e "  ${A1}${_DASH}${NC}"

    # Cek Bot
    local res1; res1=$(curl -s "https://api.telegram.org/bot${BOT_TOKEN}/getMe")
    if echo "$res1" | grep -q '"ok":true'; then
        local fn1; fn1=$(echo "$res1" | python3 -c \
            "import sys,json;d=json.load(sys.stdin);print(d['result']['first_name'])" 2>/dev/null)
        echo -e "  ${LG}🟢  Bot — Aktif & Terhubung${NC}"
        echo -e "  ${A1}${_DASH}${NC}"
        printf  "  ${DIM} Nama     :${NC}  ${W}%s${NC}\n" "$fn1"
        printf  "  ${DIM} Username :${NC}  ${W}@%s${NC}\n" "$BOT_NAME"
        printf  "  ${DIM} Chat ID  :${NC}  ${Y}%s${NC}\n" "$CHAT_ID"
        echo -e "  ${A1}${_DASH}${NC}"
    else
        echo -e "  ${LR}🔴  Bot — Tidak Terhubung!${NC}"
        echo -e "  ${A1}${_DASH}${NC}"
    fi

    echo ""
    echo -ne "  ${A3}Kirim pesan test ke bot?${NC} [y/N]: "; read -r ts
    [[ "$ts" == [yY] ]] && {
        _tg_send "🟢 <b>Test OGH-ZIV Premium</b> — Bot berjalan normal! ✅"
        ok "Pesan test dikirim!"
    }
    pause
}

tg_kirim_akun() {
    show_header
    _top; _btn "  ${IT}${AL}📤  KIRIM AKUN KE TELEGRAM${NC}"; _bot; echo ""
    [[ ! -f "$BOTF" ]] && { err "Bot belum dikonfigurasi!"; pause; return; }
    source "$BOTF" 2>/dev/null
    [[ -f "$STRF" ]] && source "$STRF" 2>/dev/null
    echo -ne "  ${A3}Username akun${NC}    : "; read -r su
    local ln; ln=$(grep "^${su}|" "$UDB" 2>/dev/null)
    [[ -z "$ln" ]] && { err "User tidak ditemukan!"; pause; return; }
    IFS='|' read -r u p e q note <<< "$ln"
    echo -ne "  ${A3}Chat ID tujuan${NC} [$CHAT_ID]: "; read -r did
    [[ -z "$did" ]] && did="$CHAT_ID"
    local domain; domain=$(get_domain); local port; port=$(get_port)
    local ip_pub; ip_pub=$(get_ip)
    local ql; [[ "$q" == "0" ]] && ql="Unlimited" || ql="${q} GB"
    local _exp_ts; _exp_ts=$(date -d "${e} 23:59:59" +%s 2>/dev/null || echo 0)
    local _now_ts; _now_ts=$(date +%s)
    local _sisa_detik=$(( _exp_ts - _now_ts ))
    local sisa_str
    if [[ $_sisa_detik -le 0 ]]; then
        sisa_str="Expired"
    else
        local _sd=$(( _sisa_detik / 86400 ))
        local _sj=$(( (_sisa_detik % 86400) / 3600 ))
        local _sm=$(( (_sisa_detik % 3600) / 60 ))
        if [[ $_sd -gt 0 ]]; then
            sisa_str="${_sd} hari ${_sj} jam lagi"
        elif [[ $_sj -gt 0 ]]; then
            sisa_str="${_sj} jam ${_sm} menit lagi"
        else
            sisa_str="${_sm} menit lagi"
        fi
    fi
    local msg="🔒 <b>${BRAND:-OGH-ZIV} — Akun VPN UDP Premium</b>

┌──────────────────────────────────────────────────
│ 👤 <b>Username</b>  : <code>$u</code>
│ 🔑 <b>Password</b>  : <code>$p</code>
├──────────────────────────────────────────────────
│ 🖥 <b>IP Publik</b>  : <code>$ip_pub</code>
│ 🌐 <b>Host</b>      : <code>$domain</code>
│ 🔌 <b>Port</b>      : <code>$port</code>
│ 📡 <b>Obfs</b>      : <code>zivpn</code>
├──────────────────────────────────────────────────
│ 📦 <b>Kuota</b>     : $ql
│ 📅 <b>Expired</b>   : $e
│ ⏳ <b>Sisa</b>      : $sisa_str
└──────────────────────────────────────────────────

📱 Download <b>ZiVPN</b> di Play Store / App Store
⚠️ Jangan share akun ini ke orang lain!"
    local r; r=$(curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
        -d "chat_id=${did}" -d "text=${msg}" -d "parse_mode=HTML")
    echo ""
    echo "$r" | grep -q '"ok":true' \
        && ok "Akun '${W}$u${NC}' berhasil dikirim ke Telegram!" \
        || err "Gagal kirim! Periksa Chat ID atau token."
    pause
}

tg_broadcast() {
    show_header
    _top; _btn "  ${IT}${AL}📢  BROADCAST PESAN${NC}"; _bot; echo ""
    [[ ! -f "$BOTF" ]] && { err "Bot belum dikonfigurasi!"; pause; return; }
    source "$BOTF" 2>/dev/null
    echo -e "  ${DIM}Ketik pesan. Ketik ${W}SELESAI${DIM} di baris baru untuk kirim.${NC}"; echo ""
    local msg="" line
    while IFS= read -r line; do
        [[ "$line" == "SELESAI" ]] && break
        msg+="$line
"
    done
    [[ -z "$msg" ]] && { err "Pesan kosong!"; pause; return; }
    curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
        -d "chat_id=${CHAT_ID}" -d "text=${msg}" &>/dev/null
    ok "Broadcast berhasil dikirim!"
    pause
}

tg_guide() {
    show_header
    _top; _btn "  ${IT}${AL}📖  PANDUAN BUAT BOT TELEGRAM${NC}"; _bot; echo ""
    echo -e "  ${A1}${_DASH}${NC}"
    echo -e "  ${Y}LANGKAH 1 — Buat Bot di BotFather${NC}"
    echo -e "  ${A1}${_DASH}${NC}"
    echo -e "  ${W}1.${NC} Buka Telegram → cari ${A3}@BotFather${NC}"
    echo -e "  ${W}2.${NC} Kirim perintah ${Y}/newbot${NC}"
    echo -e "  ${W}3.${NC} Masukkan nama bot → contoh: ${W}OGH ZIV VPN${NC}"
    echo -e "  ${W}4.${NC} Masukkan username (akhiran ${Y}bot${NC})"
    echo -e "  ${W}5.${NC} Salin ${Y}TOKEN${NC} yang diberikan BotFather"
    echo -e "  ${A1}${_DASH}${NC}"
    echo -e "  ${Y}LANGKAH 2 — Ambil Chat ID${NC}"
    echo -e "  ${A1}${_DASH}${NC}"
    echo -e "  ${W}1.${NC} Kirim ${Y}/start${NC} ke bot kamu di Telegram"
    echo -e "  ${W}2.${NC} Buka: ${DIM}api.telegram.org/bot<TOKEN>/getUpdates${NC}"
    echo -e '  ${W}3.${NC} Cari nilai ${Y}"id"${NC} di bagian ${Y}"from"${NC}'
    echo -e "  ${A1}${_DASH}${NC}"
    echo -e "  ${Y}LANGKAH 3 — Hubungkan ke OGH-ZIV${NC}"
    echo -e "  ${A1}${_DASH}${NC}"
    echo -e "  ${W}1.${NC} Menu Telegram → ${A3}[1] Setup / Konfigurasi Bot${NC}"
    echo -e "  ${W}2.${NC} Masukkan Token dan Chat ID"
    echo -e "  ${W}3.${NC} ${LG}✅ Selesai! Notifikasi otomatis aktif${NC}"
    echo -e "  ${A1}${_DASH}${NC}"
    echo -e "  ${A3}https://t.me/BotFather${NC}"
    echo -e "  ${A1}${_DASH}${NC}"
    pause
}

# ════════════════════════════════════════════════════════════
#  SERVICE
# ════════════════════════════════════════════════════════════
svc_status() {
    show_header
    _top; _btn "  ${IT}${AL}🖥️   STATUS SERVICE${NC}"; _bot; echo ""
    systemctl status zivpn --no-pager -l
    pause
}

# ════════════════════════════════════════════════════════════
#  CEK STATUS BBR  — Lengkap & Detail
# ════════════════════════════════════════════════════════════
svc_bbr() {
    show_header
    _top; _btn "  ${IT}${AL}🚀  STATUS BBR CONGESTION CONTROL${NC}"; _bot; echo ""

    # ── Cek BBR aktif atau tidak ──
    local cc; cc=$(sysctl -n net.ipv4.tcp_congestion_control 2>/dev/null || echo "unknown")
    local qdisc; qdisc=$(sysctl -n net.core.default_qdisc 2>/dev/null || echo "unknown")
    local bbr_mod; bbr_mod=$(lsmod 2>/dev/null | grep -c "^tcp_bbr" || echo 0)
    local kernel; kernel=$(uname -r 2>/dev/null || echo "unknown")
    local bbr_avail; bbr_avail=$(sysctl net.ipv4.tcp_available_congestion_control 2>/dev/null | grep -o 'bbr' || echo "")

    echo -e "  ${A1}${_DASH}${NC}"
    echo -e "  ${A4}◈  KERNEL & MODULE${NC}"
    echo -e "  ${A1}${_DASH}${NC}"
    printf  "  ${DIM}Kernel Version   :${NC}  ${W}%s${NC}\n" "$kernel"

    # Cek module tcp_bbr loaded
    if [[ "$bbr_mod" -gt 0 ]]; then
        printf  "  ${DIM}Module tcp_bbr   :${NC}  ${LG}✔  Loaded${NC}\n"
    else
        # BBR bisa built-in ke kernel tanpa module terpisah
        if [[ -n "$bbr_avail" ]]; then
            printf  "  ${DIM}Module tcp_bbr   :${NC}  ${A3}✔  Built-in Kernel${NC}\n"
        else
            printf  "  ${DIM}Module tcp_bbr   :${NC}  ${LR}✘  Tidak tersedia${NC}\n"
        fi
    fi

    # Cek BBR tersedia di daftar
    local all_cc; all_cc=$(sysctl -n net.ipv4.tcp_available_congestion_control 2>/dev/null || echo "-")
    printf  "  ${DIM}CC Tersedia      :${NC}  ${DIM}%s${NC}\n" "$all_cc"

    echo ""
    echo -e "  ${A1}${_DASH}${NC}"
    echo -e "  ${A4}◈  STATUS AKTIF${NC}"
    echo -e "  ${A1}${_DASH}${NC}"

    # Status BBR
    if [[ "$cc" == "bbr" ]]; then
        echo -e "  ${LG}  ██████╗ ██████╗ ██████╗${NC}"
        echo -e "  ${LG}  ██╔══██╗██╔══██╗██╔══██╗${NC}"
        echo -e "  ${LG}  ██████╔╝██████╔╝██████╔╝${NC}"
        echo -e "  ${LG}  ██╔══██╗██╔══██╗██╔══██╗${NC}"
        echo -e "  ${LG}  ██████╔╝██████╔╝██║  ██║${NC}"
        echo -e "  ${LG}  ╚═════╝ ╚═════╝ ╚═╝  ╚═╝  ✔ AKTIF${NC}"
        echo ""
        printf  "  ${DIM}TCP Congestion   :${NC}  ${LG}✔  BBR${NC}  ${DIM}(Google BBR v1)${NC}\n"
    else
        printf  "  ${DIM}TCP Congestion   :${NC}  ${LR}✘  %s${NC}  ${DIM}(Bukan BBR!)${NC}\n" "$cc"
    fi

    # Status Fair Queue
    if [[ "$qdisc" == "fq" || "$qdisc" == "fq_codel" ]]; then
        printf  "  ${DIM}Default Qdisc    :${NC}  ${LG}✔  %s${NC}  ${DIM}(Optimal untuk BBR)${NC}\n" "$qdisc"
    else
        printf  "  ${DIM}Default Qdisc    :${NC}  ${Y}⚠  %s${NC}  ${DIM}(Disarankan: fq)${NC}\n" "$qdisc"
    fi

    echo ""
    echo -e "  ${A1}${_DASH}${NC}"
    echo -e "  ${A4}◈  OPTIMASI KERNEL UDP${NC}"
    echo -e "  ${A1}${_DASH}${NC}"

    # Cek parameter kernel terkait
    _cek_sysctl() {
        local key="$1" label="$2" expected="$3"
        local val; val=$(sysctl -n "$key" 2>/dev/null || echo "N/A")
        if [[ -n "$expected" && "$val" == "$expected" ]]; then
            printf "  ${DIM}%-22s :${NC}  ${LG}✔  %s${NC}\n" "$label" "$val"
        elif [[ "$val" == "N/A" ]]; then
            printf "  ${DIM}%-22s :${NC}  ${LR}✘  Tidak tersedia${NC}\n" "$label"
        else
            printf "  ${DIM}%-22s :${NC}  ${A3}   %s${NC}\n" "$label" "$val"
        fi
    }
    _cek_sysctl "net.core.rmem_max"           "rmem_max"         "16777216"
    _cek_sysctl "net.core.wmem_max"           "wmem_max"         "16777216"
    _cek_sysctl "net.ipv4.udp_rmem_min"       "udp_rmem_min"     "8192"
    _cek_sysctl "net.ipv4.udp_wmem_min"       "udp_wmem_min"     "8192"
    _cek_sysctl "net.core.netdev_max_backlog" "netdev_max_backlog" "16384"
    _cek_sysctl "net.ipv4.ip_forward"         "ip_forward"       "1"

    echo ""
    echo -e "  ${A1}${_DASH}${NC}"

    # ── Kesimpulan ──
    if [[ "$cc" == "bbr" && ( "$qdisc" == "fq" || "$qdisc" == "fq_codel" ) ]]; then
        echo -e "  ${LG}✦  KESIMPULAN: BBR + Fair Queue AKTIF & OPTIMAL!${NC}"
        echo -e "  ${DIM}  Koneksi UDP ZiVPN berjalan dengan performa terbaik.${NC}"
    elif [[ "$cc" == "bbr" ]]; then
        echo -e "  ${Y}⚠  KESIMPULAN: BBR aktif tapi Qdisc belum optimal.${NC}"
        echo -e "  ${DIM}  Jalankan: sysctl -w net.core.default_qdisc=fq${NC}"
    else
        echo -e "  ${LR}✘  KESIMPULAN: BBR TIDAK AKTIF!${NC}"
        echo -e "  ${DIM}  Jalankan install ulang atau aktifkan manual:${NC}"
        echo -e "  ${W}  modprobe tcp_bbr${NC}"
        echo -e "  ${W}  sysctl -w net.ipv4.tcp_congestion_control=bbr${NC}"
        echo -e "  ${W}  sysctl -w net.core.default_qdisc=fq${NC}"
    fi

    echo -e "  ${A1}${_DASH}${NC}"
    echo ""

    # ── Opsi aktifkan BBR jika belum aktif ──
    if [[ "$cc" != "bbr" ]]; then
        echo -ne "  ${A3}Aktifkan BBR sekarang?${NC} [y/N]: "; read -r yn
        if [[ "$yn" == [yY] ]]; then
            echo ""
            inf "Mengaktifkan BBR..."
            modprobe tcp_bbr 2>/dev/null
            sysctl -w net.core.default_qdisc=fq &>/dev/null
            sysctl -w net.ipv4.tcp_congestion_control=bbr &>/dev/null
            # Simpan permanen
            grep -q 'tcp_bbr' /etc/modules-load.d/modules.conf 2>/dev/null || \
                echo "tcp_bbr" >> /etc/modules-load.d/modules.conf 2>/dev/null
            for _kv in "net.core.default_qdisc=fq" "net.ipv4.tcp_congestion_control=bbr"; do
                _k="${_kv%%=*}"
                grep -q "$_k" /etc/sysctl.conf 2>/dev/null || echo "$_kv" >> /etc/sysctl.conf
            done
            sysctl -p &>/dev/null
            local new_cc; new_cc=$(sysctl -n net.ipv4.tcp_congestion_control 2>/dev/null)
            if [[ "$new_cc" == "bbr" ]]; then
                ok "BBR berhasil diaktifkan! ✨"
            else
                err "Gagal mengaktifkan BBR. Kernel mungkin tidak mendukung."
            fi
        fi
    fi

    pause
}

svc_bandwidth() {
    show_header
    _top; _btn "  ${IT}${AL}📊  BANDWIDTH / KONEKSI AKTIF${NC}"; _bot; echo ""
    local port; port=$(get_port)
    inf "Koneksi aktif ke port ${Y}$port${NC}:"; echo ""
    ss -u -n -p 2>/dev/null | grep ":$port" || inf "Tidak ada koneksi UDP aktif saat ini."
    echo ""
    inf "Statistik network interface:"
    cat /proc/net/dev 2>/dev/null | awk 'NR>2{
        split($1,a,":");gsub(/[[:space:]]/,"",a[1]);
        if(a[1]!="lo") printf "  %-12s RX: %-12s TX: %s\n", a[1], $2, $10
    }' | head -5
    pause
}

svc_log() {
    show_header
    _top; _btn "  ${IT}${AL}📄  LOG ZIVPN${NC}"; _bot; echo ""
    [[ -f "$LOG" ]] && tail -60 "$LOG" || journalctl -u zivpn -n 60 --no-pager
    pause
}

svc_port() {
    show_header
    _top; _btn "  ${IT}${AL}🔧  GANTI PORT${NC}"; _bot; echo ""
    local cp; cp=$(get_port)
    echo -e "  Port saat ini : ${Y}$cp${NC}"
    echo -ne "  ${A3}Port baru${NC}     : "; read -r np
    [[ ! "$np" =~ ^[0-9]+$ || $np -lt 1 || $np -gt 65535 ]] && { err "Port tidak valid!"; pause; return; }
    sed -i "s/\"listen\": *\":${cp}\"/\"listen\": \":${np}\"/" "$CFG"
    command -v ufw &>/dev/null && { ufw delete allow "$cp/udp" &>/dev/null; ufw allow "$np/udp" &>/dev/null; }
    iptables -D INPUT -p udp --dport "$cp" -j ACCEPT 2>/dev/null
    iptables -I INPUT -p udp --dport "$np" -j ACCEPT 2>/dev/null
    systemctl restart zivpn
    ok "Port diubah: ${Y}$cp${NC} → ${LG}$np${NC}"
    pause
}

# ════════════════════════════════════════════════════════════
#  BACKUP & RESTORE — OGH-ZIV v2
# ════════════════════════════════════════════════════════════
BAKDIR="/root/oghziv-backups"

# ════════════════════════════════════════════════════════════
#  BACKUP & RESTORE via TELEGRAM — OGH-ZIV Premium
#  • Backup  : buat .tar.gz → kirim ke semua bot Telegram
#  • Restore : ambil file backup langsung dari Telegram
# ════════════════════════════════════════════════════════════

# Kumpulkan file yang benar-benar ada, simpan ke array global BAK_FILES
_bak_collect() {
    BAK_FILES=()
    local candidates=("$UDB" "$CFG" "$DOMF" "$BOTF" "$STRF" "$THEMEF" "$MLDB" "$SVC")
    for f in "${candidates[@]}"; do
        [[ -f "$f" ]] && BAK_FILES+=("$f")
    done
    [[ -f "$BIN" ]] && BAK_FILES+=("$BIN")
}

# Tampilkan daftar backup lokal, count ke BAK_CNT global
_bak_list() {
    mkdir -p "$BAKDIR"
    BAK_CNT=0
    local -a files=()
    while IFS= read -r -d '' f; do
        files+=("$f")
    done < <(find "$BAKDIR" -maxdepth 1 -name 'oghziv-backup-*.tar.gz' -print0 2>/dev/null | sort -z)
    BAK_CNT=${#files[@]}
    if [[ $BAK_CNT -eq 0 ]]; then
        echo ""
        warn "Belum ada file backup lokal di ${W}${BAKDIR}${NC}"
        return
    fi
    echo ""
    echo -e "  ${A1}${_DASH}${NC}"
    printf  "  ${DIM} %-3s  %-34s  %-6s  %-10s${NC}\n" "No" "Nama File" "Ukuran" "Tanggal"
    echo -e "  ${A1}${_DASH}${NC}"
    local i=0
    for f in "${files[@]}"; do
        ((i++))
        local fname; fname=$(basename "$f")
        local fsize; fsize=$(du -sh "$f" 2>/dev/null | cut -f1)
        local fdate; fdate=$(stat -c '%y' "$f" 2>/dev/null | cut -d' ' -f1)
        printf "   ${A2}%2d${NC}  ${W}%-34s${NC}  ${Y}%6s${NC}  ${DIM}%-10s${NC}\n" \
               "$i" "${fname:0:34}" "$fsize" "$fdate"
    done
    echo -e "  ${A1}${_DASH}${NC}"
    echo ""
}

# Ambil path file backup ke-N dari lokal
_bak_get_file() {
    local n="$1"
    local -a files=()
    while IFS= read -r -d '' f; do
        files+=("$f")
    done < <(find "$BAKDIR" -maxdepth 1 -name 'oghziv-backup-*.tar.gz' -print0 2>/dev/null | sort -z)
    echo "${files[$((n-1))]}"
}

# Buat backup tar.gz — inti
_bak_do_create() {
    local bfile="$1"
    _bak_collect
    if [[ ${#BAK_FILES[@]} -eq 0 ]]; then
        err "Tidak ada file data yang ditemukan untuk dibackup!"
        warn "Pastikan ZiVPN sudah diinstall (ada file di ${W}/etc/zivpn/${NC})"
        return 1
    fi
    inf "File yang akan dibackup:"
    for f in "${BAK_FILES[@]}"; do echo -e "  ${A3}•${NC}  $f"; done
    echo ""
    mkdir -p "$BAKDIR" 2>/dev/null
    if [[ ! -w "$BAKDIR" ]]; then
        err "Folder backup tidak bisa ditulis: ${W}$BAKDIR${NC}"; return 1
    fi
    inf "Membuat backup → ${W}$bfile${NC}"
    if tar -czPf "$bfile" "${BAK_FILES[@]}" 2>/tmp/oghziv_bak_err; then
        local sz; sz=$(du -sh "$bfile" 2>/dev/null | cut -f1)
        ok "Backup berhasil!"
        echo -e "  ${DIM}File   :${NC} ${W}$bfile${NC}"
        echo -e "  ${DIM}Ukuran :${NC} ${Y}$sz${NC}"
        echo -e "  ${DIM}Berisi :${NC} ${A3}${#BAK_FILES[@]} file${NC}"
        return 0
    else
        err "Backup gagal!"
        cat /tmp/oghziv_bak_err 2>/dev/null | head -5 | while read -r line; do
            echo -e "  ${LR}$line${NC}"; done
        return 1
    fi
}

# ════════════════════════════════════════════════════════════
#  BACKUP & RESTORE TELEGRAM — TULIS ULANG BERSIH
#  Prinsip:
#  • Backup  : kirim file ke bot → simpan file_id ke lokal
#  • Restore : baca file_id dari lokal → download langsung
#  • Tidak pakai getUpdates sama sekali (tidak reliable)
#  • Bot yang sama bisa dipakai di VPS baru
# ════════════════════════════════════════════════════════════

# File index yang menyimpan file_id hasil backup ke Telegram
TGIDX="$DIR/tg_backup_index.conf"
# Format: timestamp|file_id|bot_token|filename|size

# ── Simpan file_id ke index lokal ──────────────────────────────────────────────────
_tgidx_save() {
    local ts="$1" fid="$2" tok="$3" fname="$4" sz="$5"
    mkdir -p "$DIR"
    echo "${ts}|${fid}|${tok}|${fname}|${sz}" >> "$TGIDX"
}

# ── Baca index, tampilkan list, isi array global ─────────────
# Array: TGIDX_IDS  TGIDX_TOKS  TGIDX_NAMES  TGIDX_TIMES  TGIDX_CNT
_tgidx_list() {
    TGIDX_IDS=(); TGIDX_TOKS=(); TGIDX_NAMES=(); TGIDX_TIMES=(); TGIDX_CNT=0
    [[ ! -f "$TGIDX" ]] && return 1

    local -a rows=()
    while IFS= read -r line; do
        [[ -z "$line" ]] && continue
        rows+=("$line")
    done < "$TGIDX"
    [[ ${#rows[@]} -eq 0 ]] && return 1

    echo ""
    echo -e "  ${A1}${_DASH}${NC}"
    printf  "  ${DIM} %-3s  %-34s  %-6s  %-10s${NC}\n" "No" "Nama File" "Ukuran" "Tanggal"
    echo -e "  ${A1}${_DASH}${NC}"

    local i=0
    # Tampilkan urutan terbaru di atas (reverse)
    for (( idx=${#rows[@]}-1; idx>=0; idx-- )); do
        local row="${rows[$idx]}"
        local ts fid tok fname sz
        IFS='|' read -r ts fid tok fname sz <<< "$row"
        ((i++))
        TGIDX_IDS+=("$fid")
        TGIDX_TOKS+=("$tok")
        TGIDX_NAMES+=("$fname")
        TGIDX_TIMES+=("$ts")
        printf "   ${A2}%2d${NC}  ${W}%-34s${NC}  ${Y}%6s${NC}  ${DIM}%-10s${NC}\n" \
               "$i" "${fname:0:34}" "${sz:-?}" "${ts:0:10}"
    done
    echo -e "  ${A1}${_DASH}${NC}"
    echo ""
    TGIDX_CNT=$i
    return 0
}

# ── Kirim file ke Bot 1 saja, simpan file_id ────────────────
_bak_tg_send_file() {
    local bfile="$1"
    [[ ! -f "$BOTF" ]] && { err "Bot belum dikonfigurasi!"; return 1; }
    source "$BOTF" 2>/dev/null
    [[ -z "$BOT_TOKEN" || -z "$CHAT_ID" ]] && { err "Token/Chat ID belum diset!"; return 1; }

    local sz; sz=$(du -sh "$bfile" 2>/dev/null | cut -f1)
    local fname; fname=$(basename "$bfile")
    local ts; ts=$(date '+%Y-%m-%d %H:%M')
    local caption="💾 <b>Backup OGH-ZIV</b>
📁 <code>${fname}</code>
📦 ${sz} | 🖥 $(get_ip)
🕐 $(date '+%d/%m/%Y %H:%M:%S')"

    local sent=0

    # ── Bot 1 ──────────────────────────────────────────────────
    if [[ -n "$BOT_TOKEN" && -n "$CHAT_ID" ]]; then
        inf "Mengirim ke Bot 1 (@${BOT_NAME:-?})..."
        local r1
        r1=$(curl -s --max-time 180 -X POST \
            "https://api.telegram.org/bot${BOT_TOKEN}/sendDocument" \
            -F "chat_id=${CHAT_ID}" \
            -F "document=@${bfile}" \
            -F "caption=${caption}" \
            -F "parse_mode=HTML" 2>/dev/null)
        if echo "$r1" | grep -q '"ok":true'; then
            # Ambil file_id dari response dan simpan ke index
            local fid1
            fid1=$(echo "$r1" | python3 -c \
                "import sys,json; d=json.load(sys.stdin); print(d['result']['document']['file_id'])" 2>/dev/null)
            if [[ -n "$fid1" ]]; then
                _tgidx_save "$ts" "$fid1" "$BOT_TOKEN" "$fname" "$sz"
                ok "Terkirim ke Bot 1 ✔  (file_id tersimpan)"
            else
                ok "Terkirim ke Bot 1 ✔  (file_id tidak dapat diambil)"
            fi
            ((sent++))
        else
            local em; em=$(echo "$r1" | python3 -c \
                "import sys,json; d=json.load(sys.stdin); print(d.get('description','?'))" 2>/dev/null)
            warn "Bot 1 gagal: ${LR}${em}${NC}"
        fi
    fi

    # ── Bot 2 ──────────────────────────────────────────────────
    if [[ -n "$BOT_TOKEN2" && -n "$CHAT_ID2" ]]; then
        inf "Mengirim ke Bot 2 (@${BOT_NAME2:-?})..."
        local r2
        r2=$(curl -s --max-time 180 -X POST \
            "https://api.telegram.org/bot${BOT_TOKEN2}/sendDocument" \
            -F "chat_id=${CHAT_ID2}" \
            -F "document=@${bfile}" \
            -F "caption=${caption}" \
            -F "parse_mode=HTML" 2>/dev/null)
        if echo "$r2" | grep -q '"ok":true'; then
            local fid2
            fid2=$(echo "$r2" | python3 -c \
                "import sys,json; d=json.load(sys.stdin); print(d['result']['document']['file_id'])" 2>/dev/null)
            [[ -n "$fid2" ]] && _tgidx_save "$ts" "$fid2" "$BOT_TOKEN2" "$fname" "$sz"
            ok "Terkirim ke Bot 2 ✔"; ((sent++))
        else
            local em2; em2=$(echo "$r2" | python3 -c \
                "import sys,json; d=json.load(sys.stdin); print(d.get('description','?'))" 2>/dev/null)
            warn "Bot 2 gagal: ${LR}${em2}${NC}"
        fi
    fi

    # ── Bot 3 ──────────────────────────────────────────────────
    if [[ -n "$BOT_TOKEN3" && -n "$CHAT_ID3" ]]; then
        inf "Mengirim ke Bot 3 (@${BOT_NAME3:-?})..."
        local r3
        r3=$(curl -s --max-time 180 -X POST \
            "https://api.telegram.org/bot${BOT_TOKEN3}/sendDocument" \
            -F "chat_id=${CHAT_ID3}" \
            -F "document=@${bfile}" \
            -F "caption=${caption}" \
            -F "parse_mode=HTML" 2>/dev/null)
        if echo "$r3" | grep -q '"ok":true'; then
            local fid3
            fid3=$(echo "$r3" | python3 -c \
                "import sys,json; d=json.load(sys.stdin); print(d['result']['document']['file_id'])" 2>/dev/null)
            [[ -n "$fid3" ]] && _tgidx_save "$ts" "$fid3" "$BOT_TOKEN3" "$fname" "$sz"
            ok "Terkirim ke Bot 3 ✔"; ((sent++))
        else
            local em3; em3=$(echo "$r3" | python3 -c \
                "import sys,json; d=json.load(sys.stdin); print(d.get('description','?'))" 2>/dev/null)
            warn "Bot 3 gagal: ${LR}${em3}${NC}"
        fi
    fi

    [[ $sent -gt 0 ]] && return 0 || return 1
}

# ── Download file dari Telegram pakai file_id + token ───────
_bak_tg_download() {
    local file_id="$1" outfile="$2" tok="${3:-$BOT_TOKEN}"
    [[ -z "$tok" ]] && { [[ -f "$BOTF" ]] && source "$BOTF" 2>/dev/null; tok="$BOT_TOKEN"; }
    [[ -z "$tok" ]] && { err "Token tidak tersedia!"; return 1; }

    inf "Mendapatkan link download dari Telegram..."
    local finfo
    finfo=$(curl -s --max-time 30 \
        "https://api.telegram.org/bot${tok}/getFile?file_id=${file_id}" 2>/dev/null)

    if ! echo "$finfo" | grep -q '"ok":true'; then
        local tgerr; tgerr=$(echo "$finfo" | python3 -c \
            "import sys,json; d=json.load(sys.stdin); print(d.get('description','Unknown'))" 2>/dev/null)
        err "getFile gagal: ${LR}${tgerr}${NC}"
        return 1
    fi

    local fpath
    fpath=$(echo "$finfo" | python3 -c \
        "import sys,json; d=json.load(sys.stdin); print(d['result']['file_path'])" 2>/dev/null)
    [[ -z "$fpath" ]] && { err "Gagal parse file_path!"; return 1; }

    local dlurl="https://api.telegram.org/file/bot${tok}/${fpath}"
    inf "Mengunduh... (harap tunggu)"

    local tmp="${outfile}.tmp$$"
    if curl -s --max-time 300 -L "$dlurl" -o "$tmp" 2>/dev/null && [[ -s "$tmp" ]]; then
        mv "$tmp" "$outfile"
        local sz; sz=$(du -sh "$outfile" 2>/dev/null | cut -f1)
        ok "Berhasil diunduh: ${W}$(basename "$outfile")${NC} (${Y}${sz}${NC})"
        return 0
    else
        rm -f "$tmp"
        err "Download gagal atau file kosong!"
        return 1
    fi
}

# ── Auto-cleanup backup lokal lama ──────────────────────────────────────────────────
_bak_cleanup_old() {
    local keep="${1:-10}"
    local -a files=()
    while IFS= read -r -d '' f; do
        files+=("$f")
    done < <(find "$BAKDIR" -maxdepth 1 -name 'oghziv-backup-*.tar.gz' -print0 2>/dev/null | sort -z)
    local total=${#files[@]}
    if [[ $total -gt $keep ]]; then
        local del=$(( total - keep ))
        for (( i=0; i<del; i++ )); do
            rm -f "${files[$i]}" 2>/dev/null
            inf "Hapus backup lama: ${DIM}$(basename "${files[$i]}")${NC}"
        done
        ok "Auto-cleanup: ${Y}$del${NC} backup lama dihapus."
    fi
}

# ════════════════════════════════════════════════════════════
#  MENU BACKUP
# ════════════════════════════════════════════════════════════
svc_backup() {
    while true; do
        show_header
        mkdir -p "$BAKDIR" 2>/dev/null
        local total_bak; total_bak=$(find "$BAKDIR" -maxdepth 1 -name 'oghziv-backup-*.tar.gz' 2>/dev/null | wc -l)
        local bak_size; bak_size=$(du -sh "$BAKDIR" 2>/dev/null | cut -f1)
        local tgidx_cnt=0
        [[ -f "$TGIDX" ]] && tgidx_cnt=$(grep -c '' "$TGIDX" 2>/dev/null || echo 0)

        local bot_stat="${LR}Belum dikonfigurasi${NC}"
        [[ -f "$BOTF" ]] && { source "$BOTF" 2>/dev/null
            [[ -n "$BOT_TOKEN" ]] && bot_stat="${LG}@${BOT_NAME:-?} aktif${NC}"; }

        _top
        _btn "  ${IT}${AL}  💾  BACKUP DATA${NC}"
        _sep
        _btn "  ${DIM}Lokal   :${NC} ${Y}${total_bak} file${NC}  •  ${DIM}Size:${NC} ${A3}${bak_size:-0}${NC}"
        _btn "  ${DIM}TG Index:${NC} ${Y}${tgidx_cnt} entri${NC}  •  ${DIM}Bot:${NC} ${bot_stat}"
        _sep
        _btn "  ${A2}[1]${NC}  📦  Buat Backup & Kirim ke Telegram"
        _sep
        _btn "  ${A2}[2]${NC}  📋  Lihat Daftar Backup Lokal"
        _sep
        _btn "  ${A2}[3]${NC}  📤  Kirim Ulang Backup ke Telegram"
        _sep
        _btn "  ${A2}[4]${NC}  🗑️   Hapus Backup Lokal"
        _sep
        _btn "  ${A2}[5]${NC}  🧹  Bersihkan Backup Lama"
        _sep
        _btn "  ${LR}[0]${NC}  ◀   Kembali"
        _bot; echo ""
        echo -ne "  ${A1}›${NC} "; read -r ch

        case $ch in
        1)
            show_header
            _top; _btn "  ${IT}${AL}📦  BUAT BACKUP & KIRIM KE TELEGRAM${NC}"; _bot; echo ""
            if [[ ! -f "$BOTF" ]]; then
                err "Bot Telegram belum dikonfigurasi!"; pause; continue; fi
            source "$BOTF" 2>/dev/null
            [[ -z "$BOT_TOKEN" || -z "$CHAT_ID" ]] && {
                err "Token/Chat ID belum diset!"; pause; continue; }
            local bfile="${BAKDIR}/oghziv-backup-$(date +%Y%m%d-%H%M%S).tar.gz"
            echo ""
            if _bak_do_create "$bfile"; then
                _bak_cleanup_old 10
                echo ""
                inf "Mengirim backup ke Telegram..."
                echo ""
                if _bak_tg_send_file "$bfile"; then
                    echo ""
                    ok "Backup selesai & terkirim ke Telegram!"
                    inf "file_id tersimpan di index lokal untuk restore nanti."
                else
                    warn "Backup tersimpan lokal tapi GAGAL dikirim ke Telegram."
                    warn "Coba kirim ulang dengan pilihan [3]."
                fi
            fi
            pause
            ;;

        2)
            show_header
            _top; _btn "  ${IT}${AL}📋  DAFTAR BACKUP LOKAL${NC}"; _bot
            _bak_list
            [[ "$BAK_CNT" == "0" ]] && echo -e "  ${DIM}Buat backup dulu dengan pilihan [1]${NC}"
            pause
            ;;

        3)
            show_header
            _top; _btn "  ${IT}${AL}📤  KIRIM ULANG BACKUP KE TELEGRAM${NC}"; _bot; echo ""
            if [[ ! -f "$BOTF" ]]; then
                err "Bot Telegram belum dikonfigurasi!"; pause; continue; fi
            source "$BOTF" 2>/dev/null
            [[ -z "$BOT_TOKEN" || -z "$CHAT_ID" ]] && {
                err "Token/Chat ID belum diset!"; pause; continue; }
            _bak_list
            local cnt=$BAK_CNT
            [[ "$cnt" == "0" ]] && { pause; continue; }
            echo -ne "  ${A3}Nomor backup yang dikirim${NC} [1-$cnt]: "; read -r bno
            [[ ! "$bno" =~ ^[0-9]+$ || $bno -lt 1 || $bno -gt $cnt ]] && {
                err "Nomor tidak valid!"; pause; continue; }
            local bpath; bpath=$(_bak_get_file "$bno")
            [[ ! -f "$bpath" ]] && { err "File tidak ditemukan!"; pause; continue; }
            echo ""
            if _bak_tg_send_file "$bpath"; then
                ok "Backup berhasil dikirim & file_id tersimpan di index!"
            else
                err "Gagal kirim! Cek token/Chat ID atau ukuran file (maks 50MB)."
            fi
            pause
            ;;

        4)
            show_header
            _top; _btn "  ${IT}${AL}🗑️   HAPUS BACKUP LOKAL${NC}"; _bot
            _bak_list
            local cnt=$BAK_CNT
            [[ "$cnt" == "0" ]] && { pause; continue; }
            echo -ne "  ${A3}Nomor [1-$cnt] atau 'all'${NC}: "; read -r bno
            if [[ "${bno,,}" == "all" ]]; then
                echo -ne "  ${LR}Hapus SEMUA $cnt backup? [y/N]${NC}: "; read -r cf
                [[ "$cf" == [yY] ]] && \
                    { rm -f "${BAKDIR}"/oghziv-backup-*.tar.gz; ok "Semua backup lokal dihapus!"; } || \
                    inf "Dibatalkan."
            elif [[ "$bno" =~ ^[0-9]+$ && $bno -ge 1 && $bno -le $cnt ]]; then
                local bpath; bpath=$(_bak_get_file "$bno")
                echo -ne "  ${LR}Hapus ${W}$(basename "$bpath")${LR}? [y/N]${NC}: "; read -r cf
                [[ "$cf" == [yY] ]] && { rm -f "$bpath"; ok "Dihapus!"; } || inf "Dibatalkan."
            else
                err "Pilihan tidak valid!"
            fi
            pause
            ;;

        5)
            show_header
            _top; _btn "  ${IT}${AL}🧹  BERSIHKAN BACKUP LAMA${NC}"; _bot; echo ""
            local total_bak2; total_bak2=$(find "$BAKDIR" -maxdepth 1 -name 'oghziv-backup-*.tar.gz' 2>/dev/null | wc -l)
            echo -e "  ${DIM}Total backup: ${Y}$total_bak2 file${NC}"
            echo -ne "  ${A3}Simpan berapa backup terbaru${NC} [default=5]: "; read -r kp
            [[ ! "$kp" =~ ^[0-9]+$ || $kp -lt 1 ]] && kp=5
            if [[ $total_bak2 -le $kp ]]; then
                inf "Total ($total_bak2) ≤ keep ($kp). Tidak ada yang dihapus."
            else
                echo -ne "  Hapus ${LR}$((total_bak2 - kp))${NC} backup terlama? [y/N]: "; read -r cf
                [[ "$cf" == [yY] ]] && _bak_cleanup_old "$kp" || inf "Dibatalkan."
            fi
            pause
            ;;

        0) break ;;
        *) warn "Pilihan tidak valid!"; sleep 1 ;;
        esac
    done
}

# ════════════════════════════════════════════════════════════
#  RESTORE DARI VPS LAIN (beda IP) via SCP
# ════════════════════════════════════════════════════════════
_bak_restore_from_remote() {
    show_header
    _top; _btn "  ${IT}${AL}🌐  RESTORE DARI VPS LAIN (Beda IP)${NC}"; _bot; echo ""
    echo -e "  ${DIM}Ambil file backup dari VPS lain via SCP (SSH).${NC}"; echo ""

    echo -ne "  ${A3}IP / Hostname VPS asal${NC}         : "; read -r remote_ip
    [[ -z "$remote_ip" ]] && { err "IP tidak boleh kosong!"; pause; return; }
    echo -ne "  ${A3}Port SSH${NC} [22]                  : "; read -r remote_port
    [[ -z "$remote_port" || ! "$remote_port" =~ ^[0-9]+$ ]] && remote_port=22
    echo -ne "  ${A3}Username SSH${NC} [root]             : "; read -r remote_user
    [[ -z "$remote_user" ]] && remote_user="root"
    echo -ne "  ${A3}Password SSH${NC} (kosong=pakai key) : "; read -rs remote_pass; echo ""

    local scp_cmd="scp"
    local ssh_opts="-o StrictHostKeyChecking=no -o ConnectTimeout=15 -P $remote_port"
    local ssh_base="ssh -o StrictHostKeyChecking=no -o ConnectTimeout=15 -p $remote_port"

    if [[ -n "$remote_pass" ]]; then
        if ! command -v sshpass &>/dev/null; then
            inf "Menginstall sshpass..."
            apt-get install -y -qq sshpass &>/dev/null || {
                err "Gagal install sshpass!"; pause; return; }
        fi
        scp_cmd="sshpass -p '$remote_pass' scp"
        ssh_base="sshpass -p '$remote_pass' ssh -o StrictHostKeyChecking=no -o ConnectTimeout=15 -p $remote_port"
    fi

    echo ""
    inf "Menghubungi VPS ${Y}${remote_ip}${NC}:${remote_port}..."
    local ssh_test
    ssh_test=$(eval "$ssh_base ${remote_user}@${remote_ip} 'echo OK' 2>/dev/null")
    if [[ "$ssh_test" != "OK" ]]; then
        err "Gagal terhubung ke ${W}${remote_ip}:${remote_port}${NC}"
        echo -e "  ${DIM}• Cek IP/port SSH${NC}"; echo -e "  ${DIM}• Cek password/SSH key${NC}"
        pause; return
    fi
    ok "Koneksi SSH berhasil ke ${W}${remote_ip}${NC}"; echo ""

    echo -e "  ${A1}${_DASH}${NC}"
    echo -e "  ${A2}[1]${NC}  Pilih dari daftar backup VPS asal"
    echo -e "  ${A2}[2]${NC}  Input path manual"
    echo -e "  ${A1}${_DASH}${NC}"; echo ""
    echo -ne "  ${A3}Pilih${NC} [1-2]: "; read -r rch

    local remote_bak_path=""
    if [[ "$rch" == "1" ]]; then
        inf "Mengambil daftar backup dari VPS asal..."
        local remote_list
        remote_list=$(eval "$ssh_base ${remote_user}@${remote_ip} \
            'ls -1t /root/oghziv-backups/oghziv-backup-*.tar.gz 2>/dev/null | head -20'")
        if [[ -z "$remote_list" ]]; then
            warn "Tidak ada backup di /root/oghziv-backups/ VPS asal."
            echo -ne "  ${A3}Input path manual${NC}: "; read -r manual_path
            [[ -z "$manual_path" ]] && { inf "Dibatalkan."; pause; return; }
            remote_bak_path="$manual_path"
        else
            echo ""
            echo -e "  ${A1}${_DASH}${NC}"
            printf "  ${DIM} %-3s  %-42s  %-6s${NC}\n" "No" "Nama File" "Ukuran"
            echo -e "  ${A1}${_DASH}${NC}"
            local i=0; local -a remote_files=()
            while IFS= read -r rfile; do
                [[ -z "$rfile" ]] && continue; ((i++))
                remote_files+=("$rfile")
                local rfname; rfname=$(basename "$rfile")
                local rfsize; rfsize=$(eval "$ssh_base ${remote_user}@${remote_ip} \
                    'du -sh \"$rfile\" 2>/dev/null | cut -f1'")
                printf "   ${A2}%2d${NC}  ${W}%-42s${NC}  ${Y}%6s${NC}\n" \
                       "$i" "${rfname:0:42}" "${rfsize:-?}"
            done <<< "$remote_list"
            echo -e "  ${A1}${_DASH}${NC}"; echo ""
            echo -ne "  ${A3}Pilih nomor${NC} [1-$i]: "; read -r rno
            [[ ! "$rno" =~ ^[0-9]+$ || $rno -lt 1 || $rno -gt $i ]] && {
                err "Nomor tidak valid!"; pause; return; }
            remote_bak_path="${remote_files[$((rno-1))]}"
        fi
    elif [[ "$rch" == "2" ]]; then
        echo -ne "  ${A3}Path file backup di VPS asal${NC}: "; read -r remote_bak_path
        remote_bak_path="${remote_bak_path// /}"
    else
        inf "Dibatalkan."; pause; return
    fi

    [[ -z "$remote_bak_path" ]] && { err "Path tidak valid!"; pause; return; }

    local file_exists
    file_exists=$(eval "$ssh_base ${remote_user}@${remote_ip} \
        'test -f \"$remote_bak_path\" && echo YES || echo NO' 2>/dev/null")
    [[ "$file_exists" != "YES" ]] && {
        err "File tidak ditemukan di VPS asal!"; pause; return; }

    mkdir -p "$BAKDIR"
    local local_fname; local_fname=$(basename "$remote_bak_path")
    local local_dl="${BAKDIR}/${local_fname}"

    echo ""; inf "Mengunduh file dari VPS ${Y}${remote_ip}${NC}..."; echo ""

    local scp_result=0
    if [[ -n "$remote_pass" ]]; then
        sshpass -p "$remote_pass" scp -o StrictHostKeyChecking=no \
            -P "$remote_port" "${remote_user}@${remote_ip}:${remote_bak_path}" \
            "$local_dl" 2>/tmp/oghziv_scp_err; scp_result=$?
    else
        scp -o StrictHostKeyChecking=no -P "$remote_port" \
            "${remote_user}@${remote_ip}:${remote_bak_path}" \
            "$local_dl" 2>/tmp/oghziv_scp_err; scp_result=$?
    fi

    if [[ $scp_result -ne 0 || ! -s "$local_dl" ]]; then
        err "Gagal mengunduh file dari VPS asal!"
        cat /tmp/oghziv_scp_err 2>/dev/null | head -5 | while read -r line; do
            echo -e "  ${LR}$line${NC}"; done
        rm -f "$local_dl" /tmp/oghziv_scp_err 2>/dev/null
        pause; return
    fi
    ok "File berhasil diunduh: ${W}${local_fname}${NC}"
    _bak_do_restore "$local_dl"
}

# ════════════════════════════════════════════════════════════
#  RESTORE DARI TELEGRAM
#  Pakai file_id dari index lokal — tidak butuh getUpdates
# ════════════════════════════════════════════════════════════
_bak_restore_from_telegram() {
    show_header
    _top; _btn "  ${IT}${AL}📲  RESTORE DARI TELEGRAM${NC}"; _bot; echo ""

    if [[ ! -f "$BOTF" ]]; then
        err "Bot Telegram belum dikonfigurasi!"; pause; return; fi
    source "$BOTF" 2>/dev/null
    [[ -z "$BOT_TOKEN" ]] && { err "Token belum diset!"; pause; return; }

    echo -e "  ${A1}${_DASH}${NC}"
    echo -e "  ${A2}[1]${NC}  📋  Pilih dari index backup Telegram"
    echo -e "  ${A2}[2]${NC}  🔗  Input File ID manual"
    echo -e "  ${A1}${_DASH}${NC}"
    echo ""
    echo -ne "  ${A3}Pilih metode${NC} [1-2]: "; read -r tch

    # ── Opsi 1: Dari index lokal ──────────────────────────────────────────────────
    if [[ "$tch" == "1" ]]; then
        if [[ ! -f "$TGIDX" ]]; then
            err "Index backup Telegram belum ada!"
            inf "Lakukan backup dulu via menu Backup → [1] Buat Backup & Kirim ke Telegram."
            inf "Index otomatis terbuat saat backup berhasil dikirim."
            pause; return
        fi

        if ! _tgidx_list; then
            err "Index kosong atau tidak ada entri valid."
            inf "Lakukan backup dulu via menu Backup → [1]."
            pause; return
        fi

        echo -ne "  ${A3}Pilih nomor backup${NC} [1-${TGIDX_CNT}]: "; read -r bno
        [[ ! "$bno" =~ ^[0-9]+$ || $bno -lt 1 || $bno -gt $TGIDX_CNT ]] && {
            err "Nomor tidak valid!"; pause; return; }

        local sel_id="${TGIDX_IDS[$((bno-1))]}"
        local sel_tok="${TGIDX_TOKS[$((bno-1))]}"
        local sel_name="${TGIDX_NAMES[$((bno-1))]}"
        local dl_path="${BAKDIR}/${sel_name}"
        mkdir -p "$BAKDIR"

        echo ""; inf "File dipilih: ${W}${sel_name}${NC}"; echo ""

        if _bak_tg_download "$sel_id" "$dl_path" "$sel_tok"; then
            _bak_do_restore "$dl_path"
        else
            err "Gagal download dari Telegram!"
            inf "Coba opsi [2] input File ID manual, atau restore dari lokal."
            pause
        fi
        return
    fi

    # ── Opsi 2: Input File ID manual ───────────────────────
    if [[ "$tch" == "2" ]]; then
        echo ""
        inf "Cara dapat File ID:"
        echo -e "  ${DIM}1. Buka chat bot di Telegram${NC}"
        echo -e "  ${DIM}2. Klik file backup → Properties / Info${NC}"
        echo -e "  ${DIM}3. Atau buka: https://api.telegram.org/bot<TOKEN>/getUpdates${NC}"
        echo -e "  ${DIM}   Cari field \"file_id\" di bagian \"document\"${NC}"
        echo ""
        echo -ne "  ${A3}File ID${NC}       : "; read -r manual_fid
        [[ -z "$manual_fid" ]] && { err "File ID kosong!"; pause; return; }
        echo -ne "  ${A3}Nama file${NC} [oghziv-backup-manual.tar.gz]: "; read -r manual_fname
        [[ -z "$manual_fname" ]] && manual_fname="oghziv-backup-manual.tar.gz"
        echo -ne "  ${A3}Token bot${NC} [Enter = pakai Bot 1]         : "; read -r manual_tok
        [[ -z "$manual_tok" ]] && manual_tok="$BOT_TOKEN"

        mkdir -p "$BAKDIR"
        local dl_path="${BAKDIR}/${manual_fname}"
        if _bak_tg_download "$manual_fid" "$dl_path" "$manual_tok"; then
            _bak_do_restore "$dl_path"
        else
            err "Gagal download! Periksa File ID atau token."
            pause
        fi
        return
    fi

    warn "Pilihan tidak valid!"; sleep 1
}

# ════════════════════════════════════════════════════════════
#  MENU RESTORE
# ════════════════════════════════════════════════════════════
svc_restore() {
    while true; do
        show_header
        _top
        _btn "  ${IT}${AL}  ♻️   RESTORE DATA${NC}"
        _sep
        _btn "  ${A2}[1]${NC}  📲  Restore dari Telegram"
        _sep
        _btn "  ${A2}[2]${NC}  💻  Restore dari Lokal (VPS ini)"
        _sep
        _btn "  ${A2}[3]${NC}  🌐  Restore dari VPS Lain (Beda IP)"
        _sep
        _btn "  ${A2}[4]${NC}  📁  Restore dari Path Manual"
        _sep
        _btn "  ${A2}[5]${NC}  🔍  Verifikasi / Lihat Isi Backup"
        _sep
        _btn "  ${LR}[0]${NC}  ◀   Kembali"
        _bot; echo ""
        echo -ne "  ${A1}›${NC} "; read -r ch

        case $ch in
        1) _bak_restore_from_telegram ;;

        2)
            show_header
            _top; _btn "  ${IT}${AL}💻  RESTORE DARI BACKUP LOKAL${NC}"; _bot
            _bak_list
            local cnt=$BAK_CNT
            if [[ "$cnt" == "0" ]]; then
                echo -e "\n  ${DIM}Belum ada backup lokal.${NC}"; pause; continue; fi
            echo -ne "  ${A3}Nomor backup${NC} [1-$cnt]: "; read -r bno
            [[ ! "$bno" =~ ^[0-9]+$ || $bno -lt 1 || $bno -gt $cnt ]] && {
                err "Nomor tidak valid!"; pause; continue; }
            _bak_do_restore "$(_bak_get_file "$bno")"
            ;;

        3) _bak_restore_from_remote ;;

        4)
            show_header
            _top; _btn "  ${IT}${AL}📁  RESTORE DARI PATH MANUAL${NC}"; _bot; echo ""
            echo -ne "  ${A3}Path lengkap file backup (.tar.gz)${NC}: "; read -r bpath
            bpath="${bpath//\'/}"; bpath="${bpath// /}"
            if [[ ! -f "$bpath" ]]; then
                err "File tidak ditemukan: ${W}$bpath${NC}"; pause; continue; fi
            _bak_do_restore "$bpath"
            ;;

        5)
            show_header
            _top; _btn "  ${IT}${AL}🔍  VERIFIKASI BACKUP${NC}"; _bot
            _bak_list
            local cnt=$BAK_CNT
            [[ "$cnt" == "0" ]] && { pause; continue; }
            echo -ne "  ${A3}Nomor backup${NC} [1-$cnt]: "; read -r bno
            [[ ! "$bno" =~ ^[0-9]+$ || $bno -lt 1 || $bno -gt $cnt ]] && {
                err "Nomor tidak valid!"; pause; continue; }
            local bpath; bpath=$(_bak_get_file "$bno")
            echo ""; inf "Memeriksa integritas file..."
            if tar -tPf "$bpath" &>/dev/null; then
                ok "File backup VALID ✔"; echo ""
                echo -e "  ${DIM}Isi backup:${NC}"
                tar -tPf "$bpath" 2>/dev/null | while read -r item; do
                    printf "  ${A3}•${NC}  %s\n" "$item"; done
            else
                err "File backup RUSAK atau tidak valid!"
            fi
            pause
            ;;

        0) break ;;
        *) warn "Pilihan tidak valid!"; sleep 1 ;;
        esac
    done
}

# ── Eksekutor restore — fungsi inti ──────────────────────────────────────────────────
_bak_do_restore() {
    local bpath="$1"
    echo ""
    echo -e "  ${DIM}File   :${NC} ${W}$bpath${NC}"
    local sz; sz=$(du -sh "$bpath" 2>/dev/null | cut -f1)
    echo -e "  ${DIM}Ukuran :${NC} ${Y}$sz${NC}"; echo ""

    inf "Memverifikasi file backup..."
    if ! tar -tPf "$bpath" &>/dev/null; then
        err "File backup RUSAK atau bukan format tar.gz yang valid!"
        err "Restore dibatalkan."; pause; return
    fi
    ok "File valid."; echo ""

    echo -e "  ${DIM}File yang akan di-restore:${NC}"
    tar -tPf "$bpath" 2>/dev/null | while read -r item; do
        printf "  ${A3}•${NC}  %s\n" "$item"; done
    echo ""

    warn "Restore akan MENIMPA data yang ada saat ini!"
    warn "Auto-backup data saat ini akan dibuat terlebih dahulu."
    echo ""
    echo -ne "  ${A3}Ketik ${LR}RESTORE${A3} untuk konfirmasi, lainnya batal${NC}: "; read -r cf
    [[ "$cf" != "RESTORE" ]] && { inf "Dibatalkan."; pause; return; }

    echo ""; inf "Membuat auto-backup data saat ini..."
    mkdir -p "$BAKDIR"
    local safebak="${BAKDIR}/oghziv-pre-restore-$(date +%Y%m%d-%H%M%S).tar.gz"
    _bak_collect
    if [[ ${#BAK_FILES[@]} -gt 0 ]]; then
        tar -czPf "$safebak" "${BAK_FILES[@]}" 2>/dev/null && \
            ok "Auto-backup: ${W}$(basename "$safebak")${NC}" || \
            warn "Auto-backup gagal, lanjut restore..."
    else
        warn "Tidak ada data existing. Lanjut restore..."
    fi
    echo ""

    inf "Menghentikan service ZiVPN..."
    systemctl stop zivpn 2>/dev/null; sleep 1

    inf "Merestore data..."
    if tar -xPf "$bpath" 2>/tmp/oghziv_rst_err; then
        echo ""
        _reload_pw 2>/dev/null
        systemctl daemon-reload 2>/dev/null
        systemctl start zivpn 2>/dev/null; sleep 2
        echo ""
        ok "Restore selesai!"
        is_up && ok "ZiVPN ${LG}RUNNING${NC} ✔" || warn "ZiVPN belum jalan — coba: ${Y}systemctl start zivpn${NC}"
        _tg_send "♻️ <b>Restore Berhasil</b>
📁 Dari: <code>$(basename "$bpath")</code>
🖥 VPS: $(get_ip)
🕐 Waktu: $(date '+%d/%m/%Y %H:%M:%S')"
    else
        echo ""; err "Restore GAGAL!"
        warn "Detail error:"
        cat /tmp/oghziv_rst_err 2>/dev/null | head -5 | while read -r line; do
            echo -e "  ${LR}$line${NC}"; done
        warn "Auto-backup aman di: ${W}$safebak${NC}"
        systemctl start zivpn 2>/dev/null
    fi
    rm -f /tmp/oghziv_rst_err /tmp/oghziv_bak_err 2>/dev/null
    pause
}

# ════════════════════════════════════════════════════════════
#  DOMAIN MANAGEMENT
# ════════════════════════════════════════════════════════════
domain_set() {
    show_header
    _top; _btn "  ${IT}${AL}✏️   SET / GANTI DOMAIN${NC}"; _bot; echo ""
    local cur; cur=$(get_domain)
    local ip;  ip=$(get_ip)
    echo -e "  ${DIM}Domain saat ini : ${W}$cur${NC}"
    echo -e "  ${DIM}IP Publik VPS   : ${A3}$ip${NC}"; echo ""
    inf "Pastikan DNS domain sudah diarahkan ke IP: ${Y}$ip${NC}"
    echo ""
    echo -ne "  ${A3}Domain baru${NC} (kosongkan = pakai IP): "; read -r nd
    if [[ -z "$nd" ]]; then
        echo "$ip" > "$DOMF"; ok "Domain diatur ke IP publik: ${A3}$ip${NC}"
    else
        echo "$nd" > "$DOMF"; ok "Domain disimpan: ${W}$nd${NC}"
        echo -ne "  ${A3}Regenerasi SSL sekarang?${NC} [y/N]: "; read -r rs
        [[ "$rs" == [yY] ]] && domain_ssl
    fi
    pause
}

domain_use_ip() {
    show_header
    _top; _btn "  ${IT}${AL}🔄  GUNAKAN IP PUBLIK${NC}"; _bot; echo ""
    local ip; ip=$(get_ip)
    echo "$ip" > "$DOMF"
    ok "Domain direset ke IP publik: ${A3}$ip${NC}"
    pause
}

domain_check() {
    show_header
    _top; _btn "  ${IT}${AL}🔍  CEK DNS DOMAIN${NC}"; _bot; echo ""
    local dom; dom=$(get_domain)
    local ip;  ip=$(get_ip)
    echo -e "  ${DIM}Domain  : ${W}$dom${NC}"
    echo -e "  ${DIM}IP VPS  : ${A3}$ip${NC}"; echo ""
    inf "Resolving DNS..."
    local resolved
    resolved=$(host "$dom" 2>/dev/null | grep "has address" | awk '{print $NF}' | head -1)
    [[ -z "$resolved" ]] && resolved=$(nslookup "$dom" 2>/dev/null | awk '/^Address:/{print $2}' | grep -v '#' | head -1)
    if [[ -z "$resolved" ]]; then
        err "Tidak dapat meresolve domain: ${W}$dom${NC}"
    elif [[ "$resolved" == "$ip" ]]; then
        ok "DNS OK — ${W}$dom${NC} → ${A3}$resolved${NC} ${LG}(cocok dengan IP VPS)${NC}"
    else
        warn "DNS mismatch!"
        echo -e "  ${DIM}Domain resolve ke : ${LR}$resolved${NC}"
        echo -e "  ${DIM}IP VPS            : ${A3}$ip${NC}"
        inf "Arahkan DNS domain ke IP: ${Y}$ip${NC}"
    fi
    pause
}

domain_ssl() {
    show_header
    _top; _btn "  ${IT}${AL}🔄  REGENERASI SSL CERTIFICATE${NC}"; _bot; echo ""
    local dom; dom=$(get_domain)
    inf "Membuat SSL baru untuk: ${W}$dom${NC}"
    openssl req -x509 -nodes -newkey ec -pkeyopt ec_paramgen_curve:P-256 \
        -keyout "$DIR/zivpn.key" -out "$DIR/zivpn.crt" \
        -subj "/CN=$dom" -days 3650 &>/dev/null \
        && ok "SSL Certificate (10 tahun) berhasil dibuat untuk ${W}$dom${NC}" \
        || { err "Gagal generate SSL!"; pause; return; }
    systemctl restart zivpn &>/dev/null
    ok "Service direstart dengan SSL baru."
    pause
}

menu_domain() {
    while true; do
        show_header
        local cur_domain; cur_domain=$(get_domain)
        local cur_ip;     cur_ip=$(get_ip)
        _top
        _btn "  ${IT}${AL}  🌐  MANAJEMEN DOMAIN${NC}"
        _sep
        printf "  ${DIM}Domain aktif${NC} : ${W}%s${NC}\n" "$cur_domain"
        printf "  ${DIM}IP Publik   ${NC} : ${A3}%s${NC}\n" "$cur_ip"
        _sep
        _btn "  ${A2}[1]${NC}  ✏️   Set / Ganti Domain"
        _sep
        _btn "  ${A2}[2]${NC}  🔄  Gunakan IP Publik (hapus domain)"
        _sep
        _btn "  ${A2}[3]${NC}  🔍  Cek DNS Domain"
        _sep
        _btn "  ${A2}[4]${NC}  🔐  Update SSL untuk Domain Baru"
        _sep
        _btn "  ${LR}[0]${NC}  ◀   Kembali"
        _bot; echo ""
        echo -ne "  ${A1}›${NC} "; read -r ch
        case $ch in
            1) domain_set ;;   2) domain_use_ip ;;
            3) domain_check ;; 4) domain_ssl ;;
            0) break ;; *) warn "Pilihan tidak valid!"; sleep 1 ;;
        esac
    done
}

do_uninstall() {
    show_header
    _top; _btn "  ${IT}${AL}⚠️   UNINSTALL OGH-ZIV${NC}"; _bot; echo ""
    warn "Semua data user & konfigurasi akan DIHAPUS PERMANEN!"
    echo -ne "  ${LR}Ketik 'HAPUS' untuk konfirmasi${NC}: "; read -r cf
    [[ "$cf" != "HAPUS" ]] && { inf "Dibatalkan."; pause; return; }
    systemctl stop    zivpn.service 2>/dev/null
    systemctl disable zivpn.service 2>/dev/null
    rm -f "$SVC" "$BIN"
    rm -rf "$DIR"
    systemctl daemon-reload 2>/dev/null

    # Hapus iptables rules
    local IFACE; IFACE=$(ip -4 route ls | grep default | grep -Po '(?<=dev )(\S+)' | head -1)
    while iptables -t nat -D PREROUTING         -i "$IFACE" -p udp --dport 6000:19999         -j DNAT --to-destination :5667 2>/dev/null; do :; done
    iptables -D FORWARD -p udp -d 127.0.0.1 --dport 5667 -j ACCEPT 2>/dev/null
    iptables -t nat -D POSTROUTING -s 127.0.0.1/32 -o "$IFACE" -j MASQUERADE 2>/dev/null
    netfilter-persistent save &>/dev/null

    # Hapus menu command
    rm -f /usr/local/bin/menu /usr/local/bin/ogh-ziv 2>/dev/null
    rm -f /etc/profile.d/ogh-ziv.sh 2>/dev/null
    sed -i "/alias menu=/d"  ~/.bashrc  2>/dev/null
    sed -i "/alias zivpn=/d" ~/.bashrc  2>/dev/null
    sed -i "/alias menu=/d"  /root/.profile 2>/dev/null

    ok "OGH-ZIV Premium berhasil diuninstall sepenuhnya."
    echo -e "  ${DIM}Semua binary, service, data, iptables & menu telah dihapus.${NC}"
    pause
    exit 0
}

# ════════════════════════════════════════════════════════════
#  MAXLOGIN MANAGEMENT
# ════════════════════════════════════════════════════════════
u_maxlogin() {
    show_header
    _top; _btn "  ${IT}${AL}🔒  SET MAXLOGIN DEVICE${NC}"; _bot; echo ""
    [[ ! -s "$UDB" ]] && { warn "Belum ada akun terdaftar."; pause; return; }
    echo ""
    echo -e "  ${A1}${_DASH}${NC}"
    printf  "  ${DIM}%-20s  %-8s  %-10s${NC}\n" "Username" "MaxDev" "Status"
    echo -e "  ${A1}${_DASH}${NC}"
    while IFS='|' read -r u _ e _ _; do
        local ml; ml=$(get_maxlogin "$u"); [[ -z "$ml" ]] && ml="-"
        local today; today=$(date +%Y-%m-%d)
        local sc sl
        [[ "$e" < "$today" ]] && { sc="${LR}"; sl="EXPIRED"; } || { sc="${LG}"; sl="AKTIF  "; }
        printf "  ${W}%-20s${NC}  ${Y}%-8s${NC}  ${sc}%-10s${NC}\n" "$u" "$ml" "$sl"
    done < "$UDB"
    echo -e "  ${A1}${_DASH}${NC}"
    echo ""
    echo -ne "  ${A3}Username${NC}          : "; read -r mu
    grep -q "^${mu}|" "$UDB" 2>/dev/null || { err "User tidak ditemukan!"; pause; return; }
    local cur_ml; cur_ml=$(get_maxlogin "$mu"); [[ -z "$cur_ml" ]] && cur_ml=2
    echo -e "  ${DIM}MaxLogin saat ini : ${Y}${cur_ml} device${NC}"
    echo -ne "  ${A3}Max Login Device${NC} [${cur_ml}]: "; read -r nml
    [[ -z "$nml" || ! "$nml" =~ ^[0-9]+$ ]] && nml="$cur_ml"
    set_maxlogin "$mu" "$nml"
    echo ""
    echo -e "  ${A1}${_DASH}${NC}"
    echo -e "  ${LG}✔  MaxLogin berhasil diatur!${NC}"
    echo -e "  ${A1}${_DASH}${NC}"
    printf  "  ${DIM} Username :${NC}  ${W}%s${NC}\n" "$mu"
    printf  "  ${DIM} Max Dev  :${NC}  ${Y}%s${NC}\n" "${nml} device"
    printf  "  ${DIM} Info     :${NC}  ${DIM}%s${NC}\n" "Auto-delete jika melebihi limit"
    echo -e "  ${A1}${_DASH}${NC}"
    # Setup cron untuk enforce maxlogin setiap 5 menit
    local cronline="*/5 * * * * bash /usr/local/bin/ogh-ziv --check-maxlogin >/dev/null 2>&1"
    (crontab -l 2>/dev/null | grep -q "check-maxlogin") || \
        (crontab -l 2>/dev/null; echo "$cronline") | crontab - 2>/dev/null
    pause
}

# ════════════════════════════════════════════════════════════
#  UDP CUSTOM — KONSTANTA & UTILS
# ════════════════════════════════════════════════════════════
UC_DIR="/root/udp"
UC_CFG="$UC_DIR/config.json"
UC_BIN="$UC_DIR/udp-custom"
UC_SVC="/etc/systemd/system/udp-custom.service"
UC_UDB="$UC_DIR/users.db"       # format: username|password|expired|maxlogin|note
UC_MLDB="$UC_DIR/maxlogin.db"   # format: username|maxdevice
UC_INSTALL_URL="https://github.com/chanelog/max/raw/main/install-udp-custom.sh"

# Auto-detect lokasi binary & config UDP Custom
_uc_detect() {
    # Cari binary
    local bins=("/root/udp/udp-custom" "/usr/local/bin/udp-custom"
                "/usr/bin/udp-custom"  "/opt/udp-custom/udp-custom")
    for b in "${bins[@]}"; do
        [[ -f "$b" ]] && { UC_BIN="$b"; break; }
    done
    # Cari config.json
    local cfgs=("/root/udp/config.json" "/etc/udp-custom/config.json"
                "/usr/local/etc/udp-custom/config.json" "/opt/udp-custom/config.json")
    for c in "${cfgs[@]}"; do
        [[ -f "$c" ]] && { UC_CFG="$c"; UC_DIR="$(dirname "$c")"; break; }
    done
    UC_UDB="$UC_DIR/users.db"
    UC_MLDB="$UC_DIR/maxlogin.db"
}
_uc_detect   # jalankan deteksi saat script load

uc_is_installed() {
    # Cukup cek: service ada ATAU binary ada ATAU config ada
    systemctl list-units --all 2>/dev/null | grep -q "udp-custom" && return 0
    [[ -f "$UC_BIN" ]] && return 0
    [[ -f "$UC_CFG" ]] && return 0
    # Coba sekali lagi detect ulang sebelum menyerah
    _uc_detect
    [[ -f "$UC_BIN" || -f "$UC_CFG" ]] && return 0
    return 1
}
uc_is_up()        { systemctl is-active --quiet udp-custom 2>/dev/null; }
uc_get_port()     { grep -o '"listen":":[0-9]*"\|"listen": *":[0-9]*"' "$UC_CFG" 2>/dev/null | grep -o '[0-9]*' | head -1 || echo "36712"; }
uc_total_user()   { [[ -f "$UC_UDB" ]] && grep -c '' "$UC_UDB" 2>/dev/null || echo 0; }
uc_exp_count() {
    local t; t=$(date +%Y-%m-%d)
    [[ -f "$UC_UDB" ]] && awk -F'|' -v d="$t" '$3<d{c++}END{print c+0}' "$UC_UDB" || echo 0
}

uc_get_maxlogin() { grep "^${1}|" "$UC_MLDB" 2>/dev/null | cut -d'|' -f2; }
uc_set_maxlogin() {
    mkdir -p "$UC_DIR"
    sed -i "/^${1}|/d" "$UC_MLDB" 2>/dev/null
    echo "${1}|${2}" >> "$UC_MLDB"
}
uc_del_maxlogin() { sed -i "/^${1}|/d" "$UC_MLDB" 2>/dev/null; }

# Reload password list ke config.json UDP Custom
uc_reload_pw() {
    [[ ! -f "$UC_UDB" || ! -f "$UC_CFG" ]] && return
    local pws=()
    while IFS='|' read -r _ pw _ _ _; do
        [[ -n "$pw" ]] && pws+=("\"$pw\"")
    done < "$UC_UDB"
    local pwl; pwl=$(IFS=','; echo "${pws[*]}")
    python3 - <<PYEOF 2>/dev/null
import json
with open('$UC_CFG') as f: c = json.load(f)
c.setdefault('auth', {})['config'] = [${pwl:-""}]
with open('$UC_CFG', 'w') as f: json.dump(c, f, indent=2)
PYEOF
    systemctl restart udp-custom &>/dev/null
}

# Tampilkan box info akun UDP Custom
uc_show_akun_box() {
    local u="$1" p="$2" ip="$3" port="$4" exp="$5" maxl="$6" note="${7:--}"
    local now_ts; now_ts=$(date +%s)
    local exp_ts; exp_ts=$(date -d "${exp} 23:59:59" +%s 2>/dev/null || echo 0)
    local sisa_detik=$(( exp_ts - now_ts ))
    local sisa_str
    if [[ $sisa_detik -le 0 ]]; then
        sisa_str="${LR}Expired${NC}"
    else
        local sd=$(( sisa_detik / 86400 ))
        local sj=$(( (sisa_detik % 86400) / 3600 ))
        local sm=$(( (sisa_detik % 3600) / 60 ))
        if   [[ $sd -gt 0 ]]; then sisa_str="${LG}${sd} hari ${sj} jam lagi${NC}"
        elif [[ $sj -gt 0 ]]; then sisa_str="${Y}${sj} jam ${sm} menit lagi${NC}"
        else                        sisa_str="${LR}${sm} menit lagi${NC}"
        fi
    fi
    echo ""
    echo -e "  ${LG}✅ Akun UDP Custom${NC}"
    echo -e "  ${A1}┌──────────────────────────────────────────────────${NC}"
    printf  "  ${A1}│${NC} 👤 ${DIM}Username${NC}  : ${BLD}${W}%s${NC}\n" "$u"
    printf  "  ${A1}│${NC} 🔑 ${DIM}Password${NC}  : ${BLD}${A3}%s${NC}\n" "$p"
    echo -e "  ${A1}├──────────────────────────────────────────────────${NC}"
    printf  "  ${A1}│${NC} 🖥  ${DIM}IP Publik${NC}  : ${LG}%s${NC}\n" "$ip"
    printf  "  ${A1}│${NC} 🔌 ${DIM}Port     ${NC}  : ${Y}%s${NC}\n" "$port"
    echo -e "  ${A1}├──────────────────────────────────────────────────${NC}"
    printf  "  ${A1}│${NC} 🔒 ${DIM}MaxLogin${NC}   : ${Y}%s device${NC}\n" "$maxl"
    printf  "  ${A1}│${NC} 📅 ${DIM}Expired ${NC}   : ${Y}%s${NC}\n" "$exp"
    printf  "  ${A1}│${NC} ⏳ ${DIM}Sisa    ${NC}   : %b\n" "$sisa_str"
    [[ "$note" != "-" ]] && \
    printf  "  ${A1}│${NC} 📝 ${DIM}Pembeli ${NC}   : ${W}%s${NC}\n" "$note"
    echo -e "  ${A1}└──────────────────────────────────────────────────${NC}"
    echo ""
}

# ════════════════════════════════════════════════════════════
#  UDP CUSTOM — FUNGSI USER
# ════════════════════════════════════════════════════════════
uc_add() {
    show_header
    _top; _btn "  ${IT}${AL}➕  TAMBAH AKUN UDP CUSTOM${NC}"; _bot; echo ""

    _uc_detect
    if ! uc_is_installed; then
        err "UDP Custom belum diinstall!"
        echo -ne "  ${A3}Install sekarang?${NC} [y/N]: "; read -r yn
        [[ "${yn,,}" == "y" ]] && uc_install || { pause; return; }
        _uc_detect
    fi

    mkdir -p "$UC_DIR"; touch "$UC_UDB" "$UC_MLDB"

    echo -ne "  ${A3}Username${NC}               : "; read -r un
    [[ -z "$un" ]] && { err "Username kosong!"; pause; return; }
    grep -q "^${un}|" "$UC_UDB" 2>/dev/null && { err "Username sudah ada!"; pause; return; }

    echo -ne "  ${A3}Password${NC} [auto]         : "; read -r up
    [[ -z "$up" ]] && up=$(rand_pass)

    echo -ne "  ${A3}Masa aktif (hari)${NC} [30]  : "; read -r ud
    [[ -z "$ud" || ! "$ud" =~ ^[0-9]+$ ]] && ud=30
    local ue; ue=$(date -d "+${ud} days" +"%Y-%m-%d")

    echo -ne "  ${A3}Max Login Device${NC} [2]    : "; read -r uml
    [[ -z "$uml" || ! "$uml" =~ ^[0-9]+$ ]] && uml=2

    echo -ne "  ${A3}Catatan / Nama Pembeli${NC}  : "; read -r note
    [[ -z "$note" ]] && note="-"

    echo "${un}|${up}|${ue}|${uml}|${note}" >> "$UC_UDB"
    uc_set_maxlogin "$un" "$uml"
    uc_reload_pw

    local ip_pub; ip_pub=$(get_ip)
    local port;   port=$(uc_get_port)

    _tg_send "✅ <b>Akun Baru — UDP Custom</b>
┌──────────────────────────────────────────────────
│ 👤 <b>Username</b>  : <code>$un</code>
│ 🔑 <b>Password</b>  : <code>$up</code>
├──────────────────────────────────────────────────
│ 🖥 <b>IP Publik</b>  : <code>$ip_pub</code>
│ 🔌 <b>Port</b>      : <code>$port</code>
├──────────────────────────────────────────────────
│ 🔒 <b>MaxLogin</b>  : ${uml} device
│ 📅 <b>Expired</b>   : $ue
│ 📝 <b>Pembeli</b>   : $note
└──────────────────────────────────────────────────"

    uc_show_akun_box "$un" "$up" "$ip_pub" "$port" "$ue" "$uml" "$note"
    pause
}

uc_list() {
    show_header
    _top; _btn "  ${IT}${AL}📋  LIST AKUN UDP CUSTOM${NC}"; _bot; echo ""
    if [[ ! -s "$UC_UDB" ]]; then warn "Belum ada akun terdaftar."; pause; return; fi
    local today; today=$(date +"%Y-%m-%d")
    local now_ts; now_ts=$(date +%s)
    local n=1
    echo -e "  ${A1}${_DASH}${NC}"
    printf  "  ${BLD} %-2s  %-16s  %-12s  %-10s  %-10s  %-14s${NC}\n" \
        "#" "Username" "Password" "Expired" "MaxLogin" "Sisa Waktu"
    echo -e "  ${A1}${_DASH}${NC}"
    while IFS='|' read -r u p e ml _; do
        local sc sisa_str
        local exp_ts; exp_ts=$(date -d "${e} 23:59:59" +%s 2>/dev/null || echo 0)
        local sisa_detik=$(( exp_ts - now_ts ))
        if [[ $sisa_detik -le 0 ]]; then
            sc="$LR"; sisa_str="Expired"
        else
            sc="$LG"
            local sd=$(( sisa_detik / 86400 ))
            local sj=$(( (sisa_detik % 86400) / 3600 ))
            [[ $sd -gt 0 ]] && sisa_str="${sd}h ${sj}j" || sisa_str="${sj}j lagi"
        fi
        printf "   ${DIM}%-2s${NC}  ${W}%-16s${NC}  ${A3}%-12s${NC}  ${Y}%-10s${NC}  ${Y}%-10s${NC}  ${sc}%-14s${NC}\n" \
            "$n" "$u" "$p" "$e" "${ml:-2} dev" "$sisa_str"
        ((n++))
    done < "$UC_UDB"
    echo -e "  ${A1}${_DASH}${NC}"
    echo ""
    echo -e "  ${DIM}  Total: $((n-1)) akun  │  Expired: $(uc_exp_count) akun${NC}"
    pause
}

uc_del() {
    show_header
    _top; _btn "  ${IT}${AL}🗑️   HAPUS AKUN UDP CUSTOM${NC}"; _bot; echo ""
    if [[ ! -s "$UC_UDB" ]]; then warn "Tidak ada akun."; pause; return; fi
    local n=1
    while IFS='|' read -r u _ e _ _; do
        printf "  ${DIM}%3s.${NC}  ${W}%-22s${NC}  ${DIM}exp: %s${NC}\n" "$n" "$u" "$e"; ((n++))
    done < "$UC_UDB"
    echo ""
    echo -ne "  ${A3}Username yang dihapus${NC}: "; read -r du
    grep -q "^${du}|" "$UC_UDB" 2>/dev/null || { err "User tidak ditemukan!"; pause; return; }
    sed -i "/^${du}|/d" "$UC_UDB"
    uc_del_maxlogin "$du"
    uc_reload_pw
    _tg_send "🗑 <b>Akun UDP Custom Dihapus</b> : <code>$du</code>"
    ok "Akun '${W}$du${NC}' berhasil dihapus."
    pause
}

uc_renew() {
    show_header
    _top; _btn "  ${IT}${AL}🔁  PERPANJANG AKUN UDP CUSTOM${NC}"; _bot; echo ""
    if [[ ! -s "$UC_UDB" ]]; then warn "Tidak ada akun."; pause; return; fi
    local n=1
    while IFS='|' read -r u _ e _ _; do
        printf "  ${DIM}%3s.${NC}  ${W}%-22s${NC}  ${DIM}exp: %s${NC}\n" "$n" "$u" "$e"; ((n++))
    done < "$UC_UDB"
    echo ""
    echo -ne "  ${A3}Username${NC}    : "; read -r ru
    grep -q "^${ru}|" "$UC_UDB" 2>/dev/null || { err "User tidak ditemukan!"; pause; return; }
    echo -ne "  ${A3}Tambah hari${NC} : "; read -r rd; [[ -z "$rd" || ! "$rd" =~ ^[0-9]+$ ]] && rd=30
    local ce; ce=$(grep "^${ru}|" "$UC_UDB" | cut -d'|' -f3)
    local today; today=$(date +%Y-%m-%d)
    [[ "$ce" < "$today" ]] && ce="$today"
    local ne; ne=$(date -d "${ce} +${rd} days" +"%Y-%m-%d")
    sed -i "s/^\(${ru}|[^|]*|\)[^|]*/\1${ne}/" "$UC_UDB"
    _tg_send "🔁 <b>Akun UDP Custom Diperpanjang</b>
👤 User     : <code>$ru</code>
📅 Expired  : <b>$ne</b>  (+${rd} hari)"
    echo ""
    echo -e "  ${A1}${_DASH}${NC}"
    echo -e "  ${LG}✔  Akun berhasil diperpanjang!${NC}"
    echo -e "  ${A1}${_DASH}${NC}"
    printf  "  ${DIM} Username :${NC}  ${W}%s${NC}\n" "$ru"
    printf  "  ${DIM} Expired  :${NC}  ${Y}%s${NC}\n" "$ne"
    printf  "  ${DIM} Tambahan :${NC}  ${LG}+%s hari${NC}\n" "$rd"
    echo -e "  ${A1}${_DASH}${NC}"
    pause
}

uc_maxlogin() {
    show_header
    _top; _btn "  ${IT}${AL}🔒  SET MAXLOGIN UDP CUSTOM${NC}"; _bot; echo ""
    if [[ ! -s "$UC_UDB" ]]; then warn "Tidak ada akun."; pause; return; fi
    local n=1
    while IFS='|' read -r u _ _ ml _; do
        local cur_ml; cur_ml=$(uc_get_maxlogin "$u"); [[ -z "$cur_ml" ]] && cur_ml="${ml:-2}"
        printf "  ${DIM}%3s.${NC}  ${W}%-22s${NC}  ${DIM}maxlogin: ${Y}%s${NC}\n" "$n" "$u" "$cur_ml dev"
        ((n++))
    done < "$UC_UDB"
    echo ""
    echo -ne "  ${A3}Username${NC}       : "; read -r mu
    grep -q "^${mu}|" "$UC_UDB" 2>/dev/null || { err "User tidak ditemukan!"; pause; return; }
    local cur; cur=$(uc_get_maxlogin "$mu"); [[ -z "$cur" ]] && cur=2
    echo -e "  MaxLogin saat ini : ${Y}$cur device${NC}"
    echo -ne "  ${A3}MaxLogin baru${NC}  : "; read -r nml
    [[ -z "$nml" || ! "$nml" =~ ^[0-9]+$ ]] && { err "Input tidak valid!"; pause; return; }
    uc_set_maxlogin "$mu" "$nml"
    # Update juga di UDB kolom ke-4
    sed -i "s/^\(${mu}|[^|]*|[^|]*|\)[^|]*/\1${nml}/" "$UC_UDB"
    echo ""
    echo -e "  ${A1}${_DASH}${NC}"
    echo -e "  ${LG}✔  MaxLogin berhasil diatur!${NC}"
    echo -e "  ${A1}${_DASH}${NC}"
    printf  "  ${DIM} Username :${NC}  ${W}%s${NC}\n" "$mu"
    printf  "  ${DIM} Max Dev  :${NC}  ${Y}%s device${NC}\n" "$nml"
    echo -e "  ${A1}${_DASH}${NC}"
    pause
}

uc_clean() {
    show_header
    _top; _btn "  ${IT}${AL}🧹  HAPUS AKUN EXPIRED UDP CUSTOM${NC}"; _bot; echo ""
    local today; today=$(date +"%Y-%m-%d"); local cnt=0
    while IFS='|' read -r u _ e _ _; do
        if [[ "$e" < "$today" ]]; then
            sed -i "/^${u}|/d" "$UC_UDB"
            uc_del_maxlogin "$u"
            ok "Dihapus: ${W}$u${NC}  ${DIM}(exp: $e)${NC}"; ((cnt++))
        fi
    done < <(cat "$UC_UDB" 2>/dev/null)
    echo ""
    [[ $cnt -gt 0 ]] && { uc_reload_pw; ok "Total ${W}$cnt${NC} akun expired dihapus."; } \
                     || inf "Tidak ada akun expired."
    pause
}

uc_install() {
    show_header
    _top; _btn "  ${IT}${AL}🚀  INSTALL UDP CUSTOM${NC}"; _bot; echo ""
    inf "Mendownload & menjalankan installer UDP Custom..."
    echo ""
    if ! bash <(curl -Ls "$UC_INSTALL_URL" 2>/dev/null); then
        err "Gagal menjalankan installer! Periksa koneksi internet."
        pause; return
    fi
    ok "UDP Custom berhasil diinstall!"
    mkdir -p "$UC_DIR"
    touch "$UC_UDB" "$UC_MLDB"
    pause
}

uc_status() {
    show_header
    _top; _btn "  ${IT}${AL}🖥️   STATUS UDP CUSTOM${NC}"; _bot; echo ""
    local port; port=$(uc_get_port)
    local ip;   ip=$(get_ip)
    local status_str
    if uc_is_up; then
        status_str="${LG}● Aktif (running)${NC}"
    else
        status_str="${LR}● Tidak aktif (stopped)${NC}"
    fi
    echo ""
    echo -e "  ${A1}${_DASH}${NC}"
    printf  "  ${DIM} Status    :${NC}  %b\n" "$status_str"
    printf  "  ${DIM} Port      :${NC}  ${Y}%s${NC}\n" "$port"
    printf  "  ${DIM} IP Publik :${NC}  ${W}%s${NC}\n" "$ip"
    printf  "  ${DIM} Total Akun:${NC}  ${A3}%s akun${NC}\n" "$(uc_total_user)"
    printf  "  ${DIM} Expired   :${NC}  ${LR}%s akun${NC}\n" "$(uc_exp_count)"
    echo -e "  ${A1}${_DASH}${NC}"
    echo ""
    systemctl status udp-custom --no-pager -l 2>/dev/null | tail -20
    pause
}

# ════════════════════════════════════════════════════════════
#  UDP CUSTOM — SUB MENU
# ════════════════════════════════════════════════════════════
menu_udp_custom() {
    while true; do
        show_header
        local _uc_badge
        if uc_is_installed; then
            uc_is_up \
                && _uc_badge="${LG}[ON ✔]${NC}" \
                || _uc_badge="${LR}[OFF ✘]${NC}"
        else
            _uc_badge="${Y}[Belum Install]${NC}"
        fi
        _top
        _btn "  ${IT}${AL}  🌐  UDP CUSTOM${NC}             ${_uc_badge}"
        _sep; _btn "  ${A2}[1]${NC}  ➕  Tambah Akun"
        _sep; _btn "  ${A2}[2]${NC}  📋  List Akun"
        _sep; _btn "  ${A2}[3]${NC}  🗑️   Hapus Akun"
        _sep; _btn "  ${A2}[4]${NC}  🔁  Perpanjang Akun"
        _sep; _btn "  ${A2}[5]${NC}  🔒  Set MaxLogin"
        _sep; _btn "  ${A2}[6]${NC}  🧹  Hapus Akun Expired"
        _sep; _btn "  ${A2}[7]${NC}  🖥️   Status Service"
        _sep; _btn "  ${A2}[8]${NC}  ▶️   Start UDP Custom"
        _sep; _btn "  ${A2}[9]${NC}  ⏹️   Stop UDP Custom"
        _sep; _btn "  ${A2}[R]${NC}  🔄  Restart UDP Custom"
        _sep; _btn "  ${A2}[I]${NC}  🚀  Install UDP Custom"
        _sep; _btn "  ${LR}[0]${NC}  ◀   Kembali"
        _bot; echo ""
        printf "  ${DIM}Akun: ${A3}%s${NC}${DIM}  │  Expired: ${LR}%s${NC}\n" \
            "$(uc_total_user)" "$(uc_exp_count)"
        echo ""
        echo -ne "  ${A1}›${NC} "; read -r ch
        case ${ch,,} in
            1) uc_add ;;
            2) uc_list ;;
            3) uc_del ;;
            4) uc_renew ;;
            5) uc_maxlogin ;;
            6) uc_clean ;;
            7) uc_status ;;
            8) systemctl start  udp-custom; sleep 1
               uc_is_up && ok "UDP Custom dijalankan!" || err "Gagal start!"; pause ;;
            9) systemctl stop   udp-custom; ok "UDP Custom dihentikan."; pause ;;
            r) systemctl restart udp-custom; sleep 1
               uc_is_up && ok "Restart berhasil!" || err "Gagal restart!"; pause ;;
            i) uc_install ;;
            0) break ;;
            *) warn "Pilihan tidak valid!"; sleep 1 ;;
        esac
    done
}

# ════════════════════════════════════════════════════════════
#  SUB MENUS
# ════════════════════════════════════════════════════════════
menu_akun() {
    while true; do
        show_header
        _top
        _btn "  ${IT}${AL}  👤  KELOLA AKUN USER${NC}"
        _sep; _btn "  ${A2}[1]${NC}  ➕  Tambah Akun Baru"
        _sep; _btn "  ${A2}[2]${NC}  📋  List Semua Akun"
        _sep; _btn "  ${A2}[3]${NC}  🔍  Detail Akun"
        _sep; _btn "  ${A2}[4]${NC}  🗑️   Hapus Akun"
        _sep; _btn "  ${A2}[5]${NC}  🔁  Perpanjang Akun"
        _sep; _btn "  ${A2}[6]${NC}  🔑  Ganti Password"
        _sep; _btn "  ${A2}[7]${NC}  🎁  Buat Akun Trial"
        _sep; _btn "  ${A2}[8]${NC}  🧹  Hapus Akun Expired"
        _sep; _btn "  ${A2}[9]${NC}  🔒  Set MaxLogin Device"
        _sep; _btn "  ${LR}[0]${NC}  ◀   Kembali"
        _bot; echo ""
        echo -ne "  ${A1}›${NC} "; read -r ch
        case $ch in
            1) u_add ;;  2) u_list ;; 3) u_info ;;
            4) u_del ;;  5) u_renew ;; 6) u_chpass ;;
            7) u_trial ;; 8) u_clean ;; 9) u_maxlogin ;;
            0) break ;; *) warn "Pilihan tidak valid!"; sleep 1 ;;
        esac
    done
}

menu_jualan() {
    while true; do
        show_header
        [[ -f "$STRF" ]] && source "$STRF" 2>/dev/null
        _top
        _btn "  ${IT}${AL}  🛒  MENU JUALAN${NC}"
        _sep; _btn "  ${A2}[1]${NC}  📨  Template Pesan Akun"
        _sep; _btn "  ${A2}[2]${NC}  📤  Kirim Akun via Telegram"
        _sep; _btn "  ${A2}[3]${NC}  ⚙️   Pengaturan Toko"
        _sep; _btn "  ${LR}[0]${NC}  ◀   Kembali"
        _bot; echo ""
        printf "  ${DIM}Brand: ${AL}%-20s${DIM}  TG: @%s${NC}\n" "${BRAND:-OGH-ZIV}" "${ADMIN_TG:--}"
        echo ""
        echo -ne "  ${A1}›${NC} "; read -r ch
        case $ch in
            1) t_akun ;; 2) tg_kirim_akun ;; 3) set_store ;;
            0) break ;; *) warn "Pilihan tidak valid!"; sleep 1 ;;
        esac
    done
}

menu_telegram() {
    while true; do
        show_header
        local bstat="${LR}Belum dikonfigurasi${NC}"
        [[ -f "$BOTF" ]] && { source "$BOTF" 2>/dev/null
            [[ -n "$BOT_TOKEN" ]] && bstat="${LG}@${BOT_NAME:-?}${NC}"; }
        _top
        _btn "  ${IT}${AL}  🤖  TELEGRAM BOT${NC}"
        _sep
        printf "  ${DIM}Status :${NC} %b\n" "$bstat"
        _sep; _btn "  ${A2}[1]${NC}  🔧  Setup / Konfigurasi Bot"
        _sep; _btn "  ${A2}[2]${NC}  📡  Cek Status Bot"
        _sep; _btn "  ${A2}[3]${NC}  📤  Kirim Akun ke Telegram"
        _sep; _btn "  ${A2}[4]${NC}  📢  Broadcast Pesan"
        _sep; _btn "  ${A2}[5]${NC}  📖  Panduan Buat Bot"
        _sep; _btn "  ${LR}[0]${NC}  ◀   Kembali"
        _bot; echo ""
        echo -ne "  ${A1}›${NC} "; read -r ch
        case $ch in
            1) tg_setup ;; 2) tg_status ;; 3) tg_kirim_akun ;;
            4) tg_broadcast ;; 5) tg_guide ;;
            0) break ;; *) warn "Pilihan tidak valid!"; sleep 1 ;;
        esac
    done
}

menu_service() {
    while true; do
        show_header
        # Cek status BBR untuk ditampilkan di menu
        local _bbr_cc; _bbr_cc=$(sysctl -n net.ipv4.tcp_congestion_control 2>/dev/null || echo "?")
        local _bbr_badge
        if [[ "$_bbr_cc" == "bbr" ]]; then
            _bbr_badge="${LG}[BBR ✔]${NC}"
        else
            _bbr_badge="${LR}[BBR ✘]${NC}"
        fi
        _top
        _btn "  ${IT}${AL}  ⚙️   MANAJEMEN SERVICE${NC}"
        _sep; _btn "  ${A2}[1]${NC}  🖥️   Status Service"
        _sep; _btn "  ${A2}[2]${NC}  ▶️   Start ZiVPN"
        _sep; _btn "  ${A2}[3]${NC}  ⏹️   Stop ZiVPN"
        _sep; _btn "  ${A2}[4]${NC}  🔄  Restart ZiVPN"
        _sep; _btn "  ${A2}[5]${NC}  📄  Lihat Log"
        _sep; _btn "  ${A2}[6]${NC}  🔧  Ganti Port"
        _sep; _btn "  ${A2}[7]${NC}  🌐  Manajemen Domain"
        _sep; _btn "  ${A2}[8]${NC}  💾  Backup Data"
        _sep; _btn "  ${A2}[9]${NC}  ♻️   Restore Data"
        _sep; _btn "  ${A2}[B]${NC}  🚀  Cek Status BBR         ${_bbr_badge}"
        _sep; _btn "  ${LR}[0]${NC}  ◀   Kembali"
        _bot; echo ""
        echo -ne "  ${A1}›${NC} "; read -r ch
        case ${ch,,} in
            1) svc_status ;;
            2) systemctl start zivpn;   ok "ZiVPN dijalankan.";  pause ;;
            3) systemctl stop zivpn;    ok "ZiVPN dihentikan.";  pause ;;
            4) systemctl restart zivpn; sleep 1
               is_up && ok "Restart berhasil!" || err "Gagal restart!"; pause ;;
            5) svc_log ;;
            6) svc_port ;;
            7) menu_domain ;;
            8) svc_backup ;;
            9) svc_restore ;;
            b) svc_bbr ;;
            0) break ;; *) warn "Pilihan tidak valid!"; sleep 1 ;;
        esac
    done
}

# ════════════════════════════════════════════════════════════
#  CEK & UPDATE VERSI
# ════════════════════════════════════════════════════════════
cek_update() {
    show_header
    _top; _btn "  ${IT}${AL}🔄  CEK VERSI / UPDATE${NC}"; _bot; echo ""

    inf "Mengecek versi terbaru..."
    local remote_ver
    remote_ver=$(curl -s --max-time 10 "$VERSION_URL" 2>/dev/null | tr -d '[:space:]')
    [[ -z "$remote_ver" ]] && remote_ver=$(wget -qO- --timeout=10 "$VERSION_URL" 2>/dev/null | tr -d '[:space:]')

    echo ""
    _top
    printf "  ${DIM}Versi terpasang ${NC}: ${Y}%s${NC}\n" "$SCRIPT_VERSION"

    if [[ -z "$remote_ver" ]]; then
        printf "  ${DIM}Versi terbaru   ${NC}: ${LR}Gagal cek (tidak ada koneksi)${NC}\n"
        _bot; echo ""
        warn "Pastikan VPS terhubung ke internet, lalu coba lagi."
        pause; return
    fi

    printf "  ${DIM}Versi terbaru   ${NC}: ${LG}%s${NC}\n" "$remote_ver"
    _bot; echo ""

    if [[ "$remote_ver" == "$SCRIPT_VERSION" ]]; then
        ok "Script sudah versi terbaru! Tidak perlu update."
        pause; return
    fi

    # Ada versi baru
    echo -e "  ${A4}⚡  Update tersedia: ${Y}${SCRIPT_VERSION}${NC} ${A4}→${NC} ${LG}${remote_ver}${NC}"
    echo ""
    echo -ne "  ${A3}Update sekarang? [y/N]${NC}: "; read -r konfirm
    [[ "${konfirm,,}" != "y" ]] && { warn "Update dibatalkan."; pause; return; }

    do_update
}

do_update() {
    echo ""
    inf "Mendownload script versi terbaru..."

    local tmp_file; tmp_file=$(mktemp /tmp/ogh-ziv-update-XXXXXX.sh)

    if curl -Ls --max-time 30 "$SCRIPT_URL" -o "$tmp_file" 2>/dev/null && [[ -s "$tmp_file" ]]; then
        ok "Download selesai"
    elif wget -qO "$tmp_file" --timeout=30 "$SCRIPT_URL" 2>/dev/null && [[ -s "$tmp_file" ]]; then
        ok "Download selesai"
    else
        rm -f "$tmp_file"
        err "Gagal download! Periksa koneksi internet VPS."
        pause; return
    fi

    # Validasi: pastikan file hasil download adalah bash script yang valid
    if ! bash -n "$tmp_file" 2>/dev/null; then
        rm -f "$tmp_file"
        err "File update tidak valid (corrupt). Update dibatalkan."
        pause; return
    fi

    inf "Menerapkan update..."
    cp "$tmp_file" /usr/local/bin/ogh-ziv
    chmod +x /usr/local/bin/ogh-ziv
    ln -sf /usr/local/bin/ogh-ziv /usr/local/bin/menu 2>/dev/null
    rm -f "$tmp_file"

    ok "Update berhasil! Script diperbarui ke versi terbaru."
    echo ""
    echo -e "  ${DIM}╰─ Ketik ${W}menu${DIM} untuk membuka panel yang sudah diupdate.${NC}"
    echo ""
    pause

    # Restart dengan script baru
    exec bash /usr/local/bin/ogh-ziv
}

# ════════════════════════════════════════════════════════════
#  MENU UTAMA  — 2-Column Style (no outer border)
# ════════════════════════════════════════════════════════════
main_menu() {
    # _r2: cetak baris 2 kolom, separator │ di tengah, tanpa border luar
    _r2() {
        local CL="$1" TL="$2" CR="$3" TR="$4"
        printf "  ${CL}%-26b${NC} ${A1}│${NC}  ${CR}%b${NC}\n" "$TL" "$TR"
    }

    while true; do
        show_header

        # ── Judul ──────────────────────────────────────────────────
        echo -e "  ${A1}${_DASH}${NC}"
        echo -e "  ${A1}+------------ ${BLD}${AL}OGH-ZIV PREMIUM PANEL${NC} ${A1}------------+${NC}"
        echo -e "  ${A1}${_DASH}${NC}"
        echo ""

        # ── 2-Column Grid ──────────────────────────────────────────────────
        _r2 "${A2}" "[1]  👤  Kelola Akun"      "${A2}" "[2]  ⚙   Service"
        echo -e "  ${A1}${_DASH}${NC}"
        _r2 "${A2}" "[3]  🤖  Telegram Bot"     "${A2}" "[4]  🛒  Menu Jualan"
        echo -e "  ${A1}${_DASH}${NC}"
        _r2 "${A2}" "[5]  📊  Bandwidth"        "${A2}" "[6]  🔄  Restart"
        echo -e "  ${A1}${_DASH}${NC}"
        _r2 "${A2}" "[7]  🚀  Install"          "${A2}" "[8]  🌐  Domain"
        echo -e "  ${A1}${_DASH}${NC}"
        # Badge status UDP Custom
        local _uc_main_badge
        if ! uc_is_installed; then
            _uc_main_badge="${Y}Belum Install${NC}"
        elif uc_is_up; then
            _uc_main_badge="${LG}● Running${NC}"
        else
            _uc_main_badge="${LR}○ Stopped${NC}"
        fi
        _r2 "${A2}" "[9]  🎨  Tema"             "${A2}" "[C]  🌐  UDP Custom"
        printf "  ${A1}│${NC}  %-31s${A1}│${NC}  UDP: %b\n" "" "$_uc_main_badge"
        echo -e "  ${A1}${_DASH}${NC}"
        _r2 "${A2}" "[U]  🔄  Cek Update"       "${LR}" "[E]  🗑   Uninstall"
        echo -e "  ${A1}${_DASH}${NC}"
        _r2 "${A4}" "[0]  ✗   Keluar"           ""      ""
        echo -e "  ${A1}${_DASH}${NC}"
        echo -e "  ${DIM}                   OGH-ZIV v${SCRIPT_VERSION}${NC}"

        echo ""
        echo -ne "  ${A1}›${NC} Pilih menu: "; read -r ch
        case ${ch,,} in
            1) menu_akun ;;
            2) menu_service ;;
            3) menu_telegram ;;
            4) menu_jualan ;;
            5) svc_bandwidth ;;
            6) systemctl restart zivpn; sleep 1
               is_up && ok "Service berhasil direstart!" || err "Gagal restart!"; pause ;;
            7) do_install ;;
            8) menu_domain ;;
            9) menu_tema ;;
            c) menu_udp_custom ;;
            u) cek_update ;;
            e) do_uninstall ;;
            0) echo -e "\n  ${IT}${AL}Sampai jumpa! — OGH-ZIV Premium${NC}\n"; exit 0 ;;
            *) warn "Pilihan tidak valid!"; sleep 1 ;;
        esac
    done
}

# ════════════════════════════════════════════════════════════
#  SETUP COMMAND 'menu'
# ════════════════════════════════════════════════════════════
setup_menu_cmd() {
    # Daftarkan alias saja — tidak download ulang script
    # Download hanya dilakukan saat install pertama atau lewat fitur [U] Cek Update

    # Buat symlink menu → ogh-ziv jika belum ada
    if [[ ! -f /usr/local/bin/ogh-ziv ]]; then
        cp "$0" /usr/local/bin/ogh-ziv 2>/dev/null
        chmod +x /usr/local/bin/ogh-ziv 2>/dev/null
    fi
    ln -sf /usr/local/bin/ogh-ziv /usr/local/bin/menu 2>/dev/null
    chmod +x /usr/local/bin/menu 2>/dev/null

    # Tambah alias ke ~/.bashrc
    sed -i '/alias menu=/d'  ~/.bashrc 2>/dev/null
    sed -i '/alias zivpn=/d' ~/.bashrc 2>/dev/null
    echo "alias menu='bash /usr/local/bin/ogh-ziv'"  >> ~/.bashrc
    echo "alias zivpn='bash /usr/local/bin/ogh-ziv'" >> ~/.bashrc

    # Tambah ke /root/.profile
    sed -i '/alias menu=/d' /root/.profile 2>/dev/null
    echo "alias menu='bash /usr/local/bin/ogh-ziv'" >> /root/.profile

    # Tambah ke /etc/profile.d/ supaya aktif global
    cat > /etc/profile.d/ogh-ziv.sh << 'PROFEOF'
#!/bin/bash
alias menu='bash /usr/local/bin/ogh-ziv'
alias zivpn='bash /usr/local/bin/ogh-ziv'
PROFEOF
    chmod +x /etc/profile.d/ogh-ziv.sh 2>/dev/null
}

# ════════════════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════════════════
check_os
check_root
mkdir -p "$DIR"
load_theme

# Handle CLI flags
if [[ "${1:-}" == "--check-maxlogin" ]]; then
    check_maxlogin_all
    exit 0
fi

# Setup menu command (install ke /usr/local/bin supaya ketik 'menu' langsung jalan)
setup_menu_cmd 2>/dev/null

# Langsung masuk menu — tidak perlu ketik 'menu' lagi setelah script dijalankan
main_menu
exit 0
