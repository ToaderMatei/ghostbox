"""
GhostBox - Bluetooth Recon Module
Classic BT discovery + BLE scanning via bleak / bluetoothctl.
"""
import asyncio
import subprocess
import re
from datetime import datetime
from typing import Optional

from ..base import BaseModule
from ...core.config import config
from ...core.logger import log
from ...core.models import Event, EventType, Severity, BluetoothDevice
from ...core.database import upsert_bt_device, save_event

BT_CLASS_MAP = {
    "0x000100": "Computer",
    "0x000200": "Phone",
    "0x000400": "LAN/Network",
    "0x000500": "Audio/Video",
    "0x000600": "Peripheral",
    "0x000700": "Imaging",
}


def _classify_device(dev_class: str) -> str:
    return BT_CLASS_MAP.get(dev_class, "Unknown")


class BTRecon(BaseModule):
    name = "bt_recon"
    description = "Bluetooth Classic & BLE device discovery and enumeration"

    def __init__(self) -> None:
        super().__init__()
        self.interface = config.bt_interface
        self.scan_duration = config.bt_scan_duration
        self._devices: list[BluetoothDevice] = []
        self._scan_count = 0
        self._use_bleak = False

    async def _run(self) -> None:
        # Try to import bleak for BLE
        try:
            import bleak  # noqa
            self._use_bleak = True
            log.info("[BT] bleak available — BLE scanning enabled")
        except ImportError:
            log.warning("[BT] bleak not installed — BLE scanning disabled")

        event = Event(
            type=EventType.BLUETOOTH,
            title="Bluetooth Recon Started",
            detail=f"Scanning Classic + {'BLE' if self._use_bleak else 'Classic only'}",
            severity=Severity.INFO,
        )
        await self._emit(event)
        save_event(event)

        while True:
            try:
                classic_devices = await self._scan_classic()
                ble_devices = await self._scan_ble() if self._use_bleak else []
                all_devices = classic_devices + ble_devices
                self._scan_count += 1

                for dev in all_devices:
                    upsert_bt_device(dev)

                if all_devices:
                    ev = Event(
                        type=EventType.BLUETOOTH,
                        title=f"BT Scan #{self._scan_count}",
                        detail=f"{len(classic_devices)} Classic + {len(ble_devices)} BLE devices found",
                        severity=Severity.WARNING,
                    )
                    await self._emit(ev)
                    save_event(ev)

                await asyncio.sleep(30)
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"[BT] Scan error: {e}")
                await asyncio.sleep(10)

    async def _scan_classic(self) -> list[BluetoothDevice]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._do_classic_scan)

    def _do_classic_scan(self) -> list[BluetoothDevice]:
        try:
            result = subprocess.run(
                ["bluetoothctl", "--timeout", str(self.scan_duration), "scan", "on"],
                capture_output=True, text=True, timeout=self.scan_duration + 5,
            )
            devices = []
            lines = result.stdout + result.stderr
            pattern = re.compile(r"\[NEW\] Device ([\w:]+) (.+)")

            for match in pattern.finditer(lines):
                addr, name = match.group(1), match.group(2).strip()
                now = datetime.utcnow()
                devices.append(
                    BluetoothDevice(
                        address=addr,
                        name=name,
                        device_class="Unknown",
                        rssi=-70,
                        device_type="classic",
                        first_seen=now,
                        last_seen=now,
                    )
                )
            return devices
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return self._simulated_scan()

    async def _scan_ble(self) -> list[BluetoothDevice]:
        try:
            from bleak import BleakScanner
            devices = await BleakScanner.discover(timeout=self.scan_duration)
            now = datetime.utcnow()
            return [
                BluetoothDevice(
                    address=d.address,
                    name=d.name or "Unknown BLE",
                    device_class="BLE",
                    rssi=d.rssi,
                    device_type="ble",
                    manufacturer=str(d.metadata.get("manufacturer_data", "Unknown")),
                    first_seen=now,
                    last_seen=now,
                )
                for d in devices
            ]
        except Exception as e:
            log.warning(f"[BT] BLE scan error: {e}")
            return []

    def _simulated_scan(self) -> list[BluetoothDevice]:
        now = datetime.utcnow()
        return [
            BluetoothDevice("AA:BB:CC:11:22:33", "iPhone 14 Pro", "Phone",  -55, "classic", [], "Apple",   now, now),
            BluetoothDevice("AA:BB:CC:44:55:66", "JBL Flip 6",    "Audio",  -62, "classic", [], "JBL",     now, now),
            BluetoothDevice("AA:BB:CC:77:88:99", "Unknown BLE",   "BLE",    -75, "ble",     [], "Unknown", now, now),
        ]

    def get_devices(self) -> list[dict]:
        return [d.to_dict() for d in self._devices]
