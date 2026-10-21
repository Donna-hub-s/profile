from __future__ import annotations

from zoneinfo import ZoneInfoNotFoundError, ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from xcore.kernel.api import AuthPayload, get_current_user

from ..models import Profile
from ..schemas import ProfileOut, ProfileUpdateRequest
from ..skills_store import current_skills, merge_skills


def _tenant_of(current_user: AuthPayload) -> str:
    tenant_id = current_user.get("tenant_id") or (current_user.get("user") or {}).get("tenant_id")
    if not tenant_id:
        raise HTTPException(403, "Aucun espace de travail sélectionné.")
    return tenant_id


def _to_out(profile: Profile) -> ProfileOut:
    return ProfileOut(
        display_name=profile.display_name,
        avatar_url=profile.avatar_url,
        timezone=profile.timezone,
        language=profile.language,
        preferred_llm_provider=profile.preferred_llm_provider,
        preferred_tts_voice=profile.preferred_tts_voice,
        preferred_tts_speaker=profile.preferred_tts_speaker,
        preferred_tts_english_voice=profile.preferred_tts_english_voice,
        default_force_web_search=profile.default_force_web_search,
        notify_reminders_email=profile.notify_reminders_email,
        notify_reminders_whatsapp=profile.notify_reminders_whatsapp,
        whatsapp_notify_number=profile.whatsapp_notify_number,
        theme=profile.theme,
        date_format=profile.date_format,
        measurement_system=profile.measurement_system,
        skills=current_skills(profile),
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


def profile_router(db) -> APIRouter:
    router = APIRouter(tags=["profile"])

    async def _get_or_create(session, tenant_id: str, user_id: str) -> Profile:
        profile = (
            await session.execute(
                select(Profile).where(Profile.tenant_id == tenant_id, Profile.user_id == user_id)
            )
        ).scalar_one_or_none()
        if profile is None:
            profile = Profile(tenant_id=tenant_id, user_id=user_id)
            session.add(profile)
            await session.flush()
        return profile

    @router.get("/me", summary="Mon profil et mes préférences", response_model=ProfileOut)
    async def get_my_profile(current_user: AuthPayload = Depends(get_current_user)) -> ProfileOut:
        tenant_id = _tenant_of(current_user)
        async with db.session() as session:
            profile = await _get_or_create(session, tenant_id, current_user["sub"])
            return _to_out(profile)

    @router.patch("/me", summary="Modifier mon profil et mes préférences", response_model=ProfileOut)
    async def update_my_profile(
        body: ProfileUpdateRequest,
        current_user: AuthPayload = Depends(get_current_user),
    ) -> ProfileOut:
        tenant_id = _tenant_of(current_user)
        if body.timezone is not None:
            try:
                ZoneInfo(body.timezone)
            except ZoneInfoNotFoundError:
                raise HTTPException(400, f"Fuseau horaire invalide : '{body.timezone}' (nom IANA attendu, ex. 'Europe/Paris').")

        async with db.session() as session:
            profile = await _get_or_create(session, tenant_id, current_user["sub"])
            for field in (
                "display_name",
                "avatar_url",
                "timezone",
                "language",
                "preferred_llm_provider",
                "preferred_tts_voice",
                "preferred_tts_speaker",
                "preferred_tts_english_voice",
                "default_force_web_search",
                "notify_reminders_email",
                "notify_reminders_whatsapp",
                "whatsapp_notify_number",
                "theme",
                "date_format",
                "measurement_system",
            ):
                value = getattr(body, field)
                if value is not None:
                    setattr(profile, field, value)
            if body.skills:
                merge_skills(profile, body.skills)
            await session.flush()
            return _to_out(profile)

    return router
