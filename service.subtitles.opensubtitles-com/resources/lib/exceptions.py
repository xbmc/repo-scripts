
class ProviderError(Exception):
    """Exception raised by providers."""
    pass


class ConfigurationError(ProviderError):
    """Exception raised by providers when badly configured."""
    pass


class AuthenticationError(ProviderError):
    """Exception raised by providers when authentication failed."""
    pass


class ServiceUnavailable(ProviderError):
    """Exception raised when status is '503 Service Unavailable'."""
    pass


class DownloadLimitExceeded(ProviderError):
    """Exception raised by providers when download limit is exceeded."""
    pass


class TooManyRequests(ProviderError):
    """Exception raised by providers when too many requests are made."""
    pass


class BadUsernameError(ProviderError):
    """Exception raised by providers when user entered the email instead of the username in the username field."""
    pass