"""Face builders: glow layers, chat_box faces, base-color palettes."""

from __future__ import annotations

import numpy as np

from anim import masks
from anim.color import hsia_to_rgba
from anim.image import from_map, overlay
from anim.noise import MASK64, lerp

SIZE = masks.SIZE
FRAMES = 16


def _render(samples: dict, adjust):
    return from_map({k: hsia_to_rgba(*adjust(*v))
                     for k, v in samples.items()})


def _base_adjust(_h: float, _s: float, i: float, a: float):
    return (0.0, 0.0, lerp(0.7, 0.95, i), a)


def _occasional(hue: float):
    return lambda h, s, i, a: (
        hue, 1.0, 0.73,
        lerp(0.2, 1.0, (i - 0.5) * 2.0) if i > 0.5 else 0.0)


def _glow_layer(kind: str, seed: int, t: float, adjust,
                y_offset: int = 0, mask=None, size=None):
    if kind == "frame":
        return _render(masks.frame_samples(seed, 10, t), adjust)
    if kind == "custom":
        w, h = size if size is not None else (16, 16)
        return _render(masks.flowing_samples(mask, seed, t, w, h), adjust)
    return _render(masks.indicators_samples(seed, t, y_offset), adjust)


def _overlay_frames(base_frames: list, kind: str, seed: int, adjust,
                    y_offset: int = 0, mask=None, size=None) -> list:
    n = len(base_frames)
    out = []
    for idx, frame in enumerate(base_frames):
        glow = _glow_layer(kind, seed, idx / n, adjust, y_offset, mask,
                           size)
        out.append(overlay(glow, frame))
    return out


def _repeat_base(img: np.ndarray, frames: int = FRAMES) -> list:
    return [img.copy() for _ in range(frames)]


def build_side_frames(img: np.ndarray, seed: int,
                      y_offset: int = 0) -> tuple:
    """Indicator dots, delay 4, interpolate."""
    frames = _overlay_frames(_repeat_base(img), "indicators", seed,
                             _base_adjust, y_offset)
    return frames, 4, True


def build_top_frames(img: np.ndarray, seed: int) -> tuple:
    """Frame glow + purple/green flashes, delay 8, interpolate."""
    frames = _repeat_base(img)
    frames = _overlay_frames(frames, "frame", seed, _base_adjust)
    frames = _overlay_frames(frames, "frame", seed, _occasional(0.9))
    frames = _overlay_frames(
        frames, "frame", (seed + 1) & MASK64, _occasional(0.55))
    return frames, 8, True


def build_front_frames(img: np.ndarray) -> tuple:
    """Passthrough atlas split, delay 2, no interpolation."""
    from anim.image import transparent
    h, w, _ = img.shape
    frames = []
    for y in range(0, max(h, SIZE), SIZE):
        for x in range(0, max(w, SIZE), SIZE):
            tile = transparent(SIZE, SIZE)
            src = img[y:y + SIZE, x:x + SIZE]
            tile[:src.shape[0], :src.shape[1]] = src
            frames.append(tile)
    return frames, 2, False


def build_custom_frames(img: np.ndarray, seed: int, mask,
                        adjust=None) -> tuple:
    """Arbitrary white-pixel mask with flowing noise, delay 4."""
    if adjust is None:
        adjust = _base_adjust
    h, w = img.shape[:2]
    frames = _overlay_frames(_repeat_base(img), "custom", seed, adjust,
                             mask=mask, size=(w, h))
    return frames, 4, True


def build_luminance_frames(img: np.ndarray, kind: str, seed: int, mask,
                           y_offset: int = 0, lo: float = 0.55,
                           hi: float = 1.10, gain: float = 1.25) -> tuple:
    """Pulse each mask pixel around its own base color (luminance kept).

    Output = base RGB x f(noise); hue/saturation and relative brightness
    order preserved exactly, alpha untouched.
    """
    if kind == "frame":
        sampler = lambda t: masks.frame_samples(seed, 10, t)
        driver = lambda hsia: hsia[0]
        delay = 8
    elif kind == "custom":
        sampler = lambda t: masks.flowing_samples(
            mask, seed, t, img.shape[1], img.shape[0])
        driver = lambda hsia: hsia[2]
        delay = 4
    else:
        sampler = lambda t: masks.indicators_samples(seed, t, y_offset)
        driver = lambda hsia: hsia[2]
        delay = 4
    frames = []
    base_frames = _repeat_base(img)
    n = len(base_frames)
    for idx, frame in enumerate(base_frames):
        out = frame.copy()
        for (y, x), hsia in sampler(idx / n).items():
            t01 = min(max((driver(hsia) * gain + 1.0) / 2.0, 0.0), 1.0)
            f = lo + (hi - lo) * t01
            out[y, x, :3] = np.clip(frame[y, x, :3] * f, 0.0, 1.0)
        frames.append(out)
    return frames, delay, True


def extract_ramp(img: np.ndarray, points) -> list:
    """Authored shades at mask ``(x, y)`` points: unique, by luminance."""
    uniq = sorted({tuple(img[y, x, :3]) for x, y in points},
                  key=lambda c: (c[0] + c[1] + c[2], c))
    return [np.array(c) for c in uniq]


def expand_ramp(shades: list, dark_scale: float,
                light_blend: float) -> list:
    """Widen the range along the same hue: dark anchor toward black, light
    anchor toward white."""
    dark, light = shades[0], shades[-1]
    dark_anchor = np.clip(dark * dark_scale, 0.0, 1.0)
    light_anchor = np.clip(light + (1.0 - light) * light_blend, 0.0, 1.0)
    return [dark_anchor] + list(shades) + [light_anchor]


def ramp_color(stops: list, v: float, gain: float) -> np.ndarray:
    """Map noise ``v`` in [-1, 1] smoothly across the shade ramp."""
    pos = min(max((v * gain + 1.0) / 2.0, 0.0), 1.0) * (len(stops) - 1)
    i0 = min(int(pos), len(stops) - 2)
    return np.clip(stops[i0] + (stops[i0 + 1] - stops[i0]) * (pos - i0),
                   0.0, 1.0)


def build_palette_frames(img: np.ndarray, kind: str, seed: int, mask,
                         y_offset: int = 0, dark_scale: float = 0.30,
                         light_blend: float = 0.75,
                         gain: float = 1.25) -> tuple:
    """Glow recolored from the base palette (opaque, like the base)."""
    if kind == "frame":
        points = [(x, y) for (y, x) in masks.frame_samples(seed, 10, 0.0)]
        driver = lambda hsia: hsia[0]
        sampler = lambda t: masks.frame_samples(seed, 10, t)
        delay = 8
    elif kind == "custom":
        points = list(mask)
        driver = lambda hsia: hsia[2]
        w, h = img.shape[1], img.shape[0]
        sampler = lambda t: masks.flowing_samples(mask, seed, t, w, h)
        delay = 4
    else:
        points = [(x, y) for (y, x) in
                  masks.indicators_samples(seed, 0.0, y_offset)]
        driver = lambda hsia: hsia[2]
        sampler = lambda t: masks.indicators_samples(seed, t, y_offset)
        delay = 4
    stops = extract_ramp(img, points)
    uniq = {tuple(np.round(s * 255).astype(int)) for s in stops}
    print(f"Palette shades: {len(uniq)} "
          f"{sorted(tuple(int(v) for v in u) for u in uniq)}")
    stops = expand_ramp(stops, dark_scale, light_blend)
    frames = []
    base_frames = _repeat_base(img)
    n = len(base_frames)
    for idx, frame in enumerate(base_frames):
        d = {}
        for (y, x), hsia in sampler(idx / n).items():
            r, g, b = ramp_color(stops, driver(hsia), gain)
            d[(y, x)] = (r, g, b, 1.0)
        frames.append(overlay(from_map(d), frame))
    return frames, delay, True
