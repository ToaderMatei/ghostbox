"""
GhostBox - WiFi Scanner Module
Active scanning via iw/iwlist. No second adapter required.
"""
import asyncio
import re
import subprocess
from datetime import datetime

from ..base import BaseModule
from ...core.config import config
from ...core.logger import log
from ...core.models import Event, EventType, Severity, WifiNetwork
from ...core.database import upsert_wifi_network, save_event

# Known OUI prefix → vendor (small embedded table)
OUI_TABLE = {
    "00:50:f2": "Microsoft",
    "00:1a:11": "Google",
    "b8:27:eb": "Raspberry Pi",
    "dc:a6:32": "Raspberry Pi",
    "e4:5f:01": "Raspberry Pi",
    "00:23:14": "Apple",
    "f8:1e:df": "Apple",
    "3c:22:fb": "Apple",
    "00:1b:63": "Apple",
    "00:0c:29": "VMware",
    "00:50:56": "VMware",
    "00:1c:bf": "Cisco",
    "78:bc:1a": "TP-Link",
    "50:c7:bf": "TP-Link",
    "18:d6:c7": "TP-Link",
    "ec:08:6b": "TP-Link",
    "74:da:38": "Edimax",
}


def _lookup_vendor(bssid: str) -> str:
    prefix = bssid[:8].lower()
    return OUI_TABLE.get(prefix, "Unknown")


def _parse_iwlist_output(output: str) -> list[WifiNetwork]:
    networks: list[WifiNetwork] = []
    cells = re.split(r"Cell \d+ -", output)

    for cell in cells[1:]:
        try:
            ssid_match = re.search(r'ESSID:"([^"]*)"', cell)
            bssid_match = re.search(r'Address: ([\w:]+)', cell)
            channel_match = re.search(r'Channel:(\d+)', cell)
            signal_match = re.search(r'Signal level=(-\d+)', cell)
            enc_match = re.search(r'Encryption key:(on|off)', cell)
            wpa_match = re.search(r'(WPA2|WPA)', cell)

            if not (ssid_match and bssid_match):
                continue

            ssid = ssid_match.group(1) or "<hidden>"
            bssid = bssid_match.group(1)
            channel = int(channel_match.group(1)) if channel_match else 0
            signal = int(signal_match.group(1)) if signal_match else -100
            enc_on = enc_match.group(1) == "on" if enc_match else False

            if wpa_match:
                encryption = wpa_match.group(1)
            elif enc_on:
                encryption = "WEP"
            else:
                encryption = "OPEN"

            vendor = _lookup_vendor(bssid)
            now = datetime.utcnow()

            networks.append(
                WifiNetwork(
                    ssid=ssid,
                    bssid=bssid,
                    channel=channel,
                    signal=signal,
                    encryption=encryption,
                    vendor=vendor,
                    first_seen=now,
                    last_seen=now,
                )
            )
        except Exception as e:
            log.debug(f"WiFi parse error: {e}")
            continue

    return networks


class WiFiScanner(BaseModule):
    name = "wifi_scanner"
    description = "Active WiFi network discovery via iwlist"

    def __init__(self) -> None:
        super().__init__()
        self.interface = config.wifi_interface
        self.scan_interval = config.wifi_scan_interval
        self._networks: list[WifiNetwork] = []
        self._scan_count = 0

    async def _run(self) -> None:
        log.info(f"[WiFi] Starting scanner on {self.interface}")
        event = Event(
            type=EventType.WIFI,
            title="WiFi Scanner Started",
            detail=f"Scanning on {self.interface} every {self.scan_interval}s",
            severity=Severity.INFO,
        )
        await self._emit(event)
        save_event(event)

        while True:
            try:
                networks = await self._scan()
                self._scan_count += 1

                for net in networks:
                    upsert_wifi_network(net)

                if networks:
                    ev = Event(
                        type=EventType.WIFI,
                        title=f"Scan #{self._scan_count} Complete",
                        detail=f"Found {len(networks)} networks | "
                               f"Strongest: {networks[0].ssid} ({networks[0].signal} dBm)",
                        severity=Severity.INFO,
                    )
                    await self._emit(ev)
                    save_event(ev)

                await asyncio.sleep(self.scan_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"[WiFi] Scan error: {e}")
                await asyncio.sleep(5)

    async def _scan(self) -> list[WifiNetwork]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._do_scan)

    def _do_scan(self) -> list[WifiNetwork]:
        try:
            result = subprocess.run(
                ["iwlist", self.interface, "scan"],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0:
                log.warning(f"[WiFi] iwlist error: {result.stderr.strip()}")
                return []
            networks = _parse_iwlist_output(result.stdout)
            networks.sort(key=lambda n: n.signal, reverse=True)
            self._networks = networks
            return networks
        except subprocess.TimeoutExpired:
            log.warning("[WiFi] Scan timed out")
            return []
        except FileNotFoundError:
            log.warning("[WiFi] iwlist not found — running in simulation mode")
            return self._simulated_scan()

    def _simulated_scan(self) -> list[WifiNetwork]:
        """Return fake data when not running on Pi (dev/testing)."""
        import random
        now = datetime.utcnow()
        return [
            WifiNetwork("HomeNetwork_5G", "aa:bb:cc:dd:ee:01", 36, -45, "WPA2", "TP-Link", now, now),
            WifiNetwork("DIRECT-Printer", "aa:bb:cc:dd:ee:02", 1, -67, "WPA2", "HP", now, now),
            WifiNetwork("Vodafone-4F2A", "aa:bb:cc:dd:ee:03", 6, -72, "WPA2", "Unknown", now, now),
            WifiNetwork("<hidden>",       "aa:bb:cc:dd:ee:04", 11, -80, "WPA2", "Unknown", now, now),
            WifiNetwork("FreeWifi_Guest", "aa:bb:cc:dd:ee:05", 6, -88, "OPEN", "Unknown", now, now),
        ]

    def get_networks(self) -> list[dict]:
        return [n.to_dict() for n in self._networks]
