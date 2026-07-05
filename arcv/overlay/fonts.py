"""Optional helper — register a few extra system faces for typographic variety.

The core renderer bundles exactly one face (Share Tech Mono). anime.js-style HUDs
usually mix type: a condensed display face for headings, a machine/OCR face for
codes, a DIN-ish face for labels, a terminal face for data. Fonts can't be bundled
(licensing + repo size), so this maps a handful of *roles* to candidate system
font paths per platform and registers whichever actually load — gracefully
falling back to the bundled face when none are present (so it still runs off
Windows, just with less variety).

    from arcv.overlay import Draw, fonts
    d = Draw(ov)
    fonts.register_hud_fonts(d)          # adds display/ocr/din/term where available
    d.text("BOOT", 20, 20, 40, C, font="display")
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional

# role -> candidate font files, most-preferred first, across platforms.
FONT_ROLES: Dict[str, List[str]] = {
    "display": [
        "C:/Windows/Fonts/AGENCYB.TTF",     # Agency FB Bold (condensed sci-fi)
        "C:/Windows/Fonts/BAHNSCHRIFT.TTF",
        "C:/Windows/Fonts/impact.ttf",
        "/Library/Fonts/Impact.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ],
    "ocr": [
        "C:/Windows/Fonts/OCRAEXT.TTF",     # OCR-A Extended (machine-readable)
        "C:/Windows/Fonts/consolab.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
    ],
    "din": [
        "C:/Windows/Fonts/bahnschrift.ttf",  # DIN-like technical
        "C:/Windows/Fonts/tahoma.ttf",
        "/Library/Fonts/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ],
    "term": [
        "C:/Windows/Fonts/consola.ttf",     # Consolas
        "C:/Windows/Fonts/cour.ttf",
        "/System/Library/Fonts/Menlo.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    ],
}


def _resolve(paths: List[str]) -> Optional[str]:
    for p in paths:
        if os.path.exists(p):
            return p
    return None


def _text_batch(target):
    """Accept a TextBatch, a Draw, or an Overlay/FlatOverlay and return the batch."""
    if hasattr(target, "add_font"):
        return target
    if hasattr(target, "ov"):                 # Draw
        return target.ov.text
    if hasattr(target, "text") and hasattr(target.text, "add_font"):  # Overlay
        return target.text
    raise TypeError(f"cannot register fonts on {type(target).__name__}")


def register_hud_fonts(target, roles=None, size: int = 42) -> List[str]:
    """Register the named HUD faces on ``target`` (TextBatch / Draw / Overlay).

    Returns the list of role names registered. Roles whose candidate files are all
    missing still register (so ``font="display"`` never errors) but resolve to the
    bundled face. Pass ``roles`` to limit which roles to add.
    """
    tb = _text_batch(target)
    names = list(roles) if roles else list(FONT_ROLES.keys())
    for name in names:
        path = _resolve(FONT_ROLES.get(name, []))
        tb.add_font(name, font_path=path, font_size=size)
    return names


def available_roles() -> Dict[str, Optional[str]]:
    """Map each role to the font path that would be used (or ``None`` -> fallback)."""
    return {name: _resolve(paths) for name, paths in FONT_ROLES.items()}
