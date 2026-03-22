from fastapi import APIRouter, Request
from ...core.database import get_events, get_stats

router = APIRouter()


@router.get("/")
async def index(request: Request):
    templates = request.app.state.templates
    modules   = request.app.state.modules
    stats     = get_stats()
    events    = get_events(limit=20)
    mod_status = {name: m.get_status() for name, m in modules.items()}
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "stats": stats,
        "events": events,
        "modules": mod_status,
    })
