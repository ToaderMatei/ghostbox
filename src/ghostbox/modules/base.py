"""
GhostBox - Base Module Interface
"""
import asyncio
from abc import ABC, abstractmethod
from typing import Callable, List, Optional
from ..core.models import ModuleStatus, Event
from ..core.logger import log


class BaseModule(ABC):
    name: str = "base"
    description: str = ""

    def __init__(self) -> None:
        self.status = ModuleStatus.IDLE
        self._task: Optional[asyncio.Task] = None
        self._event_handlers: List[Callable] = []

    def on_event(self, handler: Callable) -> None:
        """Register a callback for events emitted by this module."""
        self._event_handlers.append(handler)

    async def _emit(self, event: Event) -> None:
        for handler in self._event_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                log.error(f"Event handler error in {self.name}: {e}")

    async def start(self) -> None:
        if self.status == ModuleStatus.RUNNING:
            log.warning(f"{self.name} is already running")
            return
        self.status = ModuleStatus.RUNNING
        log.info(f"[{self.name}] Starting...")
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        await self._cleanup()
        self.status = ModuleStatus.STOPPED
        log.info(f"[{self.name}] Stopped")

    @abstractmethod
    async def _run(self) -> None:
        """Main module loop."""
        ...

    async def _cleanup(self) -> None:
        """Override to release resources."""
        pass

    def get_status(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
        }
