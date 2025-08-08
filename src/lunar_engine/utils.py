from .text import TextEffects, FgColors


def pretty_format_error(msg: str, e: str | None = None) -> str:
    """Formats an error message for pretty printing."""
    base = f"{TextEffects.Bold}{FgColors.Red}{msg}{TextEffects.Reset}"
    if e:
        base += f" {FgColors.Red}{e}{TextEffects.Reset}"
    return base
