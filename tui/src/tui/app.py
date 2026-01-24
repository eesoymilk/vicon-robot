from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Static, ListView, ListItem, Label, Rule
from textual.binding import Binding

from .command import Command
from .redis_client import RedisClient


class ObjectItem(ListItem):
    """A list item representing a Vicon object."""

    def __init__(self, name: str, position: tuple[float, float, float]) -> None:
        super().__init__()
        self.object_name = name
        self.position = position

    def compose(self) -> ComposeResult:
        pos = self.position
        yield Label(f"[bold cyan]{self.object_name}[/]  [dim]({pos[0]:.3f}, {pos[1]:.3f}, {pos[2]:.3f})[/]")


class InfoPanel(Static):
    """Panel showing system information."""

    def __init__(self, id: str | None = None) -> None:
        super().__init__("", id=id)
        self._object_count: int = 0
        self._update_display()

    def _update_display(self) -> None:
        content = f"[bold]Objects:[/] [cyan]{self._object_count}[/]"
        self.update(content)

    def set_object_count(self, count: int) -> None:
        self._object_count = count
        self._update_display()


class BoardPanel(Static):
    """Panel showing board (drop zone) position."""

    def __init__(self, id: str | None = None) -> None:
        super().__init__("", id=id)
        self._board_pos: tuple[float, float, float] | None = None
        self._update_display()

    def _update_display(self) -> None:
        if self._board_pos:
            x, y, z = self._board_pos
            content = f"""[bold]Drop Zone (Board)[/]
[green]✓ Detected[/]
  X: [cyan]{x:+.3f}[/]
  Y: [cyan]{y:+.3f}[/]
  Z: [cyan]{z:+.3f}[/]"""
        else:
            content = """[bold]Drop Zone (Board)[/]
[red]✗ Not Detected[/]
[dim]Grab disabled until
Board is visible[/]"""
        self.update(content)

    def set_position(self, pos: tuple[float, float, float] | None) -> None:
        self._board_pos = pos
        self._update_display()


class StatusPanel(Static):
    """Panel showing current action status."""

    def __init__(self, id: str | None = None) -> None:
        super().__init__("", id=id)
        self.update_status("Ready", "info")

    def update_status(self, message: str, level: str = "info") -> None:
        color = {"info": "blue", "success": "green", "error": "red", "warning": "yellow"}.get(level, "white")
        self.update(f"[bold {color}]● {message}[/]")


class ViconTUI(App):
    """TUI application for manual robot control."""

    TITLE = "Vicon Robot Controller"
    SUB_TITLE = "Manual Control Interface"

    CSS = """
    Screen {
        background: $surface;
    }

    #main-container {
        height: 1fr;
        padding: 1 2;
    }

    #sidebar {
        width: 28;
        padding: 1;
        border: solid $primary;
        background: $surface-darken-1;
    }

    #content {
        padding: 1;
        margin-left: 1;
    }

    #object-list-container {
        height: 1fr;
        border: solid $success;
        background: $surface-darken-1;
        padding: 1;
    }

    #info-panel {
        height: auto;
        padding: 1;
        margin-bottom: 1;
    }

    #board-panel {
        height: auto;
        padding: 1;
        border: solid $secondary;
        background: $surface-darken-1;
        margin-top: 1;
    }

    #status-panel {
        height: 3;
        padding: 1;
        border: solid $warning;
        background: $surface-darken-1;
        margin-top: 1;
    }

    .title {
        text-style: bold;
        color: $text;
        padding-bottom: 1;
    }

    ListView {
        height: 1fr;
        scrollbar-gutter: stable;
    }

    ListItem {
        padding: 0 1;
        height: 2;
    }

    ListItem:hover {
        background: $accent 30%;
    }

    ListView > ListItem.--highlight {
        background: $accent;
    }

    Rule {
        margin: 1 0;
        color: $primary-darken-2;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("enter", "grab", "Grab"),
        Binding("escape", "deselect", "Deselect"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.redis_client = RedisClient()
        self.objects: dict[str, tuple[float, float, float]] = {}

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="main-container"):
            with Horizontal():
                with Vertical(id="sidebar"):
                    yield InfoPanel(id="info-panel")
                    yield BoardPanel(id="board-panel")
                    yield Rule()
                    yield Static("[bold]Keybindings[/]", classes="title")
                    yield Static("[dim]↑↓[/]  Navigate")
                    yield Static("[dim]Enter[/]  Grab object")
                    yield Static("[dim]r[/]  Refresh list")
                    yield Static("[dim]q[/]  Quit")
                with Vertical(id="content"):
                    with Vertical(id="object-list-container"):
                        yield Static("[bold]Available Objects[/]", classes="title")
                        yield ListView(id="objects")
                    yield StatusPanel(id="status-panel")
        yield Footer()

    def on_mount(self) -> None:
        """Called when the app is mounted."""
        self.refresh_objects()
        self.set_interval(2.0, self.refresh_objects)

    def refresh_objects(self) -> None:
        """Refresh the object list from Redis."""
        status = self.query_one("#status-panel", StatusPanel)
        info = self.query_one("#info-panel", InfoPanel)
        board_panel = self.query_one("#board-panel", BoardPanel)

        try:
            self.objects = self.redis_client.get_objects()
            board_pos = self.redis_client.get_board_position()

            list_view = self.query_one("#objects", ListView)
            list_view.clear()

            for name, position in self.objects.items():
                list_view.append(ObjectItem(name, position))

            info.set_object_count(len(self.objects))
            board_panel.set_position(board_pos)

            if not self.objects:
                status.update_status("No objects detected", "warning")
            elif not board_pos:
                status.update_status("Board not detected - grab disabled", "warning")
            else:
                status.update_status("Ready", "info")

        except Exception as e:
            status.update_status(f"Redis error: {e}", "error")

    def action_refresh(self) -> None:
        """Refresh action triggered by 'r' key."""
        self.refresh_objects()
        status = self.query_one("#status-panel", StatusPanel)
        status.update_status("Refreshed", "success")

    def action_deselect(self) -> None:
        """Deselect current item."""
        list_view = self.query_one("#objects", ListView)
        list_view.index = None

    def action_grab(self) -> None:
        """Grab the selected object."""
        list_view = self.query_one("#objects", ListView)
        status = self.query_one("#status-panel", StatusPanel)

        if list_view.highlighted_child is None:
            status.update_status("No object selected", "warning")
            return

        item = list_view.highlighted_child
        if not isinstance(item, ObjectItem):
            return

        board_position = self.redis_client.get_board_position()
        if board_position is None:
            status.update_status("Board not found - cannot grab", "error")
            return

        command = Command(
            function_name="grab_object",
            name=item.object_name,
            position=item.position,
            inrange=True,
            return_position=board_position,
        )

        try:
            self.redis_client.publish_command(command.model_dump_json())
            status.update_status(f"Grabbing {item.object_name}...", "success")
        except Exception as e:
            status.update_status(f"Command failed: {e}", "error")
