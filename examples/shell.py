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


@command()
def set_prompt(text: str) -> None:
    # You can also do it with prompt, and handlers!
    # See handlers.py to see the usage for the latter
    """Change the prompt test."""
    shell.prompt.text = text

    # We can also replace the prompt entirely by a new one:
    # shell.prompt = Prompt(text, "Today is a good day")


prompt = Prompt("$ ")

shell = Shell()
shell.run(prompt, start_text="Hi there!")
