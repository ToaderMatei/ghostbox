"""
GhostBox - Page routes for USB, WiFi, BT, Evil Twin
"""
from fastapi import APIRouter, Request
from ...core.database import get_payloads, get_wifi_networks, get_bt_devices, get_credentials

router = APIRouter()


@router.get("/usb")
async def usb_page(request: Request):
    payloads = get_payloads()
    return request.app.state.templates.TemplateResponse("usb.html", {
        "request": request,
        "payloads": payloads,
        "module": request.app.state.modules["usb"].get_status(),
    })


@router.get("/wifi")
async def wifi_page(request: Request):
    networks = get_wifi_networks()
    return request.app.state.templates.TemplateResponse("wifi.html", {
        "request": request,
        "networks": networks,
        "module": request.app.state.modules["wifi"].get_status(),
    })


@router.get("/bluetooth")
async def bt_page(request: Request):
    devices = get_bt_devices()
    return request.app.state.templates.TemplateResponse("bluetooth.html", {
        "request": request,
        "devices": devices,
        "module": request.app.state.modules["bluetooth"].get_status(),
    })


@router.get("/evil-twin")
async def et_page(request: Request):
    creds = get_credentials()
    return request.app.state.templates.TemplateResponse("evil_twin.html", {
        "request": request,
        "credentials": creds,
        "module": request.app.state.modules["evil_twin"].get_status(),
    })
