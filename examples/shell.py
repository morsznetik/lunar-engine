from lunar_engine.utils import FgColors, TextEffects
from lunar_engine.command import CommandRegistry
from lunar_engine.shell import Shell, handlers
from lunar_engine.prompt import Prompt, CommandCompleter

registry: CommandRegistry = CommandRegistry()

prompt = Prompt("$ ", completer=CommandCompleter(registry))


@handlers.on_command_error
def on_command_error(e: Exception) -> None:
    print(f"{FgColors.Red}---ERROR: {e}---{TextEffects.Reset}")


@handlers.on_interrupt
def on_interrupt() -> None:
    print("---INTERRUPTED---")


@handlers.on_unknown_command
def on_unknown_command(name: str) -> None:
    print(f"---COMMAND NOT FOUND: {name}---")


@registry.command(description="A command.")
def test(should_fail: bool) -> None:
    print("You ran this command!")
    if should_fail:
        raise Exception(f"{should_fail=}")


shell = Shell(registry)


shell.run(prompt, start_text="Hi there!")
