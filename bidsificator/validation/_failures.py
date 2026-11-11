"""Logging of failures inside the validator itself.

A validation run visits every file, so a bug in one check fails once per file
(or per metadata field). `FailureLog` writes the first failure of each kind
with its traceback and the repeats at DEBUG, so the log names the bug without
being flooded by it.
"""

import logging


class FailureLog:
    """Per-validator record of which internal failures were already logged."""

    def __init__(self, logger: logging.Logger):
        self._logger = logger
        self._seen: set[str] = set()

    def exception(self, kind: str, message: str, *args) -> None:
        """Log the exception being handled: at ERROR the first time for `kind`, then at DEBUG."""
        self._log(logging.ERROR, kind, message, *args)

    def warning(self, kind: str, message: str, *args) -> None:
        """Log the exception being handled: at WARNING the first time for `kind`, then at DEBUG."""
        self._log(logging.WARNING, kind, message, *args)

    def _log(self, level: int, kind: str, message: str, *args) -> None:
        if kind in self._seen:
            level = logging.DEBUG
        else:
            self._seen.add(kind)
            message += " (repeats of this failure are logged at DEBUG)"
        self._logger.log(level, message, *args, exc_info=True)


def describe(error: BaseException) -> str:
    """`ExceptionType: message`, for a report entry the user can read without the log."""
    return f"{type(error).__name__}: {error}"
