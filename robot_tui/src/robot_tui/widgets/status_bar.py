"""Status bar widget for connection and board position display."""

from pathlib import Path

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static


class StatusBar(Widget):
    """Status bar showing Redis connection and board position."""

    CSS_PATH = Path(__file__).parent / "status_bar.tcss"

    redis_connected: reactive[bool] = reactive(False)
    board_position: reactive[tuple[float, float, float] | None] = reactive(None)

    def compose(self) -> ComposeResult:
        yield Static("[red]○ Redis Disconnected[/red]", id="redis-status")
        yield Static("[dim]● Board: Not available[/dim]", id="board-status")

    def watch_redis_connected(self, connected: bool) -> None:
        """Update Redis status display."""
        status_widget = self.query_one("#redis-status", Static)
        if connected:
            status_widget.update("[green]● Redis Connected[/green]")
        else:
            status_widget.update("[red]○ Redis Disconnected[/red]")

    def watch_board_position(self, position: tuple[float, float, float] | None) -> None:
        """Update board position display."""
        board_widget = self.query_one("#board-status", Static)
        if position:
            x, y, z = position
            board_widget.update(f"[blue]● Board:[/blue] ({x:.3f}, {y:.3f}, {z:.3f})")
        else:
            board_widget.update("[dim]● Board: Not available[/dim]")
