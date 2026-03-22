from fastapi import APIRouter, Request
from ...core.database import get_wifi_networks, get_events

router = APIRouter()


@router.get("/status")
async def wifi_status(request: Request):
    return request.app.state.modules["wifi"].get_status()


@router.post("/start")
async def wifi_start(request: Request):
    m = request.app.state.modules["wifi"]
    await m.start()
    return {"ok": True, "status": m.status.value}


@router.post("/stop")
async def wifi_stop(request: Request):
    m = request.app.state.modules["wifi"]
    await m.stop()
    return {"ok": True}


@router.get("/networks")
async def wifi_networks():
    return get_wifi_networks()


@router.get("/events")
async def wifi_events():
    return get_events(limit=50, event_type="wifi")
