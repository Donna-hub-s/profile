from __future__ import annotations

from typing import TypedDict

from sqlalchemy import select
from xcore.sdk import AutoDispatchMixin, action, error, ok, schema

from .models import Profile
from .skills_store import current_skills

GET_PROFILE_SCHEMA: TypedDict = {  # type: ignore
    "tenant_id": (str, ...),
    "user_id": (str, ...),
}


class IPCCommands(AutoDispatchMixin):
    """Actions IPC du plugin profile — appelées via call_plugin("profile", ...)
    par d'autres plugins (chat notamment, pour timezone/voix/préférences par
    défaut) sans passer par HTTP. La classe héritante doit fournir self._db."""

    @action("profile.get", side_effect="read")
    @schema(
        version="1.0",
        input=GET_PROFILE_SCHEMA,
        description="Préférences de l'appelant (timezone, voix TTS, recherche web par défaut, skills).",
        type_response="model",
        unset=False,
    )  # type: ignore
    async def _ipc_get_profile(self, payload) -> dict:
        """Renvoie les préférences d'un utilisateur, ou les défauts (UTC,
        pas de préférence) si aucun profil n'a encore été créé — jamais
        d'erreur pour « profil absent », c'est l'état normal avant le
        premier GET/PATCH /app/profile/me."""
        try:
            async with self._db.session() as session:  # type: ignore
                profile = (
                    await session.execute(
                        select(Profile).where(
                            Profile.tenant_id == payload.tenant_id, Profile.user_id == payload.user_id
                        )
                    )
                ).scalar_one_or_none()
            if profile is None:
                return ok(
                    timezone="UTC",
                    language=None,
                    preferred_llm_provider=None,
                    preferred_tts_voice=None,
                    preferred_tts_speaker=None,
                    preferred_tts_english_voice=None,
                    default_force_web_search=False,
                    notify_reminders_email=False,
                    notify_reminders_whatsapp=False,
                    whatsapp_notify_number=None,
                    skills={},
                )
            return ok(
                timezone=profile.timezone,
                language=profile.language,
                preferred_llm_provider=profile.preferred_llm_provider,
                preferred_tts_voice=profile.preferred_tts_voice,
                # Le locuteur doit voyager avec la voix : sans lui, le choix serait perdu à chaque tour.
                preferred_tts_speaker=profile.preferred_tts_speaker,
                preferred_tts_english_voice=profile.preferred_tts_english_voice,
                default_force_web_search=profile.default_force_web_search,
                notify_reminders_email=profile.notify_reminders_email,
                notify_reminders_whatsapp=profile.notify_reminders_whatsapp,
                whatsapp_notify_number=profile.whatsapp_notify_number,
                # Réglages de skills : sans eux, le chat ne voyait JAMAIS une skill désactivée par
                # l'utilisateur (le filtre d'outils retombait sur « tout activé »).
                skills=current_skills(profile),
            )
        except Exception as exc:
            return error(f"Lecture du profil échouée : {exc}", code="error")
