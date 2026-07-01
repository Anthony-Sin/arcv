"""TypeOnText — typewriter reveal with a blinking cursor."""

from __future__ import annotations

import math
from typing import List, Tuple

from .base import TextComponent


class TypeOnText(TextComponent):
    def _resolve(self, text: str, progress: float, time: float, li: int) -> Tuple[List[Tuple[int, str]], int]:
        revealed = int(math.floor(progress * len(text)))
        out = [(k, text[k]) for k in range(revealed)]
        cursor = revealed if revealed < len(text) else -1
        return out, cursor
