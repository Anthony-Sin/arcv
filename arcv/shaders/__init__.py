"""GLSL shader source loader with a tiny ``#include`` resolver.

Shaders live alongside this module as ``.vert`` / ``.frag`` / ``.glsl`` files.
``load(name)`` returns the source string with any ``#include "other.glsl"``
lines inlined (each file included at most once). All shaders target GLSL
``330 core`` for broad compatibility (including Intel integrated GPUs).
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

_DIR = Path(__file__).parent
_INCLUDE = re.compile(r'^[ \t]*#include[ \t]+"([^"]+)"[ \t]*$', re.M)


def _resolve(name: str, seen: set) -> str:
    text = (_DIR / name).read_text(encoding="utf-8")

    def repl(match: "re.Match") -> str:
        inc = match.group(1)
        if inc in seen:
            return ""
        seen.add(inc)
        return _resolve(inc, seen)

    return _INCLUDE.sub(repl, text)


@lru_cache(maxsize=None)
def load(name: str) -> str:
    return _resolve(name, set())
