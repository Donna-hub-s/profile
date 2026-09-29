from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text
from xcore.sdk import AutoDispatchMixin, TrustedBase, get_logger

from .ipc import IPCCommands
from .models import Base
from .routes.profile_routes import profile_router

logger = get_logger("profile.plugin")

# Colonnes ajoutées APRÈS la création initiale de la table. Ce plugin n'a pas
# d'Alembic (contrairement à xauth) : `create_all` crée la table mais n'ajoute
# JAMAIS une colonne à une table existante — sans ça, une base déjà en place
# planterait sur `no such column` et le plugin profile ne monterait pas du
# tout, donc plus aucun tour de chat (les préférences best-effort restent
# OK, mais /profil est cassé).
#
# ALTER TABLE plutôt que recréer : les profils et leurs réglages déjà
# enregistrés doivent survivre au déploiement. PRAGMA table_info plutôt
# qu'un try/except sur l'ALTER : une erreur SQL au milieu de cette
# transaction DDL la laisserait dans un état incertain sous
# SQLite/aiosqlite. NOT NULL + DEFAULT explicite pour que les lignes
# existantes adoptent la valeur par défaut au lieu de NULL (les colonnes
# appliquent le default aux lignes préexistantes).
_ADDED_COLUMNS: tuple[tuple[str, str], ...] = (
    ("theme", "VARCHAR(16) NOT NULL DEFAULT 'system'"),
    ("date_format", "VARCHAR(16) NOT NULL DEFAULT 'auto'"),
    ("measurement_system", "VARCHAR(16) NOT NULL DEFAULT 'metric'"),
    ("enable_web_search", "BOOLEAN NOT NULL DEFAULT 1"),
    ("enable_sub_agents", "BOOLEAN NOT NULL DEFAULT 1"),
    ("enable_reminders", "BOOLEAN NOT NULL DEFAULT 1"),
    ("enable_memory", "BOOLEAN NOT NULL DEFAULT 1"),
    ("enable_email_calendar", "BOOLEAN NOT NULL DEFAULT 1"),
    ("enable_drive", "BOOLEAN NOT NULL DEFAULT 1"),
    ("enable_create_document", "BOOLEAN NOT NULL DEFAULT 1"),
)


async def _ensure_added_columns(conn) -> None:
    existing = {
        row[1] for row in (await conn.execute(text("PRAGMA table_info(profile_profiles)"))).fetchall()
    }
    if not existing:
        # Table pas encore créée (create_all vient de la créer après) : rien
        # à ajouter, le modèle porte déjà les bonnes colonnes.
        return
    for column, ddl in _ADDED_COLUMNS:
        if column not in existing:
            await conn.execute(text(f"ALTER TABLE profile_profiles ADD COLUMN {column} {ddl}"))
            logger.info("colonne profil ajoutée", column=column)


class Plugin(IPCCommands, AutoDispatchMixin, TrustedBase):
    async def on_load(self) -> None:
        self._db = self.get_service("db")

        async with self._db.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await _ensure_added_columns(conn)

        self.app = APIRouter()
        self.app.include_router(profile_router(self._db))
        logger.info("profile plugin prêt")

    async def on_unload(self) -> None:
        pass

    def get_router(self) -> APIRouter | None:
        return self.app
