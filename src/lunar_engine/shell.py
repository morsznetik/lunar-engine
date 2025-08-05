import traceback
import inspect
import sys
from enum import Enum, auto
from inspect import Parameter
from itertools import zip_longest
from types import NoneType, UnionType
from typing import (
    Any,
    Callable,
    NoReturn,
    Literal,
    Self,
    get_args,
    get_origin,
    get_type_hints,
)
from .command import CommandRegistry, get_registry
from .exceptions import InterruptException, InvalidArgumentTypeException
from .prompt import CommandCompleter, Prompt
from .utils import pretty_format_error


type UnexpectedExceptionHandler = Callable[[Exception], None]
type CommandExceptionHandler = Callable[[Exception], None]
type UnknownCommandHandler = Callable[[str], None]
type InterruptHandler = Callable[[], None]
type CommandInterruptHandler = Callable[[], None]
type TypeTransformErrorHandler = Callable[
    [str, str, str | None, list[str], ValueError | None], None
]
type ArgumentCountErrorHandler = Callable[[str, list[str] | None, int, int, int], None]
type Handler = Callable[..., None]

type TransformedArgs = (
    int | float | str | bool | bytes | list[TransformedArgs] | NoneType | Enum
)


class Event(Enum):
    UNEXPECTED_EXCEPTION = auto()
    COMMAND_EXCEPTION = auto()
    UNKNOWN_COMMAND = auto()
    INTERRUPT = auto()
    TYPE_TRANSFORM_ERROR = auto()
    ARGUMENT_COUNT_ERROR = auto()
    COMMAND_INTERRUPT = auto()


def _default_unexpected_exception(e: Exception) -> None:
    print(pretty_format_error("Unexpected exception caught:", str(e)))
    traceback.print_exception(type(e), e, e.__traceback__, file=sys.stderr)


def _default_command_exception(e: Exception) -> None:
    print(pretty_format_error("Command error:", str(e)))
    traceback.print_exception(type(e), e, e.__traceback__, file=sys.stderr)


def _default_unknown_command(name: str) -> None:
    print(f"Unknown command: {name}")


def _default_interrupt() -> None:
    print("Interrupted.")


def _default_command_interrupt() -> None:
    print("\nCommand interrupted.")


def _default_type_transform_error(
    arg: str,
    arg_name: str,
    arg_type: str | None = None,
    options: list[str] | None = None,
    e: ValueError | None = None,
) -> None:
    msg = f"For argument {arg_name!r}, could not interpret {arg!r}"
    if arg_type is not None:
        msg += f" as type {arg_type}"
    if e:
        msg += f"; error: {e}"
    print(msg)
    if options:
        print(f"Expected one of: {', '.join(options)}")


def _default_argument_error(
    command_name: str,
    missing_args: list[str] | None,
    provided: int,
    _expected: int,
    total: int,
) -> None:
    if missing_args is not None:
        arg_list = "', '".join(missing_args)
        print(
            f"For command {command_name!r}, missing {len(missing_args)} required argument{'s' if len(missing_args) != 1 else ''}: {arg_list!r}"
        )
    else:
        print(
            f"For command {command_name!r}, got {provided - total} extra argument{'s' if provided - total != 1 else ''}"
        )


class HandlerRegistry:
    """Registry for event handlers using decorators."""

    _handlers: dict[Event, Handler]

    def __init__(self) -> None:
        self._handlers = {
            Event.UNEXPECTED_EXCEPTION: _default_unexpected_exception,
            Event.UNKNOWN_COMMAND: _default_unknown_command,
            Event.INTERRUPT: _default_interrupt,
            Event.COMMAND_EXCEPTION: _default_command_exception,
            Event.TYPE_TRANSFORM_ERROR: _default_type_transform_error,
            Event.ARGUMENT_COUNT_ERROR: _default_argument_error,
            Event.COMMAND_INTERRUPT: _default_command_interrupt,
        }

    def __getitem__(self, event: Event) -> Handler:
        return self._handlers[event]

    def on_unexpected_exception[T: UnexpectedExceptionHandler](
        self, func: T | None = None
    ) -> T | Callable[[T], T]:
        """Decorator for unexpected error event.

        The decorated function will be called with the following arguments:
            e: The exception that was caught.
        """

        def decorator(f: T) -> T:
            self._handlers[Event.UNEXPECTED_EXCEPTION] = f
            return f

        if func is not None:
            return decorator(func)
        return decorator

    def on_command_exception[T: CommandExceptionHandler](
        self, func: T | None = None
    ) -> T | Callable[[T], T]:
        """Decorator for command error event.

        The decorated function will be called with the following arguments:
            e: The exception that was caught.
        """

        def decorator(f: T) -> T:
            self._handlers[Event.COMMAND_EXCEPTION] = f
            return f

        if func is not None:
            return decorator(func)
        return decorator

    def on_unknown_command[T: UnknownCommandHandler](
        self, func: T | None = None
    ) -> T | Callable[[T], T]:
        """Decorator for unknown command event.

        The decorated function will be called with the following arguments:
            name: The name of the command that was not found.
        """

        def decorator(f: T) -> T:
            self._handlers[Event.UNKNOWN_COMMAND] = f
            return f

        if func is not None:
            return decorator(func)
        return decorator

    def on_interrupt[T: InterruptHandler](
        self, func: T | None = None
    ) -> T | Callable[[T], T]:
        """Decorator for interrupt event.

        The decorated function will be called with no arguments.
        """

        def decorator(f: T) -> T:
            self._handlers[Event.INTERRUPT] = f
            return f

        if func is not None:
            return decorator(func)
        return decorator

    def on_command_interrupt[T: CommandInterruptHandler](
        self, func: T | None = None
    ) -> T | Callable[[T], T]:
        """Decorator for command interrupt event.

        The decorated function will be called with no arguments.
        """

        def decorator(f: T) -> T:
            self._handlers[Event.COMMAND_INTERRUPT] = f
            return f

        if func is not None:
            return decorator(func)
        return decorator

    def on_type_transform_error[T: TypeTransformErrorHandler](
        self, func: T | None = None
    ) -> T | Callable[[T], T]:
        """Decorator for type transform error event.

        The decorated function will be called with the following arguments:
            arg: The argument that failed to transform.
            arg_name: The name of the argument that failed to transform.
            arg_type: The expected type of the argument.
            options: A list of possible values for the argument.
            e: The exception that was caught.
        """

        def decorator(f: T) -> T:
            self._handlers[Event.TYPE_TRANSFORM_ERROR] = f
            return f

        if func is not None:
            return decorator(func)
        return decorator

    def on_argument_count_error[T: ArgumentCountErrorHandler](
        self, func: T | None = None
    ) -> T | Callable[[T], T]:
        """Decorator for argument count error event.

        The decorated function will be called with the following arguments:
            command_name: The name of the command that was called.
            missing_args: A list of missing argument names, if any.
            provided: The number of arguments provided.
            expected: The number of required arguments.
            total: The total number of arguments.
        """

        def decorator(f: T) -> T:
            self._handlers[Event.ARGUMENT_COUNT_ERROR] = f
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

    CLI usage (automatic detection):
        >>> # uv run app.py adder 1 + 1
        >>> # uv run app.py --help
        >>> # uv run app.py -h
        >>> # uv run app.py help adder

    The prompt passed to shell must have a completer of type CommandCompleter. Shell should only be instantiated once.
    """

    _registry: CommandRegistry
    _handlers: HandlerRegistry
    _prompt: Prompt | None
    _instance: bool = False

    # cli args
    _cli_use_alt_buffer: bool | None = None
    _cli_use_alt_buffer_flag: bool

    def __new__(
        cls,
        registry: CommandRegistry | None = None,
        handlers: HandlerRegistry | None = None,
        *,
        builtins: bool = True,
        enable_cli: bool = True,
        cli_use_alt_buffer_flag: bool = True,
    ) -> Self:
        if cls._instance:
            raise RuntimeError(f"{cls.__name__} cannot be instantiated more than once")

        cls._instance = True
        return super(Shell, cls).__new__(cls)

    def __init__(
        self,
        registry: CommandRegistry | None = None,
        handlers: HandlerRegistry | None = None,
        *,
        builtins: bool = True,
        enable_cli: bool = True,
        cli_use_alt_buffer_flag: bool = True,
    ) -> None:
        self._registry = registry or get_registry()
        # TODO: pls figure out a way to not use globals name wrangling
        self._handlers = handlers or globals()["handlers"]
        self._prompt = None
        self._cli_use_alt_buffer_flag = cli_use_alt_buffer_flag

        # cli arg flags
        self._cli_use_alt_buffer = None

        if builtins:
            self._register_builtin_commands()

    @property
    def registry(self) -> CommandRegistry:
        """Get the command registry."""
        return self._registry

    @registry.setter
    def registry(self, registry: CommandRegistry) -> None:
        """Set the command registry of the shell and the prompt's completer."""
        self._registry = registry
        # ensure the prompt completer's registry matches the Shell's to prevent faulty completions
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

    def _show_cli_help(self) -> None:
        print("Usage:")
        print(f" {sys.argv[0]} [options]")
        print(f" {sys.argv[0]} <command> [args...]")
        print()
        print("Options:")
        print(" --help, -h, -? Show this help message")
        if self._cli_use_alt_buffer_flag:
            print(" --no-alt-buffer Disable alternative screen buffer")
        print()
        try:
            self._help_command(sys.argv[2])
        except IndexError:
            self._help_command(None)
        print()
        print("If no command is provided, starts interactive shell mode.")

    def _handle_cli_args(self) -> bool:
        args = sys.argv[1:]  # skip script name

        if not args:
            return True

        if args[0] in ("--help", "-h", "-?"):
            self._show_cli_help()
            return False

        # TODO: maybe use a named tuple for this instead?
        # isn't as pythonic but more extensible; tbd
        filtered_args: list[str] = []
        for arg in args:
            if arg == "--no-alt-buffer" and self._cli_use_alt_buffer_flag:
                self._cli_use_alt_buffer = False
            else:
                filtered_args.append(arg)

        # no command after filtering flags, run shell
        if not filtered_args:
            return True

        try:
            self._execute(" ".join(filtered_args))
        except InterruptException:
            # ignore exit commands in cli mode
            # causes issues from my testing
            pass
        except Exception as e:
            self._handlers[Event.UNEXPECTED_EXCEPTION](e)
            sys.exit(1)

        return False

    def _transform_types(
        self, types: list[Any], args: list[str], arg_names: list[str]
    ) -> list[TransformedArgs]:
        # for any ignore Anys in this function, it's because it should be Any
        transformed_args: list[TransformedArgs] = []

        for i, (arg_type, arg) in enumerate(zip_longest(types, args, fillvalue=None)):
            if arg == "none" or arg is None:
                origin = get_origin(arg_type)
                if origin is UnionType:
                    type_args = get_args(arg_type)
                    assert type_args, f"Union type {arg_type} has no args"
                    if type(None) in type_args:
                        transformed_args.append(None)
                        continue
                # if None is not allowed in the union, this will fail below

            assert arg is not None, (
                f"Argument is None but type {arg_type} doesn't allow None"
            )

            # handle union types
            origin = get_origin(arg_type)
            if origin is UnionType:
                type_args = get_args(arg_type)

                # filter out NoneType since we handled None above
                non_none_types = [t for t in type_args if t is not type(None)]  # pyright: ignore[reportAny]
                assert non_none_types, (
                    f"Union type {arg_type} only contains None"
                )  # shouldn't happen?

                transformed_value: TransformedArgs = None
                last_exception: Exception | None = None

                # bruteforce each type in the union until one works
                for attempt_type in non_none_types:  # pyright: ignore[reportAny]
                    try:
                        transformed_value = self._transform_single_type(
                            attempt_type, arg, arg_names[i], suppress_error=True
                        )
                        break
                    except InvalidArgumentTypeException as e:
                        # for some reason when you explicitly give the type for last_exception it freaks out
                        last_exception = e
                        continue

                if transformed_value is None and last_exception:
                    # crap, none of the union types worked
                    type_names = " | ".join(t.__name__ for t in non_none_types)  # pyright: ignore[reportAny]
                    self._handlers[Event.TYPE_TRANSFORM_ERROR](
                        arg,
                        arg_names[i],
                        type_names,
                    )
                    raise InvalidArgumentTypeException from last_exception

                transformed_args.append(transformed_value)
            else:
                # simple single types
                transformed_value = self._transform_single_type(
                    arg_type, arg, arg_names[i]
                )
                transformed_args.append(transformed_value)

        return transformed_args

    def _transform_single_type(
        self,
        arg_type: Any,  # pyright: ignore[reportAny]
        arg: str,
        arg_name: str,
        *,
        suppress_error: bool = False,
    ) -> TransformedArgs:
        # for any ignore Anys in this function, it's because it should be Any, same as above
        origin = get_origin(arg_type)  # pyright: ignore[reportAny]

        # Literal types
        if origin is Literal:
            literal_values = get_args(arg_type)

            # try to match the argument with literal values
            # ignore Any since they can be any type and that is fine
            for literal_value in literal_values:  # pyright: ignore[reportAny]
                if isinstance(literal_value, Enum):
                    if literal_value.name == arg:
                        return literal_value
                elif str(literal_value) == arg:  # pyright: ignore[reportAny]
                    return literal_value  # pyright: ignore[reportAny]
                # also try case-insensitive comparison for string literals
                if (
                    isinstance(literal_value, str)
                    and literal_value.lower() == arg.lower()
                ):
                    return literal_value

            # no match
            literal_options_list = [
                v.name if isinstance(v, Enum) else str(v)  # pyright: ignore[reportAny]
                for v in literal_values  # pyright: ignore[reportAny]
            ]
            if not suppress_error:
                self._handlers[Event.TYPE_TRANSFORM_ERROR](
                    arg,
                    arg_name,
                    None,
                    literal_options_list,
                )
            raise InvalidArgumentTypeException

        elif isinstance(arg_type, type) and issubclass(arg_type, Enum):
            try:
                return arg_type[arg]
            except KeyError as e:
                if not suppress_error:
                    self._handlers[Event.TYPE_TRANSFORM_ERROR](
                        arg,
                        arg_name,
                        arg_type.__name__,
                        set(arg_type._member_map_.keys()),
                        e,
                    )
                raise InvalidArgumentTypeException from e

        if arg_type is int:
            try:
                return int(arg)
            except ValueError as e:
                if not suppress_error:
                    self._handlers[Event.TYPE_TRANSFORM_ERROR](
                        arg,
                        arg_name,
                        arg_type.__name__,
                        None,
                        e,
                    )
                raise InvalidArgumentTypeException from e

        elif arg_type is float:
            try:
                return float(arg)
            except ValueError as e:
                if not suppress_error:
                    self._handlers[Event.TYPE_TRANSFORM_ERROR](
                        arg,
                        arg_name,
                        arg_type.__name__,
                        None,
                        e,
                    )
                raise InvalidArgumentTypeException from e

        elif arg_type is bytes:
            try:
                return bytes(arg, "utf-8")
            except ValueError as e:
                if not suppress_error:
                    self._handlers[Event.TYPE_TRANSFORM_ERROR](
                        arg,
                        arg_name,
                        arg_type.__name__,
                        None,
                        e,
                    )
                raise InvalidArgumentTypeException from e

        elif arg_type is bool:
            if arg.lower() not in ("true", "false"):
                # fake bool() error
                e = ValueError(f"Invalid boolean literal: '{arg}'")
                if not suppress_error:
                    self._handlers[Event.TYPE_TRANSFORM_ERROR](
                        arg,
                        arg_name,
                        arg_type.__name__,
                        {"true", "false"},
                        e,
                    )
                raise InvalidArgumentTypeException from e
            return arg.lower() == "true"

        elif origin is list:
            elements = arg.split(",") if arg else []
            if not elements:
                return []

            type_args = get_args(arg_type)
            list_item_type = type_args[0] if type_args else str

            transformed_elements: list[TransformedArgs] = []
            for element in elements:
                element = element.strip()
                transformed_element = self._transform_single_type(
                    list_item_type, element, arg_name
                )
                transformed_elements.append(transformed_element)

            return transformed_elements

        else:
            return arg

    def _execute(self, line: str) -> None:
        try:
            parts = line.strip().split()
            if not parts:
                return

            cmd_info = self._registry[parts[0]]
            if not cmd_info or cmd_info.parent is not None:
                self._handlers[Event.UNKNOWN_COMMAND](parts[0])
                return

            args_start_index = 1
            for i, part in enumerate(parts[1:], 1):
                if part in cmd_info.children:
                    cmd_info = cmd_info.children[part]
                    args_start_index = i + 1
                else:
                    break

            args = parts[args_start_index:]

            func_signature = inspect.signature(cmd_info.func)
            type_hints = get_type_hints(cmd_info.func)

            # ignore Any because we don't know the type yet
            param_types = {
                k: v
                for k, v in type_hints.items()  # pyright: ignore[reportAny]
                if k != "return"
            }

            params: list[Parameter] = list(func_signature.parameters.values())
            param_names = list(param_types.keys())
            param_type_list = list(param_types.values())

            # ignore Any since default can be of any type and that intended
            required_params = [
                p
                for p in params
                if p.default == inspect.Parameter.empty  # pyright: ignore[reportAny]
                and p.kind != Parameter.VAR_POSITIONAL
            ]
            num_required = len(required_params)

            effective_args: list[Any] = []
            for i, arg in enumerate(args):
                if arg == "none" and i < len(params):
                    param = params[i]
                    # ignore Any since default can be of any type and that intended
                    if param.default != inspect.Parameter.empty:  # pyright: ignore[reportAny]
                        break
                effective_args.append(arg)

            has_var_positional = any(p.kind == Parameter.VAR_POSITIONAL for p in params)

            # validate count
            if len(effective_args) < num_required or (
                not has_var_positional and len(effective_args) > len(params)
            ):
                missing_args = None
                if len(effective_args) < num_required:
                    missing_arg_names = [p.name for p in required_params]
                    missing_args = missing_arg_names[len(effective_args) :]

                self._handlers[Event.ARGUMENT_COUNT_ERROR](
                    cmd_info.name,
                    missing_args,
                    len(effective_args),
                    num_required,
                    len(params),
                )
                return

            if effective_args:
                types_to_transform = param_type_list[: len(effective_args)]
                names_to_transform = param_names[: len(effective_args)]

                if has_var_positional:
                    # subtract 1 for the *args parameter itself
                    num_non_var = len(param_type_list) - 1

                    var_type = param_type_list[-1]  # pyright: ignore[reportAny]
                    types_to_transform = list(param_type_list[:-1])
                    num_var_args_provided = len(effective_args) - num_non_var
                    types_to_transform.extend([var_type] * num_var_args_provided)

                    var_name = param_names[-1]
                    names_to_transform = list(param_names[:-1])
                    names_to_transform.extend([var_name] * num_var_args_provided)

                transformed_args = self._transform_types(
                    types_to_transform,
                    effective_args,
                    arg_names=names_to_transform,
                )
            else:
                if num_required > 0:
                    self._handlers[Event.ARGUMENT_COUNT_ERROR](
                        0, num_required, len(params)
                    )
                    return
                transformed_args = []

            try:
                cmd_info.func(*transformed_args)
            except KeyboardInterrupt:
                self._handlers[Event.COMMAND_INTERRUPT]()
                return
            except Exception as e:
                self._handlers[Event.COMMAND_EXCEPTION](e)
                return
        except InvalidArgumentTypeException:
            pass
        except InterruptException:
            raise
        except Exception as e:
            self._handlers[Event.UNEXPECTED_EXCEPTION](e)

    def run(
        self,
        prompt: Prompt,
        /,
        start_text: str | None = None,
        use_alt_buffer: bool = True,
    ) -> None:
        """
        Runs the shell loop with the specified prompt and other configuration.
        Automatically handles CLI arguments if provided.

        Args:
            prompt: The Prompt instance to use for input
            start_text: Optional text to print at the beginning
            use_alt_buffer: Whether to use the terminal's alternative screen buffer
        """
        should_run_interactive = self._handle_cli_args()

        if not should_run_interactive:
            return

        # Use CLI config if provided, otherwise use parameter
        if self._cli_use_alt_buffer is not None:
            use_alt_buffer = self._cli_use_alt_buffer

        if not isinstance(prompt.completer, CommandCompleter):
            raise TypeError(
                f"Prompt must have a completer of type CommandCompleter, got {prompt.completer.__class__.__name__}"
            )

        self._prompt = prompt

        if use_alt_buffer:
            self._enter_alt_buffer()

        try:
            if start_text:
                print(start_text)

            with prompt:
                try:
                    for line in prompt:
                        self._execute(line)
                except InterruptException:
                    if use_alt_buffer:
                        self._leave_alt_buffer()
                    self._handlers[Event.INTERRUPT]()
        finally:
            if use_alt_buffer:
                self._leave_alt_buffer()
