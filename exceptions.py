class NetworkManagerError(Exception):
    """Custom exception for network management errors."""
    def __init__(self, message, code=None):
        super().__init__(message)
        self.code = code