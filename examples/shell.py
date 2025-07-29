from typing import override
from lunar_engine.command import command
from lunar_engine.shell import Shell
from lunar_engine.prompt import Prompt, CommandCompleter

p = Prompt("$ ", completer=CommandCompleter())


class MyShell(Shell):
    @override
    def on_unknown_command(self, name: str):
        print(f"Command not found: {name}")

    @override
    def on_interrupt(self):
        print("Interrupted! Exiting.")

    @override
    def on_command_error(self, e: Exception):
        print(f"An error occurred! {e}")


@command(description="A command.")
def test():
    print("You ran this command!")


shell = MyShell()

shell.run(p, start_text="Hi there!")
