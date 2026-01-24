from textual.app import App, ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Header, Footer, Static, ListView, ListItem, Label
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
        yield Label(
            f"{self.object_name}: ({self.position[0]:.3f}, {self.position[1]:.3f}, {self.position[2]:.3f})"
        )


class StatusPanel(Static):
    """Panel showing current status."""

    def __init__(self, id: str | None = None) -> None:
        super().__init__("", id=id)
        self.update_status("Ready")

    def update_status(self, message: str) -> None:
        self.update(f"[bold]Status:[/bold] {message}")


class ViconTUI(App):
    """TUI application for manual robot control."""

    CSS = """
    Screen {
        layout: vertical;
    }

    #main-container {
        height: 1fr;
        padding: 1;
    }

    #object-list {
        height: 1fr;
        border: solid green;
        padding: 1;
    }

    #status-panel {
        height: 3;
        padding: 1;
        border: solid blue;
    }

    ListView {
        height: 1fr;
    }

    ListItem {
        padding: 0 1;
    }

    ListItem:hover {
        background: $accent-darken-1;
    }

    ListView > ListItem.--highlight {
        background: $accent;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("enter", "grab", "Grab Object"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.redis_client = RedisClient()
        self.objects: dict[str, tuple[float, float, float]] = {}

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="main-container"):
            with Vertical(id="object-list"):
                yield Static("[bold]Available Objects[/bold]")
                yield ListView(id="objects")
            yield StatusPanel(id="status-panel")
        yield Footer()

    def on_mount(self) -> None:
        """Called when the app is mounted."""
        self.refresh_objects()
        self.set_interval(2.0, self.refresh_objects)

    def refresh_objects(self) -> None:
        """Refresh the object list from Redis."""
        try:
            self.objects = self.redis_client.get_objects()
            list_view = self.query_one("#objects", ListView)
            list_view.clear()

            for name, position in self.objects.items():
                list_view.append(ObjectItem(name, position))

            status = self.query_one("#status-panel", StatusPanel)
            status.update_status(f"Found {len(self.objects)} objects")
        except Exception as e:
            status = self.query_one("#status-panel", StatusPanel)
            status.update_status(f"Error: {e}")

    def action_refresh(self) -> None:
        """Refresh action triggered by 'r' key."""
        self.refresh_objects()

    def action_grab(self) -> None:
        """Grab the selected object."""
        list_view = self.query_one("#objects", ListView)
        status = self.query_one("#status-panel", StatusPanel)

        if list_view.highlighted_child is None:
            status.update_status("No object selected")
            return

        item = list_view.highlighted_child
        if not isinstance(item, ObjectItem):
            return

        board_position = self.redis_client.get_board_position()
        if board_position is None:
            status.update_status("Error: Board not found in Vicon")
            return

        command = Command(
            function_name="grab_object",
            position=item.position,
            return_position=board_position,
        )

        try:
            self.redis_client.publish_command(command.model_dump_json())
            status.update_status(f"Sent grab command for {item.object_name}")
        except Exception as e:
            status.update_status(f"Error sending command: {e}")
