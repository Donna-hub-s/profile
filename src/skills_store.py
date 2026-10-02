"""Réglages de skills d'un profil : validation, fusion et migration des anciens flags.

Le plugin profile ne connaît pas le catalogue des skills (chat/src/skills.py) : il stocke des
réglages {identifiant: bool} et laisse le chat décider de leur sens. Il valide seulement la forme
(identifiant en minuscules/chiffres/underscore, nombre borné), pour qu'une requête ne puisse pas
gonfler la ligne de profil.
"""

from __future__ import annotations

import re

from sqlalchemy import select

from .models import Profile

SKILL_ID_RE = re.compile(r"^[a-z][a-z0-9_]{0,39}$")
MAX_SKILL_SETTINGS = 64

# Anciennes colonnes (une par skill) -> identifiant de skill. Voir models.Profile (OBSOLÈTES).
LEGACY_SKILL_FLAGS = (
    "enable_web_search",
    "enable_sub_agents",
    "enable_reminders",
    "enable_memory",
    "enable_email_calendar",
    "enable_drive",
    "enable_create_document",
)


def current_skills(profile: Profile) -> dict[str, bool]:
    """Réglages valides du profil (une valeur corrompue en base est ignorée plutôt que de casser le GET)."""
    stored = profile.skills if isinstance(profile.skills, dict) else {}
    return {k: v for k, v in stored.items() if isinstance(k, str) and isinstance(v, bool)}


def merge_skills(profile: Profile, changes: dict[str, bool]) -> None:
    # Nouveau dict : SQLAlchemy ne détecte pas la mutation en place d'une colonne JSON.
    profile.skills = {**current_skills(profile), **changes}


async def migrate_legacy_skill_flags(session) -> int:
    """Reprend les skills désactivées AVANT le passage au champ `skills` : un flag `enable_x` à False
    devient `skills["x"] = False`, sauf si un réglage explicite existe déjà. Idempotent (rejouable à
    chaque démarrage) ; renvoie le nombre de profils modifiés."""
    changed = 0
    for profile in (await session.execute(select(Profile))).scalars().all():
        settings = current_skills(profile)
        seeded = dict(settings)
        for flag in LEGACY_SKILL_FLAGS:
            skill_id = flag.removeprefix("enable_")
            if getattr(profile, flag) is False and skill_id not in seeded:
                seeded[skill_id] = False
        if seeded != settings:
            profile.skills = seeded
            changed += 1
    return changed
