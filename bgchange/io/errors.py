"""The error raised when an input cannot be turned into a usable image."""


class ImageLoadError(ValueError):
    """Raised when the input cannot be turned into a usable image.

    The message is always written for the end user (it is shown as-is by the
    CLI and the API), so it says what went wrong and what to do.
    """
