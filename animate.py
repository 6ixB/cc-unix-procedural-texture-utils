#!/usr/bin/env -S uv run

# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "pillow>=10.0",
#   "numpy>=1.26",
# ]
# ///

"""Animate the glowing parts of a texture with seamless Perlin noise.

    uv run animate.py input.png --mask side --seed 42

Side/top masks need 16x16 chat_box faces; --mask-image accepts any size
as long as the mask dimensions match the input.

Always writes ``./out/{input-name}.png`` plus ``.mcmeta``.
"""

from __future__ import annotations

import argparse
import random
from pathlib import Path

import numpy as np
from PIL import Image

from anim import faces
from anim.image import load_rgba_float, write_atlas


def _load_mask_image(path: Path) -> tuple:
    arr = np.asarray(Image.open(path).convert("RGB"), dtype=np.float64)
    h, w = arr.shape[:2]
    points = [(x, y) for y in range(h) for x in range(w)
              if arr[y, x].mean() >= 128]
    if not points:
        raise ValueError("--mask-image has no pixels with luminance >= 128")
    return points, w, h


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(
        prog="animate.py",
        description="Animate the glowing parts of a 16x16 texture with "
                    "seamless Perlin noise.",
    )
    parser.add_argument("input", type=Path, help="Source PNG")
    parser.add_argument("--mask", choices=["side", "top", "front"],
                        default="side", help="Face to animate (default: side)")
    parser.add_argument("--mask-image", type=Path, default=None,
                        help="Custom mask PNG (dimensions must match the "
                             "input): pixels with luminance >= 128 get a "
                             "flowing Perlin animation (overrides --mask)")
    parser.add_argument("--seed", type=int, default=None,
                        help="Noise seed (default: random, printed on run)")
    parser.add_argument("--keep-base-colors", action="store_true",
                        help="Recolor glow from the texture's own mask "
                             "pixels instead of the hardcoded chat_box colors")
    parser.add_argument("--shade-dark", type=float, default=0.30,
                        help="Base-color mode: darkest anchor as a fraction "
                             "of the darkest shade")
    parser.add_argument("--shade-light", type=float, default=0.75,
                        help="Base-color mode: lightest anchor blend toward "
                             "white, 0..1 (lower = dimmer brights)")
    parser.add_argument("--ramp-gain", type=float, default=1.25,
                        help="Base-color mode: noise spread across the ramp")
    parser.add_argument("--side-y-offset", type=int, default=0,
                        help="Shift the side indicator mask down by N pixels "
                             "(e.g. 2 for computer sides)")
    parser.add_argument("--keep-luminance", action="store_true",
                        help="Pulse each mask pixel around its own base "
                             "color instead of replacing it")
    parser.add_argument("--lum-lo", type=float, default=0.55,
                        help="Luminance mode: brightness factor at noise "
                             "minimum")
    parser.add_argument("--lum-hi", type=float, default=1.10,
                        help="Luminance mode: brightness factor at noise "
                             "maximum")
    args = parser.parse_args(argv)

    if args.keep_base_colors and args.keep_luminance:
        parser.error("--keep-base-colors and --keep-luminance "
                     "are mutually exclusive")

    seed = args.seed if args.seed is not None else random.getrandbits(64)
    seed &= 0xFFFFFFFFFFFFFFFF

    img = load_rgba_float(args.input)

    custom_mask = None
    if args.mask_image is not None:
        try:
            custom_mask, mw, mh = _load_mask_image(args.mask_image)
        except ValueError as e:
            parser.error(str(e))
        ih, iw = img.shape[:2]
        if (mw, mh) != (iw, ih):
            parser.error(f"--mask-image is {mw}x{mh} but input is "
                         f"{iw}x{ih}; dimensions must match")
        print(f"Custom mask pixels: {len(custom_mask)}")

    if custom_mask is None and args.mask in ("side", "top") \
            and img.shape[:2] != (16, 16):
        parser.error("side/top masks need an exactly 16x16 input")

    if custom_mask is not None:
        if args.keep_base_colors:
            frames, delay, interpolate = faces.build_palette_frames(
                img, "custom", seed, custom_mask, 0, args.shade_dark,
                args.shade_light, args.ramp_gain)
        elif args.keep_luminance:
            frames, delay, interpolate = faces.build_luminance_frames(
                img, "custom", seed, custom_mask, 0, args.lum_lo,
                args.lum_hi, args.ramp_gain)
        else:
            frames, delay, interpolate = faces.build_custom_frames(
                img, seed, custom_mask)
    elif args.keep_luminance and args.mask in ("side", "top"):
        kind = "frame" if args.mask == "top" else "indicators"
        frames, delay, interpolate = faces.build_luminance_frames(
            img, kind, seed, None, args.side_y_offset, args.lum_lo,
            args.lum_hi, args.ramp_gain)
    elif args.keep_base_colors and args.mask in ("side", "top"):
        kind = "frame" if args.mask == "top" else "indicators"
        frames, delay, interpolate = faces.build_palette_frames(
            img, kind, seed, None, args.side_y_offset, args.shade_dark,
            args.shade_light, args.ramp_gain)
    elif args.mask == "side":
        frames, delay, interpolate = faces.build_side_frames(
            img, seed, args.side_y_offset)
    elif args.mask == "top":
        frames, delay, interpolate = faces.build_top_frames(img, seed)
    else:
        if args.keep_base_colors or args.keep_luminance:
            print("Note: recolor modes have no effect on front faces")
        if img.shape[:2] != (16, 16):
            print("Note: front face splits any height into 16x16 frames")
        frames, delay, interpolate = faces.build_front_frames(img)

    outdir = Path("out")
    prefix = args.input.stem
    write_atlas(frames, outdir / (prefix + ".png"), delay, interpolate)

    print(f"Input:  {args.input}")
    print(f"Output: {outdir / (prefix + '.png')}")
    if custom_mask is not None:
        print(f"Mask:   custom ({args.mask_image}, {len(custom_mask)} px)")
    else:
        print(f"Mask:   {args.mask}")
    print(f"Seed:   {seed}")
    print("Done.")


if __name__ == "__main__":
    main()
