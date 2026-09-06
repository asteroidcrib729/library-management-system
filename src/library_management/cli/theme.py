"""Color definitions shared by the interactive CLI."""

from prompt_toolkit.styles import Style
from rich.console import Console
from rich.theme import Theme

RICH_THEME = Theme(
    {
        "accent": "bold #55D6BE",
        "command": "bold #F7B267",
        "heading": "bold #7AA2F7",
        "muted": "#8994A5",
        "success": "bold #9ECE6A",
        "warning": "bold #E0AF68",
        "error": "bold #F7768E",
    }
)

PROMPT_STYLE = Style.from_dict(
    {
        "app": "bold #55D6BE",
        "shell": "bold #7AA2F7",
        "path": "#BB9AF7",
        "symbol": "bold #F7B267",
    }
)


def create_console(*, color_enabled: bool = True) -> Console:
    """Create the Rich console used by the application."""
    return Console(theme=RICH_THEME, no_color=not color_enabled)
