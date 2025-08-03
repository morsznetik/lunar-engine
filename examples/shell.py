# EXAMPLE: Shell
#
# The Shell is the main orchestrator of your app.
# It executes commands, passes errors to handlers, and manages output.

from lunar_engine.command import CommandRegistry, command
from lunar_engine.shell import Shell
from lunar_engine.prompt import Prompt


@command()
def test(should_fail: bool) -> None:
    if should_fail:
        raise Exception("Failure!")
    print("Success!")


# @command(), Shell, and Prompt default to using the global registry for everything.
# However, you can also create your own registry.
my_registry = CommandRegistry()


@my_registry.command()
def secret() -> None:
    print("Secret command!")


@command()
def switch() -> None:
    # You can switch registries at runtime!
    # After this, the secret command will become available.
    shell.registry = my_registry
    print("Switched registries!")


prompt = Prompt("$ ")

shell = Shell()
shell.run(prompt, start_text="Hi there!")
