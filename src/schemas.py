from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ProfileOut(BaseModel):
    display_name: str | None = None
    avatar_url: str | None = None
    timezone: str = "UTC"
    language: str | None = None
    preferred_llm_provider: str | None = None
    preferred_tts_voice: str | None = None
    default_force_web_search: bool = False
    notify_reminders_email: bool = False
    notify_reminders_whatsapp: bool = False
    whatsapp_notify_number: str | None = None
    theme: str = "system"
    date_format: str = "auto"
    measurement_system: str = "metric"
    # Skills activables — clés alignées sur _SKILL_TOOLS (chat/src/tools.py).
    # Préférences et non permissions : ne peuvent qu'enlever des outils.
    enable_web_search: bool = True
    enable_sub_agents: bool = True
    enable_reminders: bool = True
    enable_memory: bool = True
    enable_email_calendar: bool = True
    enable_drive: bool = True
    enable_create_document: bool = True
    created_at: datetime
    updated_at: datetime


class ProfileUpdateRequest(BaseModel):
    display_name: str | None = None
    avatar_url: str | None = None
    timezone: str | None = None
    language: str | None = None
    preferred_llm_provider: str | None = None
    preferred_tts_voice: str | None = None
    default_force_web_search: bool | None = None
    notify_reminders_email: bool | None = None
    notify_reminders_whatsapp: bool | None = None
    whatsapp_notify_number: str | None = None
    theme: str | None = None
    date_format: str | None = None
    measurement_system: str | None = None
    enable_web_search: bool | None = None
    enable_sub_agents: bool | None = None
    enable_reminders: bool | None = None
    enable_memory: bool | None = None
    enable_email_calendar: bool | None = None
    enable_drive: bool | None = None
    enable_create_document: bool | None = None
