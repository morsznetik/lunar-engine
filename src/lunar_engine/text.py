from typing import Literal, Self, override
from enum import Enum
from collections.abc import Iterator
from prompt_toolkit.formatted_text import OneStyleAndTextTuple, StyleAndTextTuples


type AnsiColor = Literal[
    "ansidefault",
    "ansiblack",
    "ansired",
    "ansigreen",
    "ansiyellow",
    "ansiblue",
    "ansimagenta",
    "ansicyan",
    "ansigray",
    "ansibrightblack",
    "ansibrightred",
    "ansibrightgreen",
    "ansibrightyellow",
    "ansibrightblue",
    "ansibrightmagenta",
    "ansibrightcyan",
    "ansiwhite",
]

type TrueColor = Literal[
    "black",
    "red",
    "green",
    "yellow",
    "blue",
    "magenta",
    "cyan",
    "white",
    "brightblack",
    "brightred",
    "brightgreen",
    "brightyellow",
    "brightblue",
    "brightmagenta",
    "brightcyan",
    "brightwhite",
]

type Color = AnsiColor | TrueColor


class StyledText:
    parts: list[OneStyleAndTextTuple]

    def __init__(self, parts: list[OneStyleAndTextTuple]) -> None:
        self.parts = parts

    def __pt_formatted_text__(self) -> StyleAndTextTuples:
        return self.parts

    def __add__(self, other: Self | str) -> Self:
        cls = type(self)
        if isinstance(other, str):
            return cls(self.parts + [("", other)])
        return cls(self.parts + other.parts)

    def __radd__(self, other: Self | str) -> Self:
        cls = type(self)
        if isinstance(other, str):
            return cls([("", other)] + self.parts)
        return cls(other.parts + self.parts)

    def __iter__(self) -> Iterator[OneStyleAndTextTuple]:
        return iter(self.parts)


def text(
    text: str,
    *,
    fg: Color | str | None = None,
    bg: Color | str | None = None,
    bold: bool = False,
    italic: bool = False,
    underline: bool = False,
) -> StyledText:
    style_parts: list[str] = []
    if fg:
        style_parts.append(f"fg:{fg}")
    if bg:
        style_parts.append(f"bg:{bg}")
    if bold:
        style_parts.append("bold")
    if italic:
        style_parts.append("italic")
    if underline:
        style_parts.append("underline")
    style = " ".join(style_parts)
    return StyledText([(style, text)])


# alias
t = text


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
