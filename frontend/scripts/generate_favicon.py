"""
Generate favicon.ico from PNG source.

Usage:
    python frontend/scripts/generate_favicon.py
"""
from pathlib import Path
import sys

SRC = Path(__file__).parent.parent / "assets" / "images" / "podcast_finder_logo.png"
DST = Path(__file__).parent.parent / "assets" / "favicon.ico"


def main():
    try:
        from PIL import Image
    except Exception as e:
        print("Pillow not installed. Please run: python -m pip install pillow")
        raise

    if not SRC.exists():
        print(f"Source PNG not found: {SRC}")
        sys.exit(1)

    DST.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(SRC) as im:
        # Ensure RGBA for transparency support
        im = im.convert("RGBA")
        # Save as ICO with common favicon sizes
        sizes = [(16, 16), (32, 32), (48, 48)]
        im.save(DST, format="ICO", sizes=sizes)

    print(f"Wrote {DST}")


if __name__ == '__main__':
    main()
