from typing import Self
import sys
from lunar_engine.prompt import Prompt
from lunar_engine.command import get_registry
from lunar_engine.exceptions import InterruptException


class Shell:
    """
    Shell is a helper for running a Prompt loop. It parses user input for registered commands and their arguments and runs them.

    Basic usage:
        >>> prompt = Prompt("> ")
        >>> shell = Shell()
        >>> shell.run(prompt)

    It may be subclassed to override some methods, but should only be instantiated once.
    """

    _instance: bool = False

    def __new__(cls) -> Self:
        if cls._instance:
            raise RuntimeError(f"{repr(Shell)} cannot be instantiated more than once")
        cls._instance = True
        return super(Shell, cls).__new__(cls)

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
        end_text: str | None = None,
        use_alt_buffer: bool = True,
    ) -> None:
        """
        Runs the shell loop with the specified prompt and other configuration.

        Args:
            prompt: The Prompt instance to use for input
            start_text: Optional text to print at the beginning
            end_text: Optional text to print at the end
            use_alt_buffer: Whether to use the terminal's alternative screen buffer
        """
        registry = get_registry()

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
                            cmd_info = registry[parts[0]]
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
                        except Exception as e:
                            self.on_command_error(e)

                except InterruptException:
                    if use_alt_buffer:
                        self._leave_alt_buffer()
                    self.on_interrupt()

        finally:
            if use_alt_buffer:
                self._leave_alt_buffer()

            if end_text:
                print(end_text)
