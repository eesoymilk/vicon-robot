# RLDS Converter for Vicon Robot Dataset

Convert robot manipulation trajectories and camera observations to RLDS (Reinforcement Learning Datasets) format for VLA (Vision-Language-Action) model training.

## Features

- **Action Chunking**: Each observation predicts multiple future actions (default: 6)
- **Multi-frequency Alignment**: Synchronizes 50Hz robot trajectories with ~8-10Hz camera images
- **TFDS Format**: Compatible with TensorFlow Datasets for easy loading
- **VLA-Ready**: Structured for training models like Octo, RT-1, etc.

## Dataset Structure

Each episode contains:

```
observation:
  - image: [H, W, 3] RGB uint8
  - state:
    - joint_positions: [6] float32
    - ee_pose: [7] float32 (x, y, z, qw, qx, qy, qz)
    - gripper: float32
  - phase: string (move_to_grab, lift_object, move_to_return, return_home)

action:
  - joint_positions: [chunk_size, 6] float32
  - ee_pose: [chunk_size, 7] float32
  - gripper: [chunk_size] float32

metadata:
  - is_first: bool
  - is_last: bool
  - is_terminal: bool
```

## Installation

```bash
cd rlds_converter
uv sync
```

This installs all dependencies including:
- TensorFlow & TensorFlow Datasets
- NumPy, Pandas, OpenCV
- Pillow, Matplotlib

## Usage

### Quick Start

Convert your trajectories to RLDS format:

```bash
cd rlds_converter
uv run rlds-convert --input ../data/trajectories --output ../rlds_output --chunk-size 6 --verify
```

### Command-Line Options

```bash
uv run rlds-convert --help
```

The CLI is built with [Typer](https://typer.tiangolo.com/) for a modern, user-friendly interface:

Options:
- `-i, --input PATH`: Input directory with trajectory CSVs and frame folders (required)
- `-o, --output PATH`: Output directory for TFDS dataset (required)
- `-c, --chunk-size N`: Number of future actions per observation (default: 6, min: 1)
- `--verify`: Run verification checks after conversion
- `--config NAME`: Use predefined config (default, chunk_4, chunk_8)

Short form example:
```bash
uv run rlds-convert -i ../data/trajectories -o ../rlds_output -c 6 --verify
```

### Expected Input Structure

```
data/trajectories/
├── trajectory_20260130_184539_897609.csv       # 50Hz robot state
├── 20260130_184539_897609_frames/
│   ├── 000000.jpg
│   ├── 000001.jpg
│   ├── ...
│   └── metadata.jsonl                          # ~8-10Hz image metadata
├── trajectory_20260130_183916_915588.csv
└── 20260130_183916_915588_frames/
    └── ...
```

### Loading the Dataset

After conversion, load with TensorFlow Datasets:

```python
import tensorflow_datasets as tfds

# Load the dataset
ds = tfds.load(
    'vicon_robot',
    data_dir='rlds_output',
    split='train'
)

# Iterate through episodes
for episode in ds:
    steps = episode['steps']
    session_id = episode['episode_metadata']['session_id']
    
    for step in steps:
        image = step['observation']['image']        # [H, W, 3]
        joint_pos = step['observation']['state']['joint_positions']  # [6]
        action_chunk = step['action']['joint_positions']  # [6, 6] for chunk_size=6
        
        # Your training code here...
```

## Testing

Run the test suite to verify conversion:

```bash
cd rlds_converter
uv run python tests/test_converter.py --data-dir ../data/trajectories --chunk-size 6
```

This will:
- Test all conversion functions
- Verify data alignment
- Check action chunk dimensions
- Generate visualization of sample frames

## How It Works

### 1. Data Alignment

- **Trajectory**: 50Hz robot state (joint positions, end effector pose, gripper)
- **Images**: ~8-10Hz RGB frames with timestamps
- **Alignment**: Images are interpolated (repeated) to 50Hz, observations sampled at original image timestamps

### 2. Action Chunking

For VLA training, each observation predicts multiple future actions:

```
Observation at t=0 → Actions [t=0, t=1, t=2, t=3, t=4, t=5]
Observation at t=1 → Actions [t=1, t=2, t=3, t=4, t=5, t=6]
...
```

At episode end, action chunks are zero-padded if insufficient future actions remain.

### 3. Episode Structure

Each grab sequence becomes one episode:
1. **move_to_grab**: Arm moves to object location
2. **lift_object**: Gripper closes and lifts
3. **move_to_return**: Arm moves to return position
4. **return_home**: Arm returns to home position

## Configuration

The dataset builder supports multiple configurations:

- **default**: chunk_size=6 (Octo default)
- **chunk_4**: chunk_size=4
- **chunk_8**: chunk_size=8

To use a specific config:

```bash
uv run rlds-convert --config chunk_8 --input ../data/trajectories --output ../rlds_output
```

## Development

### Project Structure

```
rlds_converter/
├── src/rlds_converter/
│   ├── __init__.py
│   ├── converter.py              # Core conversion logic
│   ├── vicon_robot_dataset.py    # TFDS dataset builder
│   └── cli.py                    # Command-line interface
├── tests/
│   ├── __init__.py
│   └── test_converter.py         # Test suite
├── pyproject.toml
└── README.md
```

### Adding New Configurations

Edit `vicon_robot_dataset.py` to add new `ViconRobotConfig` entries:

```python
ViconRobotConfig(
    name='my_config',
    description='Custom config',
    chunk_size=10,
)
```

## Troubleshooting

### Missing Dependencies

If you see import errors:
```bash
cd rlds_converter
uv sync
```

### Data Not Found

Ensure your data follows the expected structure:
- CSV files named `trajectory_YYYYMMDD_HHMMSS_MICROSECONDS.csv`
- Corresponding folders named `YYYYMMDD_HHMMSS_MICROSECONDS_frames/`
- Each folder contains `metadata.jsonl` and image files

### Verification Fails

Run tests to debug:
```bash
uv run python tests/test_converter.py --data-dir ../data/trajectories
```

Check the generated `episode_visualization.png` for visual inspection.

## License

MIT License - See LICENSE file for details.

## Citation

If you use this dataset converter in your research, please cite:

```bibtex
@software{vicon_robot_rlds_converter,
  title={RLDS Converter for Vicon Robot Dataset},
  author={Your Name},
  year={2026},
  url={https://github.com/yourusername/vicon-robot}
}
```
