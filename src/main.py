from __future__ import annotations

from fastapi import APIRouter
from xcore.sdk import AutoDispatchMixin, TrustedBase, get_logger

from .ipc import IPCCommands
from .models import Base
from .routes.profile_routes import profile_router

logger = get_logger("profile.plugin")


class Plugin(IPCCommands, AutoDispatchMixin, TrustedBase):
    async def on_load(self) -> None:
        self._db = self.get_service("db")

        async with self._db.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        self.app = APIRouter()
        self.app.include_router(profile_router(self._db))
        logger.info("profile plugin prêt")

    async def on_unload(self) -> None:
        pass

    def get_router(self) -> APIRouter | None:
        return self.app
