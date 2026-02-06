"""Command-line interface for RLDS conversion."""

from pathlib import Path
import sys
from typing import Optional
from typing_extensions import Annotated
import typer
import tensorflow_datasets as tfds

from rlds_converter.vicon_robot_dataset import ViconRobot

app = typer.Typer(
    name="rlds-convert",
    help="Convert Vicon robot trajectories to RLDS format for VLA training",
    add_completion=False,
)


def verify_dataset(dataset_dir: Path, chunk_size: int):
    """Verify the generated dataset by loading and inspecting it.
    
    Args:
        dataset_dir: Directory where the dataset was saved
        chunk_size: Expected action chunk size
    """
    typer.echo(typer.style("\n=== Verifying Dataset ===", fg=typer.colors.BRIGHT_CYAN, bold=True))
    
    try:
        # Load the dataset
        ds = tfds.load(
            'vicon_robot',
            data_dir=dataset_dir,
            split='train',
        )
        
        # Count episodes
        episode_count = 0
        total_steps = 0
        
        for episode in ds:
            episode_count += 1
            steps = episode['steps']
            step_count = len(list(steps))
            total_steps += step_count
            
            # Get session ID
            session_id = episode['episode_metadata']['session_id'].numpy().decode('utf-8')
            
            typer.echo(f"\nEpisode {episode_count}: {typer.style(session_id, fg=typer.colors.BRIGHT_BLUE)}")
            typer.echo(f"  - Steps: {step_count}")
            
            # Inspect first and last step
            steps_list = list(steps)
            if steps_list:
                first_step = steps_list[0]
                last_step = steps_list[-1]
                
                # Check dimensions
                img_shape = first_step['observation']['image'].shape
                action_jp_shape = first_step['action']['joint_positions'].shape
                action_ee_shape = first_step['action']['ee_pose'].shape
                action_gripper_shape = first_step['action']['gripper'].shape
                
                typer.echo(f"  - Image shape: {img_shape}")
                typer.echo(f"  - Action joint_positions shape: {action_jp_shape} (expected: ({chunk_size}, 6))")
                typer.echo(f"  - Action ee_pose shape: {action_ee_shape} (expected: ({chunk_size}, 7))")
                typer.echo(f"  - Action gripper shape: {action_gripper_shape} (expected: ({chunk_size},))")
                typer.echo(f"  - First step is_first: {first_step['is_first'].numpy()}")
                typer.echo(f"  - Last step is_last: {last_step['is_last'].numpy()}")
                typer.echo(f"  - Last step is_terminal: {last_step['is_terminal'].numpy()}")
                typer.echo(f"  - Phase: {first_step['observation']['phase'].numpy().decode('utf-8')}")
        
        typer.echo(typer.style("\n=== Summary ===", fg=typer.colors.BRIGHT_CYAN, bold=True))
        typer.echo(f"Total episodes: {episode_count}")
        typer.echo(f"Total steps: {total_steps}")
        typer.echo(f"Average steps per episode: {total_steps / episode_count:.1f}")
        typer.echo(typer.style("\n✓ Dataset verification complete!", fg=typer.colors.BRIGHT_GREEN, bold=True))
        
    except Exception as e:
        typer.echo(typer.style(f"\n✗ Dataset verification failed: {e}", fg=typer.colors.BRIGHT_RED, bold=True))
        import traceback
        traceback.print_exc()
        raise typer.Exit(code=1)


@app.command()
def convert(
    input: Annotated[
        Path,
        typer.Option(
            "--input",
            "-i",
            help="Path to trajectories directory containing CSV files and frame folders",
            exists=True,
            file_okay=False,
            dir_okay=True,
            resolve_path=True,
        ),
    ],
    output: Annotated[
        Path,
        typer.Option(
            "--output",
            "-o",
            help="Output directory for TFDS dataset",
            resolve_path=True,
        ),
    ],
    chunk_size: Annotated[
        int,
        typer.Option(
            "--chunk-size",
            "-c",
            help="Number of future actions per observation",
            min=1,
        ),
    ] = 6,
    session_id: Annotated[
        Optional[str],
        typer.Option(
            "--session-id",
            "-s",
            help="Convert only a specific session ID (e.g., '20260130_184539_897609'). If not specified, converts all.",
        ),
    ] = None,
    verify: Annotated[
        bool,
        typer.Option(
            "--verify",
            help="Run verification checks after conversion",
        ),
    ] = False,
    config: Annotated[
        str,
        typer.Option(
            "--config",
            help="Dataset configuration to use",
            case_sensitive=False,
        ),
    ] = "default",
):
    """Convert robot trajectories to RLDS format.
    
    This command converts Vicon robot trajectory data (50Hz) and camera images
    (~8-10Hz) into RLDS format with action chunking for VLA model training.
    """
    # Create output directory
    output.mkdir(parents=True, exist_ok=True)
    
    typer.echo(typer.style("=== RLDS Converter ===", fg=typer.colors.BRIGHT_CYAN, bold=True))
    typer.echo(f"Input: {input}")
    typer.echo(f"Output: {output}")
    typer.echo(f"Action chunk size: {chunk_size}")
    typer.echo(f"Config: {config}")
    if session_id:
        typer.echo(f"Session filter: {typer.style(session_id, fg=typer.colors.BRIGHT_YELLOW)}")
    
    # Determine config based on chunk size if custom
    if chunk_size == 4:
        config_name = 'chunk_4'
    elif chunk_size == 8:
        config_name = 'chunk_8'
    elif chunk_size == 6:
        config_name = 'default'
    else:
        # Use default config but it will use chunk_size=6
        typer.echo(
            typer.style(
                f"⚠ Warning: Custom chunk size {chunk_size} not supported by pre-defined configs.",
                fg=typer.colors.YELLOW,
            )
        )
        typer.echo("Using 'default' config with chunk_size=6.")
        typer.echo("To use custom chunk sizes, modify the ViconRobotConfig in vicon_robot_dataset.py")
        config_name = 'default'
    
    try:
        typer.echo(typer.style("\n=== Building Dataset ===", fg=typer.colors.BRIGHT_CYAN, bold=True))
        
        # Build the dataset
        builder = ViconRobot(
            config=config_name,
            data_dir=str(output),
        )
        
        # Set the source data directory and optional session filter
        builder._source_data_dir = str(input)
        if session_id:
            builder._session_filter = session_id
        
        # Download and prepare (in this case, just convert the data)
        # Use manual_dir to pass the source data directory
        download_config = tfds.download.DownloadConfig(
            manual_dir=str(input)
        )
        builder.download_and_prepare(download_config=download_config)
        
        typer.echo(typer.style("\n✓ Dataset conversion complete!", fg=typer.colors.BRIGHT_GREEN, bold=True))
        typer.echo(f"Dataset saved to: {output / 'vicon_robot'}")
        
        # Run verification if requested
        if verify:
            verify_dataset(output, chunk_size)
        else:
            typer.echo("\n💡 Tip: Run with --verify to check the dataset after conversion")
            
    except Exception as e:
        typer.echo(typer.style(f"\n✗ Conversion failed: {e}", fg=typer.colors.BRIGHT_RED, bold=True))
        import traceback
        traceback.print_exc()
        raise typer.Exit(code=1)


def main():
    """Entry point for the CLI."""
    app()


if __name__ == '__main__':
    app()
