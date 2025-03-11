class ContextWindowExceeded(Exception):
    """Exception raised when input exceeds model context window."""

    def __init__(self, message="Input length exceeds model context window"):
        self.message = message
        super().__init__(self.message)


class MaxIterationsExceeded(Exception):
    """Exception raised when the the iteration limit is exceeded"""

    def __init__(self, message="The maximum iteration limit has been exceeded"):
        self.message = message
        super().__init__(self.message)
