from fastapi import APIRouter, Request
from pydantic import BaseModel
from ...core.database import get_credentials, get_events

router = APIRouter()


class APConfig(BaseModel):
    ssid: str = "FreeWiFi"
    channel: int = 6


@router.get("/status")
async def et_status(request: Request):
    return request.app.state.modules["evil_twin"].get_status()


@router.post("/start")
async def et_start(body: APConfig, request: Request):
    m = request.app.state.modules["evil_twin"]
    m.set_ssid(body.ssid)
    m.set_channel(body.channel)
    await m.start()
    return {"ok": True, "ssid": body.ssid, "status": m.status.value}


@router.post("/stop")
async def et_stop(request: Request):
    m = request.app.state.modules["evil_twin"]
    await m.stop()
    return {"ok": True}


@router.get("/credentials")
async def et_credentials():
    return get_credentials()


@router.get("/events")
async def et_events():
    return get_events(limit=50, event_type="evil_twin")
