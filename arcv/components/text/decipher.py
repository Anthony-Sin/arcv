"""DecipherText — Arwes scramble/decode labels.

Characters past the reveal point show a random glyph from the charset, re-picked
a few times per second, until the reveal sweep passes them.
"""

from __future__ import annotations

from typing import List, Tuple

from .base import TextComponent

_SCRAMBLE_HZ = 14.0


class DecipherText(TextComponent):
    def _resolve(self, text: str, progress: float, time: float, li: int) -> Tuple[List[Tuple[int, str]], int]:
        revealed = int(round(progress * len(text)))
        bucket = int(time * _SCRAMBLE_HZ)
        out: List[Tuple[int, str]] = []
        for k, ch in enumerate(text):
            if ch == " ":
                continue
            if k < revealed:
                out.append((k, ch))
            else:
                seed = (bucket * 73856093) ^ (k * 19349663) ^ (li * 83492791)
                out.append((k, self._scramble(seed & 0x7FFFFFFF)))
        return out, -1
