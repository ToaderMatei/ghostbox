"""
GhostBox - FastAPI Application
"""
import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from ..core.config import config
from ..core.database import init_db, get_stats
from ..core.logger import log
from ..core.models import Event

from ..modules.usb_arsenal import USBArsenal
from ..modules.wifi_scanner import WiFiScanner
from ..modules.bt_recon import BTRecon
from ..modules.evil_twin import EvilTwin

from .routes import usb, wifi, bluetooth, evil_twin_router, dashboard, pages

BASE_DIR = Path(__file__).resolve().parent.parent

# ── Module registry ────────────────────────────────────────────────────────────

modules: dict[str, Any] = {}
ws_clients: list[WebSocket] = []


async def broadcast(event: Event) -> None:
    """Send event to all connected WebSocket clients."""
    dead = []
    msg = json.dumps(event.to_dict())
    for ws in ws_clients:
        try:
            await ws.send_text(msg)
        except Exception:
            dead.append(ws)
    for ws in dead:
        ws_clients.remove(ws)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()

    usb_m = USBArsenal()
    wifi_m = WiFiScanner()
    bt_m   = BTRecon()
    et_m   = EvilTwin()

    for m in [usb_m, wifi_m, bt_m, et_m]:
        m.on_event(broadcast)

    modules["usb"]        = usb_m
    modules["wifi"]       = wifi_m
    modules["bluetooth"]  = bt_m
    modules["evil_twin"]  = et_m

    app.state.modules    = modules
    app.state.ws_clients = ws_clients

    log.info("GhostBox started — all modules loaded")
    yield

    for m in modules.values():
        if m.status.value == "running":
            await m.stop()
    log.info("GhostBox shutdown complete")


# ── App factory ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="GhostBox",
    version="1.0.0",
    description="Modular security research toolkit for Raspberry Pi Zero 2W",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static + templates
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "web" / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "web" / "templates"))
app.state.templates = templates

# Routers
app.include_router(dashboard.router)
app.include_router(usb.router,              prefix="/api/usb",        tags=["USB Arsenal"])
app.include_router(wifi.router,             prefix="/api/wifi",       tags=["WiFi Scanner"])
app.include_router(bluetooth.router,        prefix="/api/bluetooth",  tags=["BT Recon"])
app.include_router(evil_twin_router.router, prefix="/api/evil-twin",  tags=["Evil Twin"])
app.include_router(pages.router,                                       tags=["Pages"])


# ── WebSocket live feed ────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    ws_clients.append(websocket)
    log.info(f"[WS] Client connected: {websocket.client}")
    try:
        while True:
            await websocket.receive_text()   # keep-alive ping
    except WebSocketDisconnect:
        ws_clients.remove(websocket)
        log.info(f"[WS] Client disconnected")


# ── System endpoints ───────────────────────────────────────────────────────────

@app.get("/api/stats")
async def api_stats():
    return get_stats()


@app.get("/api/modules")
async def api_modules():
    return {name: m.get_status() for name, m in modules.items()}


@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}
