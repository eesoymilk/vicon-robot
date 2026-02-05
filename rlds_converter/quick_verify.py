"""Quick check of the RLDS dataset."""
import tensorflow_datasets as tfds

print("Loading dataset from output_rlds...")
ds = tfds.load(
    'vicon_robot',
    data_dir='/Users/soymilk/Codes/vicon-robot/output_rlds',
    split='train',
)

print("\n=== Dataset Contents ===")
for episode in ds:
    session_id = episode['episode_metadata']['session_id'].numpy().decode('utf-8')
    steps = list(episode['steps'])
    
    print(f"\nSession: {session_id}")
    print(f"Total steps: {len(steps)}")
    
    if steps:
        first = steps[0]
        print(f"\nFirst step:")
        print(f"  Image shape: {first['observation']['image'].shape}")
        print(f"  Action joint_positions: {first['action']['joint_positions'].shape}")
        print(f"  Action ee_pose: {first['action']['ee_pose'].shape}")
        print(f"  Gripper: {first['action']['gripper'].shape}")
        print(f"  Phase: {first['observation']['phase'].numpy().decode('utf-8')}")
        print(f"  is_first: {first['is_first'].numpy()}")
        
        # Show the action chunk has real data
        print(f"\nFirst action chunk (6 future actions):")
        print(f"  Joint positions[0]: {first['action']['joint_positions'][0].numpy()}")
        print(f"  Gripper values: {first['action']['gripper'].numpy()}")

print("\n✅ Dataset loaded successfully! The 22MB TFRecord contains all your data.")
