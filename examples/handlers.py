import copy
from lunar_engine.shell import handlers, Shell, HandlerRegistry
from lunar_engine.prompt import Prompt
from lunar_engine.command import command, get_registry
from typing import Literal


@handlers.on_unknown_command
def unknown_command(name: str) -> None:
    print(f"Oops! {name} is not a command.")


@handlers.on_interrupt
def interrupt() -> None:
    print("Connection terminated.")


my_handlers = HandlerRegistry()
shell = Shell()


@my_handlers.on_unknown_command
def my_unknown_command(name: str) -> None:
    print(f"This is a different handler! {name} is not a command.")


@command()
def hello(name: str = "world", n: int = 1) -> None:
    """Hiii!! >;3"""
    print("\n".join([f"Hello, {name}!"] * int(n)))


@command(parent=hello)
def fastfetch() -> None:
    import subprocess

    subprocess.run(["fastfetch"])


@command()
def switch_handler() -> None:
    shell.handlers = my_handlers
    print("Handler switched")


@command()
def switch_to_secret_mode() -> None:
    if shell.registry is not my_commands:
        shell.registry = my_commands
    else:
        shell.registry = get_registry()
    print("Commands switched")
    print(shell.registry)
    print(shell.registry.keys())


my_commands = copy.deepcopy(get_registry())


@my_commands.command()
def secret(
    a: int | float, b: int | float, c: Literal["hello", 1, False] = "hello"
) -> None:
    assert isinstance(a, (int, float))
    assert isinstance(b, (int, float))
    print(f"{a} + {b} = {a + b}, {c}")


@my_commands.command()
def hello2(name: list[str]) -> None:
    print(f"Hello, {name}!")


shell.run(
    Prompt(
        "$ ",
    )
)
