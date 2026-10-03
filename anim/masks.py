"""Mask geometry + per-frame raw HSIA noise samples."""

from __future__ import annotations

from anim.noise import MASK64, to_sphere, to_torus_parametric

SIZE = 16


def square_at(i: float):
    if 0.00 <= i < 0.25:
        return (-0.5 + i * 4, -0.5)
    if 0.25 <= i < 0.50:
        return (0.5, -0.5 + (i - 0.25) * 4)
    if 0.50 <= i < 0.75:
        return (0.5 - (i - 0.5) * 4, 0.5)
    if 0.75 <= i <= 1.00:
        return (-0.5, 0.5 - (i - 0.75) * 4)
    raise ValueError(f"curve parameter out of [0,1]: {i}")


def indicators_at(i: float):
    if 0.00 <= i < 0.50:
        return (3, 8 + i * 5)
    if 0.50 <= i <= 1.00:
        return (5, 8 + (i - 0.5) * 5)
    raise ValueError(f"curve parameter out of [0,1]: {i}")


def _rescale(size: int, v: float) -> int:
    return round(v * (size - 0.5) + 7.5)


def _parametric_scaled(i: float):
    x, y = square_at(i)
    return (x * 1.8, y * 1.8)


def frame_samples(seed: int, size: int, t: float) -> dict:
    """``{(y, x): (v, 1, v, 1)}`` along the square frame (travels with t)."""
    d = {}
    for n in range(41):
        i = n / 40
        x, y = square_at(i)
        px, py = _rescale(size, x), _rescale(size, y)
        if not (0 <= px < SIZE and 0 <= py < SIZE):
            continue
        j = (t + i) % 1.0
        v = to_torus_parametric(seed, 0.4, t, _parametric_scaled, j)
        d[(py, px)] = (v, 1.0, v, 1.0)
    return d


def indicators_samples(seed: int, t: float, y_offset: int = 0) -> dict:
    """``{(y, x): (h, 1, i, 1)}`` for the indicator dots."""
    d = {}
    for n in range(11):
        i = n / 10.0
        x, y = indicators_at(i)
        px, py = round(x), round(y) + y_offset
        if not (0 <= px < SIZE and 0 <= py < SIZE):
            continue
        h = to_sphere(seed, 1.0, i, t)
        inten = to_sphere((seed + 1) & MASK64, 1.0, i, t)
        d[(py, px)] = (h, 1.0, inten, 1.0)
    return d


def flowing_samples(mask, seed: int, t: float, w: int = 16,
                    h: int = 16) -> dict:
    """``{(y, x): (h, 1, i, 1)}`` for arbitrary mask pixels."""
    d = {}
    for x, y in mask:
        h = to_sphere(seed, 1.0, x / w * 0.8 + t, y / h * 0.8)
        inten = to_sphere((seed + 1) & MASK64, 1.0,
                          x / w * 0.8 + t, y / h * 0.8)
        d[(y, x)] = (h, 1.0, inten, 1.0)
    return d
