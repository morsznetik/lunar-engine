import threading
import time
from datetime import datetime
from prompt_toolkit.styles import Style
from lunar_engine.command import command
from lunar_engine.shell import Event, Shell, handlers
from lunar_engine.prompt import Prompt
from lunar_engine.text import t
from typing import Literal
from enum import Enum

stop_event = threading.Event()


class Language(Enum):
    ENGLISH = "english"
    GERMAN = "german"
    POLISH = "polish"


shell = Shell()


@command()
def greet(
    name: str,
    formal: bool,
    age: int,
    tone: Literal["friendly", "neutral", "serious"],
    hobbies: list[str] | None = None,
    language: Language = Language.ENGLISH,
) -> None:
    greeting = ""

    if formal:
        greeting = f"Hello, {name}. It is a pleasure to meet you."
    else:
        greeting = f"Hey, {name}!"

    if age:
        greeting += f" You're {age}, nice!"

    greeting += f" Your tone preference is '{tone}'."

    if hobbies:
        hobby_str = ", ".join(hobbies)
        greeting += f" You enjoy: {hobby_str}."

    greeting += f" Language selected: {language.value.capitalize()}."

    print(greeting)


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
    for i in range(start, 0, -1):
        print(i)
        time.sleep(1)
    print("Blast off!")


type priorities = Literal["low", "medium", "high"]


@command()
def process_data(
    priority: list[priorities] | None = None, data: list[str] | None = None
) -> None:
    """Processes a list of data with a given priority."""
    priority = priority or ["medium"]
    print(f"Processing data: {data} with priority {priority}")


@command()
def single_item_list(data: list[Event | priorities]) -> None:
    print(len(data))


@command()
def raise_with_event(event: Event) -> None:
    """Raises an exception with a given event."""
    print(f"Throwing {event}")


@command()
def factory(*, a: bool | str) -> None:
    print(f"{a=}")


@command()
def set_prompt(prompt: str) -> None:
    print(f"Setting prompt to '{prompt}'")
    shell.prompt.text = prompt


@handlers.on_unknown_command
def unknown_command(name: str) -> None:
    """Custom handler for unknown commands."""
    print(f"Woah, I don't know the command '{name}'!")


@handlers.on_interrupt
def interrupt() -> None:
    """Custom handler for interrupts."""
    stop_event.set()
    print("Goodbye!")


start_time: float | None = None
execution_time: float | None = None


@handlers.on_command_start
def on_command_start(_: str) -> None:
    global start_time
    start_time = time.time()


@handlers.on_command_end
def on_command_end(_: str) -> None:
    global execution_time
    if start_time is not None:
        execution_time = time.time() - start_time
    else:
        execution_time = 0.0


def update_time_rtext() -> None:
    """Continuously update the right text with the current time."""
    while not stop_event.is_set():
        current_time = datetime.now().strftime("%H:%M:%S")

        # Only show execution time if it's > 1 second
        if execution_time is not None and execution_time > 1.0:
            exec_time_str = f"{execution_time:.1f}s"
            shell.prompt.rtext = (
                "test " + t(f" {exec_time_str} ", fg="ansired") + current_time
            )
        else:
            shell.prompt.rtext = current_time

        shell.refresh()
        stop_event.wait(1)


def main() -> None:
    style = Style.from_dict(
        {
            "completion-menu.completion": "bg:ansired ansibrightred",
            "completion-menu.completion.current": "bg:ansibrightred ansibrightyellow",
        }
    )
    prompt = Prompt("> ", style=style)
    threading.Thread(target=update_time_rtext).start()
    shell.run(
        prompt, start_text="Welcome to the Lunar Engine showcase!", use_alt_buffer=False
    )


if __name__ == "__main__":
    main()
