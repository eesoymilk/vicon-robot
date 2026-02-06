"""Core conversion functions for transforming robot trajectories to RLDS format."""

import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import numpy as np
import pandas as pd
import cv2
from PIL import Image


def load_trajectory_csv(csv_path: Path) -> pd.DataFrame:
    """Load trajectory CSV file with 50Hz robot state data.
    
    Args:
        csv_path: Path to trajectory CSV file
        
    Returns:
        DataFrame with columns: timestamp, j0-j5, x, y, z, qw, qx, qy, qz, gripper, phase
    """
    df = pd.read_csv(csv_path)
    
    # Ensure required columns exist
    required_cols = ['timestamp', 'j0', 'j1', 'j2', 'j3', 'j4', 'j5', 
                     'x', 'y', 'z', 'qw', 'qx', 'qy', 'qz', 'gripper', 'phase']
    
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Required column '{col}' not found in trajectory CSV")
    
    # Sort by timestamp to ensure temporal order
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    return df


def load_image_metadata(metadata_path: Path) -> List[Dict]:
    """Load image metadata from JSONL file.
    
    Args:
        metadata_path: Path to metadata.jsonl file
        
    Returns:
        List of metadata dicts with keys: frame_id, filename, timestamp, phase, gripper_position
    """
    metadata = []
    with open(metadata_path, 'r') as f:
        for line in f:
            if line.strip():
                metadata.append(json.loads(line))
    
    # Sort by timestamp
    metadata.sort(key=lambda x: x['timestamp'])
    
    return metadata


def interpolate_images(
    image_dir: Path,
    metadata: List[Dict],
    trajectory_timestamps: np.ndarray
) -> Tuple[List[np.ndarray], List[float]]:
    """Interpolate images to match trajectory timestamps using nearest-neighbor.
    
    For VLA training, we repeat frames to match the 50Hz trajectory rate.
    
    Args:
        image_dir: Directory containing image files
        metadata: List of image metadata dicts
        trajectory_timestamps: Array of trajectory timestamps (50Hz)
        
    Returns:
        Tuple of (interpolated_images, interpolated_timestamps)
    """
    # Load all images
    images = []
    image_timestamps = []
    
    for meta in metadata:
        img_path = image_dir / meta['filename']
        img = cv2.imread(str(img_path))
        if img is None:
            raise ValueError(f"Failed to load image: {img_path}")
        # Convert BGR to RGB
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        images.append(img)
        image_timestamps.append(meta['timestamp'])
    
    image_timestamps = np.array(image_timestamps)
    
    # For each trajectory timestamp, find the nearest image
    interpolated_images = []
    for traj_ts in trajectory_timestamps:
        # Find nearest image timestamp
        idx = np.argmin(np.abs(image_timestamps - traj_ts))
        interpolated_images.append(images[idx])
    
    return interpolated_images, trajectory_timestamps.tolist()


def create_action_chunks(
    trajectory_df: pd.DataFrame,
    observation_indices: List[int],
    chunk_size: int = 6
) -> List[Dict[str, np.ndarray]]:
    """Create action chunks for each observation.
    
    For each observation at index i, extract the next chunk_size actions.
    Zero-pad at the end of the episode.
    
    Args:
        trajectory_df: DataFrame with trajectory data
        observation_indices: Indices of observations in the trajectory
        chunk_size: Number of future actions per observation
        
    Returns:
        List of action chunk dicts with keys: joint_positions, ee_pose, gripper
    """
    action_chunks = []
    
    for obs_idx in observation_indices:
        # Extract next chunk_size actions
        chunk_end = min(obs_idx + chunk_size, len(trajectory_df))
        chunk_data = trajectory_df.iloc[obs_idx:chunk_end]
        
        # Extract joint positions
        joint_positions = chunk_data[['j0', 'j1', 'j2', 'j3', 'j4', 'j5']].values
        
        # Extract end effector pose
        ee_pose = chunk_data[['x', 'y', 'z', 'qw', 'qx', 'qy', 'qz']].values
        
        # Extract gripper values
        gripper = chunk_data['gripper'].values
        
        # Zero-pad if we don't have enough future actions
        if len(chunk_data) < chunk_size:
            pad_length = chunk_size - len(chunk_data)
            joint_positions = np.vstack([
                joint_positions,
                np.zeros((pad_length, 6), dtype=np.float32)
            ])
            ee_pose = np.vstack([
                ee_pose,
                np.zeros((pad_length, 7), dtype=np.float32)
            ])
            gripper = np.concatenate([
                gripper,
                np.zeros(pad_length, dtype=np.float32)
            ])
        
        action_chunks.append({
            'joint_positions': joint_positions.astype(np.float32),
            'ee_pose': ee_pose.astype(np.float32),
            'gripper': gripper.astype(np.float32)
        })
    
    return action_chunks


def align_data(
    trajectory_df: pd.DataFrame,
    metadata: List[Dict],
    interpolated_images: List[np.ndarray]
) -> Tuple[List[int], List[float]]:
    """Align trajectory data with image metadata to get observation indices.
    
    We sample observations only at original image timestamps (not interpolated).
    
    Args:
        trajectory_df: DataFrame with trajectory data
        metadata: Original image metadata (not interpolated)
        interpolated_images: List of interpolated images (for validation)
        
    Returns:
        Tuple of (observation_indices, observation_timestamps)
    """
    trajectory_timestamps = trajectory_df['timestamp'].values
    observation_timestamps = [meta['timestamp'] for meta in metadata]
    observation_indices = []
    
    # For each original image timestamp, find the closest trajectory index
    for img_ts in observation_timestamps:
        idx = np.argmin(np.abs(trajectory_timestamps - img_ts))
        observation_indices.append(int(idx))
    
    return observation_indices, observation_timestamps


def generate_episode(
    trajectory_path: Path,
    frames_dir: Path,
    chunk_size: int = 6
) -> Dict[str, List]:
    """Generate a complete episode from trajectory and frames.
    
    Args:
        trajectory_path: Path to trajectory CSV file
        frames_dir: Path to directory containing frames and metadata.jsonl
        chunk_size: Number of future actions per observation
        
    Returns:
        Dict containing episode data with keys:
        - observations: List of observation dicts
        - actions: List of action chunk dicts
        - is_first: List of booleans
        - is_last: List of booleans
        - is_terminal: List of booleans
    """
    # Load trajectory and metadata
    trajectory_df = load_trajectory_csv(trajectory_path)
    metadata_path = frames_dir / 'metadata.jsonl'
    metadata = load_image_metadata(metadata_path)
    
    # Interpolate images to 50Hz
    trajectory_timestamps = trajectory_df['timestamp'].values
    interpolated_images, _ = interpolate_images(
        frames_dir, metadata, trajectory_timestamps
    )
    
    # Get observation indices (at original image timestamps)
    observation_indices, observation_timestamps = align_data(
        trajectory_df, metadata, interpolated_images
    )
    
    # Create action chunks
    action_chunks = create_action_chunks(
        trajectory_df, observation_indices, chunk_size
    )
    
    # Build observations
    observations = []
    for i, obs_idx in enumerate(observation_indices):
        obs_row = trajectory_df.iloc[obs_idx]
        
        # Get the image at this timestamp
        img = interpolated_images[obs_idx]
        
        observation = {
            'image': img,  # [H, W, 3] uint8
            'state': {
                'joint_positions': np.array([
                    obs_row['j0'], obs_row['j1'], obs_row['j2'],
                    obs_row['j3'], obs_row['j4'], obs_row['j5']
                ], dtype=np.float32),
                'ee_pose': np.array([
                    obs_row['x'], obs_row['y'], obs_row['z'],
                    obs_row['qw'], obs_row['qx'], obs_row['qy'], obs_row['qz']
                ], dtype=np.float32),
                'gripper': np.float32(obs_row['gripper'])
            },
            'phase': str(obs_row['phase'])
        }
        observations.append(observation)
    
    # Create episode flags
    num_steps = len(observations)
    is_first = [True] + [False] * (num_steps - 1)
    is_last = [False] * (num_steps - 1) + [True]
    is_terminal = [False] * (num_steps - 1) + [True]
    
    return {
        'observations': observations,
        'actions': action_chunks,
        'is_first': is_first,
        'is_last': is_last,
        'is_terminal': is_terminal
    }
