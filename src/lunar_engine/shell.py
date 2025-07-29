from typing import Self, Callable
from enum import Enum, auto
import sys
from lunar_engine.prompt import CommandCompleter, Prompt
from lunar_engine.command import CommandRegistry, get_registry
from lunar_engine.exceptions import InterruptException

type UnknownHandler = Callable[[str], None]
type InterruptHandler = Callable[[], None]
type ErrorHandler = Callable[[Exception], None]
type Handler = Callable[..., None]


class Event(Enum):
    UNKNOWN_COMMAND = auto()
    INTERRUPT = auto()
    COMMAND_ERROR = auto()


def _default_unknown_command(name: str) -> None:
    print(f"Unknown command: {name}")


def _default_interrupt() -> None:
    print("Interrupted.")


def _default_command_error(e: Exception) -> None:
    print(f"Error: {e}")


class HandlerRegistry:
    """Registry for event handlers using decorators."""

    _handlers: dict[Event, Handler]

    def __init__(self) -> None:
        self._handlers = {
            Event.UNKNOWN_COMMAND: _default_unknown_command,
            Event.INTERRUPT: _default_interrupt,
            Event.COMMAND_ERROR: _default_command_error,
        }

    def __getitem__(self, event: Event) -> Handler:
        return self._handlers[event]

    def on_unknown_command(
        self, func: UnknownHandler | None = None
    ) -> UnknownHandler | Callable[[UnknownHandler], UnknownHandler]:
        """Decorator for unknown command event."""

        def decorator(f: UnknownHandler) -> UnknownHandler:
            self._handlers[Event.UNKNOWN_COMMAND] = f
            return f

        if func is not None:
            return decorator(func)
        return decorator

    def on_interrupt(
        self, func: InterruptHandler | None = None
    ) -> InterruptHandler | Callable[[InterruptHandler], InterruptHandler]:
        """Decorator for interrupt event."""

        def decorator(f: InterruptHandler) -> InterruptHandler:
            self._handlers[Event.INTERRUPT] = f
            return f

        if func is not None:
            return decorator(func)
        return decorator

    def on_command_error(
        self, func: ErrorHandler | None = None
    ) -> ErrorHandler | Callable[[ErrorHandler], ErrorHandler]:
        """Decorator for command error event."""

        def decorator(f: ErrorHandler) -> ErrorHandler:
            self._handlers[Event.COMMAND_ERROR] = f
            return f

        if func is not None:
            return decorator(func)
        return decorator


handlers = HandlerRegistry()


class Shell:
    """
    Shell runs a prompt loop with the specified Prompt and parses user input for registered commands and their arguments.
    It then executes them and prints the result, if any.

    Basic usage:
        >>> prompt = Prompt("> ")
        >>> shell = Shell()
        >>> shell.run(prompt)

    The prompt passed to shell must have a completer of type CommandCompleter. Shell should only be instantiated once.
    """

    _registry: CommandRegistry
    _handlers: HandlerRegistry
    _prompt: Prompt | None
    _instance: bool = False

    def __new__(
        cls,
        registry: CommandRegistry | None = None,
        handlers: HandlerRegistry | None = None,
    ) -> Self:
        if cls._instance:
            raise RuntimeError(f"{type(cls)} cannot be instantiated more than once")
        cls._instance = True
        return super(Shell, cls).__new__(cls)

    def __init__(
        self,
        registry: CommandRegistry | None = None,
        handlers: HandlerRegistry | None = None,
    ) -> None:
        self._registry = registry or get_registry()
        # TODO: pls figure out a way to not use globals name wrangling
        self._handlers = handlers or globals()["handlers"]
        self._prompt = None

    @property
    def registry(self) -> CommandRegistry:
        """Get the command registry."""
        return self._registry

    @registry.setter
    def registry(self, registry: CommandRegistry) -> None:
        """Set the command registry."""
        self._registry = registry
        if self._prompt is not None and isinstance(
            self._prompt.completer, CommandCompleter
        ):
            self._prompt.completer.registry = registry

    @property
    def handlers(self) -> HandlerRegistry:
        """Get the handlers registry."""
        return self._handlers

    @handlers.setter
    def handlers(self, handlers: HandlerRegistry) -> None:
        """Set the handlers registry."""
        self._handlers = handlers

    @classmethod
    def _enter_alt_buffer(cls) -> None:
        sys.stdout.write("\033[?1049h")
        sys.stdout.flush()

    @classmethod
    def _leave_alt_buffer(cls) -> None:
        sys.stdout.write("\033[?1049l")
        sys.stdout.flush()

    def run(
        self,
        prompt: Prompt,
        /,
        start_text: str | None = None,
        use_alt_buffer: bool = True,
    ) -> None:
        """
        Runs the shell loop with the specified prompt and other configuration.

        Args:
            prompt: The Prompt instance to use for input
            start_text: Optional text to print at the beginning
            use_alt_buffer: Whether to use the terminal's alternative screen buffer
        """
        if not isinstance(prompt.completer, CommandCompleter):
            raise TypeError(
                f"Prompt must have a completer of type CommandCompleter, got {type(prompt.completer)}"
            )

        self._prompt = prompt
        prompt.completer.registry = self._registry

        if use_alt_buffer:
            self._enter_alt_buffer()

        try:
            if start_text:
                print(start_text)

            with prompt:
                try:
                    for line in prompt:
                        try:
                            parts = line.strip().split()
                            if not parts:
                                continue  # No input provided

                            # Traverse command tree to find the correct command
                            cmd_info = self._registry[parts[0]]
                            if not cmd_info:
                                self._handlers[Event.UNKNOWN_COMMAND](parts[0])
                                continue

                            args_start_index = 1
                            for i, part in enumerate(parts[1:], 1):
                                if part in cmd_info.children:
                                    cmd_info = cmd_info.children[part]
                                    args_start_index = i + 1
                                else:
                                    break  # No more subcommands

                            args = parts[args_start_index:]

                            # Execute command
                            cmd_info.func(*args)

                        except InterruptException:
                            self._handlers[Event.INTERRUPT]()
                            break
                        except Exception as e:
                            self._handlers[Event.COMMAND_ERROR](e)

                except InterruptException:
                    if use_alt_buffer:
                        self._leave_alt_buffer()
                    self._handlers[Event.INTERRUPT]()

        finally:
            if use_alt_buffer:
                self._leave_alt_buffer()
