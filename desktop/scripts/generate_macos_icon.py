#!/usr/bin/env python3
"""Build a macOS-standard squircle app icon from the full-bleed master.

Usage (from desktop/):
  python3 scripts/generate_macos_icon.py
  npx tauri icon app-icon.png -o src-tauri/icons
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageChops, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "static/brand/nous-app-icon-fullbleed.png"
SIZE = 1024


def superellipse_mask(size: int, n: float = 5.2) -> Image.Image:
    """Apple-like continuous-corner squircle (superellipse / Lamé curve)."""
    import numpy as np

    scale = 4
    big = size * scale
    ys, xs = np.mgrid[0:big, 0:big]
    cx = cy = (big - 1) / 2.0
    a = b = cx
    inside = (np.abs((xs - cx) / a) ** n + np.abs((ys - cy) / b) ** n) <= 1.0
    mask = Image.fromarray((inside.astype("uint8") * 255), mode="L")
    mask = mask.filter(ImageFilter.GaussianBlur(radius=scale * 0.35))
    return mask.resize((size, size), Image.Resampling.LANCZOS)


def main() -> None:
    src = Image.open(SRC).convert("RGBA")
    if src.size != (SIZE, SIZE):
        src = src.resize((SIZE, SIZE), Image.Resampling.LANCZOS)

    mask = superellipse_mask(SIZE)
    r, g, b, a = src.split()
    icon = Image.merge("RGBA", (r, g, b, ImageChops.multiply(a, mask)))

    outputs = [
        ROOT / "static/brand/nous-app-icon-macos.png",
        ROOT / "static/brand/nous-app-icon.png",
        ROOT / "app-icon.png",
        ROOT / "app-icon-macos.png",
    ]
    for path in outputs:
        icon.save(path, "PNG")
        print(f"wrote {path.relative_to(ROOT)}")

    fav = icon.resize((32, 32), Image.Resampling.LANCZOS)
    fav.save(ROOT / "static/favicon.png")
    print("wrote static/favicon.png")


if __name__ == "__main__":
    main()
