from typing import Self, override
from enum import Enum
from collections.abc import Iterator
from prompt_toolkit.formatted_text import OneStyleAndTextTuple, StyleAndTextTuples


class AnsiColor(Enum):
    DEFAULT = "ansidefault"
    BLACK = "ansiblack"
    RED = "ansired"
    GREEN = "ansigreen"
    YELLOW = "ansiyellow"
    BLUE = "ansiblue"
    MAGENTA = "ansimagenta"
    CYAN = "ansicyan"
    GRAY = "ansigray"
    BRIGHT_BLACK = "ansibrightblack"
    BRIGHT_RED = "ansibrightred"
    BRIGHT_GREEN = "ansibrightgreen"
    BRIGHT_YELLOW = "ansibrightyellow"
    BRIGHT_BLUE = "ansibrightblue"
    BRIGHT_MAGENTA = "ansibrightmagenta"
    BRIGHT_CYAN = "ansibrightcyan"
    WHITE = "ansiwhite"


class TrueColor(Enum):
    DEFAULT = "default"
    BLACK = "black"
    RED = "red"
    GREEN = "green"
    YELLOW = "yellow"
    BLUE = "blue"
    MAGENTA = "magenta"
    CYAN = "cyan"
    WHITE = "white"


type Color = AnsiColor | TrueColor | str


class StyledText:
    """
    Represents styled text segments for prompt_toolkit rendering.
    Compatible with FormattedText with additional features like, built in concatenation
    """

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
    fg: Color | None = None,
    bg: Color | None = None,
    bold: bool = False,
    italic: bool = False,
    underline: bool = False,
    strike: bool = False,
    blink: bool = False,
    reverse: bool = False,
    hidden: bool = False,
    dim: bool = False,
) -> StyledText:
    """
    Create a StyledText object with specified colors and text effects.

    Args:
        text: The content to style.
        fg: Foreground color (AnsiColor, TrueColor, or string).
        bg: Background color (AnsiColor, TrueColor, or string).
        bold: Whether to apply bold styling.
        italic: Whether to apply italic styling.
        underline: Whether to underline the text.
        strike: Whether to apply strikethrough.
        blink: Whether to apply blinking effect.
        reverse: Whether to reverse foreground and background colors.
        hidden: Whether to hide the text.
        ~dim: Whether to dim the text.

    Returns:
        A StyledText object containing the styled text - compatible with
         prompt_toolkit's FormattedText
    """

    def normalize_color(c: Color) -> str:
        return c.value if isinstance(c, Enum) else c

    style_parts: list[str] = []
    if fg:
        style_parts.append(f"fg:{normalize_color(fg)}")
    if bg:
        style_parts.append(f"bg:{normalize_color(bg)}")
    if bold:
        style_parts.append("bold")
    if italic:
        style_parts.append("italic")
    if underline:
        style_parts.append("underline")
    if strike:
        style_parts.append("strike")
    if blink:
        style_parts.append("blink")
    if reverse:
        style_parts.append("reverse")
    if hidden:
        style_parts.append("hidden")
    if dim:
        # style_parts.append("dim")
        raise NotImplementedError("Available in a future version of prompt_toolkit")

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
