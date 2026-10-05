from __future__ import annotations

from fastapi import APIRouter
from xcore.sdk import AutoDispatchMixin, TrustedBase, get_logger

from extensions.db_columns import ensure_columns
from .ipc import IPCCommands
from .models import Base
from .routes.profile_routes import profile_router
from .skills_store import migrate_legacy_skill_flags

logger = get_logger("profile.plugin")

# Colonnes ajoutées APRÈS la création initiale de la table. Ce plugin n'a pas
# d'Alembic (contrairement à xauth) : `create_all` crée la table mais n'ajoute
# JAMAIS une colonne à une table existante — sans ça, une base déjà en place
# planterait sur `no such column` et le plugin profile ne monterait pas du
# tout, donc plus aucun tour de chat (les préférences best-effort restent
# OK, mais /profil est cassé).
#
# ALTER TABLE plutôt que recréer : les profils et leurs réglages déjà
# enregistrés doivent survivre au déploiement. NOT NULL + DEFAULT explicite
# pour que les lignes existantes adoptent la valeur par défaut au lieu de
# NULL. Paire (sqlite, postgres) : Postgres refuse `BOOLEAN DEFAULT 1`
# (attend TRUE/FALSE), SQLite accepte les deux formes — voir
# extensions/db_columns.py.
_ADDED_COLUMNS: tuple[tuple[str, str, str], ...] = (
    ("theme", "VARCHAR(16) NOT NULL DEFAULT 'system'", "VARCHAR(16) NOT NULL DEFAULT 'system'"),
    ("date_format", "VARCHAR(16) NOT NULL DEFAULT 'auto'", "VARCHAR(16) NOT NULL DEFAULT 'auto'"),
    ("measurement_system", "VARCHAR(16) NOT NULL DEFAULT 'metric'", "VARCHAR(16) NOT NULL DEFAULT 'metric'"),
    ("enable_web_search", "BOOLEAN NOT NULL DEFAULT 1", "BOOLEAN NOT NULL DEFAULT TRUE"),
    ("enable_sub_agents", "BOOLEAN NOT NULL DEFAULT 1", "BOOLEAN NOT NULL DEFAULT TRUE"),
    ("enable_reminders", "BOOLEAN NOT NULL DEFAULT 1", "BOOLEAN NOT NULL DEFAULT TRUE"),
    ("enable_memory", "BOOLEAN NOT NULL DEFAULT 1", "BOOLEAN NOT NULL DEFAULT TRUE"),
    ("enable_email_calendar", "BOOLEAN NOT NULL DEFAULT 1", "BOOLEAN NOT NULL DEFAULT TRUE"),
    ("enable_drive", "BOOLEAN NOT NULL DEFAULT 1", "BOOLEAN NOT NULL DEFAULT TRUE"),
    ("enable_create_document", "BOOLEAN NOT NULL DEFAULT 1", "BOOLEAN NOT NULL DEFAULT TRUE"),
    # Réglages par skill (remplace les colonnes enable_*). '{}' = tout par défaut.
    ("skills", "JSON NOT NULL DEFAULT '{}'", "JSON NOT NULL DEFAULT '{}'"),
    # Voix de synthèse. Le nom est validé à l'écriture (schemas.py), le locuteur est un entier
    # — sans tuile, une base déjà en place n'aurait jamais ces colonnes (create_all ne modifie
    # pas une table existante).
    ("preferred_tts_voice", "VARCHAR(64) NULL", "VARCHAR(64) NULL"),
    ("preferred_tts_speaker", "INTEGER NULL", "INTEGER NULL"),
    ("preferred_tts_english_voice", "VARCHAR(64) NULL", "VARCHAR(64) NULL"),
)


async def _ensure_added_columns(conn) -> None:
    await ensure_columns(conn, "profile_profiles", _ADDED_COLUMNS, logger=logger)


class Plugin(IPCCommands, AutoDispatchMixin, TrustedBase):
    async def on_load(self) -> None:
        self._db = self.get_service("db")

        async with self._db.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await _ensure_added_columns(conn)

        # Les skills désactivées avant le champ `skills` (anciennes colonnes enable_*) ne doivent pas
        # se réactiver au déploiement.
        async with self._db.session() as session:
            migrated = await migrate_legacy_skill_flags(session)
        if migrated:
            logger.info("réglages de skills migrés", profils=migrated)

        self.app = APIRouter()
        self.app.include_router(profile_router(self._db))
        logger.info("profile plugin prêt")

    async def on_unload(self) -> None:
        pass

    def get_router(self) -> APIRouter | None:
        return self.app
