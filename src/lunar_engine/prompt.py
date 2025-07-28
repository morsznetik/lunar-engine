from typing import Any, Self, override, Final
from types import TracebackType
from collections.abc import Generator, Iterator
from difflib import SequenceMatcher
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.history import History, InMemoryHistory
from prompt_toolkit.styles import BaseStyle
from prompt_toolkit.auto_suggest import AutoSuggest, AutoSuggestFromHistory
from prompt_toolkit.clipboard import Clipboard, InMemoryClipboard
from prompt_toolkit.document import Document
from prompt_toolkit.completion import CompleteEvent
from .exceptions import InterruptException
from .command import get_registry, CommandRegistry, CommandInfo
import inspect


class Prompt:
    """
    Prompt for Lunar Engine. Throws InterruptException on KeyboardInterrupt and EOFError.

    Basic usage:
        >>> with Prompt('> ') as p:
        ...     for user_input in p:
        ...         print(user_input)
        >>> assert not p

    Supports context management and iteration. Evaluates as True while the prompt loop is active.
    """

    _prompt: str
    _rprompt: str | None
    _completer: Final[Completer | None]
    _auto_suggest: Final[AutoSuggest | None]
    _history: Final[History | None]
    _clipboard: Final[Clipboard | None]
    _style: Final[BaseStyle | None]
    _session: Final[PromptSession[str]]
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
        self._completer = completer or CommandCompleter()
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
            interrupt_exception=InterruptException,
            eof_exception=InterruptException,
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

    def __iter__(self) -> Generator[str, None, None]:
        # catch all exceptions to ensure we don't leave the prompt in a bad state
        # for an edge case where we are not in context but we try to iterate over it
        try:
            # we have to be in context to iterate safely
            if not self._in_context:
                raise RuntimeError("Prompt can only be iterated within its context")
            while self._running:
                yield self.get_input()
        except Exception:
            self._running = False
            raise


class CommandCompleter(Completer):
    """
    Simple fuzzy command completer for Lunar Engine that suggests commands and their arguments.

    Args:
        min_match_score: Minimum fuzzy match score for suggestions
        strict_positional: Whether to enforce strict positional argument order
    """

    _registry: CommandRegistry
    _min_match_score: Final[float]
    _strict_positional: Final[bool]

    def __init__(
        self,
        min_match_score: float = 0.3,
        strict_positional: bool = True,
    ) -> None:
        self._registry = get_registry()
        self._min_match_score = min_match_score
        self._strict_positional = strict_positional

    def _get_fuzzy_ratio(self, s1: str, s2: str) -> float:
        """Calculate fuzzy match ratio between two strings."""
        return SequenceMatcher(None, s1.lower(), s2.lower()).ratio()

    def _get_type_str(self, annotation: inspect.Parameter.empty | type | Any) -> str:
        if annotation == inspect.Parameter.empty:
            return "Any"

        if isinstance(annotation, type):
            return annotation.__name__

        # clean up the type string representation
        type_str = str(annotation)
        patterns_to_remove = ["typing.", "class '", "'", "<", ">"]
        for pattern in patterns_to_remove:
            type_str = type_str.replace(pattern, "")

        return type_str

    def _parse_command_line(self, text: str) -> tuple[list[str], list[str], str]:
        words = text.split()
        if not words:
            return [], [], ""

        # we're starting a new word if the text ends with a space
        if text.endswith(" "):
            current_word = ""
        else:
            current_word = words[-1]
            words = words[:-1]

        # find where command ends and arguments begin
        command_parts = []
        arg_parts = []

        # start with first word as potential command
        if words:
            command_parts = [words[0]]
            remaining = words[1:]

            # walk through remaining words to find command boundary
            current_cmd = self._registry[words[0]]
            if current_cmd:
                for word in remaining:
                    # arguments start with -- or we've hit a word that's not a subcommand
                    if word.startswith("--") or word not in current_cmd.children:
                        break

                    # this word is a subcommand, add it to command path
                    command_parts.append(word)
                    current_cmd = current_cmd.children[word]

                # everything after command path is arguments
                arg_parts = remaining[len(command_parts) - 1 :]

        return command_parts, arg_parts, current_word

    def _get_command_from_path(self, command_parts: list[str]) -> CommandInfo | None:
        if not command_parts:
            return None

        current_cmd = self._registry[command_parts[0]]
        if not current_cmd:
            return None

        for part in command_parts[1:]:
            if part not in current_cmd.children:
                return None
            current_cmd = current_cmd.children[part]

        return current_cmd

    def _should_complete_subcommands(
        self,
        command: CommandInfo,
        arg_parts: list[str],
        current_word: str,
        text_ends_with_space: bool,
    ) -> bool:
        # no subcommands
        if not command.children:
            return False

        # if we have any arguments, complete arguments
        if arg_parts or any(word.startswith("--") for word in arg_parts):
            return False

        # if current word starts with --, complete arguments
        if current_word.startswith("--"):
            return False

        # if we're at a space after the command with no args, complete subcommands
        if text_ends_with_space and not arg_parts:
            return True

        # if current word matches a subcommand better than any argument
        if current_word:
            best_subcommand_score = max(
                (
                    self._get_fuzzy_ratio(current_word, name)
                    for name in command.children.keys()
                ),
                default=0,
            )

            # get best argument score
            sig = inspect.signature(command.func)
            best_arg_score = 0
            for param in sig.parameters.values():
                if param.kind != param.VAR_KEYWORD:  # skip **kwargs
                    param_name = param.name.lstrip("*")  # handle *args
                    score = self._get_fuzzy_ratio(current_word, param_name)
                    best_arg_score = max(best_arg_score, score)
                else:
                    raise NotImplementedError

            # prefer subcommands if they match better
            return best_subcommand_score > best_arg_score

        return True

    def _get_subcommand_completions(
        self, command: CommandInfo, current_word: str
    ) -> Iterator[Completion]:
        for name, cmd in command.children.items():
            if (
                not current_word
                or self._get_fuzzy_ratio(current_word, name) >= self._min_match_score
            ):
                yield Completion(
                    name,
                    start_position=-len(current_word),
                    display=name,
                    display_meta=cmd.description or "subcommand",
                )

    def _get_arg_completions(
        self,
        command: CommandInfo,
        arg_parts: list[str],
        current_word: str,
    ) -> Iterator[Completion]:
        sig = inspect.signature(command.func)

        # skip commands with **kwargs for now
        for param in sig.parameters.values():
            if param.kind == param.VAR_KEYWORD:
                return

        # track used parameters
        used_keyword_params: set[str] = set()
        positional_count = 0

        # parse existing arguments
        for arg in arg_parts:
            if arg.startswith("--"):
                param_name = arg.lstrip("-").split("=")[0]
                used_keyword_params.add(param_name)
            else:
                positional_count += 1

        # get parameter list
        params = list(sig.parameters.values())
        positional_params = [
            p for p in params if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)
        ]

        for param in params:
            param_name = param.name

            # skip already used keyword parameters
            if param_name in used_keyword_params and param.kind != param.VAR_POSITIONAL:
                continue

            # handle different parameter types
            if param.kind == param.KEYWORD_ONLY:
                # always suggest keyword-only as --flag
                complete_text = f"--{param_name}"
                display_text = complete_text

            elif param.kind == param.VAR_POSITIONAL:
                # *args - can always be added (for now)
                complete_text = param_name.lstrip("*")
                display_text = f"*{complete_text}"

            else:
                # regular positional parameter
                # show all arguments when none have been provided yet; otherwise enforce strict order
                if self._strict_positional and positional_count > 0:
                    # in strict mode, only suggest next positional parameter
                    try:
                        param_index = positional_params.index(param)
                        if param_index != positional_count:
                            continue
                    except ValueError:
                        continue

                complete_text = param_name
                display_text = param_name

            # the next 3 type ignores the types for param.annotation, param.default cannot be inferred
            # get type information
            type_str = self._get_type_str(param.annotation)  # pyright: ignore[reportAny]

            # add default value if present
            if param.default != inspect.Parameter.empty:  # pyright: ignore[reportAny]
                type_str += f" = {param.default!r}"  # pyright: ignore[reportAny]
                display_text += " (optional)"
            elif "| None" in type_str:
                display_text += " (optional)"

            # check if this matches current word
            if (
                not current_word
                or self._get_fuzzy_ratio(current_word, complete_text)
                >= self._min_match_score
            ):
                yield Completion(
                    complete_text,
                    start_position=-len(current_word) if current_word else 0,
                    display=display_text,
                    display_meta=type_str,
                )

    def _get_root_command_completions(self, current_word: str) -> Iterator[Completion]:
        for cmd_info in self._registry:
            if cmd_info and cmd_info.parent is None:  # only root commands
                if (
                    not current_word
                    or self._get_fuzzy_ratio(current_word, cmd_info.name)
                    >= self._min_match_score
                ):
                    yield Completion(
                        cmd_info.name,
                        start_position=-len(current_word),
                        display=cmd_info.name,
                        display_meta=cmd_info.description or "command",
                    )

    @override
    def get_completions(
        self, document: Document, complete_event: CompleteEvent
    ) -> Iterator[Completion]:
        text = document.text_before_cursor

        # handle empty input
        if not text.strip():
            # HACK: f the input is empty, we must yield root command completions,
            # otherwise prompt_toolkit's completion menu behaves oddly and doesn't show anything
            yield from self._get_root_command_completions("")
            return

        # parse the command line
        command_parts, arg_parts, current_word = self._parse_command_line(text)

        # if no command parts, complete root commands
        if not command_parts:
            yield from self._get_root_command_completions(current_word)
            return

        # get the command
        command = self._get_command_from_path(command_parts)
        if not command:
            # invalid command path, try completing root commands
            yield from self._get_root_command_completions(current_word)
            return

        # determine what to complete
        text_ends_with_space = text.endswith(" ")

        if self._should_complete_subcommands(
            command, arg_parts, current_word, text_ends_with_space
        ):
            yield from self._get_subcommand_completions(command, current_word)
        else:
            yield from self._get_arg_completions(command, arg_parts, current_word)
