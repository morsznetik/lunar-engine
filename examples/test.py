from lunar_engine.prompt import CommandCompleter, Prompt
from lunar_engine.command import get_registry, command
from lunar_engine.exceptions import InterruptException
from prompt_toolkit.completion import FuzzyWordCompleter
from typing import Literal


prompt = Prompt(
    "> ",
    rprompt="Hi, test!",
    completer=FuzzyWordCompleter(
        ["hello", "world", "exit"],
        meta_dict={
            "hello": "hello world",
            "world": "world bye",
        },
    ),
)

with prompt:
    try:
        for input in prompt:
            if input == "exit":
                break  # should not raise
            print(input)
    except InterruptException:
        print("Goodbye!")
    else:
        print("passed")

assert not prompt

prompt._running = True  # pyright: ignore[reportPrivateUsage]

try:
    for input in prompt:
        print(input)
except InterruptException:
    print("Goodbye!")
except RuntimeError:
    print("passed")

assert not prompt

registry = get_registry()


# Define some example commands
@command()
def hello(name: str) -> str:
    """Say hello to someone."""
    return f"hello {name}"


@command()
def add(*nums: float | int) -> str:
    """Add numbers together."""
    return str(sum(nums))


@command()
def add_three_nums(a: float, b: float, c: float) -> str:
    """Add three numbers together."""
    return str(a + b + c)


@command()
def help() -> str:
    """Show available commands and their descriptions."""
    lines: list[str] = []
    for cmd in registry:
        desc = cmd.description or "No description"
        lines.append(f"{cmd.name}: {desc}")
    return "\n".join(lines)


@command()
def exit() -> None:
    """Exit the CLI."""
    raise InterruptException


@command()
def test(a: int, b: str | None = None, c: int = 0) -> str:
    """Test command."""
    return f"{a=} {b=} {c=}"


@command()
def git():
    """Git version control"""
    pass


@command(parent=git)
def commit(message: str) -> str:
    """Record changes to the repository"""
    return f"committing {message}"


@command(parent=git)
def push(remote: str = "origin", branch: str = "master") -> str:
    """Update remote refs along with associated objects"""
    return f"pushing {remote} {branch}"


@command(parent=git)
def checkout(branch: str) -> str:
    """Switch branches or restore working tree files"""
    return f"checking out {branch}"


@command()
def test_literal(
    a: Literal["a", "b", "c"],
    b: Literal[True, False, None, 1, 2, 3, "a", "b", "c"],
) -> str:
    """Test literal completion."""
    return f"test literal {a} {b}"


@command()
def test_infer(
    a: Literal["a", "b", "c"] | None,
    b: str | None,
) -> str:
    return f"{a=} {b=}"


# Create a CLI prompt with command completion
prompt2 = Prompt(
    "> ",
    rprompt="Welcome to Lunar CLI!",
    completer=CommandCompleter(registry),
)

del registry["1"]

for cmd in registry:
    print(cmd.name)


# Shell example implementation

with prompt2:
    try:
        for input_line in prompt2:
            try:
                parts = input_line.strip().split()
                if not parts:
                    continue

                # Traverse command tree to find the correct command
                cmd_info = registry[parts[0]]
                if not cmd_info:
                    print(f"Unknown command: {parts[0]}")
                    continue

                args_start_index = 1
                for i, part in enumerate(parts[1:], 1):
                    if part in cmd_info.children:
                        cmd_info = cmd_info.children[part]
                        args_start_index = i + 1
                    else:
                        break  # No more subcommands

                args = parts[args_start_index:]

                # Execute command
                result = cmd_info.func(*args)
                if result is not None:
                    print(result)

            except InterruptException:
                print("Goodbye!")
                break
            except Exception as e:
                print(f"Error: {e}")

    except InterruptException:
        print("\nGoodbye!")
