"""
GhostBox - Core Configuration
"""
import os
from dataclasses import dataclass, field
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = BASE_DIR / "data"
PAYLOAD_DIR = BASE_DIR / "payloads"
LOG_DIR = BASE_DIR / "logs"

for d in [DATA_DIR, PAYLOAD_DIR, LOG_DIR]:
    d.mkdir(parents=True, exist_ok=True)


@dataclass
class Config:
    # Server
    host: str = "0.0.0.0"
    port: int = 8080
    debug: bool = False

    # Database
    db_path: str = str(DATA_DIR / "ghostbox.db")

    # WiFi
    wifi_interface: str = "wlan0"
    wifi_scan_interval: int = 30

    # Bluetooth
    bt_interface: str = "hci0"
    bt_scan_duration: int = 10

    # Evil Twin
    ap_interface: str = "wlan0"
    ap_ssid: str = "FreeWiFi"
    ap_channel: int = 6
    ap_ip: str = "192.168.69.1"
    ap_subnet: str = "192.168.69.0/24"
    captive_portal_port: int = 80

    # USB Arsenal
    usb_gadget_path: str = "/sys/kernel/config/usb_gadget/ghostbox"
    hid_device: str = "/dev/hidg0"

    # Logging
    log_level: str = "INFO"
    log_file: str = str(LOG_DIR / "ghostbox.log")


config = Config()
