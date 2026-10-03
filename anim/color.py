"""HSI color math (port of hip's HSI colorspace conversions)."""

from __future__ import annotations

import math


def hsia_to_rgba(h: float, s: float, i: float, a: float):
    h_rad = (h % 1.0) * 2.0 * math.pi
    i_s = i * s
    second = i - i_s

    def first(a1: float, b1: float) -> float:
        return i + i_s * math.cos(a1) / math.cos(b1)

    def third(v1: float, v2: float) -> float:
        return i + 2.0 * i_s + v1 - v2

    two_pi = 2.0 * math.pi
    if h_rad < two_pi / 3.0:
        r = first(h_rad, math.pi / 3.0 - h_rad)
        b = second
        g = third(b, r)
    elif h_rad < 4.0 * two_pi / 6.0:
        g = first(h_rad - two_pi / 3.0, h_rad + math.pi)
        r = second
        b = third(r, g)
    else:
        b = first(h_rad - 4.0 * two_pi / 6.0, two_pi - math.pi / 3.0 - h_rad)
        g = second
        r = third(g, b)
    return (r, g, b, a)


def rgb_to_hsi(r: float, g: float, b: float):
    i = (r + g + b) / 3.0
    x = (2.0 * r - g - b) / 2.449489742783178
    y = (g - b) / 1.4142135623730951
    h_prime = math.atan2(y, x)
    h = ((h_prime + 2.0 * math.pi) if h_prime < 0 else h_prime) / (2.0 * math.pi)
    s = 0.0 if i == 0 else 1.0 - min(r, g, b) / i
    return (h, s, i)
