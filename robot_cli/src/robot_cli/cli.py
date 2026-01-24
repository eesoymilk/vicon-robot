"""CLI for robot control using Typer."""

import typer
from rich.console import Console
from rich.table import Table

from .command import Command
from .redis_client import RedisClient

app = typer.Typer(help="Vicon Robot Controller CLI", invoke_without_command=True)
console = Console()


@app.callback()
def callback(ctx: typer.Context):
    """Vicon Robot Controller CLI. Runs interactive mode by default."""
    if ctx.invoked_subcommand is None:
        interactive()


@app.command()
def status():
    """Show current objects and board position."""
    redis = RedisClient()
    objects = redis.get_objects()
    board_pos = redis.get_board_position()

    # Board status
    if board_pos:
        console.print(f"[green]Board:[/] ({board_pos[0]:.3f}, {board_pos[1]:.3f}, {board_pos[2]:.3f})")
    else:
        console.print("[red]Board:[/] NOT DETECTED")

    # Objects table
    if not objects:
        console.print("[yellow]No objects detected[/]")
        return

    table = Table(title="Available Objects")
    table.add_column("Name", style="cyan")
    table.add_column("X", justify="right")
    table.add_column("Y", justify="right")
    table.add_column("Z", justify="right")

    for name, pos in objects.items():
        table.add_row(name, f"{pos[0]:.3f}", f"{pos[1]:.3f}", f"{pos[2]:.3f}")

    console.print(table)


@app.command()
def grab(name: str):
    """Grab an object by name."""
    redis = RedisClient()
    objects = redis.get_objects()
    board_pos = redis.get_board_position()

    if name not in objects:
        console.print(f"[red]Object '{name}' not found[/]")
        console.print(f"Available: {', '.join(objects.keys()) or 'none'}")
        raise typer.Exit(1)

    if not board_pos:
        console.print("[red]Board not detected - cannot grab[/]")
        raise typer.Exit(1)

    pos = objects[name]
    command = Command(
        function_name="grab_object",
        name=name,
        position=pos,
        inrange=True,
        return_position=board_pos,
    )

    console.print(f"[dim]Command: {command.model_dump_json()}[/]")
    redis.publish_command(command.model_dump_json())
    console.print(f"[green]Sent grab command for {name}[/]")


@app.command()
def watch():
    """Watch objects and board position (refresh every 2s)."""
    import time

    redis = RedisClient()

    try:
        while True:
            console.clear()
            status()
            console.print("\n[dim]Refreshing every 2s... Ctrl+C to exit[/]")
            time.sleep(2)
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopped[/]")


def build_display(objects: dict, board_pos: tuple | None, message: str = "") -> Table:
    """Build the display table."""
    table = Table(title="Robot Controller", box=None, expand=True)
    table.add_column("Idx", style="cyan", width=4)
    table.add_column("Name", style="bold")
    table.add_column("X", justify="right")
    table.add_column("Y", justify="right")
    table.add_column("Z", justify="right")

    for i, (name, pos) in enumerate(objects.items()):
        table.add_row(f"[{i}]", name, f"{pos[0]:.3f}", f"{pos[1]:.3f}", f"{pos[2]:.3f}")

    return table


@app.command()
def interactive():
    """Interactive mode with live updates."""
    import threading
    import sys
    import select

    redis = RedisClient()
    running = True
    message = ""
    selected_idx: int | None = None

    def get_input():
        """Non-blocking input check."""
        if select.select([sys.stdin], [], [], 0.0)[0]:
            return sys.stdin.readline().strip().lower()
        return None

    from rich.live import Live
    from rich.panel import Panel
    from rich.layout import Layout

    def make_layout():
        objects = redis.get_objects()
        board_pos = redis.get_board_position()
        obj_list = list(objects.items())

        # Board info
        if board_pos:
            board_str = f"[green]✓ Board:[/] ({board_pos[0]:.3f}, {board_pos[1]:.3f}, {board_pos[2]:.3f})"
        else:
            board_str = "[red]✗ Board: NOT DETECTED[/]"

        # Objects table
        if objects:
            table = Table(box=None, expand=True, show_header=True)
            table.add_column("", width=4)
            table.add_column("Name", style="bold")
            table.add_column("X", justify="right")
            table.add_column("Y", justify="right")
            table.add_column("Z", justify="right")

            for i, (name, pos) in enumerate(obj_list):
                idx_style = "bold cyan" if i == selected_idx else "cyan"
                table.add_row(f"[{idx_style}][{i}][/]", name, f"{pos[0]:.3f}", f"{pos[1]:.3f}", f"{pos[2]:.3f}")
            obj_display = table
        else:
            obj_display = "[yellow]No objects detected[/]"

        content = f"{board_str}\n\n"

        layout = Layout()
        layout.split_column(
            Layout(Panel(f"{board_str}", title="Status"), size=3),
            Layout(Panel(obj_display, title="Objects")),
            Layout(Panel(f"{message}\n[dim]number=grab, q=quit[/]", title="Input"), size=4),
        )
        return layout, obj_list, board_pos

    console.print("[dim]Starting interactive mode... Type number + Enter to grab, q to quit[/]")

    with Live(make_layout()[0], refresh_per_second=4, console=console) as live:
        while running:
            layout, obj_list, board_pos = make_layout()
            live.update(layout)

            choice = get_input()
            if choice is None:
                continue

            if choice == "q":
                running = False
                message = "[yellow]Exiting...[/]"
            elif choice.isdigit():
                idx = int(choice)
                if 0 <= idx < len(obj_list):
                    if not board_pos:
                        message = "[red]Board not detected![/]"
                        continue
                    name, pos = obj_list[idx]
                    command = Command(
                        function_name="grab_object",
                        name=name,
                        position=pos,
                        inrange=True,
                        return_position=board_pos,
                    )
                    redis.publish_command(command.model_dump_json())
                    message = f"[green]Sent grab for {name}[/]"
                else:
                    message = f"[red]Invalid index: {idx}[/]"
            else:
                message = f"[red]Unknown: {choice}[/]"


def main():
    app()


if __name__ == "__main__":
    main()
