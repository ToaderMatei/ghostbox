"""
GhostBox - Data Models
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class ModuleStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    ERROR = "error"
    STOPPED = "stopped"


class EventType(str, Enum):
    USB = "usb"
    WIFI = "wifi"
    BLUETOOTH = "bluetooth"
    EVIL_TWIN = "evil_twin"
    SYSTEM = "system"


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    DANGER = "danger"
    SUCCESS = "success"


@dataclass
class Event:
    type: EventType
    title: str
    detail: str
    severity: Severity = Severity.INFO
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "type": self.type.value,
            "title": self.title,
            "detail": self.detail,
            "severity": self.severity.value,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class WifiNetwork:
    ssid: str
    bssid: str
    channel: int
    signal: int
    encryption: str
    vendor: str = "Unknown"
    first_seen: datetime = field(default_factory=datetime.utcnow)
    last_seen: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "ssid": self.ssid,
            "bssid": self.bssid,
            "channel": self.channel,
            "signal": self.signal,
            "encryption": self.encryption,
            "vendor": self.vendor,
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat(),
        }


@dataclass
class BluetoothDevice:
    address: str
    name: str
    device_class: str
    rssi: int
    device_type: str = "classic"
    services: list = field(default_factory=list)
    manufacturer: str = "Unknown"
    first_seen: datetime = field(default_factory=datetime.utcnow)
    last_seen: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "address": self.address,
            "name": self.name,
            "device_class": self.device_class,
            "rssi": self.rssi,
            "device_type": self.device_type,
            "services": self.services,
            "manufacturer": self.manufacturer,
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat(),
        }


@dataclass
class CapturedCredential:
    source: str
    username: str
    password: str
    ip_address: str
    user_agent: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "username": self.username,
            "password": self.password,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class HIDPayload:
    name: str
    description: str
    content: str
    language: str = "en-US"
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "content": self.content,
            "language": self.language,
            "created_at": self.created_at.isoformat(),
        }
