import copy
from lunar_engine.shell import handlers, Shell, HandlerRegistry
from lunar_engine.prompt import Prompt
from lunar_engine.command import command, get_registry


@handlers.on_unknown_command
def unknown_command(name: str) -> None:
    print(f"Dumbass {name} is not a command")


@handlers.on_interrupt
def interrupt() -> None:
    print("Connection terminated.")


my_handlers = HandlerRegistry()
shell = Shell()


@my_handlers.on_unknown_command
def my_unknown_command(name: str) -> None:
    print(f"Hi from my handler! {name} is not a command tho btw")


@command()
def hello(name: str = "world", n: int = 1) -> str:
    """Hiii!! >;3"""
    return "\n".join([f"Hello, {name}!"] * int(n))


@command(parent=hello)
def fastfetch() -> None:
    import subprocess

    subprocess.run(["fastfetch"])


@command()
def switch_handler() -> str:
    shell.handlers = my_handlers
    return "Handler switched"


@command()
def switch_to_secret_mode() -> str:
    shell.registry = my_commands
    return "Commands switched"


my_commands = copy.deepcopy(get_registry())


@my_commands.command()
def secret(a: int, b: int) -> str:
    return f"{a} + {b} = {a + b}"


shell.run(
    Prompt(
        "$ ",
    )
)
