from .atlas import FontAtlas, CHARSET
from .base import TextComponent
from .decipher import DecipherText
from .typeon import TypeOnText

#: name -> class, used by Scene(text_style=...)
TEXT_STYLES = {
    "decipher": DecipherText,
    "typeon": TypeOnText,
}

__all__ = ["FontAtlas", "CHARSET", "TextComponent", "DecipherText", "TypeOnText", "TEXT_STYLES"]
