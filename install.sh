#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  GhostBox — One-command installer for Raspberry Pi Zero 2W
#  Usage: sudo bash install.sh
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'
YELLOW='\033[1;33m'; NC='\033[0m'; BOLD='\033[1m'

log()  { echo -e "${GREEN}[✓]${NC} $*"; }
info() { echo -e "${CYAN}[i]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
err()  { echo -e "${RED}[✗]${NC} $*"; exit 1; }

INSTALL_DIR="/opt/ghostbox"
SERVICE_USER="ghostbox"
PYTHON_MIN="3.10"

banner() {
cat << 'EOF'

  ██████╗ ██╗  ██╗ ██████╗ ███████╗████████╗██████╗  ██████╗ ██╗  ██╗
 ██╔════╝ ██║  ██║██╔═══██╗██╔════╝╚══██╔══╝██╔══██╗██╔═══██╗╚██╗██╔╝
 ██║  ███╗███████║██║   ██║███████╗   ██║   ██████╔╝██║   ██║ ╚███╔╝
 ██║   ██║██╔══██║██║   ██║╚════██║   ██║   ██╔══██╗██║   ██║ ██╔██╗
 ╚██████╔╝██║  ██║╚██████╔╝███████║   ██║   ██████╔╝╚██████╔╝██╔╝ ██╗
  ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝   ╚═╝   ╚═════╝  ╚═════╝ ╚═╝  ╚═╝
           Security Research Toolkit for Raspberry Pi Zero 2W
           ⚠  FOR AUTHORIZED USE ONLY  ⚠

EOF
}

check_root() {
  [[ $EUID -eq 0 ]] || err "Run as root: sudo bash install.sh"
}

check_pi() {
  if grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
    log "Detected: $(cat /proc/device-tree/model)"
  else
    warn "Not detected as Raspberry Pi — continuing anyway"
  fi
}

install_system_deps() {
  info "Updating package lists..."
  apt-get update -qq

  info "Installing system dependencies..."
  apt-get install -y -qq \
    python3 python3-pip python3-venv \
    hostapd dnsmasq \
    bluez bluetooth \
    wireless-tools iw \
    git curl \
    libglib2.0-dev

  # Enable services but don't start yet
  systemctl unmask hostapd 2>/dev/null || true
  systemctl disable hostapd dnsmasq 2>/dev/null || true

  log "System dependencies installed"
}

enable_dwc2() {
  info "Enabling USB OTG (dwc2)..."

  # /boot/config.txt
  if ! grep -q "dtoverlay=dwc2" /boot/config.txt 2>/dev/null; then
    echo "dtoverlay=dwc2" >> /boot/config.txt
    log "Added dtoverlay=dwc2 to /boot/config.txt"
  fi

  # /boot/cmdline.txt — add modules-load after rootwait
  if ! grep -q "modules-load=dwc2,libcomposite" /boot/cmdline.txt 2>/dev/null; then
    sed -i 's/rootwait/rootwait modules-load=dwc2,libcomposite/' /boot/cmdline.txt
    log "Added dwc2,libcomposite to /boot/cmdline.txt"
  fi

  # Load modules now (best-effort)
  modprobe dwc2 2>/dev/null || warn "dwc2 not loaded (reboot required)"
  modprobe libcomposite 2>/dev/null || warn "libcomposite not loaded (reboot required)"
}

install_ghostbox() {
  info "Installing GhostBox to ${INSTALL_DIR}..."

  # Create user
  id -u "$SERVICE_USER" &>/dev/null || useradd -r -s /bin/false "$SERVICE_USER"

  # Copy files
  mkdir -p "$INSTALL_DIR"
  cp -r "$(dirname "$(realpath "$0")")/." "$INSTALL_DIR/"
  chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"
  chmod +x "$INSTALL_DIR/install.sh"

  # Python venv
  python3 -m venv "$INSTALL_DIR/.venv"
  "$INSTALL_DIR/.venv/bin/pip" install --quiet --upgrade pip
  "$INSTALL_DIR/.venv/bin/pip" install --quiet -r "$INSTALL_DIR/requirements.txt"

  log "GhostBox installed to $INSTALL_DIR"
}

create_service() {
  info "Creating systemd service..."
  cat > /etc/systemd/system/ghostbox.service << EOF
[Unit]
Description=GhostBox Security Toolkit
After=network.target bluetooth.target

[Service]
Type=simple
User=root
WorkingDirectory=${INSTALL_DIR}
ExecStart=${INSTALL_DIR}/.venv/bin/python -m ghostbox
Restart=on-failure
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

  systemctl daemon-reload
  systemctl enable ghostbox
  log "Service created and enabled"
}

print_success() {
  local ip
  ip=$(hostname -I | awk '{print $1}')
  echo ""
  echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo -e "${GREEN}${BOLD}  GhostBox installed successfully!${NC}"
  echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo ""
  echo -e "  Dashboard: ${CYAN}http://${ip}:8080${NC}"
  echo -e "  Start:     ${CYAN}systemctl start ghostbox${NC}"
  echo -e "  Logs:      ${CYAN}journalctl -u ghostbox -f${NC}"
  echo ""
  echo -e "${YELLOW}  ⚠ Reboot required for USB OTG changes${NC}"
  echo -e "${YELLOW}  ⚠ For authorized security testing ONLY${NC}"
  echo ""
}

main() {
  banner
  check_root
  check_pi
  install_system_deps
  enable_dwc2
  install_ghostbox
  create_service
  print_success
}

main "$@"
