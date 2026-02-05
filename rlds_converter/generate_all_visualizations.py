"""Generate visualizations for all episodes in the dataset."""
import tensorflow_datasets as tfds
import matplotlib.pyplot as plt
import numpy as np

print("Loading dataset from output_rlds...")
ds = tfds.load(
    'vicon_robot',
    data_dir='/Users/soymilk/Codes/vicon-robot/output_rlds',
    split='train',
)

print(f"\n{'='*70}")
print("RLDS Dataset - All Episodes")
print(f"{'='*70}\n")

episode_list = list(ds)
print(f"Total episodes: {len(episode_list)}\n")

# Summary for all episodes
for i, episode in enumerate(episode_list):
    session_id = episode['episode_metadata']['session_id'].numpy().decode('utf-8')
    steps = list(episode['steps'])
    
    print(f"Episode {i+1}: {session_id}")
    print(f"  Steps: {len(steps)}")
    
    if steps:
        first = steps[0]
        img_shape = first['observation']['image'].shape
        print(f"  Image shape: {img_shape}")
        
        phases = set([s['observation']['phase'].numpy().decode('utf-8') for s in steps])
        print(f"  Phases: {', '.join(phases)}")
    print()

# Generate comprehensive visualization for all episodes
fig = plt.figure(figsize=(20, 6 * len(episode_list)))
gs = fig.add_gridspec(len(episode_list), 4, hspace=0.4, wspace=0.3)

for ep_idx, episode in enumerate(episode_list):
    session_id = episode['episode_metadata']['session_id'].numpy().decode('utf-8')
    steps = list(episode['steps'])
    
    # First image
    ax1 = fig.add_subplot(gs[ep_idx, 0])
    first_img = steps[0]['observation']['image'].numpy()
    ax1.imshow(first_img)
    ax1.set_title(f'Episode {ep_idx+1}: {session_id}\nFirst Frame', fontsize=10)
    ax1.axis('off')
    
    # Middle image
    ax2 = fig.add_subplot(gs[ep_idx, 1])
    mid_img = steps[len(steps)//2]['observation']['image'].numpy()
    ax2.imshow(mid_img)
    ax2.set_title(f'Middle Frame (Step {len(steps)//2})', fontsize=10)
    ax2.axis('off')
    
    # Last image
    ax3 = fig.add_subplot(gs[ep_idx, 2])
    last_img = steps[-1]['observation']['image'].numpy()
    ax3.imshow(last_img)
    ax3.set_title(f'Last Frame (Step {len(steps)-1})', fontsize=10)
    ax3.axis('off')
    
    # Gripper trajectory
    ax4 = fig.add_subplot(gs[ep_idx, 3])
    gripper_values = [s['observation']['state']['gripper'].numpy() for s in steps]
    ax4.plot(gripper_values, linewidth=2, color='darkgreen')
    ax4.fill_between(range(len(gripper_values)), gripper_values, alpha=0.3, color='green')
    ax4.set_title(f'Gripper Over Time\n{len(steps)} steps', fontsize=10)
    ax4.set_xlabel('Step')
    ax4.set_ylabel('Gripper Value')
    ax4.grid(True, alpha=0.3)
    ax4.set_ylim([0, 1000])

plt.suptitle('RLDS Dataset - All Episodes Overview', fontsize=16, fontweight='bold', y=0.995)
plt.savefig('/Users/soymilk/Codes/vicon-robot/rlds_converter/viz_all_episodes.png', 
            dpi=150, bbox_inches='tight')
print(f"✅ Saved: viz_all_episodes.png\n")
plt.close()

# Generate individual detailed visualization for each episode
for ep_idx, episode in enumerate(episode_list):
    session_id = episode['episode_metadata']['session_id'].numpy().decode('utf-8')
    steps = list(episode['steps'])
    
    print(f"Generating detailed visualization for {session_id}...")
    
    fig, axes = plt.subplots(2, 4, figsize=(20, 10))
    fig.suptitle(f'Episode {ep_idx+1}: {session_id} - Detailed View\n{len(steps)} steps', 
                 fontsize=14, fontweight='bold')
    
    # Sample 8 images
    indices = np.linspace(0, len(steps)-1, 8, dtype=int)
    for i, idx in enumerate(indices):
        row, col = i // 4, i % 4
        step = steps[idx]
        img = step['observation']['image'].numpy()
        phase = step['observation']['phase'].numpy().decode('utf-8')
        gripper = step['observation']['state']['gripper'].numpy()
        
        axes[row, col].imshow(img)
        axes[row, col].set_title(f"Step {idx}\n{phase}\nGripper: {gripper:.0f}", fontsize=9)
        axes[row, col].axis('off')
    
    plt.tight_layout()
    plt.savefig(f'/Users/soymilk/Codes/vicon-robot/rlds_converter/viz_episode_{ep_idx+1}_{session_id}.png', 
                dpi=120, bbox_inches='tight')
    print(f"  ✅ Saved: viz_episode_{ep_idx+1}_{session_id}.png")
    plt.close()

print(f"\n{'='*70}")
print("✅ All visualizations generated!")
print(f"{'='*70}")
print(f"\nGenerated files in rlds_converter/:")
print(f"  - viz_all_episodes.png (overview of all episodes)")
for i, episode in enumerate(episode_list):
    session_id = episode['episode_metadata']['session_id'].numpy().decode('utf-8')
    print(f"  - viz_episode_{i+1}_{session_id}.png (detailed view)")

print(f"\nDataset summary:")
print(f"  Total episodes: {len(episode_list)}")
print(f"  Total steps: {sum(len(list(ep['steps'])) for ep in episode_list)}")
print(f"  Location: /Users/soymilk/Codes/vicon-robot/output_rlds/vicon_robot/")
print(f"\nReady for VLA training! 🚀")
