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
