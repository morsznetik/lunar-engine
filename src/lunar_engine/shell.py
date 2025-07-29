from typing import Self
import sys
from lunar_engine.prompt import Prompt
from lunar_engine.command import CommandRegistry
from lunar_engine.exceptions import InterruptException


class Shell:
    """
    Shell runs a prompt loop with the specified Prompt and parses user input for registered commands and their arguments.
    It then executes them and prints the result, if any.

    Basic usage:
        >>> registry = CommandRegistry()
        >>> prompt = Prompt("> ", completer=CommandCompleter(registry))
        >>> shell = Shell(registry)
        >>> shell.run(prompt)

    It may be subclassed to override some methods, but should only be instantiated once.
    """

    _registry: CommandRegistry
    _instance: bool = False

    def __new__(cls, registry: CommandRegistry) -> Self:
        if cls._instance:
            raise RuntimeError(f"{repr(cls)} cannot be instantiated more than once")
        cls._instance = True
        return super(Shell, cls).__new__(cls)

    def __init__(self, registry: CommandRegistry) -> None:
        self._registry = registry

    @classmethod
    def _enter_alt_buffer(cls) -> None:
        sys.stdout.write("\033[?1049h")
        sys.stdout.flush()

    @classmethod
    def _leave_alt_buffer(cls) -> None:
        sys.stdout.write("\033[?1049l")
        sys.stdout.flush()

    def on_unknown_command(self, name: str) -> None:
        """Called when the user attempts to run an unknown command."""
        print(f"Unknown command: {name}")

    def on_interrupt(self) -> None:
        """
        Called if an InterruptException is raised.
        This will be run before the prompt loop is terminated.
        """
        pass

    def on_command_error(self, e: Exception) -> None:
        """
        Called if a command fails during execution.
        """
        print(f"Error: {e}")

    def run(
        self,
        prompt: Prompt,
        start_text: str | None = None,
        use_alt_buffer: bool = True,
    ) -> None:
        """
        Runs the shell loop with the specified prompt and other configuration.

        Args:
            prompt: The Prompt instance to use for input
            start_text: Optional text to print at the beginning
            use_alt_buffer: Whether to use the terminal's alternative screen buffer
        """

        if use_alt_buffer:
            self._enter_alt_buffer()

        try:
            if start_text:
                print(start_text)

            with prompt:
                try:
                    for line in prompt:
                        try:
                            parts = line.strip().split()
                            if not parts:
                                continue  # No input provided

                            # Traverse command tree to find the correct command
                            cmd_info = self._registry[parts[0]]
                            if not cmd_info:
                                self.on_unknown_command(parts[0])
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
                            self.on_interrupt()
                            break
                        except Exception as e:
                            self.on_command_error(e)

                except InterruptException:
                    if use_alt_buffer:
                        self._leave_alt_buffer()
                    self.on_interrupt()

        finally:
            if use_alt_buffer:
                self._leave_alt_buffer()
