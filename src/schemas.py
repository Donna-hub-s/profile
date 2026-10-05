from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from .skills_store import MAX_SKILL_SETTINGS, SKILL_ID_RE


class ProfileOut(BaseModel):
    display_name: str | None = None
    avatar_url: str | None = None
    timezone: str = "UTC"
    language: str | None = None
    preferred_llm_provider: str | None = None
    preferred_tts_voice: str | None = None
    # Locuteur d'une voix multi-locuteurs (upmc : 2, mls : 125) ; None = celui du modèle.
    preferred_tts_speaker: int | None = None
    # Voix des bouts anglais ; None = celle du serveur (plugin.yaml tts.english_voice).
    preferred_tts_english_voice: str | None = None
    default_force_web_search: bool = False
    notify_reminders_email: bool = False
    notify_reminders_whatsapp: bool = False
    whatsapp_notify_number: str | None = None
    theme: str = "system"
    date_format: str = "auto"
    measurement_system: str = "metric"
    # Réglages par skill ({identifiant: bool}, catalogue : chat/src/skills.py). Une skill absente
    # garde sa valeur par défaut. Préférences et non permissions : ne peuvent qu'enlever des outils.
    skills: dict[str, bool] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class ProfileUpdateRequest(BaseModel):
    display_name: str | None = None
    avatar_url: str | None = None
    timezone: str | None = None
    language: str | None = None
    preferred_llm_provider: str | None = None
    # Nom de modèle Piper. Validé ici plutôt qu'à la synthèse : une faute de frappe est
    # refusée au bon endroit, et rien d'autre que [A-Za-z0-9_-] n'atteint le nom de fichier
    # du modèle (chat/src/tts.py::_VOICE_NAME_RE, même motif).
    preferred_tts_voice: str | None = Field(default=None, max_length=64, pattern=r"^[A-Za-z0-9_-]*$")
    preferred_tts_speaker: int | None = Field(default=None, ge=0, le=999)
    # Vide = « pas de voix anglaise choisie » (le serveur décide). Même motif de nom que la voix.
    preferred_tts_english_voice: str | None = Field(
        default=None, max_length=64, pattern=r"^[A-Za-z0-9_-]*$"
    )
    default_force_web_search: bool | None = None
    notify_reminders_email: bool | None = None
    notify_reminders_whatsapp: bool | None = None
    whatsapp_notify_number: str | None = None
    theme: str | None = None
    date_format: str | None = None
    measurement_system: str | None = None
    # Fusionné avec les réglages existants (un PATCH ne touche que les skills qu'il nomme).
    skills: dict[str, bool] | None = None

    @field_validator("skills")
    @classmethod
    def _valid_skills(cls, value: dict[str, bool] | None) -> dict[str, bool] | None:
        if value is None:
            return value
        if len(value) > MAX_SKILL_SETTINGS:
            raise ValueError(f"{MAX_SKILL_SETTINGS} réglages de skill maximum.")
        for skill_id in value:
            if not SKILL_ID_RE.match(skill_id):
                raise ValueError(f"Identifiant de skill invalide : {skill_id!r}.")
        return value
