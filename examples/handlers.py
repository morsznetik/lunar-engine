# EXAMPLE: Handlers
#
# Handlers are used to respond to events that occur during the shell's execution.
# For example, when a command fails, an unknown command is run, or invalid arguments are provided.

from lunar_engine.shell import handlers, Shell, HandlerRegistry
from lunar_engine.prompt import Prompt
from lunar_engine.command import command


# Handlers are generally registered with the global "handlers" variable. This represents the global handler registry.
# When an unknown command is run
@handlers.on_unknown_command
def unknown_command(name: str) -> None:
    print(f"Oops! {name} is not a command.")


# When the program is interrupted
@handlers.on_interrupt
def interrupt() -> None:
    print("Connection terminated.")


# You can also define your own sets of handlers.
my_handlers = HandlerRegistry()
shell = Shell()


# This callback is only defined under "my_handlers", so shell won't be running this on it's own, as it defaults
# to the global handlers.
@my_handlers.on_unknown_command
def my_unknown_command(name: str) -> None:
    print(f"This is a different handler! {name} is not a command.")


@command()
def hello(name: str = "world", n: int = 1) -> None:
    """Hi!"""
    print("\n".join([f"Hello, {name}!"] * int(n)))


@command(parent=hello)
def fastfetch() -> None:
    import subprocess

    subprocess.run(["fastfetch"])


# Handler registries can be switched at runtime.
# After this command is run, only the handlers from "my_handlers" will be used.
@command()
def switch_handler() -> None:
    shell.handlers = my_handlers  # Switches handlers!
    print("Handler switched")


shell.run(
    Prompt(
        "$ ",
    )
)
