"""RGBA float image helpers (HIP-style alpha overlay, atlas IO)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image


def transparent(h: int, w: int) -> np.ndarray:
    return np.zeros((h, w, 4), dtype=np.float64)


def from_map(mapping: dict) -> np.ndarray | None:
    if not mapping:
        return None
    h = max(y for y, _ in mapping) + 1
    w = max(x for _, x in mapping) + 1
    img = transparent(h, w)
    for (y, x), px in mapping.items():
        img[y, x] = px
    return img


def overlay(top: np.ndarray | None, bottom: np.ndarray) -> np.ndarray:
    if top is None:
        return bottom.copy()
    h = max(top.shape[0], bottom.shape[0])
    w = max(top.shape[1], bottom.shape[1])
    out = transparent(h, w)
    bh, bw, _ = bottom.shape
    out[:bh, :bw] = bottom
    th, tw, _ = top.shape
    base = out[:th, :tw].copy()
    a_t = top[..., 3:4]
    rgb = top[..., :3] * a_t + base[..., :3] * (1.0 - a_t)
    alpha = a_t + base[..., 3:4] * (1.0 - a_t)
    out[:th, :tw] = np.concatenate([rgb, alpha], axis=-1)
    return out


def float_to_image(arr: np.ndarray) -> Image.Image:
    return Image.fromarray(
        np.round(np.clip(arr, 0.0, 1.0) * 255.0).astype(np.uint8), "RGBA")


def load_rgba_float(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGBA"),
                      dtype=np.float64) / 255.0


def write_atlas(frames: list, output: Path, delay: int,
                interpolate: bool) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    float_to_image(np.concatenate(frames, axis=0)).save(output)
    output.with_name(output.name + ".mcmeta").write_text(
        "{\n"
        '  "animation": {\n'
        f'    "interpolate": {"true" if interpolate else "false"},\n'
        f'    "frametime": {delay}\n'
        "  }\n"
        "}\n",
        encoding="utf-8",
    )
