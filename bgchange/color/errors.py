"""The error raised when the colour text is not a valid hex colour."""


class ColorParseError(ValueError):
    """Raised when the colour text is not a valid hex colour.

    Like ImageLoadError, the message is written for the end user and shown
    as-is by the CLI and the API.
    """
