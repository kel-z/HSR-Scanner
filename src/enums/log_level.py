from enum import Enum


class LogLevel(Enum):
    """LogLevel enum for logging the events"""

    INFO = "INFO"
    ERROR = "ERROR"
    WARNING = "WARN"
    DEBUG = "DEBUG"
    TRACE = "TRACE"
    FATAL = "FATAL"
