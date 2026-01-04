#!/usr/bin/env python3
"""
Update the main logo.png to be circular-safe
"""

from PIL import Image
import shutil

def create_circular_safe_logo(source_path, output_path, scale_factor=0.75):
    """
    Create a circular-safe version of the logo by adding padding.

    Args:
        source_path: Path to source logo
        output_path: Path to save the output
        scale_factor: How much to scale down (0.75 = 75%)
    """
    # First, backup the original
    backup_path = source_path.replace('.png', '_original_backup.png')
    shutil.copy2(source_path, backup_path)
    print(f"✓ Backed up original to {backup_path}")

    # Open the source logo
    logo = Image.open(source_path).convert('RGBA')
    original_size = logo.size

    # Create new image with same size but with padding
    output = Image.new('RGBA', original_size, (76, 175, 80, 255))  # Green background

    # Calculate scaled size
    scaled_size = int(min(original_size) * scale_factor)

    # Resize logo to scaled size
    logo_resized = logo.resize((scaled_size, scaled_size), Image.Resampling.LANCZOS)

    # Center the resized logo
    x = (original_size[0] - scaled_size) // 2
    y = (original_size[1] - scaled_size) // 2

    # Paste onto output
    output.paste(logo_resized, (x, y), logo_resized)

    # Save
    output.save(output_path, 'PNG', optimize=True)
    print(f"✓ Created circular-safe logo at {output_path}")
    print(f"  Original size: {original_size}")
    print(f"  Logo scaled to: {scaled_size}x{scaled_size} ({int(scale_factor*100)}%)")

def main():
    logo_path = '/home/user/GigHala/static/images/logo.png'

    print("Creating circular-safe main logo...")
    print("=" * 50)

    create_circular_safe_logo(logo_path, logo_path, scale_factor=0.75)

    print("=" * 50)
    print("✓ Main logo updated successfully!")
    print("\nThe logo now has proper padding for circular display.")

if __name__ == '__main__':
    main()
