from typing import Callable
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer
from prompt_toolkit.history import History, InMemoryHistory
from prompt_toolkit.styles import BaseStyle
from prompt_toolkit.auto_suggest import AutoSuggest, AutoSuggestFromHistory
from prompt_toolkit.clipboard import Clipboard, InMemoryClipboard
from .exceptions import LunarEngineInterrupt


class Prompt:
    _prompt: str
    _rprompt: str | None
    _completer: Completer | None
    _auto_suggest: AutoSuggest | None
    _history: History | None
    _clipboard: Clipboard | None
    _style: BaseStyle | None
    _session: PromptSession[str]
    _running: bool

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
        return self._session.prompt(self._prompt, rprompt=self._rprompt)

    def run_loop(self, callback: Callable[[str], None] | None = None) -> None:
        """
        Continuously prompt for input until interrupted.
        If a callback is provided, it will be called with each input string.
        """
        try:
            while self._running:
                user_input = self.get_input()
                if callback:
                    callback(user_input)
        except Exception:
            self._running = False
            raise
