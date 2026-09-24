"""Country packs: everything that changes when a candidate searches in another country.

A pack is a folder under backend/countries/<code>/ holding `pack.yml` (names, time
zone, paper, spelling, location matching, wording) and the templates a new profile
starts from (`sponsorship.yml`, `regions.yml`, `portals.yml`, `guides/*.md`). The
intake copies those templates into the profile's own data/config/, so each profile
owns and can edit its rules; the pack itself is never written.

A workspace's pack comes from `country_pack` in its profile.yml, else from
`location_preferences.country`. Annie's profile names "United States", so she
keeps the US pack without any change to her files.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from backend.paths import COUNTRIES

DEFAULT_CODE = "us"


@dataclass(frozen=True)
class Pack:
    code: str
    name: str
    data: dict = field(repr=False)

    # --- identity --------------------------------------------------------
    @property
    def folder(self) -> Path:
        return COUNTRIES / self.code

    @property
    def adjective(self) -> str:
        """'US' / 'Irish': as in 'US postings'."""
        return str(self.data.get("adjective") or self.name)

    @property
    def names(self) -> list[str]:
        return [self.name, *[str(n) for n in self.data.get("names") or []]]

    @property
    def timezone(self) -> str:
        return str(self.data.get("timezone") or "UTC")

    @property
    def paper(self) -> str:
        return str(self.data.get("paper") or "letter")

    @property
    def paper_label(self) -> str:
        return str(self.data.get("paper_label") or ("US Letter" if self.paper == "letter" else "A4"))

    @property
    def spelling(self) -> str:
        return str(self.data.get("spelling") or "")

    @property
    def sponsor_index(self) -> str | None:
        """'uscis' when the USCIS H-1B employer history applies; None otherwise."""
        return self.data.get("sponsor_index") or None

    @property
    def tier_labels(self) -> dict:
        """The tier wording of this country's gate (sponsorship.yml `tier_labels`); empty
        where the page's own wording applies (the US pack)."""
        try:
            rules = yaml.safe_load(self.template("sponsorship.yml").read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            return {}
        return {str(k): str(v) for k, v in (rules.get("tier_labels") or {}).items()}

    def text(self, key: str, **values: Any) -> str:
        """A wording from the pack's `messages`, with {placeholders} filled."""
        template = str((self.data.get("messages") or {}).get(key, ""))
        return template.format(**values) if values else template

    # --- location --------------------------------------------------------
    def location_ok(self, location: str) -> bool:
        """True when the posting's location is in this country (or remote within it)."""
        if self.code == "us":
            from backend.job_quality import is_us_location

            return is_us_location(location)
        return _matcher(self.code).matches(location or "")

    def open_remote(self, location: str) -> bool:
        """A bare or region-wide 'Remote': not a refusal, checked at research time."""
        patterns = (self.data.get("location") or {}).get("open_remote") or [r"\s*remote\s*"]
        return any(re.fullmatch("(?i)" + p, location or "") for p in patterns)

    # --- templates a new profile starts from ----------------------------
    def template(self, relative: str) -> Path:
        return self.folder / relative


class _Matcher:
    """Location matching from a pack's `location` block (all regex fragments)."""

    def __init__(self, spec: dict):
        def alternation(key):
            items = [str(i) for i in spec.get(key) or []]
            return re.compile(r"(?i)\b(?:" + "|".join(items) + r")\b") if items else None

        self.strong = alternation("strong")          # the country's own name(s)
        self.places = alternation("places")          # cities, counties, regions
        self.remote = alternation("remote")          # "Remote (Ireland)" and the like
        self.strip = alternation("strip_before_match")  # "Northern Ireland" is not Ireland
        self.foreign = alternation("foreign")        # other countries that outweigh a bare city
        self.twin_markers = [re.compile(p) for p in spec.get("twin_markers") or []]

    def matches(self, location: str) -> bool:
        text = self.strip.sub(" ", location) if self.strip else location
        if self.strong and self.strong.search(text):
            return True
        if self.remote and self.remote.search(text):
            return True
        if not (self.places and self.places.search(text)):
            return False
        # A city that also exists elsewhere (Dublin, OH; Waterford, MI) needs no foreign marker.
        if any(marker.search(location) for marker in self.twin_markers):
            return False
        return not (self.foreign and self.foreign.search(text))


@lru_cache(maxsize=None)
def _matcher(code: str) -> _Matcher:
    return _Matcher(load_pack(code).data.get("location") or {})


@lru_cache(maxsize=None)
def load_pack(code: str) -> Pack:
    code = (code or DEFAULT_CODE).lower()
    path = COUNTRIES / code / "pack.yml"
    if not path.is_file():
        raise ValueError(f"No country pack '{code}'")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return Pack(code=code, name=str(data.get("name") or code.upper()), data=data)


def available() -> list[Pack]:
    return [load_pack(p.name) for p in sorted(COUNTRIES.iterdir()) if (p / "pack.yml").is_file()]


def code_for(profile: dict | None) -> str:
    """The pack a profile uses: `country_pack`, else its target country's name."""
    profile = profile or {}
    code = str(profile.get("country_pack") or "").strip().lower()
    if code and (COUNTRIES / code / "pack.yml").is_file():
        return code
    country = str((profile.get("location_preferences") or {}).get("country") or "").strip().casefold()
    if country:
        for pack in available():
            if country in {n.casefold() for n in pack.names} or country == pack.code:
                return pack.code
    return DEFAULT_CODE


_PROFILE_CACHE: dict[str, tuple[int, str]] = {}


def pack_for(root) -> Pack:
    """The pack for the workspace rooted at `root` (read from its profile.yml)."""
    path = Path(root) / "data/config/profile.yml"
    try:
        stamp = path.stat().st_mtime_ns
    except OSError:
        return load_pack(DEFAULT_CODE)
    cached = _PROFILE_CACHE.get(str(path))
    if not cached or cached[0] != stamp:
        try:
            profile = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            profile = {}
        cached = (stamp, code_for(profile))
        _PROFILE_CACHE[str(path)] = cached
    return load_pack(cached[1])
