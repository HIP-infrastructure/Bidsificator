"""Manager for status bar messages with styled feedback."""


from PyQt6.QtWidgets import QStatusBar


class StatusBarManager:
    """
    Manages status bar messages with visual styling for different states.

    Provides methods to show progress, success, and error messages
    with appropriate colors and icons.
    """

    # Status icons
    ICON_PROGRESS = "\u23F3"  # Hourglass
    ICON_SUCCESS = "\u2714"   # Check mark
    ICON_WARNING = "\u26A0"   # Warning triangle
    ICON_ERROR = "\u2718"     # X mark

    # Color styles
    STYLE_PROGRESS = "color: #2196F3;"  # Blue
    STYLE_SUCCESS = "color: #4CAF50;"   # Green
    STYLE_WARNING = "color: #FF9800;"   # Amber
    STYLE_ERROR = "color: #F44336;"     # Red
    STYLE_DEFAULT = ""

    def __init__(self, status_bar: QStatusBar):
        """
        Initialize the StatusBarManager.

        Args:
            status_bar: The QStatusBar widget to manage
        """
        self._status_bar = status_bar

    def show_progress(self, message: str, progress: int | None = None) -> None:
        """
        Show a progress message in blue.

        Args:
            message: The message to display
            progress: Optional progress percentage (0-100)
        """
        if progress is not None:
            display_message = f"{self.ICON_PROGRESS} {message} {progress}%"
        else:
            display_message = f"{self.ICON_PROGRESS} {message}"

        self._status_bar.setStyleSheet(self.STYLE_PROGRESS)
        self._status_bar.showMessage(display_message)

    def show_success(self, message: str) -> None:
        """
        Show a success message in green.

        Args:
            message: The message to display
        """
        display_message = f"{self.ICON_SUCCESS} {message}"
        self._status_bar.setStyleSheet(self.STYLE_SUCCESS)
        self._status_bar.showMessage(display_message)

    def show_warning(self, message: str) -> None:
        """
        Show a warning message in amber.

        Used for a "completed with errors" import: unlike a progress/success
        message, this is meant to persist after the completion dialog closes, so
        callers deliberately do not clear it on dialog dismissal.

        Args:
            message: The message to display
        """
        display_message = f"{self.ICON_WARNING} {message}"
        self._status_bar.setStyleSheet(self.STYLE_WARNING)
        self._status_bar.showMessage(display_message)

    def show_error(self, message: str) -> None:
        """
        Show an error message in red.

        Args:
            message: The message to display
        """
        display_message = f"{self.ICON_ERROR} {message}"
        self._status_bar.setStyleSheet(self.STYLE_ERROR)
        self._status_bar.showMessage(display_message)

    def clear(self) -> None:
        """Clear the status bar message and reset styling."""
        self._status_bar.setStyleSheet(self.STYLE_DEFAULT)
        self._status_bar.clearMessage()
