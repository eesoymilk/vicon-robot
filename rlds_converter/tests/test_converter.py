"""Tests and verification tools for the RLDS converter."""

import sys
from pathlib import Path
import numpy as np
import cv2
import matplotlib.pyplot as plt

from rlds_converter.converter import (
    load_trajectory_csv,
    load_image_metadata,
    interpolate_images,
    create_action_chunks,
    align_data,
    generate_episode,
)


def test_load_trajectory(trajectory_path: Path):
    """Test loading trajectory CSV."""
    print(f"\n=== Testing load_trajectory_csv ===")
    print(f"Loading: {trajectory_path}")
    
    df = load_trajectory_csv(trajectory_path)
    print(f"✓ Loaded {len(df)} rows")
    print(f"  Columns: {list(df.columns)}")
    print(f"  Timestamp range: {df['timestamp'].min():.2f} - {df['timestamp'].max():.2f}")
    print(f"  Duration: {df['timestamp'].max() - df['timestamp'].min():.2f}s")
    print(f"  Phases: {df['phase'].unique()}")
    
    return df


def test_load_metadata(frames_dir: Path):
    """Test loading image metadata."""
    print(f"\n=== Testing load_image_metadata ===")
    print(f"Loading from: {frames_dir}")
    
    metadata_path = frames_dir / 'metadata.jsonl'
    metadata = load_image_metadata(metadata_path)
    print(f"✓ Loaded {len(metadata)} image metadata entries")
    print(f"  Timestamp range: {metadata[0]['timestamp']:.2f} - {metadata[-1]['timestamp']:.2f}")
    print(f"  Frame IDs: {metadata[0]['frame_id']} - {metadata[-1]['frame_id']}")
    
    return metadata


def test_interpolation(frames_dir: Path, trajectory_df):
    """Test image interpolation."""
    print(f"\n=== Testing interpolate_images ===")
    
    metadata_path = frames_dir / 'metadata.jsonl'
    metadata = load_image_metadata(metadata_path)
    trajectory_timestamps = trajectory_df['timestamp'].values
    
    interpolated_images, interpolated_timestamps = interpolate_images(
        frames_dir, metadata, trajectory_timestamps
    )
    
    print(f"✓ Interpolated {len(interpolated_images)} images")
    print(f"  Original images: {len(metadata)}")
    print(f"  Trajectory points: {len(trajectory_timestamps)}")
    print(f"  Image shape: {interpolated_images[0].shape}")
    
    return interpolated_images, interpolated_timestamps


def test_action_chunks(trajectory_df, observation_indices, chunk_size=6):
    """Test action chunk creation."""
    print(f"\n=== Testing create_action_chunks ===")
    print(f"Chunk size: {chunk_size}")
    print(f"Observations: {len(observation_indices)}")
    
    action_chunks = create_action_chunks(trajectory_df, observation_indices, chunk_size)
    
    print(f"✓ Created {len(action_chunks)} action chunks")
    
    # Check first and last chunk
    first_chunk = action_chunks[0]
    last_chunk = action_chunks[-1]
    
    print(f"  First chunk shapes:")
    print(f"    - joint_positions: {first_chunk['joint_positions'].shape} (expected: ({chunk_size}, 6))")
    print(f"    - ee_pose: {first_chunk['ee_pose'].shape} (expected: ({chunk_size}, 7))")
    print(f"    - gripper: {first_chunk['gripper'].shape} (expected: ({chunk_size},))")
    
    print(f"  Last chunk (may have zero-padding):")
    print(f"    - joint_positions: {last_chunk['joint_positions'].shape}")
    print(f"    - Zeros in last chunk: {np.sum(last_chunk['joint_positions'] == 0)}")
    
    return action_chunks


def test_full_episode(trajectory_path: Path, frames_dir: Path, chunk_size=6):
    """Test full episode generation."""
    print(f"\n=== Testing generate_episode ===")
    
    episode = generate_episode(trajectory_path, frames_dir, chunk_size)
    
    print(f"✓ Generated episode with {len(episode['observations'])} steps")
    print(f"  Actions: {len(episode['actions'])}")
    print(f"  is_first: {sum(episode['is_first'])} True values")
    print(f"  is_last: {sum(episode['is_last'])} True values")
    print(f"  is_terminal: {sum(episode['is_terminal'])} True values")
    
    # Check first observation
    first_obs = episode['observations'][0]
    print(f"\n  First observation:")
    print(f"    - Image shape: {first_obs['image'].shape}")
    print(f"    - Joint positions shape: {first_obs['state']['joint_positions'].shape}")
    print(f"    - EE pose shape: {first_obs['state']['ee_pose'].shape}")
    print(f"    - Phase: {first_obs['phase']}")
    
    # Check first action
    first_action = episode['actions'][0]
    print(f"\n  First action:")
    print(f"    - Joint positions shape: {first_action['joint_positions'].shape}")
    print(f"    - EE pose shape: {first_action['ee_pose'].shape}")
    print(f"    - Gripper shape: {first_action['gripper'].shape}")
    
    return episode


def visualize_episode(episode, output_path: Path = None, num_frames: int = 5):
    """Visualize random frames from an episode with action information.
    
    Args:
        episode: Episode dict from generate_episode
        output_path: Optional path to save visualization
        num_frames: Number of frames to display
    """
    print(f"\n=== Visualizing Episode ===")
    
    num_steps = len(episode['observations'])
    indices = np.linspace(0, num_steps - 1, num_frames, dtype=int)
    
    fig, axes = plt.subplots(1, num_frames, figsize=(4 * num_frames, 4))
    if num_frames == 1:
        axes = [axes]
    
    for i, idx in enumerate(indices):
        obs = episode['observations'][idx]
        action = episode['actions'][idx]
        
        # Display image
        axes[i].imshow(obs['image'])
        axes[i].axis('off')
        
        # Add info
        phase = obs['phase']
        gripper = obs['state']['gripper']
        is_first = episode['is_first'][idx]
        is_last = episode['is_last'][idx]
        
        title = f"Step {idx}\n{phase}\n"
        title += f"Gripper: {gripper:.0f}\n"
        if is_first:
            title += "FIRST "
        if is_last:
            title += "LAST"
        
        axes[i].set_title(title, fontsize=10)
    
    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"✓ Saved visualization to: {output_path}")
    else:
        plt.show()
    
    plt.close()


def run_all_tests(data_dir: Path, chunk_size: int = 6):
    """Run all tests on the first trajectory found.
    
    Args:
        data_dir: Path to data/trajectories directory
        chunk_size: Action chunk size to test
    """
    print("=" * 60)
    print("RLDS Converter Test Suite")
    print("=" * 60)
    
    # Find first trajectory
    trajectory_files = sorted(data_dir.glob('trajectory_*.csv'))
    if not trajectory_files:
        print("Error: No trajectory files found in", data_dir)
        sys.exit(1)
    
    trajectory_path = trajectory_files[0]
    session_id = trajectory_path.stem.replace('trajectory_', '')
    frames_dir = data_dir / f"{session_id}_frames"
    
    print(f"\nTesting with:")
    print(f"  Trajectory: {trajectory_path.name}")
    print(f"  Frames: {frames_dir.name}")
    
    # Run tests
    try:
        df = test_load_trajectory(trajectory_path)
        metadata = test_load_metadata(frames_dir)
        interpolated_images, _ = test_interpolation(frames_dir, df)
        
        # Test alignment
        observation_indices, _ = align_data(df, metadata, interpolated_images)
        print(f"\n=== Testing align_data ===")
        print(f"✓ Found {len(observation_indices)} observation points")
        print(f"  Observation indices: {observation_indices[:5]}... (showing first 5)")
        
        action_chunks = test_action_chunks(df, observation_indices, chunk_size)
        episode = test_full_episode(trajectory_path, frames_dir, chunk_size)
        
        # Visualize
        viz_path = data_dir.parent.parent / 'rlds_converter' / 'episode_visualization.png'
        visualize_episode(episode, viz_path, num_frames=5)
        
        print("\n" + "=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Test RLDS converter')
    parser.add_argument(
        '--data-dir',
        type=Path,
        default=Path('data/trajectories'),
        help='Path to trajectories directory'
    )
    parser.add_argument(
        '--chunk-size',
        type=int,
        default=6,
        help='Action chunk size to test'
    )
    
    args = parser.parse_args()
    run_all_tests(args.data_dir, args.chunk_size)
