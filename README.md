# Lunar Engine

[![CI](https://github.com/morsznetik/lunar-engine/actions/workflows/ci.yml/badge.svg)](https://github.com/morsznetik/lunar-engine/actions/workflows/ci.yml)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A fully type-safe, DX-first, "shell-like" CLI tool framework, for the newest versions of Python!

> [!IMPORTANT]
> This project is in early development and very much a **work in progress.**

## What is this?

Lunar Engine allows you to make a command-line app that acts like a shell. You simply define some commands, a shell prompt, and you're ready!

By default, commands will also be accepted straight from the normal command line.

## Usage

See [examples](https://github.com/morsznetik/lunar-engine/tree/master/examples) for more in-depth detail.

### Hello, world!

A bare minimum Lunar Engine app could look like this.

```python
prompt = Prompt(">> ") # shell prompt
shell = Shell()

@command()
def adder(a: int, b: int) -> None:
    """Adds two numbers."""
    print(f"{a} + {b} = {a+b}")

shell.run(prompt)

```

### Commands

Commands in Lunar Engine are created via the `@command` decorator. It automatically registers the command in the command registry and determines description and name based on the function's signature.

These can also be customized with parameters to the decorator.

```python
@command()
def adder(a: int, b: int) -> None: # cmd name from function name
    """Adds two numbers.""" # description
    print(f"{a} + {b} = {a+b}")

@command(register=False) # manual registration
def manual() -> None:
    """Nothing important."""
    print("Hello, world!")

registry = get_registry() # global command registry
registry.register(manual) # register the command yourself
```

**Note:** `command` is an alias of `get_registry().command` which is the global command registry.

### Prompt

The Prompt handles all user input to the app. You will likely want to use it in combination with Shell, which actually handles execution of commands.

```python
prompt = Prompt(">> ", rprompt="Hi there!")
```

You can also set a custom completer on the prompt. By default, it uses CommandCompleter on the global command registry.

```python
prompt = Prompt(">> ", rprompt="Hi there!", completer=CommandCompleter())
```

**Note:** If the prompt is used in a shell, its completer must be of type CommandCompleter.

### Handlers

Handling events like command errors, or unknown commands is an important part of the shell. There are some reasonable defaults, but you will likely want to customize the handlers to fit your app.

```python
@handlers.on_unknown_command
def unknown_command(name: str) -> None:
    print(f"Oops! {name} is not a command.")


@handlers.on_interrupt
def interrupt() -> None:
    print("App is terminating!")

```

There are a few different handlers that you can hook into.

You may also create different sets of handlers which can be switched at runtime.

```python
# "handlers" is the global set of handlers
my_handlers = HandlerRegistry()
@my_handlers.on_unknown_command
def unknown_command(name: str) -> None:
    print(f"Oops! {name} is not a command.")
...
shell = Shell()
shell.handlers = my_handlers # defaults to global handlers, but can be switched at runtime
```

### Multiple command registries

If you wish to have multiple command registries, you simply have to define them and register commands with their specific decorator.

**Note:** Make sure you set your registry as the completer for the prompt, otherwise you will get results from the global registry.

```python

my_registry = CommandRegistry()

@my_registry.command(register=False)
def test() -> None:
    print("Hello, world!")

# Run Shell
prompt = Prompt(">> ", completer=CommandCompleter(my_registry))
shell = Shell(my_registry)
shell.run()

## --- OR --- ##

prompt = Prompt(">> ")
shell = Shell()
shell.registry = my_registry # sets values automatically

```
