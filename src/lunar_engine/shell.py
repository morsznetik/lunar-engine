from itertools import zip_longest
from types import NoneType, UnionType
from typing import (
    Any,
    NoReturn,
    Self,
    Callable,
    get_args,
    get_origin,
    get_type_hints,
)
from enum import Enum, auto
import sys
from lunar_engine.prompt import CommandCompleter, Prompt
from lunar_engine.command import CommandRegistry, get_registry
from lunar_engine.exceptions import InterruptException

type UnknownCommandHandler = Callable[[str], None]
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
        self, func: UnknownCommandHandler | None = None
    ) -> (
        UnknownCommandHandler | Callable[[UnknownCommandHandler], UnknownCommandHandler]
    ):
        """Decorator for unknown command event."""

        def decorator(f: UnknownCommandHandler) -> UnknownCommandHandler:
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
        *,
        builtins: bool = True,
    ) -> Self:
        if cls._instance:
            raise RuntimeError(f"{cls} cannot be instantiated more than once")
        cls._instance = True
        return super(Shell, cls).__new__(cls)

    def __init__(
        self,
        registry: CommandRegistry | None = None,
        handlers: HandlerRegistry | None = None,
        *,
        builtins: bool = True,
    ) -> None:
        self._registry = registry or get_registry()
        # TODO: pls figure out a way to not use globals name wrangling
        self._handlers = handlers or globals()["handlers"]
        self._prompt = None

        if builtins:
            self._register_builtin_commands()

    def _register_builtin_commands(self) -> None:
        self._registry.register(self._exit_command, name="exit")
        self._registry.register(self._help_command, name="help")

    def _exit_command(self) -> NoReturn:
        """Exit the shell."""
        raise InterruptException()

    def _help_command(self, command_name: str | None = None) -> None:
        """Show help for commands."""
        if command_name is None:
            print("Available commands:")
            for cmd_info in self._registry:
                if cmd_info.parent is None:  # show top-level commands
                    desc = f" - {cmd_info.description}" if cmd_info.description else ""
                    print(f"  {cmd_info.name}{desc}")
        else:
            cmd_info = self._registry[command_name]
            if cmd_info is None:
                print(f"Unknown command: {command_name}")
                return

            print(f"Help for '{command_name}':")
            if cmd_info.description:
                print(f"  {cmd_info.description}")

            # show subcommands if any
            if cmd_info.children:
                print("  Subcommands:")
                for child_name, child_info in cmd_info.children.items():
                    desc = (
                        f" - {child_info.description}" if child_info.description else ""
                    )
                    print(f"    {child_name}{desc}")

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

                            types = get_type_hints(cmd_info.func)
                            transformed_args = _transform_types(
                                [v for k, v in types.items() if k != "return"],  # pyright: ignore[reportAny] - required because of runtime type checking
                                args,
                            )

                            # Execute command
                            cmd_info.func(*transformed_args)

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


type TransformedArgs = (
    int | float | str | bool | bytes | list[TransformedArgs] | NoneType
)


def _transform_types(types: list[Any], args: list[str]) -> list[TransformedArgs]:
    transformed_args: list[TransformedArgs] = []

    # ignore required because runtime type checking is necessary here
    for arg_type, arg in zip_longest(types, args, fillvalue=None):
        if arg == "none" or arg is None:
            if get_origin(arg_type) is UnionType:
                if NoneType in get_args(arg_type):
                    transformed_args.append(None)
                    continue
            raise ValueError(f"Expected value for required argument, got {arg}")

        assert arg is not None
        if arg_type is int:
            transformed_args.append(int(arg))
        elif arg_type is float:
            transformed_args.append(float(arg))
        elif arg_type is bytes:
            num = int(arg)
            transformed_args.append(bytes(num))
        elif arg_type is bool:
            if arg == "true" or arg == "false":
                transformed_args.append(True if arg == "true" else False)
            else:
                raise ValueError(f'Expected "true" or "false" for type bool, got {arg}')
        elif arg_type is list:
            elements = arg.split(",")
            transformed_elements = _transform_types(
                [arg_type for _ in range(len(elements))], elements
            )
            transformed_args.append(transformed_elements)
        else:
            transformed_args.append(arg)

    return transformed_args
