from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from ...core.database import get_payloads, save_payload, get_events
from ...core.models import HIDPayload
from datetime import datetime

router = APIRouter()


class PayloadCreate(BaseModel):
    name: str
    description: str = ""
    content: str
    language: str = "en-US"


class InjectRequest(BaseModel):
    payload_name: str = "manual"
    script: str


@router.get("/status")
async def usb_status(request: Request):
    return request.app.state.modules["usb"].get_status()


@router.post("/start")
async def usb_start(request: Request):
    m = request.app.state.modules["usb"]
    await m.start()
    return {"ok": True, "status": m.status.value}


@router.post("/stop")
async def usb_stop(request: Request):
    m = request.app.state.modules["usb"]
    await m.stop()
    return {"ok": True}


@router.post("/inject")
async def usb_inject(body: InjectRequest, request: Request):
    m = request.app.state.modules["usb"]
    log_lines = await m.inject_payload(body.script, body.payload_name)
    return {"ok": True, "log": log_lines}


@router.post("/gadget/setup")
async def gadget_setup(request: Request):
    m = request.app.state.modules["usb"]
    ok = await m.setup_gadget()
    return {"ok": ok}


@router.post("/gadget/teardown")
async def gadget_teardown(request: Request):
    m = request.app.state.modules["usb"]
    await m.teardown_gadget()
    return {"ok": True}


@router.get("/payloads")
async def list_payloads():
    return get_payloads()


@router.post("/payloads")
async def create_payload(body: PayloadCreate):
    payload = HIDPayload(
        name=body.name,
        description=body.description,
        content=body.content,
        language=body.language,
        created_at=datetime.utcnow(),
    )
    save_payload(payload)
    return {"ok": True}


@router.get("/events")
async def usb_events():
    return get_events(limit=50, event_type="usb")
