from enum import Enum
from typing import override


def _esc(*arg: int) -> str:
    esc = "\033["
    for i, code in enumerate(arg):
        esc += str(code)
        if i < len(arg) - 1:
            esc += ";"
    return esc + "m"


class FgColors(Enum):
    """ANSI constants for foreground colors."""

    Black = _esc(30)
    Red = _esc(31)
    Green = _esc(32)
    Yellow = _esc(33)
    Blue = _esc(34)
    Magenta = _esc(35)
    Cyan = _esc(36)
    White = _esc(37)
    Gray = _esc(90)

    @override
    def __str__(self) -> str:
        return self.value


class BgColors(Enum):
    """ANSI constants for background colors."""

    Black = _esc(40)
    Red = _esc(41)
    Green = _esc(42)
    Yellow = _esc(43)
    Blue = _esc(44)
    Magenta = _esc(45)
    Cyan = _esc(46)
    White = _esc(47)
    Gray = _esc(90)

    @override
    def __str__(self) -> str:
        return self.value


class TextEffects(Enum):
    """ANSI constants for text effects, e.g., bold, underline."""

    Reset = _esc(0)
    Bold = _esc(1)
    Underline = _esc(4)

    @override
    def __str__(self) -> str:
        return self.value
