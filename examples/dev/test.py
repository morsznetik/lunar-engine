"""Created to have a basepoint for development and testing."""

from prompt_toolkit.styles import Style
from lunar_engine.command import command
from lunar_engine.shell import Event, Shell, handlers
from lunar_engine.prompt import Prompt
from typing import Literal


@command()
def greet(name: str, formal: bool = False) -> None:
    """Greets the user."""
    if formal:
        print(f"Hello, {name}. It is a pleasure to meet you.")
    else:
        print(f"Hey, {name}!")


@command()
def calc() -> None:
    """A calculator command."""
    pass


@command(name="add")
def add_non_calc(*_: int | float) -> None:
    pass


@command(parent=calc)
def add(*nums: int | float) -> None:
    """Adds numbers together."""
    print(sum(nums))


@command(parent=calc)
def subtract(a: int | float, b: int | float) -> None:
    """Subtracts two numbers."""
    print(a - b)


@command()
def countdown(start: int = 10) -> None:
    """Counts down from a number."""
    import time

    for i in range(start, 0, -1):
        print(i)
        time.sleep(1)
    print("Blast off!")


@command()
def process_data(
    priority: Literal["low", "medium", "high"] = "medium", data: list[str] | None = None
) -> None:
    """Processes a list of data with a given priority."""
    print(f"Processing data: {data} with priority {priority}")


@command()
def raise_with_event(event: Event) -> None:
    """Raises an exception with a given event."""
    print(f"Throwing {event}")


@handlers.on_unknown_command
def unknown_command(name: str) -> None:
    """Custom handler for unknown commands."""
    print(f"Woah, I don't know the command '{name}'!")


@handlers.on_interrupt
def interrupt() -> None:
    """Custom handler for interrupts."""
    print("Goodbye!")


def main() -> None:
    style = Style.from_dict(
        {
            "completion-menu.completion": "bg:ansired ansibrightred",
            "completion-menu.completion.current": "bg:ansibrightred ansibrightyellow",
        }
    )
    shell = Shell()
    prompt = Prompt("> ", style=style)
    shell.run(prompt, start_text="Welcome to the Lunar Engine showcase!")


if __name__ == "__main__":
    main()
