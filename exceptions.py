class NetworkManagerError(Exception):
    """
    Custom exception for network management errors.

    Attributes:
        message (str): The human-readable error message.
        code (str | None): An optional machine-readable error code for
                           specific error handling.
    """
    def __init__(self, message: str, code: str | None = None):
        super().__init__(message)
        self.code = code

    def __str__(self) -> str:
        """Return the string representation of the error, including the code
        if present."""
        if self.code:
            return f"{super().__str__()} (code: {self.code})"
        return super().__str__()