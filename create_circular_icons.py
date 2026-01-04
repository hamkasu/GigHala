#!/usr/bin/env python3
"""
Create circular-safe icon files from the logo.
This script creates icon versions where the content is scaled down to fit
comfortably within a circular display area, preventing cropping.
"""

from PIL import Image, ImageDraw
import os

def create_circular_safe_icon(source_path, output_path, size, scale_factor=0.80):
    """
    Create a circular-safe icon by scaling down the source image.

    Args:
        source_path: Path to source logo image
        output_path: Path to save the output icon
        size: Output size (width, height)
        scale_factor: How much to scale down the logo (0.80 = 80% of original)
    """
    # Open the source logo
    logo = Image.open(source_path).convert('RGBA')

    # Create output image with the same green background
    output = Image.new('RGBA', size, (76, 175, 80, 255))  # Green background

    # Calculate the safe area size (scaled down to fit in circle)
    safe_size = int(min(size) * scale_factor)

    # Resize the logo to fit within the safe area
    logo_resized = logo.resize((safe_size, safe_size), Image.Resampling.LANCZOS)

    # Center the resized logo
    x = (size[0] - safe_size) // 2
    y = (size[1] - safe_size) // 2

    # Paste the logo onto the output
    output.paste(logo_resized, (x, y), logo_resized)

    # For very small icons, we might want to sharpen
    if size[0] <= 32:
        from PIL import ImageEnhance
        enhancer = ImageEnhance.Sharpness(output)
        output = enhancer.enhance(1.5)

    # Save as PNG
    output.save(output_path, 'PNG', optimize=True)
    print(f"✓ Created {output_path} ({size[0]}x{size[1]})")

def main():
    # Paths
    source_logo = '/home/user/GigHala/static/images/logo.png'
    icons_dir = '/home/user/GigHala/static/icons'

    # Ensure icons directory exists
    os.makedirs(icons_dir, exist_ok=True)

    print("Creating circular-safe icon files...")
    print("=" * 50)

    # Create all icon sizes
    icons = [
        ('favicon-32x32.png', (32, 32), 0.75),      # Favicon - smaller scale for clarity
        ('apple-touch-icon.png', (180, 180), 0.80),  # iOS home screen
        ('icon-192x192.png', (192, 192), 0.80),      # Android/PWA
        ('icon-512x512.png', (512, 512), 0.80),      # High-res PWA
    ]

    for filename, size, scale in icons:
        output_path = os.path.join(icons_dir, filename)
        create_circular_safe_icon(source_logo, output_path, size, scale)

    print("=" * 50)
    print("✓ All icons created successfully!")
    print("\nThese icons are now safe for circular display.")
    print("The logo content has been scaled down and centered to prevent cropping.")

if __name__ == '__main__':
    main()
