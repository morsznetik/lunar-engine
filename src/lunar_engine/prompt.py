from typing import Self, override, Final
from types import TracebackType
from collections.abc import Generator, Iterator
from dataclasses import dataclass
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


@dataclass(frozen=True)
class ParsedCommand:
    command_parts: list[str]
    arg_parts: list[str]
    current_word: str
    ends_with_space: bool


@dataclass(frozen=True)
class CompletionContext:
    command: CommandInfo | None
    parsed: ParsedCommand
    used_keyword_params: set[str]
    positional_count: int


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

    # ============================================================================
    # API
    # ============================================================================

    @override
    def get_completions(
        self, document: Document, complete_event: CompleteEvent
    ) -> Iterator[Completion]:
        text = document.text_before_cursor

        if not text.strip():
            yield from self._complete_root_commands("")
            return

        parsed = self._parse_command_line(text)
        command = self._resolve_command(parsed.command_parts)
        context = self._build_completion_context(command, parsed)

        yield from self._generate_completions(context)

    # ============================================================================
    # PARSING & RESOLUTION
    # ============================================================================

    def _parse_command_line(self, text: str) -> ParsedCommand:
        words = text.split()
        ends_with_space = text.endswith(" ")

        if not words:
            return ParsedCommand([], [], "", ends_with_space)

        # extract current word being typed
        if ends_with_space:
            current_word = ""
        else:
            current_word = words[-1]
            words = words[:-1]

        # split into command parts and argument parts
        command_parts, arg_parts = self._split_command_and_args(words)

        return ParsedCommand(command_parts, arg_parts, current_word, ends_with_space)

    def _split_command_and_args(self, words: list[str]) -> tuple[list[str], list[str]]:
        if not words:
            return [], []

        command_parts = [words[0]]
        remaining = words[1:]

        # follow command path through subcommands
        current_cmd = self._registry[words[0]]
        if current_cmd:
            for word in remaining:
                if word.startswith("--") or word not in current_cmd.children:
                    break
                command_parts.append(word)
                current_cmd = current_cmd.children[word]

            # everything after command path is arguments
            arg_parts = remaining[len(command_parts) - 1 :]
        else:
            arg_parts = remaining

        return command_parts, arg_parts

    def _resolve_command(self, command_parts: list[str]) -> CommandInfo | None:
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

    def _build_completion_context(
        self, command: CommandInfo | None, parsed: ParsedCommand
    ) -> CompletionContext:
        used_keyword_params: set[str] = set()
        positional_count = 0

        # check if any arguments are already used
        for arg in parsed.arg_parts:
            if arg.startswith("--"):
                param_name = arg.lstrip("-").split("=")[0]
                used_keyword_params.add(param_name)
            else:
                positional_count += 1

        return CompletionContext(command, parsed, used_keyword_params, positional_count)

    # ============================================================================
    # COMPLETION GENERATION
    # ============================================================================

    def _generate_completions(self, context: CompletionContext) -> Iterator[Completion]:
        if not context.command:
            yield from self._complete_root_commands(context.parsed.current_word)
            return

        if self._should_complete_subcommands(context):
            yield from self._complete_subcommands(context)
        else:
            yield from self._complete_arguments(context)

    def _should_complete_subcommands(self, context: CompletionContext) -> bool:
        command = context.command
        parsed = context.parsed

        # no subcommands
        if not command or not command.children:
            return False

        # already have arguments or flags
        if parsed.arg_parts or any(word.startswith("--") for word in parsed.arg_parts):
            return False

        # current word is a flag
        if parsed.current_word.startswith("--"):
            return False

        # at space after command with no args
        if parsed.ends_with_space and not parsed.arg_parts:
            return True

        # compare fuzzy match scores to decide
        if parsed.current_word:
            subcommand_score = self._get_best_subcommand_score(
                command, parsed.current_word
            )
            argument_score = self._get_best_argument_score(command, parsed.current_word)
            return subcommand_score > argument_score

        return True

    def _complete_root_commands(self, current_word: str) -> Iterator[Completion]:
        for cmd_info in self._registry:
            if cmd_info and cmd_info.parent is None:
                if self._matches_fuzzy(current_word, cmd_info.name):
                    yield self._create_completion(
                        cmd_info.name,
                        current_word,
                        display_meta=cmd_info.description or "command",
                    )

    def _complete_subcommands(self, context: CompletionContext) -> Iterator[Completion]:
        command = context.command
        current_word = context.parsed.current_word

        if not command or not command.children:
            return

        for name, cmd in command.children.items():
            if self._matches_fuzzy(current_word, name):
                yield self._create_completion(
                    name, current_word, display_meta=cmd.description or "subcommand"
                )

    def _complete_arguments(self, context: CompletionContext) -> Iterator[Completion]:
        if not context.command:
            return

        sig = inspect.signature(context.command.func)

        # skip commands with **kwargs for now
        if any(p.kind == p.VAR_KEYWORD for p in sig.parameters.values()):
            return

        params = list(sig.parameters.values())
        positional_params = [
            p for p in params if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)
        ]

        for param in params:
            completion = self._create_parameter_completion(
                param, context, positional_params
            )
            if completion:
                yield completion

    def _create_parameter_completion(
        self,
        param: inspect.Parameter,
        context: CompletionContext,
        positional_params: list[inspect.Parameter],
    ) -> Completion | None:
        # skip already used keyword parameters
        if (
            param.name in context.used_keyword_params
            and param.kind != param.VAR_POSITIONAL
        ):
            return None

        # handle different parameter types
        if param.kind == param.KEYWORD_ONLY:
            complete_text = f"--{param.name}"
            display_text = complete_text

        elif param.kind == param.VAR_POSITIONAL:
            complete_text = param.name.lstrip("*")
            display_text = f"*{complete_text}"

        else:
            # regular positional parameter
            if not self._should_suggest_positional(param, context, positional_params):
                return None
            complete_text = param.name
            display_text = param.name

        # check fuzzy match
        if not self._matches_fuzzy(context.parsed.current_word, complete_text):
            return None

        # build display metadata
        # ignore param.default return type because the type checker cannot infer it statically
        default = param.default  # pyright: ignore[reportAny]
        type_str = self._format_parameter_type(param)
        if default != inspect.Parameter.empty:
            type_str += f" = {default!r}"
            display_text += " (optional)"
        elif "| None" in type_str:
            display_text += " (optional)"

        return self._create_completion(
            complete_text,
            context.parsed.current_word,
            display=display_text,
            display_meta=type_str,
        )

    def _should_suggest_positional(
        self,
        param: inspect.Parameter,
        context: CompletionContext,
        positional_params: list[inspect.Parameter],
    ) -> bool:
        if not self._strict_positional or context.positional_count == 0:
            return True

        try:
            param_index = positional_params.index(param)
            return param_index == context.positional_count
        except ValueError:
            return False

    # ============================================================================
    # UTILITIES
    # ============================================================================

    def _get_fuzzy_ratio(self, s1: str, s2: str) -> float:
        return SequenceMatcher(None, s1.lower(), s2.lower()).ratio()

    def _matches_fuzzy(self, input_word: str, target: str) -> bool:
        if not input_word:
            return True
        return self._get_fuzzy_ratio(input_word, target) >= self._min_match_score

    def _get_best_subcommand_score(
        self, command: CommandInfo, current_word: str
    ) -> float:
        return max(
            (
                self._get_fuzzy_ratio(current_word, name)
                for name in command.children.keys()
            ),
            default=0,
        )

    def _get_best_argument_score(
        self, command: CommandInfo, current_word: str
    ) -> float:
        sig = inspect.signature(command.func)
        best_score = 0

        for param in sig.parameters.values():
            if param.kind != param.VAR_KEYWORD:
                param_name = param.name.lstrip("*")
                score = self._get_fuzzy_ratio(current_word, param_name)
                best_score = max(best_score, score)
            else:
                raise NotImplementedError

        return best_score

    def _format_parameter_type(self, param: inspect.Parameter) -> str:
        # ignore param.annotation return type because the type checker cannot infer it statically
        annotation = param.annotation  # pyright: ignore[reportAny]

        # this case shouldn't happen but we handle it anyway
        if annotation == inspect.Parameter.empty:
            return "Any"

        if isinstance(annotation, type):
            return annotation.__name__

        # clean up type string representation
        type_str = str(annotation)  # pyright: ignore[reportAny]
        patterns_to_remove = ["typing.", "class '", "'", "<", ">"]
        for pattern in patterns_to_remove:
            type_str = type_str.replace(pattern, "")

        return type_str

    def _create_completion(
        self,
        text: str,
        current_word: str,
        display: str | None = None,
        display_meta: str | None = None,
    ) -> Completion:
        return Completion(
            text,
            start_position=-len(current_word) if current_word else 0,
            display=display or text,
            display_meta=display_meta,
        )
