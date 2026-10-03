"""Perlin noise core (port of pure-noise Perlin3 + seamless samplers)."""

from __future__ import annotations

import math

MASK64 = 0xFFFFFFFFFFFFFFFF

_PRIME_X = 501125321
_PRIME_Y = 1136930381
_PRIME_Z = 1720413743
_HASH_MULT = 0x27D4EB2D
_NORMALIZE3 = 0.96492141485214233398437
_U32 = 0xFFFFFFFF

_GRAD3_BASE = [
    0, 1, 1, 0, 0, -1, 1, 0, 0, 1, -1, 0, 0, -1, -1, 0,
    1, 0, 1, 0, -1, 0, 1, 0, 1, 0, -1, 0, -1, 0, -1, 0,
    1, 1, 0, 0, -1, 1, 0, 0, 1, -1, 0, 0, -1, -1, 0, 0,
]
_GRAD3_LAST = [
    1, 1, 0, 0, 0, -1, 1, 0, -1, 1, 0, 0, 0, -1, -1, 0,
]
_GRAD3 = tuple(_GRAD3_BASE * 5 + _GRAD3_LAST)
assert len(_GRAD3) == 256


def _u32(n: int) -> int:
    return n & _U32


def _quintic(t: float) -> float:
    return t * t * t * (t * (t * 6 - 15) + 10)


def lerp(a: float, b: float, t: float) -> float:
    return a + t * (b - a)


def _grad3(seed: int, xp: int, yp: int, zp: int,
           xd: float, yd: float, zd: float) -> float:
    h = _u32((seed & _U32) ^ xp ^ yp ^ zp)
    h = _u32(h * _HASH_MULT)
    ix = (h ^ (h >> 15)) & 0xFC
    return xd * _GRAD3[ix] + yd * _GRAD3[ix + 1] + zd * _GRAD3[ix + 2]


def perlin3(seed: int, x: float, y: float, z: float) -> float:
    seed = seed & 0xFFFFFFFFFFFFFFFF
    x0 = math.floor(x)
    y0 = math.floor(y)
    z0 = math.floor(z)

    xd0 = x - x0
    yd0 = y - y0
    zd0 = z - z0
    xd1, yd1, zd1 = xd0 - 1.0, yd0 - 1.0, zd0 - 1.0

    u, v, w = _quintic(xd0), _quintic(yd0), _quintic(zd0)

    x0p = _u32(x0 * _PRIME_X)
    y0p = _u32(y0 * _PRIME_Y)
    z0p = _u32(z0 * _PRIME_Z)
    x1p = _u32(x0p + _PRIME_X)
    y1p = _u32(y0p + _PRIME_Y)
    z1p = _u32(z0p + _PRIME_Z)

    x1 = lerp(
        lerp(_grad3(seed, x0p, y0p, z0p, xd0, yd0, zd0),
             _grad3(seed, x1p, y0p, z0p, xd1, yd0, zd0), u),
        lerp(_grad3(seed, x0p, y1p, z0p, xd0, yd1, zd0),
             _grad3(seed, x1p, y1p, z0p, xd1, yd1, zd0), u),
        v,
    )
    x2 = lerp(
        lerp(_grad3(seed, x0p, y0p, z1p, xd0, yd0, zd1),
             _grad3(seed, x1p, y0p, z1p, xd1, yd0, zd1), u),
        lerp(_grad3(seed, x0p, y1p, z1p, xd0, yd1, zd1),
             _grad3(seed, x1p, y1p, z1p, xd1, yd1, zd1), u),
        v,
    )
    return _NORMALIZE3 * lerp(x1, x2, w)


def to_sphere(seed: int, r: float, alpha: float, beta: float) -> float:
    theta = 2.0 * math.pi * alpha
    phi = 2.0 * math.pi * beta
    return perlin3(seed,
                   r * math.cos(phi) * math.cos(theta),
                   r * math.sin(theta),
                   r * math.sin(phi) * math.cos(theta))


def to_torus_parametric(seed: int, r: float, alpha: float,
                        f, i: float) -> float:
    theta = 2.0 * math.pi * alpha
    xp, yp = f(i)
    x = (r + xp) * math.cos(theta)
    z = (r + xp) * math.sin(theta)
    return perlin3(seed, x, yp, z)
