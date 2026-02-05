"""Quick verification script for the converted RLDS dataset."""

import tensorflow_datasets as tfds
from pathlib import Path

def verify_dataset():
    """Verify the converted dataset."""
    print("=== Loading RLDS Dataset ===")
    
    data_dir = Path('/Users/soymilk/Codes/vicon-robot/test_rlds_output')
    
    # Load the dataset
    ds = tfds.load(
        'vicon_robot',
        data_dir=str(data_dir),
        split='train',
    )
    
    print("✓ Dataset loaded successfully\n")
    
    # Count episodes and steps
    episode_count = 0
    total_steps = 0
    
    print("=== Episode Summary ===")
    for episode in ds:
        episode_count += 1
        steps = list(episode['steps'])
        step_count = len(steps)
        total_steps += step_count
        
        session_id = episode['episode_metadata']['session_id'].numpy().decode('utf-8')
        
        print(f"\nEpisode {episode_count}: {session_id}")
        print(f"  Steps: {step_count}")
        
        if steps:
            first = steps[0]
            last = steps[-1]
            
            print(f"  Image shape: {first['observation']['image'].shape}")
            print(f"  Action joint_positions: {first['action']['joint_positions'].shape}")
            print(f"  Action ee_pose: {first['action']['ee_pose'].shape}")
            print(f"  Action gripper: {first['action']['gripper'].shape}")
            print(f"  First phase: {first['observation']['phase'].numpy().decode('utf-8')}")
            print(f"  Last phase: {last['observation']['phase'].numpy().decode('utf-8')}")
            print(f"  is_first: {first['is_first'].numpy()}")
            print(f"  is_last: {last['is_last'].numpy()}")
    
    print(f"\n=== Summary ===")
    print(f"Total episodes: {episode_count}")
    print(f"Total steps: {total_steps}")
    print(f"Avg steps/episode: {total_steps/episode_count:.1f}")
    print("\n✓ Verification complete!")

if __name__ == '__main__':
    verify_dataset()
