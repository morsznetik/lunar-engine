class LunarEngineException(Exception):
    """
    Base exception for all Lunar Engine exceptions.
    """

    pass


class LunarEngineInterrupt(LunarEngineException):
    """
    Exception raised when the something interrupts the prompt loop.
    """

    pass
