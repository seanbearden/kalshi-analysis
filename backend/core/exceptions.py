"""Custom application exceptions."""


class KalshiAnalysisException(Exception):
    """Base exception for Kalshi Analysis application."""

    def __init__(self, message: str, status_code: int = 500) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class KalshiAPIError(KalshiAnalysisException):
    """Exception raised when Kalshi API request fails."""

    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message, status_code)


class DatabaseError(KalshiAnalysisException):
    """Exception raised when database operation fails."""

    def __init__(self, message: str, status_code: int = 500) -> None:
        super().__init__(message, status_code)


class ValidationError(KalshiAnalysisException):
    """Exception raised when data validation fails."""

    def __init__(self, message: str, status_code: int = 422) -> None:
        super().__init__(message, status_code)


class NotFoundError(KalshiAnalysisException):
    """Exception raised when requested resource not found."""

    def __init__(self, message: str, status_code: int = 404) -> None:
        super().__init__(message, status_code)
