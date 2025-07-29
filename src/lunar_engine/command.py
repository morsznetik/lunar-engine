import inspect
import weakref
from collections.abc import Iterator, Callable
from dataclasses import dataclass, field
from typing import Final, Self, get_type_hints
from lunar_engine.exceptions import UntypedCommandException

type CommandFunc = Callable[..., str | None]


@dataclass
class CommandInfo:
    """Stores metadata about a registered command."""

    func: Final[CommandFunc]
    name: Final[str]
    description: Final[str | None] = None
    parent: weakref.ref[Self] | None = None
    children: dict[str, Self] = field(default_factory=dict)

    def __post_init__(self) -> None:
        sig = inspect.signature(self.func)
        hints = get_type_hints(self.func)

        # assert that each parameter has a type hint
        for name, param in sig.parameters.items():
            # skip keyword-only args for now  # TODO: support keyword-only args
            if param.kind == param.VAR_KEYWORD:
                continue

            # positional-only args aka capture-all args aka *args
            if param.kind == param.VAR_POSITIONAL and name not in hints:
                raise UntypedCommandException(
                    f"Command {self.name!r}: '*{name}' must have a type hint"
                )

            # everything else
            if param.kind in (
                param.POSITIONAL_ONLY,
                param.POSITIONAL_OR_KEYWORD,
                param.KEYWORD_ONLY,
            ):
                if name not in hints:
                    raise UntypedCommandException(
                        f"Command {self.name!r}: parameter {name!r} must have a type hint"
                    )


class CommandRegistry:
    """Registry for storing and managing commands in a tree."""

    def __init__(self) -> None:
        self._commands: dict[str, CommandInfo] = {}

    def __iter__(self) -> Iterator[CommandInfo]:
        return iter(self._commands.values())

    def __getitem__(self, name: str) -> CommandInfo | None:
        return self._commands.get(name)

    def __delitem__(self, name: str) -> None:
        if name not in self._commands:
            return

        cmd = self._commands[name]

        # remove from parent's children if it has a parent
        if cmd.parent is not None:
            parent = cmd.parent()
            if parent is not None:
                parent.children.pop(name, None)

        # remove all children
        for child in list(cmd.children.keys()):
            del self[child]

        del self._commands[name]

    def keys(self) -> list[str]:
        # return a list of all registered command names
        return list(self._commands.keys())

    def register(
        self,
        func: CommandFunc,
        *,
        name: str | None = None,
        description: str | None = None,
        parent: str | None = None,
    ) -> CommandInfo:
        # infers name, description, and parent from function if not provided
        cmd_name = name or func.__name__

        # validate uniqueness within the appropriate scope, root-level or under a parent
        if parent is None:
            # root-level commands cannot share names
            if cmd_name in self._commands:
                raise ValueError(f"Command {cmd_name!r} is already registered")
        else:
            # When attaching to a parent, ensure the parent exists and the subcommand name is unique
            if parent not in self._commands:
                raise ValueError(f"Parent command {parent!r} not found")

            if cmd_name in self._commands[parent].children:
                raise ValueError(
                    f"Subcommand {cmd_name!r} is already registered under {parent!r}"
                )

        if description is None and func.__doc__:
            # cleandoc so we don't get weird formatting
            description = inspect.cleandoc(func.__doc__).split("\n")[0]

        cmd_info = CommandInfo(
            func=func,
            name=cmd_name,
            description=description,
        )

        # set up a parent-child relationship if a parent is specified
        if parent:
            parent_cmd = self._commands[parent]
            cmd_info.parent = weakref.ref(parent_cmd)
            parent_cmd.children[cmd_name] = cmd_info

        # keep a flat mapping of all commands including nested for fast lookup
        # this allows later registrations to reference non-root parents
        # if a duplicate name already exists, we only overwrite it when the existing
        # command is also a non-root command (i.e. it has a parent)
        # this avoids collisions between different subcommand branches while still protecting
        # root-level command uniqueness enforced earlier
        if cmd_name not in self._commands or cmd_info.parent is None:
            self._commands[cmd_name] = cmd_info
        return cmd_info

    def command[T: CommandFunc](
        self,
        name: str | None = None,
        *,
        description: str | None = None,
        parent: CommandFunc | None = None,
        register: bool = True,
    ) -> Callable[[T], T]:
        """
        Decorator for registering command functions.

        Args:
            name: Optional override for the command name
            description: Optional command description
            parent: Optional parent command function for subcommands
            register: Whether to register immediately or wait for manual registration

        Basic usage:
            >>> @command()
            ... def echo(string: str) -> str:
            ...     '''Echo the input string.'''
            ...     return string

            >>> @command()
            ... def calc():
            ...     '''A calculator command'''
            ...     pass

            >>> @command(parent=calc)
            ... def add_command(*nums: int | float) -> str:
            ...     return str(sum(nums))
        """

        def decorator(func: T) -> T:
            if register:
                parent_name = parent.__name__ if parent else None
                self.register(
                    func,
                    name=name,
                    description=description,
                    parent=parent_name,
                )
            return func

        return decorator
