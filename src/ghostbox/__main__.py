"""
GhostBox — entry point
Usage: python -m ghostbox
"""
import uvicorn
from .core.config import config

if __name__ == "__main__":
    uvicorn.run(
        "ghostbox.api.app:app",
        host=config.host,
        port=config.port,
        reload=config.debug,
        log_level=config.log_level.lower(),
    )
