from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Profile(Base):
    """Un par (tenant_id, user_id) — pas de FK vers xauth_users : les
    plugins sont cloisonnés, user_id est résolu via le JWT (AuthPayload),
    comme partout ailleurs dans le backend (chat, rag). Créé paresseusement
    au premier GET /me si absent (voir routes/profile_routes.py) — jamais
    besoin d'une étape d'initialisation séparée."""

    __tablename__ = "profile_profiles"
    __table_args__ = (UniqueConstraint("tenant_id", "user_id", name="uq_profile_tenant_user"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)

    # ── Profil ───────────────────────────────────────────────
    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # IANA (ex: "Europe/Paris") — défaut UTC, jamais NULL : set_reminder
    # (chat/src/tools.py) en a besoin à chaque calcul de due_at, un NULL
    # forcerait un repli implicite silencieux à chaque appel plutôt qu'un
    # défaut explicite posé une fois ici.
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    # Préférence d'affichage/notifications — n'influence PAS la langue de
    # réponse de Donna (déjà auto-détectée par message, voir plugin.yaml
    # chat::ollama.system_prompt).
    language: Mapped[str | None] = mapped_column(String(8), nullable=True)

    # ── Préférences chat ─────────────────────────────────────
    # Stocké mais PAS encore branché sur un changement de provider réel par
    # requête : ProviderRouter (chat/src/providers/router.py) est un état
    # partagé par TOUT le process (API_WORKERS=1) — router par utilisateur
    # sans le rendre thread-safe changerait le provider d'un autre
    # utilisateur en cours de requête. Voir ETAT_BACKEND.md.
    preferred_llm_provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # Branché : voir chat/src/tts.py::Synthesizer (plusieurs voix mises en
    # cache, pas d'état partagé dangereux comme le provider ci-dessus).
    preferred_tts_voice: Mapped[str | None] = mapped_column(String(64), nullable=True)
    default_force_web_search: Mapped[bool] = mapped_column(Boolean, default=False)

    # ── Notifications de rappel ──────────────────────────────
    # Branchés via reminder_notify_bridge.py (chat plugin, processus API) :
    # le worker Celery (fire_reminder) publie déjà chaque déclenchement sur
    # Redis (canal "reminders") pour l'affichage temps réel — un second
    # abonné, côté API, dispatch email/WhatsApp depuis LÀ où ext.email et
    # ext.mcp_bridge existent réellement (le worker, process séparé, n'a
    # accès à aucun des deux).
    notify_reminders_email: Mapped[bool] = mapped_column(Boolean, default=False)
    notify_reminders_whatsapp: Mapped[bool] = mapped_column(Boolean, default=False)
    # Téléphone/JID destinataire pour la notification WhatsApp (wa_send
    # exige un `recipient` explicite — Donna n'a pas de notion de "mon
    # propre numéro" par défaut). notify_reminders_whatsapp reste sans
    # effet tant que ce champ est vide.
    whatsapp_notify_number: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # ── Affichage ────────────────────────────────────────────
    theme: Mapped[str] = mapped_column(String(16), default="system")
    date_format: Mapped[str] = mapped_column(String(16), default="auto")
    measurement_system: Mapped[str] = mapped_column(String(16), default="metric")

    # ── Skills activables/désactivables ──────────────────────
    # Toutes à True : une skill désactivée retire des tools au modèle
    # (_SKILL_TOOLS côté chat). Un profil existant ne doit perdre aucun outil
    # au déploiement, donc jamais de valeur False par défaut ici.
    # Ce sont des PRÉFÉRENCES, pas des permissions : elles ne peuvent
    # qu'enlever, jamais accorder (les droits viennent de xauth).
    # Clés alignées sur _SKILL_TOOLS (backend/app/chat/src/tools.py).
    enable_web_search: Mapped[bool] = mapped_column(Boolean, default=True)
    enable_sub_agents: Mapped[bool] = mapped_column(Boolean, default=True)
    enable_reminders: Mapped[bool] = mapped_column(Boolean, default=True)
    enable_memory: Mapped[bool] = mapped_column(Boolean, default=True)
    enable_email_calendar: Mapped[bool] = mapped_column(Boolean, default=True)
    enable_drive: Mapped[bool] = mapped_column(Boolean, default=True)
    enable_create_document: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)
