"""TensorFlow Datasets builder for Vicon Robot dataset in RLDS format."""

from pathlib import Path
from typing import Iterator, Tuple, Any
import tensorflow_datasets as tfds
import tensorflow as tf
import numpy as np

from rlds_converter.converter import generate_episode


class ViconRobotConfig(tfds.core.BuilderConfig):
    """BuilderConfig for ViconRobot dataset."""
    
    def __init__(self, *, chunk_size: int = 6, **kwargs):
        """Initialize config.
        
        Args:
            chunk_size: Number of future actions per observation
            **kwargs: Additional keyword arguments passed to parent
        """
        super().__init__(**kwargs)
        self.chunk_size = chunk_size


class ViconRobot(tfds.core.GeneratorBasedBuilder):
    """DatasetBuilder for Vicon Robot trajectories in RLDS format.
    
    This dataset contains robot manipulation trajectories with synchronized
    camera observations. Each episode represents a complete grab sequence
    (move_to_grab -> lift_object -> move_to_return -> return_home).
    
    The dataset is structured for VLA (Vision-Language-Action) model training
    with action chunking, where each observation predicts multiple future actions.
    """
    
    VERSION = tfds.core.Version('1.0.0')
    RELEASE_NOTES = {
        '1.0.0': 'Initial release with action chunking support.',
    }
    
    BUILDER_CONFIGS = [
        ViconRobotConfig(
            name='default',
            description='Default config with 6 action chunks',
            chunk_size=6,
        ),
        ViconRobotConfig(
            name='chunk_4',
            description='Config with 4 action chunks',
            chunk_size=4,
        ),
        ViconRobotConfig(
            name='chunk_8',
            description='Config with 8 action chunks',
            chunk_size=8,
        ),
    ]
    
    def _info(self) -> tfds.core.DatasetInfo:
        """Returns the dataset metadata."""
        chunk_size = self.builder_config.chunk_size
        
        # Define the feature structure matching RLDS format
        features = tfds.features.FeaturesDict({
            'steps': tfds.features.Dataset({
                'observation': tfds.features.FeaturesDict({
                    'image': tfds.features.Image(
                        shape=(None, None, 3),
                        dtype=tf.uint8,
                        encoding_format='jpeg'
                    ),
                    'state': tfds.features.FeaturesDict({
                        'joint_positions': tfds.features.Tensor(
                            shape=(6,),
                            dtype=tf.float32
                        ),
                        'ee_pose': tfds.features.Tensor(
                            shape=(7,),
                            dtype=tf.float32
                        ),
                        'gripper': tf.float32,
                    }),
                    'phase': tfds.features.Text(),
                }),
                'action': tfds.features.FeaturesDict({
                    'joint_positions': tfds.features.Tensor(
                        shape=(chunk_size, 6),
                        dtype=tf.float32
                    ),
                    'ee_pose': tfds.features.Tensor(
                        shape=(chunk_size, 7),
                        dtype=tf.float32
                    ),
                    'gripper': tfds.features.Tensor(
                        shape=(chunk_size,),
                        dtype=tf.float32
                    ),
                }),
                'is_first': tf.bool,
                'is_last': tf.bool,
                'is_terminal': tf.bool,
            }),
            'episode_metadata': tfds.features.FeaturesDict({
                'session_id': tfds.features.Text(),
            }),
        })
        
        return tfds.core.DatasetInfo(
            builder=self,
            description=(
                "Vicon Robot manipulation dataset with synchronized camera observations. "
                "Each episode contains a complete grab sequence with action chunks for VLA training."
            ),
            features=features,
            supervised_keys=None,
            homepage='https://github.com/yourusername/vicon-robot',
            citation=None,
        )
    
    def _split_generators(self, dl_manager: tfds.download.DownloadManager):
        """Returns SplitGenerators."""
        # Get source data directory from manual_dir if provided
        # Otherwise fall back to default location
        if hasattr(self, '_source_data_dir'):
            data_dir = Path(self._source_data_dir)
        elif dl_manager.manual_dir:
            data_dir = Path(dl_manager.manual_dir)
        else:
            data_dir = Path('data/trajectories')
        
        return {
            'train': self._generate_examples(data_dir),
        }
    
    def _generate_examples(self, data_dir: Path) -> Iterator[Tuple[str, Any]]:
        """Yields examples.
        
        Args:
            data_dir: Path to directory containing trajectory CSVs and frame directories
            
        Yields:
            Tuple of (episode_id, episode_data)
        """
        # Find all trajectory CSV files
        trajectory_files = sorted(data_dir.glob('trajectory_*.csv'))
        
        # Filter by session_id if specified
        if hasattr(self, '_session_filter'):
            session_filter = self._session_filter
            trajectory_files = [f for f in trajectory_files if session_filter in f.name]
            print(f"Filtering to session: {session_filter} ({len(trajectory_files)} files)")
        
        for traj_file in trajectory_files:
            # Extract session ID from filename
            # Format: trajectory_YYYYMMDD_HHMMSS_MICROSECONDS.csv
            session_id = traj_file.stem.replace('trajectory_', '')
            
            # Find corresponding frames directory
            frames_dir = data_dir / f"{session_id}_frames"
            
            if not frames_dir.exists():
                print(f"Warning: Frames directory not found for {session_id}, skipping")
                continue
            
            metadata_path = frames_dir / 'metadata.jsonl'
            if not metadata_path.exists():
                print(f"Warning: metadata.jsonl not found in {frames_dir}, skipping")
                continue
            
            try:
                # Generate episode data
                episode = generate_episode(
                    traj_file,
                    frames_dir,
                    chunk_size=self.builder_config.chunk_size
                )
                
                # Convert to TFDS format
                steps = []
                for i in range(len(episode['observations'])):
                    obs = episode['observations'][i]
                    action = episode['actions'][i]
                    
                    step = {
                        'observation': {
                            'image': obs['image'],
                            'state': {
                                'joint_positions': obs['state']['joint_positions'],
                                'ee_pose': obs['state']['ee_pose'],
                                'gripper': obs['state']['gripper'],
                            },
                            'phase': obs['phase'],
                        },
                        'action': {
                            'joint_positions': action['joint_positions'],
                            'ee_pose': action['ee_pose'],
                            'gripper': action['gripper'],
                        },
                        'is_first': episode['is_first'][i],
                        'is_last': episode['is_last'][i],
                        'is_terminal': episode['is_terminal'][i],
                    }
                    steps.append(step)
                
                episode_data = {
                    'steps': steps,
                    'episode_metadata': {
                        'session_id': session_id,
                    },
                }
                
                yield session_id, episode_data
                
            except Exception as e:
                print(f"Error processing episode {session_id}: {e}")
                continue
