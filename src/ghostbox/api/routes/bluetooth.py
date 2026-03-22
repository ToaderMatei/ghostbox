from fastapi import APIRouter, Request
from ...core.database import get_bt_devices, get_events

router = APIRouter()


@router.get("/status")
async def bt_status(request: Request):
    return request.app.state.modules["bluetooth"].get_status()


@router.post("/start")
async def bt_start(request: Request):
    m = request.app.state.modules["bluetooth"]
    await m.start()
    return {"ok": True, "status": m.status.value}


@router.post("/stop")
async def bt_stop(request: Request):
    m = request.app.state.modules["bluetooth"]
    await m.stop()
    return {"ok": True}


@router.get("/devices")
async def bt_devices():
    return get_bt_devices()


@router.get("/events")
async def bt_events():
    return get_events(limit=50, event_type="bluetooth")
