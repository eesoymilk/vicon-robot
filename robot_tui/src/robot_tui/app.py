"""Main Textual TUI application for robot control."""

from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import DataTable, Footer, Header, RichLog

from robot_tui.command import Command
from robot_tui.redis_client import AsyncRedisClient
from robot_tui.screens import ConfirmGrabScreen
from robot_tui.widgets import StatusBar


class RobotTUI(App):
    """Beautiful TUI for robot control via Vicon."""

    TITLE = "Vicon Robot Controller"
    CSS_PATH = Path(__file__).parent / "app.tcss"

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("g", "grab", "Grab"),
        Binding("r", "refresh", "Refresh"),
    ]

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
    ) -> None:
        super().__init__()
        self._redis = AsyncRedisClient(
            host=host,
            port=port,
            on_connect=self._on_redis_connect,
            on_disconnect=self._on_redis_disconnect,
        )
        self._objects: dict[str, tuple[float, float, float]] = {}
        self._reconnect_pending = False

    def compose(self) -> ComposeResult:
        yield Header()
        yield StatusBar()
        yield DataTable(cursor_type="row")
        yield RichLog(highlight=True, markup=True)
        yield Footer()

    async def on_mount(self) -> None:
        """Initialize the app after mounting."""
        # Set up the data table
        table = self.query_one(DataTable)
        table.add_columns("Object", "X (m)", "Y (m)", "Z (m)")

        # Log startup
        log = self.query_one(RichLog)
        log.write("[cyan]Starting Vicon Robot Controller...[/cyan]")

        # Connect to Redis
        if await self._redis.connect():
            log.write("[green]Connected to Redis[/green]")
        else:
            log.write("[yellow]Redis not available, will retry...[/yellow]")

        # Start polling
        self.set_interval(0.25, self._poll_redis)

    async def _poll_redis(self) -> None:
        """Poll Redis for updates at 4Hz."""
        status_bar = self.query_one(StatusBar)

        if not self._redis.connected:
            # Try to reconnect
            if not self._reconnect_pending:
                self._reconnect_pending = True
                if await self._redis.try_reconnect():
                    log = self.query_one(RichLog)
                    log.write("[green]Reconnected to Redis[/green]")
                self._reconnect_pending = False
            return

        # Update status bar
        status_bar.redis_connected = True

        # Get board position
        board_pos = await self._redis.get_board_position()
        status_bar.board_position = board_pos

        # Get objects and update table
        objects = await self._redis.get_objects()
        if objects != self._objects:
            self._objects = objects
            self._update_table()

    def _update_table(self) -> None:
        """Update the data table with current objects."""
        table = self.query_one(DataTable)

        # Remember current selection
        current_row = table.cursor_row

        # Clear and repopulate
        table.clear()
        for name, (x, y, z) in sorted(self._objects.items()):
            table.add_row(name, f"{x:.3f}", f"{y:.3f}", f"{z:.3f}", key=name)

        # Restore selection if possible
        if current_row is not None and table.row_count > 0:
            table.move_cursor(row=min(current_row, table.row_count - 1))

    def _on_redis_connect(self) -> None:
        """Handle Redis connection."""
        self.query_one(StatusBar).redis_connected = True

    def _on_redis_disconnect(self) -> None:
        """Handle Redis disconnection."""
        self.query_one(StatusBar).redis_connected = False
        log = self.query_one(RichLog)
        log.write("[yellow]Redis connection lost, reconnecting...[/yellow]")

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle Enter key on table row."""
        self.action_grab()

    def action_grab(self) -> None:
        """Open grab confirmation for selected object."""
        table = self.query_one(DataTable)

        if table.row_count == 0:
            log = self.query_one(RichLog)
            log.write("[red]No objects available[/red]")
            return

        # Get selected row
        row_key = table.get_row_at(table.cursor_row)
        if not row_key:
            return

        # Get object name from the first column
        object_name = str(row_key[0])
        if object_name not in self._objects:
            return

        position = self._objects[object_name]

        # Show confirmation modal
        self.push_screen(
            ConfirmGrabScreen(object_name, position),
            self._handle_grab_confirm,
        )

    async def _handle_grab_confirm(self, confirmed: bool) -> None:
        """Handle the grab confirmation result."""
        if not confirmed:
            return

        table = self.query_one(DataTable)
        log = self.query_one(RichLog)

        # Get selected object
        row_key = table.get_row_at(table.cursor_row)
        if not row_key:
            return

        object_name = str(row_key[0])
        if object_name not in self._objects:
            log.write(f"[red]Object '{object_name}' no longer available[/red]")
            return

        position = self._objects[object_name]

        # Get board position for return
        board_pos = await self._redis.get_board_position()

        # Create and send command
        command = Command(
            function_name="grab_object",
            name=object_name,
            position=position,
            inrange=True,
            return_position=board_pos,
        )

        if await self._redis.publish_command(command.model_dump_json()):
            log.write(f"[green]Sent grab command for '{object_name}'[/green]")
        else:
            log.write("[red]Failed to send command (Redis disconnected)[/red]")

    def action_refresh(self) -> None:
        """Force refresh the object list."""
        log = self.query_one(RichLog)
        log.write("[cyan]Refreshing...[/cyan]")
        # Clear cached objects to force update
        self._objects = {}

    async def action_quit(self) -> None:
        """Quit the application."""
        await self._redis.disconnect()
        self.exit()


def main() -> None:
    """Entry point for the TUI application."""
    app = RobotTUI()
    app.run()


if __name__ == "__main__":
    main()
