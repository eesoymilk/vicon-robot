# RLDS Converter - Usage Examples

## Basic Conversion

Convert your trajectories with default settings (6 action chunks):

```bash
cd rlds_converter
uv run rlds-convert --input ../data/trajectories --output ../rlds_output
```

Or using short flags:

```bash
uv run rlds-convert -i ../data/trajectories -o ../rlds_output
```

## With Verification

Run verification checks after conversion to ensure data quality:

```bash
uv run rlds-convert -i ../data/trajectories -o ../rlds_output --verify
```

## Custom Action Chunk Size

For different VLA architectures that need different chunk sizes:

```bash
# 4 action chunks
uv run rlds-convert -i ../data/trajectories -o ../rlds_output -c 4

# 8 action chunks
uv run rlds-convert -i ../data/trajectories -o ../rlds_output -c 8
```

## Using Pre-defined Configs

Use a specific configuration:

```bash
uv run rlds-convert -i ../data/trajectories -o ../rlds_output --config chunk_4
```

Available configs:
- `default`: 6 action chunks (Octo default)
- `chunk_4`: 4 action chunks
- `chunk_8`: 8 action chunks

## Complete Example

Full conversion with verification:

```bash
cd rlds_converter
uv run rlds-convert \
  --input ../data/trajectories \
  --output ../rlds_output \
  --chunk-size 6 \
  --verify \
  --config default
```

## Help

Get detailed help and all available options:

```bash
uv run rlds-convert --help
```

This will show a nicely formatted help message with all options, types, and defaults.

## Loading the Converted Dataset

After conversion, load with TensorFlow Datasets:

```python
import tensorflow_datasets as tfds

# Load the dataset
ds = tfds.load(
    'vicon_robot',
    data_dir='rlds_output',
    split='train'
)

# Iterate
for episode in ds:
    for step in episode['steps']:
        image = step['observation']['image']
        actions = step['action']['joint_positions']  # Shape: [6, 6]
        # Train your VLA model...
```

## Troubleshooting

### Input directory not found

Make sure the path exists and contains trajectory CSV files:

```bash
ls -la ../data/trajectories/
# Should show trajectory_*.csv and *_frames/ directories
```

### Import errors

Ensure all dependencies are installed:

```bash
cd rlds_converter
uv sync
```

### Verification takes long

For large datasets with many trajectories, verification can take a while as it loads and inspects each episode. You can skip it and verify manually later:

```python
import tensorflow_datasets as tfds
ds = tfds.load('vicon_robot', data_dir='rlds_output', split='train')
print(f"Episodes: {len(list(ds))}")
```
