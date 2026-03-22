# 👻 GhostBox

> Modular security research toolkit for **Raspberry Pi Zero 2W**

[![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)
[![Platform](https://img.shields.io/badge/Platform-RPi_Zero_2W-red?style=flat-square&logo=raspberry-pi)](https://www.raspberrypi.com)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)
[![Stars](https://img.shields.io/github/stars/yourusername/ghostbox?style=flat-square)](https://github.com/yourusername/ghostbox)

GhostBox transforms a **Raspberry Pi Zero 2W** into a portable security research platform with a real-time web dashboard. Built with Python 3.10+ and FastAPI.

> ⚠️ **FOR AUTHORIZED SECURITY TESTING ONLY** — Use only on networks and devices you own or have explicit permission to test. The authors assume no liability for misuse.

---

---

## Features

| Module | Description | Hardware Required |
|--------|-------------|------------------|
| 🔌 **USB Arsenal** | DuckyScript v1 HID injection engine + USB gadget | Built-in USB OTG |
| 📡 **WiFi Scanner** | Active network discovery, OUI vendor lookup, signal strength | Built-in wlan0 |
| 🔵 **BT Recon** | Classic Bluetooth + BLE device discovery via `bleak` | Built-in BT |
| 👻 **Evil Twin** | Rogue AP + captive portal + credential harvester | Built-in wlan0 |

### Dashboard Features
- ⚡ Real-time WebSocket event feed
- 📊 Live stats (networks, devices, credentials, payloads)
- 🎛️ Start/stop all modules from one place
- 🌑 Dark hacker-aesthetic UI

---

## Hardware Requirements

| Component | Spec |
|-----------|------|
| Board | Raspberry Pi Zero 2W |
| Storage | 8GB+ microSD (Class 10) |
| OS | Raspberry Pi OS Lite (64-bit) |
| Power | 5V 2A via micro-USB |

**No external adapters needed** — uses built-in WiFi + Bluetooth + USB OTG.

---

## Quick Start

### 1. Flash OS
```bash
# Use Raspberry Pi Imager
# Choose: Raspberry Pi OS Lite (64-bit)
# Enable SSH in advanced settings
```

### 2. Install GhostBox
```bash
# SSH into your Pi
ssh pi@<pi-ip>

# Clone and install
git clone https://github.com/yourusername/ghostbox.git
cd ghostbox
sudo bash install.sh
```

### 3. Start
```bash
sudo systemctl start ghostbox
```

### 4. Open Dashboard
```
http://<pi-ip>:8080
```

---

## Manual Setup (without install.sh)

```bash
# Install system dependencies
sudo apt-get install -y hostapd dnsmasq bluez wireless-tools iw python3 python3-pip python3-venv

# Create venv and install Python deps
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run
python -m ghostbox
```

---

## USB OTG Setup (HID Injection)

For USB Arsenal to work, enable dwc2:

```bash
# /boot/config.txt — add:
dtoverlay=dwc2

# /boot/cmdline.txt — add after rootwait:
modules-load=dwc2,libcomposite
```

Reboot, then use **Setup Gadget** button in the USB Arsenal page.

---

## DuckyScript Example

```ducky
REM Open Run dialog and execute command
DELAY 1000
GUI r
DELAY 500
STRING cmd /k systeminfo
ENTER
```

---

## Project Structure

```
ghostbox/
├── src/ghostbox/
│   ├── core/           # Config, DB, models, logger
│   ├── modules/
│   │   ├── usb_arsenal/    # HID injection engine
│   │   ├── wifi_scanner/   # iwlist-based scanner
│   │   ├── bt_recon/       # bluetoothctl + bleak
│   │   └── evil_twin/      # hostapd + aiohttp portal
│   ├── api/            # FastAPI app + routes
│   └── web/            # Jinja2 templates + CSS/JS
├── payloads/           # DuckyScript payload files
├── install.sh          # One-command Pi installer
└── requirements.txt
```

---

## API Reference

Interactive docs available at `http://<pi-ip>:8080/api/docs`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/stats` | GET | Dashboard statistics |
| `/api/modules` | GET | Module status |
| `/api/usb/inject` | POST | Execute DuckyScript |
| `/api/usb/payloads` | GET/POST | Manage payloads |
| `/api/wifi/networks` | GET | Discovered networks |
| `/api/bluetooth/devices` | GET | Discovered BT devices |
| `/api/evil-twin/start` | POST | Deploy rogue AP |
| `/api/evil-twin/credentials` | GET | Captured credentials |
| `/ws` | WS | Real-time event stream |

---

## Legal Disclaimer

This tool is intended for **authorized security research, CTF competitions, and educational purposes only**.

- Only use on networks/devices you own or have explicit written permission to test
- Unauthorized access to computer systems is illegal in most jurisdictions
- The authors are not responsible for any misuse or damage caused

---

## License

MIT © 2024
