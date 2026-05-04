#!/usr/bin/env python3
"""
coordinate_hunter.py
====================
Scans transparent PNG mask images organized by truck and cabin variant
inside the `masks/` folder hierarchy:

    masks/<truck_internal_name>/<cabin_internal_name>.png
    e.g.  masks/daf.xf/space_cab.png

Detects specific solid-colored rectangles and extracts their bounding
boxes as a nested JSON dictionary ready to paste into the ETS2 skin
creator pipeline.

COLOR CODE DICTIONARY
---------------------
  #FF00E1  →  Doors          (2 boxes → left_door, right_door)
  #2BFF3C  →  Hood           (1 box   → hood)
  #F7FF60  →  Roof           (1 box   → roof)
  #FF1B0F  →  C-Pillar Upper (2 boxes → left_c_pillar_upper, right_c_pillar_upper)
  #141CFF  →  Side Skirt     (2 boxes → left_c_pillar_lower, right_c_pillar_lower)

NOISE FILTERING
---------------
  Detected regions with area < 400 px² or width/height < 10 px are
  discarded as artifacts before the expected-count validation.

Usage:
    python coordinate_hunter.py
    (reads from ./masks/, writes to ./extracted_coords.json)
"""

import json
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image

# ── Folder / output configuration ──────────────────────────────────────────
MASKS_DIR = Path(__file__).parent / "masks"
OUTPUT_FILE = Path(__file__).parent / "extracted_coords.json"

# ── RGB tolerance for color matching (±) ───────────────────────────────────
TOLERANCE = 2

# ── Noise filtering thresholds ─────────────────────────────────────────────
MIN_BOX_AREA = 400        # Ignore regions with bounding-box area < this
MIN_BOX_DIM  = 10         # Ignore regions with width OR height < this

# ── Color definitions ─────────────────────────────────────────────────────
# Each entry: (hex_label, (R, G, B), expected_count, key_names)
#   key_names: list of key names.  If len > 1, boxes are sorted by X.
COLOR_MAP = [
    ("#FF00E1", (255,   0, 225), 2, ["left_door", "right_door"]),
    ("#2BFF3C", ( 43, 255,  60), 1, ["hood"]),
    ("#F7FF60", (247, 255,  96), 1, ["roof"]),
    ("#FF1B0F", (255,  27,  15), 2, ["left_c_pillar_upper", "right_c_pillar_upper"]),
    ("#141CFF", ( 20,  28, 255), 2, ["left_c_pillar_lower", "right_c_pillar_lower"]),
]


# ── Helpers ────────────────────────────────────────────────────────────────

def _color_mask(pixels: np.ndarray, target_rgb: tuple[int, ...]) -> np.ndarray:
    """Return a boolean 2-D mask where the pixel's RGB is within TOLERANCE of *target_rgb*.

    *pixels* is expected to have shape (H, W, C) where C >= 3.
    Only the first three channels (R, G, B) are compared; alpha is ignored.
    """
    rgb = pixels[:, :, :3].astype(np.int16)
    target = np.array(target_rgb, dtype=np.int16)
    diff = np.abs(rgb - target)
    return np.all(diff <= TOLERANCE, axis=2)


def _is_valid_box(box: dict) -> bool:
    """Return True if a bounding box passes the noise filter."""
    return (box["w"] >= MIN_BOX_DIM
            and box["h"] >= MIN_BOX_DIM
            and box["w"] * box["h"] >= MIN_BOX_AREA)


def _find_contiguous_boxes(mask: np.ndarray) -> list[dict]:
    """Find bounding boxes around contiguous regions of *True* values.

    Uses a simple connected-component flood-fill so we don't need
    scipy / cv2 as a hard dependency.  The masks are expected to contain
    clean, axis-aligned rectangles so performance is fine.

    Small / thin regions are discarded via the noise filter before
    the result is returned.

    Returns a list of dicts: {"x": ..., "y": ..., "w": ..., "h": ...}
    sorted by the x coordinate.
    """
    raw_boxes: list[dict] = []

    # Try to use scipy for speed if available; fall back to manual BFS.
    try:
        from scipy.ndimage import label as _label
        labeled, num_features = _label(mask)
        for i in range(1, num_features + 1):
            ys, xs = np.where(labeled == i)
            x_min, x_max = int(xs.min()), int(xs.max())
            y_min, y_max = int(ys.min()), int(ys.max())
            raw_boxes.append({"x": x_min, "y": y_min,
                              "w": x_max - x_min + 1,
                              "h": y_max - y_min + 1})
    except ImportError:
        # Manual BFS fallback
        visited = np.zeros_like(mask, dtype=bool)
        height, width = mask.shape

        for start_y in range(height):
            for start_x in range(width):
                if mask[start_y, start_x] and not visited[start_y, start_x]:
                    # BFS to find all connected pixels
                    queue = [(start_y, start_x)]
                    visited[start_y, start_x] = True
                    min_x, max_x = start_x, start_x
                    min_y, max_y = start_y, start_y
                    head = 0
                    while head < len(queue):
                        cy, cx = queue[head]
                        head += 1
                        min_x = min(min_x, cx)
                        max_x = max(max_x, cx)
                        min_y = min(min_y, cy)
                        max_y = max(max_y, cy)
                        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                            ny, nx = cy + dy, cx + dx
                            if 0 <= ny < height and 0 <= nx < width:
                                if mask[ny, nx] and not visited[ny, nx]:
                                    visited[ny, nx] = True
                                    queue.append((ny, nx))

                    raw_boxes.append({"x": min_x, "y": min_y,
                                      "w": max_x - min_x + 1,
                                      "h": max_y - min_y + 1})

    # ── Noise filter: discard tiny / thin artifacts ────────────────────
    boxes = [b for b in raw_boxes if _is_valid_box(b)]
    boxes.sort(key=lambda b: b["x"])
    return boxes


def process_mask(image_path: Path, label: str = "") -> dict | None:
    """Process a single mask PNG and return the zone dictionary.

    *label* is used for log messages (e.g. "daf.xf/space_cab").
    """
    display = label or image_path.stem
    img = Image.open(image_path).convert("RGBA")
    pixels = np.array(img)

    zones: dict = {}

    for hex_label, target_rgb, expected_count, key_names in COLOR_MAP:
        mask = _color_mask(pixels, target_rgb)
        if not mask.any():
            # Color not present in this mask → skip silently
            continue

        boxes = _find_contiguous_boxes(mask)   # already noise-filtered

        if len(boxes) != expected_count:
            print(
                f"  ⚠  [{display}] Color {hex_label}: expected {expected_count} "
                f"region(s), found {len(boxes)} (after noise filter).  "
                f"Skipping this color.",
                file=sys.stderr,
            )
            continue

        # Boxes are already sorted by X from _find_contiguous_boxes
        for key_name, box in zip(key_names, boxes):
            zones[key_name] = box

    return zones if zones else None


# ── Main ───────────────────────────────────────────────────────────────────

def main() -> None:
    if not MASKS_DIR.is_dir():
        print(f"ERROR: Masks directory not found at '{MASKS_DIR}'.", file=sys.stderr)
        print("       Create a 'masks/' folder next to this script with "
              "sub-folders per truck.", file=sys.stderr)
        sys.exit(1)

    # ── Discover nested structure: masks/<truck>/<cabin>.png ───────────
    truck_dirs = sorted(
        [d for d in MASKS_DIR.iterdir() if d.is_dir()]
    )
    if not truck_dirs:
        print(f"ERROR: No truck sub-folders found in '{MASKS_DIR}'.",
              file=sys.stderr)
        print("       Expected structure: masks/<truck_name>/<cabin>.png",
              file=sys.stderr)
        sys.exit(1)

    total_masks = 0
    result: dict = {}

    for truck_dir in truck_dirs:
        truck_key = truck_dir.name     # e.g. "daf.xf"
        png_files = sorted(truck_dir.glob("*.png"))
        if not png_files:
            continue

        print(f"\n  📂  {truck_key}/")
        cabins: dict = {}

        for png in png_files:
            cabin_key = png.stem       # e.g. "space_cab"
            label = f"{truck_key}/{cabin_key}"
            print(f"      ▸  {png.name} …")
            total_masks += 1

            zones = process_mask(png, label=label)
            if zones is not None:
                cabins[cabin_key] = zones
                for zone_name, coords in zones.items():
                    print(f"           ✔ {zone_name:>25s}  →  "
                          f"x={coords['x']:>5d}  y={coords['y']:>5d}  "
                          f"w={coords['w']:>5d}  h={coords['h']:>5d}")
            else:
                print(f"           (no recognized zones)")

        if cabins:
            result[truck_key] = cabins

    if total_masks == 0:
        print(f"ERROR: No .png mask files found under '{MASKS_DIR}'.",
              file=sys.stderr)
        sys.exit(1)

    print(f"\n🔍  Processed {total_masks} mask(s) across "
          f"{len(result)} truck(s).")

    # ── Write output ───────────────────────────────────────────────────
    json_text = json.dumps(result, indent=2)

    print(f"\n{'═' * 60}")
    print("📋  FINAL JSON OUTPUT")
    print(f"{'═' * 60}\n")
    print(json_text)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(json_text + "\n")

    print(f"\n✅  Saved to '{OUTPUT_FILE}'.")


if __name__ == "__main__":
    main()
