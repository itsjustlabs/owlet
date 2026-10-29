class OwletError(Exception):
    """Generic exception."""


class OwletConnectionError(OwletError):
    """When a connection error occurs."""


class OwletRateLimitError(OwletConnectionError):
    """When Owlet is rate limiting or failing and requests are paused."""

    def __init__(self, message: str, retry_after: float) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class OwletAuthenticationError(OwletError):
    """When login details are incorrect."""


class OwletCredentialsError(OwletError):
    """When login creds are incorrect, api no longer returns if this is username or password that is incorrect."""


class OwletDevicesError(OwletError):
    """when no devices are found."""
