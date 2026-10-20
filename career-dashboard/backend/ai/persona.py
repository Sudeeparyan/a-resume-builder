"""Who the agents are working for, in the words their instructions need.

The Template builds a persona per profile and fills ``${name}`` tokens in the
specialists' ``profile_system`` text. This workspace has one person, Annie, and her
specialists carry her own wording in ``system`` (US English, one US Letter page, the
sponsorship gate), so no persona is needed: ``None`` keeps that wording exactly.
"""

from __future__ import annotations


def persona_for(root) -> dict | None:
    return None
