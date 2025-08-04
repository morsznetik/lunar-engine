class LunarEngineException(Exception):
    """
    Base exception for all Lunar Engine exceptions.
    """

    pass


class PromptException(LunarEngineException):
    """
    Base class for prompt-related errors.
    """

    pass


class InterruptException(PromptException, StopIteration):
    """
    Exception raised when the something interrupts the prompt loop.
    This is typically raised on KeyboardInterrupt or EOFError,
    but can be raised by any code that wants to interrupt the prompt loop.
    like a command that wants to exit the prompt loop.
    """

    pass


class CommandException(LunarEngineException):
    """
    Base class for command-related errors.
    """

    pass


class UntypedCommandException(CommandException):
    """
    Raised when a command has parameters without type hints.
    """

    pass


class InvalidArgumentTypeException(CommandException):
    """
    Raised when a command has an invalid argument type.
    """

    pass
