def get_color(severity):
    """Returns a color string based on severity level."""
    return {
        "CRITICAL": "bold red",
        "HIGH": "red",
        "MEDIUM": "yellow",
        "LOW": "cyan",
        "INFO": "blue"
    }.get(severity.upper(), "default")


