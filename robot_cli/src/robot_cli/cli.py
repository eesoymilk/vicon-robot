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
    """Interactive mode - select object by number."""
    redis = RedisClient()

    while True:
        console.print("\n" + "=" * 50)
        objects = redis.get_objects()
        board_pos = redis.get_board_position()

        # Board
        if board_pos:
            console.print(f"[green]Board:[/] ({board_pos[0]:.3f}, {board_pos[1]:.3f}, {board_pos[2]:.3f})")
        else:
            console.print("[red]Board: NOT DETECTED[/]")

        # Objects
        if not objects:
            console.print("[yellow]No objects[/]")
            input("Enter to refresh...")
            continue

        obj_list = list(objects.items())
        for i, (name, pos) in enumerate(obj_list):
            console.print(f"  [cyan][{i}][/] {name}: ({pos[0]:.3f}, {pos[1]:.3f}, {pos[2]:.3f})")

        console.print("[dim]number=grab, r=refresh, q=quit[/]")
        choice = input("> ").strip().lower()

        if choice == "q":
            break
        elif choice == "r":
            continue
        elif choice.isdigit():
            idx = int(choice)
            if 0 <= idx < len(obj_list):
                if not board_pos:
                    console.print("[red]Board not detected![/]")
                    continue
                name, pos = obj_list[idx]
                command = Command(
                    function_name="grab_object",
                    name=name,
                    position=pos,
                    inrange=True,
                    return_position=board_pos,
                )
                console.print(f"[dim]{command.model_dump_json()}[/]")
                redis.publish_command(command.model_dump_json())
                console.print(f"[green]Grabbed {name}[/]")


def main():
    app()


if __name__ == "__main__":
    main()
