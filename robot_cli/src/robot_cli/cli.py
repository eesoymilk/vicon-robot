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


@app.command()
def interactive():
    """Interactive mode with live updates."""
    import threading
    import queue

    from rich.live import Live
    from rich.panel import Panel
    from rich.layout import Layout

    redis = RedisClient()
    input_queue = queue.Queue()
    running = threading.Event()
    running.set()
    message = [""]  # Use list to allow mutation in closure

    def input_thread():
        """Thread to handle blocking input."""
        while running.is_set():
            try:
                choice = input().strip().lower()
                input_queue.put(choice)
                if choice == "q":
                    break
            except EOFError:
                break

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
                table.add_row(f"[cyan][{i}][/]", name, f"{pos[0]:.3f}", f"{pos[1]:.3f}", f"{pos[2]:.3f}")
            obj_display = table
        else:
            obj_display = "[yellow]No objects detected[/]"

        layout = Layout()
        layout.split_column(
            Layout(Panel(board_str, title="Status"), size=3),
            Layout(Panel(obj_display, title="Objects")),
            Layout(Panel(f"{message[0]}\n[dim]number + Enter = grab, q = quit[/]", title="Input"), size=4),
        )
        return layout, obj_list, board_pos

    # Start input thread
    t = threading.Thread(target=input_thread, daemon=True)
    t.start()

    with Live(make_layout()[0], refresh_per_second=4, console=console) as live:
        while running.is_set():
            layout, obj_list, board_pos = make_layout()
            live.update(layout)

            # Check for input
            try:
                choice = input_queue.get_nowait()
            except queue.Empty:
                continue

            if choice == "q":
                running.clear()
                message[0] = "[yellow]Exiting...[/]"
            elif choice.isdigit():
                idx = int(choice)
                if 0 <= idx < len(obj_list):
                    if not board_pos:
                        message[0] = "[red]Board not detected![/]"
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
                    message[0] = f"[green]Sent grab for {name}[/]"
                else:
                    message[0] = f"[red]Invalid index: {idx}[/]"
            elif choice:
                message[0] = f"[red]Unknown: {choice}[/]"


def main():
    app()


if __name__ == "__main__":
    main()
