"""
GhostBox - SQLite Database Layer
"""
import sqlite3
import json
from contextlib import contextmanager
from datetime import datetime
from typing import List, Optional
from .config import config
from .logger import log
from .models import Event, WifiNetwork, BluetoothDevice, CapturedCredential, HIDPayload


@contextmanager
def get_db():
    conn = sqlite3.connect(config.db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def init_db() -> None:
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS events (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                type      TEXT NOT NULL,
                title     TEXT NOT NULL,
                detail    TEXT NOT NULL,
                severity  TEXT NOT NULL DEFAULT 'info',
                timestamp TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS wifi_networks (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                ssid       TEXT NOT NULL,
                bssid      TEXT NOT NULL UNIQUE,
                channel    INTEGER,
                signal     INTEGER,
                encryption TEXT,
                vendor     TEXT DEFAULT 'Unknown',
                first_seen TEXT NOT NULL,
                last_seen  TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS bt_devices (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                address     TEXT NOT NULL UNIQUE,
                name        TEXT,
                device_class TEXT,
                rssi        INTEGER,
                device_type TEXT DEFAULT 'classic',
                services    TEXT DEFAULT '[]',
                manufacturer TEXT DEFAULT 'Unknown',
                first_seen  TEXT NOT NULL,
                last_seen   TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS credentials (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                source     TEXT NOT NULL,
                username   TEXT NOT NULL,
                password   TEXT NOT NULL,
                ip_address TEXT NOT NULL,
                user_agent TEXT DEFAULT '',
                timestamp  TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS hid_payloads (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL UNIQUE,
                description TEXT,
                content     TEXT NOT NULL,
                language    TEXT DEFAULT 'en-US',
                created_at  TEXT NOT NULL
            );
        """)
        log.info("Database initialized")


# --- Events ---

def save_event(event: Event) -> None:
    with get_db() as conn:
        conn.execute(
            "INSERT INTO events (type, title, detail, severity, timestamp) VALUES (?,?,?,?,?)",
            (event.type.value, event.title, event.detail, event.severity.value, event.timestamp.isoformat()),
        )


def get_events(limit: int = 100, event_type: Optional[str] = None) -> List[dict]:
    with get_db() as conn:
        if event_type:
            rows = conn.execute(
                "SELECT * FROM events WHERE type=? ORDER BY id DESC LIMIT ?",
                (event_type, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]


# --- WiFi ---

def upsert_wifi_network(net: WifiNetwork) -> None:
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM wifi_networks WHERE bssid=?", (net.bssid,)
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE wifi_networks SET signal=?, last_seen=? WHERE bssid=?",
                (net.signal, datetime.utcnow().isoformat(), net.bssid),
            )
        else:
            conn.execute(
                """INSERT INTO wifi_networks
                   (ssid, bssid, channel, signal, encryption, vendor, first_seen, last_seen)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (net.ssid, net.bssid, net.channel, net.signal, net.encryption,
                 net.vendor, net.first_seen.isoformat(), net.last_seen.isoformat()),
            )


def get_wifi_networks(limit: int = 200) -> List[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM wifi_networks ORDER BY signal DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


# --- Bluetooth ---

def upsert_bt_device(dev: BluetoothDevice) -> None:
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM bt_devices WHERE address=?", (dev.address,)
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE bt_devices SET rssi=?, last_seen=? WHERE address=?",
                (dev.rssi, datetime.utcnow().isoformat(), dev.address),
            )
        else:
            conn.execute(
                """INSERT INTO bt_devices
                   (address, name, device_class, rssi, device_type, services, manufacturer, first_seen, last_seen)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (dev.address, dev.name, dev.device_class, dev.rssi, dev.device_type,
                 json.dumps(dev.services), dev.manufacturer,
                 dev.first_seen.isoformat(), dev.last_seen.isoformat()),
            )


def get_bt_devices(limit: int = 200) -> List[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM bt_devices ORDER BY rssi DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


# --- Credentials ---

def save_credential(cred: CapturedCredential) -> None:
    with get_db() as conn:
        conn.execute(
            "INSERT INTO credentials (source, username, password, ip_address, user_agent, timestamp) VALUES (?,?,?,?,?,?)",
            (cred.source, cred.username, cred.password, cred.ip_address, cred.user_agent, cred.timestamp.isoformat()),
        )


def get_credentials(limit: int = 100) -> List[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM credentials ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


# --- HID Payloads ---

def save_payload(payload: HIDPayload) -> None:
    with get_db() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO hid_payloads (name, description, content, language, created_at)
               VALUES (?,?,?,?,?)""",
            (payload.name, payload.description, payload.content, payload.language, payload.created_at.isoformat()),
        )


def get_payloads() -> List[dict]:
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM hid_payloads ORDER BY name").fetchall()
        return [dict(r) for r in rows]


def get_stats() -> dict:
    with get_db() as conn:
        return {
            "wifi_networks": conn.execute("SELECT COUNT(*) FROM wifi_networks").fetchone()[0],
            "bt_devices": conn.execute("SELECT COUNT(*) FROM bt_devices").fetchone()[0],
            "credentials": conn.execute("SELECT COUNT(*) FROM credentials").fetchone()[0],
            "events": conn.execute("SELECT COUNT(*) FROM events").fetchone()[0],
            "payloads": conn.execute("SELECT COUNT(*) FROM hid_payloads").fetchone()[0],
        }
