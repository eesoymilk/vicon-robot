"""Generate comprehensive visualizations of the converted RLDS dataset."""
import tensorflow_datasets as tfds
import matplotlib.pyplot as plt
import numpy as np

print("Loading dataset from output_rlds...")
ds = tfds.load(
    'vicon_robot',
    data_dir='/Users/soymilk/Codes/vicon-robot/output_rlds',
    split='train',
)

for episode in ds:
    session_id = episode['episode_metadata']['session_id'].numpy().decode('utf-8')
    steps = list(episode['steps'])
    
    print(f"\n{'='*60}")
    print(f"Session: {session_id}")
    print(f"Total steps: {len(steps)}")
    print(f"{'='*60}")
    
    # === VISUALIZATION 1: Sample Images Throughout Episode ===
    print("\nGenerating image samples visualization...")
    fig1, axes1 = plt.subplots(2, 4, figsize=(20, 10))
    fig1.suptitle(f'RLDS Dataset - Session {session_id}\nSample Images Throughout Episode', 
                  fontsize=16, fontweight='bold')
    
    # Sample 8 images evenly distributed
    indices = np.linspace(0, len(steps)-1, 8, dtype=int)
    
    for i, idx in enumerate(indices):
        row, col = i // 4, i % 4
        step = steps[idx]
        img = step['observation']['image'].numpy()
        phase = step['observation']['phase'].numpy().decode('utf-8')
        gripper = step['observation']['state']['gripper'].numpy()
        
        axes1[row, col].imshow(img)
        axes1[row, col].set_title(
            f"Step {idx}/{len(steps)-1}\n"
            f"Phase: {phase}\n"
            f"Gripper: {gripper:.0f}",
            fontsize=10
        )
        axes1[row, col].axis('off')
    
    plt.tight_layout()
    plt.savefig('/Users/soymilk/Codes/vicon-robot/rlds_converter/viz_images.png', 
                dpi=150, bbox_inches='tight')
    print("✅ Saved: viz_images.png")
    plt.close()
    
    # === VISUALIZATION 2: Action Chunks ===
    print("\nGenerating action chunks visualization...")
    fig2, axes2 = plt.subplots(3, 2, figsize=(16, 12))
    fig2.suptitle(f'RLDS Dataset - Action Chunks (6 future actions per observation)\n'
                  f'Session {session_id}', fontsize=16, fontweight='bold')
    
    # Sample 5 timesteps to show action chunking
    sample_steps = [0, 20, 40, 60, 80]
    
    # Plot joint positions for first 5 samples
    for i, step_idx in enumerate(sample_steps):
        if step_idx < len(steps):
            step = steps[step_idx]
            action_jp = step['action']['joint_positions'].numpy()  # [6, 6]
            
            ax = axes2[0, 0] if i < 3 else axes2[0, 1]
            for joint_idx in range(6):
                ax.plot(action_jp[:, joint_idx], marker='o', label=f'J{joint_idx}', alpha=0.7)
            ax.set_title(f'Step {step_idx} - Joint Position Actions')
            ax.set_xlabel('Future Action Index (0-5)')
            ax.set_ylabel('Joint Position (rad)')
            ax.legend(fontsize=8)
            ax.grid(True, alpha=0.3)
    
    # Plot gripper actions
    for i, step_idx in enumerate(sample_steps):
        if step_idx < len(steps):
            step = steps[step_idx]
            gripper_actions = step['action']['gripper'].numpy()  # [6]
            phase = step['observation']['phase'].numpy().decode('utf-8')
            
            ax = axes2[1, i % 2]
            ax.bar(range(6), gripper_actions, color='steelblue', alpha=0.7)
            ax.set_title(f'Step {step_idx} - Gripper Actions\nPhase: {phase}')
            ax.set_xlabel('Future Action Index')
            ax.set_ylabel('Gripper Value')
            ax.set_ylim([0, 1000])
            ax.grid(True, alpha=0.3, axis='y')
    
    # Plot end effector trajectory
    ee_positions = []
    for step in steps:
        ee_pose = step['observation']['state']['ee_pose'].numpy()
        ee_positions.append(ee_pose[:3])  # x, y, z
    ee_positions = np.array(ee_positions)
    
    axes2[2, 0].plot(ee_positions[:, 0], ee_positions[:, 1], 'b-', linewidth=2)
    axes2[2, 0].scatter(ee_positions[0, 0], ee_positions[0, 1], 
                        c='green', s=100, marker='o', label='Start', zorder=5)
    axes2[2, 0].scatter(ee_positions[-1, 0], ee_positions[-1, 1], 
                        c='red', s=100, marker='X', label='End', zorder=5)
    axes2[2, 0].set_title('End Effector XY Trajectory')
    axes2[2, 0].set_xlabel('X Position (m)')
    axes2[2, 0].set_ylabel('Y Position (m)')
    axes2[2, 0].legend()
    axes2[2, 0].grid(True, alpha=0.3)
    axes2[2, 0].axis('equal')
    
    axes2[2, 1].plot(range(len(steps)), ee_positions[:, 2], 'b-', linewidth=2)
    axes2[2, 1].set_title('End Effector Z Height Over Time')
    axes2[2, 1].set_xlabel('Step')
    axes2[2, 1].set_ylabel('Z Position (m)')
    axes2[2, 1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('/Users/soymilk/Codes/vicon-robot/rlds_converter/viz_actions.png', 
                dpi=150, bbox_inches='tight')
    print("✅ Saved: viz_actions.png")
    plt.close()
    
    # === VISUALIZATION 3: Data Summary ===
    print("\nGenerating data summary...")
    fig3 = plt.figure(figsize=(16, 10))
    gs = fig3.add_gridspec(3, 3, hspace=0.3, wspace=0.3)
    
    fig3.suptitle(f'RLDS Dataset Summary - Session {session_id}', 
                  fontsize=16, fontweight='bold')
    
    # Phase distribution
    ax1 = fig3.add_subplot(gs[0, 0])
    phases = [step['observation']['phase'].numpy().decode('utf-8') for step in steps]
    phase_counts = {}
    for p in phases:
        phase_counts[p] = phase_counts.get(p, 0) + 1
    ax1.bar(phase_counts.keys(), phase_counts.values(), color='steelblue', alpha=0.7)
    ax1.set_title('Steps per Phase')
    ax1.set_ylabel('Count')
    ax1.tick_params(axis='x', rotation=45)
    ax1.grid(True, alpha=0.3, axis='y')
    
    # Gripper values over time
    ax2 = fig3.add_subplot(gs[0, 1:])
    gripper_values = [step['observation']['state']['gripper'].numpy() for step in steps]
    ax2.plot(gripper_values, linewidth=2, color='darkgreen')
    ax2.fill_between(range(len(gripper_values)), gripper_values, alpha=0.3, color='green')
    ax2.set_title('Gripper State Over Time')
    ax2.set_xlabel('Step')
    ax2.set_ylabel('Gripper Value')
    ax2.grid(True, alpha=0.3)
    
    # Joint positions over time
    ax3 = fig3.add_subplot(gs[1, :])
    joint_positions = np.array([step['observation']['state']['joint_positions'].numpy() for step in steps])
    for j in range(6):
        ax3.plot(joint_positions[:, j], label=f'Joint {j}', alpha=0.7)
    ax3.set_title('Joint Positions Over Time')
    ax3.set_xlabel('Step')
    ax3.set_ylabel('Position (rad)')
    ax3.legend(loc='best', ncol=6)
    ax3.grid(True, alpha=0.3)
    
    # Sample image with annotations
    ax4 = fig3.add_subplot(gs[2, :])
    mid_step = steps[len(steps)//2]
    mid_img = mid_step['observation']['image'].numpy()
    ax4.imshow(mid_img)
    ax4.axis('off')
    
    # Add text annotations
    info_text = (
        f"Dataset Info:\n"
        f"• Total Steps: {len(steps)}\n"
        f"• Image Size: {mid_img.shape}\n"
        f"• Action Chunk Size: 6\n"
        f"• Phases: {', '.join(set(phases))}\n"
        f"• File Size: 22MB (TFRecord)"
    )
    ax4.text(0.02, 0.98, info_text, transform=ax4.transAxes,
             fontsize=11, verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    ax4.set_title('Sample Observation (Middle of Episode)')
    
    plt.savefig('/Users/soymilk/Codes/vicon-robot/rlds_converter/viz_summary.png', 
                dpi=150, bbox_inches='tight')
    print("✅ Saved: viz_summary.png")
    plt.close()
    
    print(f"\n{'='*60}")
    print("✅ All visualizations generated successfully!")
    print(f"{'='*60}")
    print("\nGenerated files:")
    print("  1. viz_images.png   - Sample images throughout episode")
    print("  2. viz_actions.png  - Action chunks and trajectories")
    print("  3. viz_summary.png  - Complete data summary")
    print(f"\nDataset location: /Users/soymilk/Codes/vicon-robot/output_rlds/vicon_robot/")
    print(f"TFRecord size: 22MB")
    print(f"Ready for VLA training! 🚀")
    
    break  # Only process first episode
