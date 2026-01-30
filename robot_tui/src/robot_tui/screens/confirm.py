"""Confirmation modal screen for grab commands."""

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static


class ConfirmGrabScreen(ModalScreen[bool]):
    """Modal screen to confirm a grab command."""

    CSS_PATH = Path(__file__).parent / "confirm.tcss"

    BINDINGS = [
        ("y", "confirm", "Yes"),
        ("n", "cancel", "No"),
        ("enter", "confirm", "Confirm"),
        ("escape", "cancel", "Cancel"),
    ]

    def __init__(
        self,
        object_name: str,
        position: tuple[float, float, float],
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes)
        self.object_name = object_name
        self.position = position

    def compose(self) -> ComposeResult:
        x, y, z = self.position
        with Vertical(id="confirm-dialog"):
            yield Label("Confirm Grab Command", id="confirm-title")
            yield Static(f"Object: [bold cyan]{self.object_name}[/bold cyan]", id="confirm-object")
            yield Static(f"Position: ({x:.3f}, {y:.3f}, {z:.3f})", id="confirm-position")
            yield Label("Send grab command to robot?", id="confirm-question")
            with Horizontal(id="button-row"):
                yield Button("Yes [Y]", variant="success", id="btn-yes")
                yield Button("No [N]", variant="error", id="btn-no")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "btn-yes":
            self.dismiss(True)
        else:
            self.dismiss(False)

    def action_confirm(self) -> None:
        """Confirm the grab command."""
        self.dismiss(True)

    def action_cancel(self) -> None:
        """Cancel the grab command."""
        self.dismiss(False)
