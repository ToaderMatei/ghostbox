"""
GhostBox - USB Arsenal Module
Handles USB HID injection, DuckyScript execution, and USB gadget configuration.
"""
import asyncio
import subprocess
import os
import time
from pathlib import Path
from typing import Optional

from ..base import BaseModule
from ...core.config import config
from ...core.logger import log
from ...core.models import Event, EventType, Severity
from ...core.database import save_event

# DuckyScript key map (US layout)
DUCKY_KEYMAP = {
    "ENTER": "\n", "TAB": "\t", "SPACE": " ", "BACKSPACE": "\x7f",
    "ESCAPE": "\x1b", "DELETE": "\x7f", "HOME": "\x01", "END": "\x05",
    "UP": "\x1b[A", "DOWN": "\x1b[B", "RIGHT": "\x1b[C", "LEFT": "\x1b[D",
}

MODIFIER_KEYS = {
    "CTRL":  0x01, "SHIFT": 0x02, "ALT":  0x04,
    "GUI":   0x08, "META": 0x08,  "WINDOWS": 0x08,
}


class DuckyParser:
    """Parse DuckyScript v1 and execute via /dev/hidg0."""

    def __init__(self, hid_device: str = "/dev/hidg0"):
        self.hid_device = hid_device
        self._default_delay = 0

    def _send_hid_report(self, modifier: int, keycode: int) -> None:
        report = bytes([modifier, 0, keycode, 0, 0, 0, 0, 0])
        null_report = bytes(8)
        try:
            with open(self.hid_device, "wb") as f:
                f.write(report)
                f.write(null_report)
        except (PermissionError, FileNotFoundError):
            log.warning(f"HID device {self.hid_device} not accessible (not on Pi?)")

    def _char_to_keycode(self, char: str) -> tuple[int, int]:
        """Returns (modifier, keycode)."""
        upper = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        symbols_shift = "!@#$%^&*()_+{}|:\"<>?~"
        symbols_shift_keys = "1234567890-=[]\\;',./`"

        if char in upper:
            return (0x02, ord(char) - ord('A') + 4)
        if char.islower():
            return (0x00, ord(char) - ord('a') + 4)
        if char.isdigit():
            kc_map = {'1':30,'2':31,'3':32,'4':33,'5':34,'6':35,'7':36,'8':37,'9':38,'0':39}
            return (0x00, kc_map.get(char, 0))
        if char == ' ':
            return (0x00, 0x2C)
        if char == '\n':
            return (0x00, 0x28)
        if char == '\t':
            return (0x00, 0x2B)
        return (0x00, 0x00)

    def _type_string(self, text: str) -> None:
        for char in text:
            modifier, keycode = self._char_to_keycode(char)
            self._send_hid_report(modifier, keycode)
            time.sleep(0.02)

    def execute(self, script: str) -> list[str]:
        """Execute a DuckyScript and return execution log."""
        log_lines = []
        lines = script.strip().splitlines()

        for raw_line in lines:
            line = raw_line.strip()
            if not line or line.startswith("REM"):
                continue

            parts = line.split(" ", 1)
            cmd = parts[0].upper()
            arg = parts[1] if len(parts) > 1 else ""

            if cmd == "STRING":
                self._type_string(arg)
                log_lines.append(f"STRING: {arg[:30]}...")

            elif cmd == "DELAY":
                try:
                    time.sleep(int(arg) / 1000)
                    log_lines.append(f"DELAY {arg}ms")
                except ValueError:
                    pass

            elif cmd == "DEFAULTDELAY":
                try:
                    self._default_delay = int(arg)
                except ValueError:
                    pass

            elif cmd == "ENTER":
                self._send_hid_report(0, 0x28)
                log_lines.append("ENTER")

            elif cmd in MODIFIER_KEYS:
                # e.g. "GUI r", "CTRL ALT DELETE"
                modifier = 0
                key_parts = line.split()
                for kp in key_parts[:-1]:
                    modifier |= MODIFIER_KEYS.get(kp.upper(), 0)
                last = key_parts[-1].lower()
                if last.isalpha() and len(last) == 1:
                    keycode = ord(last) - ord('a') + 4
                else:
                    keycode = 0
                self._send_hid_report(modifier, keycode)
                log_lines.append(f"COMBO: {line}")

            if self._default_delay > 0:
                time.sleep(self._default_delay / 1000)

        return log_lines


class USBGadget:
    """Manage USB gadget configuration via ConfigFS."""

    GADGET_PATH = "/sys/kernel/config/usb_gadget/ghostbox"

    @classmethod
    def setup(cls) -> bool:
        """Configure Pi Zero as HID USB device."""
        g = cls.GADGET_PATH
        try:
            cmds = [
                f"mkdir -p {g}",
                f"echo 0x1d6b > {g}/idVendor",
                f"echo 0x0104 > {g}/idProduct",
                f"echo 0x0100 > {g}/bcdDevice",
                f"echo 0x0200 > {g}/bcdUSB",
                f"mkdir -p {g}/strings/0x409",
                f'echo "GhostBox" > {g}/strings/0x409/manufacturer',
                f'echo "USB HID Device" > {g}/strings/0x409/product',
                f'echo "GBHID001" > {g}/strings/0x409/serialnumber',
                f"mkdir -p {g}/configs/c.1/strings/0x409",
                f'echo "HID Config" > {g}/configs/c.1/strings/0x409/configuration',
                f"echo 250 > {g}/configs/c.1/MaxPower",
                f"mkdir -p {g}/functions/hid.usb0",
                f"echo 1 > {g}/functions/hid.usb0/protocol",
                f"echo 1 > {g}/functions/hid.usb0/subclass",
                f"echo 8 > {g}/functions/hid.usb0/report_length",
                f"echo -ne '\\x05\\x01\\x09\\x06\\xa1\\x01\\x05\\x07\\x19\\xe0\\x29\\xe7\\x15\\x00\\x25\\x01\\x75\\x01\\x95\\x08\\x81\\x02\\x95\\x01\\x75\\x08\\x81\\x03\\x95\\x05\\x75\\x01\\x05\\x08\\x19\\x01\\x29\\x05\\x91\\x02\\x95\\x01\\x75\\x03\\x91\\x03\\x95\\x06\\x75\\x08\\x15\\x00\\x25\\x65\\x05\\x07\\x19\\x00\\x29\\x65\\x81\\x00\\xc0' > {g}/functions/hid.usb0/report_desc",
                f"ln -sf {g}/functions/hid.usb0 {g}/configs/c.1/",
                f"ls /sys/class/udc > {g}/UDC",
            ]
            for cmd in cmds:
                result = subprocess.run(cmd, shell=True, capture_output=True)
                if result.returncode != 0:
                    log.debug(f"Gadget cmd warning: {cmd} → {result.stderr.decode()}")
            log.info("USB Gadget configured successfully")
            return True
        except Exception as e:
            log.error(f"USB Gadget setup failed: {e}")
            return False

    @classmethod
    def teardown(cls) -> None:
        g = cls.GADGET_PATH
        subprocess.run(f"echo '' > {g}/UDC 2>/dev/null", shell=True)
        subprocess.run(f"rm -rf {g} 2>/dev/null", shell=True)
        log.info("USB Gadget removed")


class USBArsenal(BaseModule):
    name = "usb_arsenal"
    description = "USB HID injection & DuckyScript execution engine"

    def __init__(self) -> None:
        super().__init__()
        self.parser = DuckyParser(config.hid_device)
        self._current_payload: Optional[str] = None
        self._execution_log: list[str] = []

    async def _run(self) -> None:
        event = Event(
            type=EventType.USB,
            title="USB Arsenal Ready",
            detail="HID device initialized and awaiting payload",
            severity=Severity.SUCCESS,
        )
        await self._emit(event)
        save_event(event)

        # Keep module alive, payload injection is triggered via API
        while True:
            await asyncio.sleep(1)

    async def inject_payload(self, script: str, payload_name: str = "manual") -> list[str]:
        """Inject a DuckyScript payload asynchronously."""
        log.info(f"[USB] Injecting payload: {payload_name}")
        loop = asyncio.get_event_loop()
        self._execution_log = await loop.run_in_executor(None, self.parser.execute, script)

        event = Event(
            type=EventType.USB,
            title="Payload Injected",
            detail=f"Executed '{payload_name}' — {len(self._execution_log)} commands",
            severity=Severity.DANGER,
        )
        await self._emit(event)
        save_event(event)
        return self._execution_log

    async def setup_gadget(self) -> bool:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, USBGadget.setup)

    async def teardown_gadget(self) -> None:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, USBGadget.teardown)

    async def _cleanup(self) -> None:
        await self.teardown_gadget()
