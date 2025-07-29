from typing import override
from lunar_engine.command import CommandRegistry
from lunar_engine.shell import Shell
from lunar_engine.prompt import Prompt, CommandCompleter

registry: CommandRegistry = CommandRegistry()

prompt = Prompt("$ ", completer=CommandCompleter(registry))


class MyShell(Shell):
    @override
    def on_unknown_command(self, name: str) -> str:
        return f"Command not found: {name}"

    @override
    def on_interrupt(self) -> str:
        return "Interrupted! Exiting."

    @override
    def on_command_error(self, e: Exception) -> str:
        return f"An error occurred! {e}"


@registry.command(description="A command.")
def test(should_fail: str):
    print("You ran this command!")
    if should_fail == "yes":
        raise Exception(f"{should_fail=}")


shell = MyShell(registry)

shell.run(prompt, start_text="Hi there!")
