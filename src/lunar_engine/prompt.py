from typing import Any, Self
from types import TracebackType
from collections.abc import Generator
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer
from prompt_toolkit.history import History, InMemoryHistory
from prompt_toolkit.styles import BaseStyle
from prompt_toolkit.auto_suggest import AutoSuggest, AutoSuggestFromHistory
from prompt_toolkit.clipboard import Clipboard, InMemoryClipboard
from .exceptions import LunarEngineInterrupt


class Prompt:
    """
    Prompt for Lunar Engine. Throws LunarEngineInterrupt on KeyboardInterrupt and EOFError.

    Basic usage:
        >>> with Prompt('> ') as p:
        ...     for user_input in p:
        ...         print(user_input)
        >>> assert not p

    Supports context management and iteration. Evaluates as True while the prompt loop is active.
    """

    _prompt: str
    _rprompt: str | None
    _completer: Completer | None
    _auto_suggest: AutoSuggest | None
    _history: History | None
    _clipboard: Clipboard | None
    _style: BaseStyle | None
    _session: PromptSession[str]
    _running: bool
    _in_context: bool

    def __init__(
        self,
        prompt: str,
        /,
        *,
        rprompt: str | None = None,
        completer: Completer | None = None,
        auto_suggest: AutoSuggest | None = None,
        history: History | None = None,
        clipboard: Clipboard | None = None,
        style: BaseStyle | None = None,
        session: PromptSession[str] | None = None,
    ) -> None:
        self._prompt = prompt
        self._rprompt = rprompt
        self._completer = completer
        self._history = history or InMemoryHistory()
        self._clipboard = clipboard or InMemoryClipboard()
        self._style = style
        self._auto_suggest = auto_suggest or AutoSuggestFromHistory()
        self._session = session or PromptSession(
            message=self._prompt,
            rprompt=self._rprompt,
            completer=self._completer,
            history=self._history,
            clipboard=self._clipboard,
            style=self._style,
            auto_suggest=self._auto_suggest,
            search_ignore_case=True,
            interrupt_exception=LunarEngineInterrupt,
            eof_exception=LunarEngineInterrupt,
        )
        self._running = True
        self._in_context = False  # track if in context manager

    @property
    def running(self) -> bool:
        """
        Check if the prompt loop is running.
        """
        return self._running

    def get_input(self) -> str:
        """
        Display the prompt and return user input as a string.
        """
        return self._session.prompt()

    def __bool__(self) -> bool:
        return self._running

    def __enter__(self) -> Self:
        # enter context
        self._running = True
        self._in_context = True
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        # clean up state
        self._running = False
        self._in_context = False

    def __iter__(self) -> Generator[str, Any, None]:
        # we have to be in the context to iterate safely
        if not self._in_context:
            raise RuntimeError("Prompt can only be iterated within its context")
        while self._running:
            yield self.get_input()
