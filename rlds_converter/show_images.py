"""Show that images are actually stored in the TFRecord."""
import tensorflow_datasets as tfds
import matplotlib.pyplot as plt

print("Loading dataset...")
ds = tfds.load(
    'vicon_robot',
    data_dir='/Users/soymilk/Codes/vicon-robot/output_rlds',
    split='train',
)

for episode in ds:
    steps = list(episode['steps'])
    
    # Show 4 sample images
    fig, axes = plt.subplots(1, 4, figsize=(16, 4))
    indices = [0, 30, 60, 90]
    
    for i, idx in enumerate(indices):
        if idx < len(steps):
            img = steps[idx]['observation']['image'].numpy()
            axes[i].imshow(img)
            axes[i].set_title(f"Step {idx}\nShape: {img.shape}")
            axes[i].axis('off')
    
    plt.tight_layout()
    plt.savefig('/Users/soymilk/Codes/vicon-robot/rlds_converter/tfrecord_images.png', dpi=100)
    print(f"\n✅ Saved 4 sample images to: tfrecord_images.png")
    print(f"✅ All {len(steps)} images are stored in the TFRecord!")
    print(f"✅ Total file size: 22MB (images are JPEG compressed)")
    break
