class LunarEngineException(Exception):
    """
    Base exception for all Lunar Engine exceptions.
    """

    pass


class InterruptException(LunarEngineException):
    """
    Exception raised when the something interrupts the prompt loop.
    """

    pass
