# Procedural Texture Animator

`animate.py` animates the glowing parts of a Minecraft texture with
seamless-looping Perlin noise. The noise core, mask geometry, HSI color math,
and alpha compositing are ported from
[sjeulu/advanced-peripherals-util](https://github.com/sjeulu/advanced-peripherals-util).
Use any built-in mask (`side`, `top`, `front`) or supply your own mask image
(any size, must match the input), pick any seed, and optionally recolor the
glow from the texture itself.

## Requirements

- Python ≥ 3.10 with `numpy` and `pillow` (`uv run` resolves these automatically)

## Usage

```sh
uv run animate.py INPUT.png --mask side --seed 42
```

Output always lands in `./out/` under the original filename, plus a `.mcmeta`
sidecar (`frametime` in ticks, 1 tick = 50 ms) that makes the atlas work
in-game. The seed prints on every run; pass it back to reproduce bytes exactly.
Omit `--seed` for a fresh random animation each time.

## Options

| Option | Default | Description |
| ------ | ------- | ----------- |
| `INPUT` | — | Source PNG (16×16 required for `side`/`top`) |
| `--mask side\|top\|front` | `side` | Built-in animated region: indicator dots, top frame, or passthrough front |
| `--mask-image FILE` | — | Custom mask PNG (dimensions must match the input, any size); pixels with luminance ≥ 128 get a flowing noise animation (overrides `--mask`) |
| `--seed N` | random | Noise seed (`Word64`) |
| `--keep-base-colors` | off | Recolor glow from the texture's own mask pixels instead of the built-in gray/purple/green palette |
| `--shade-dark X` | `0.30` | Base-color mode: darkest anchor as a fraction of the darkest shade (lower = darker darks) |
| `--shade-light X` | `0.75` | Base-color mode: lightest anchor blend toward white, 0–1 (lower = dimmer brights) |
| `--ramp-gain X` | `1.25` | Base-color mode: noise spread across the shade ramp (higher visits the extremes more) |
| `--keep-luminance` | off | Pulse each mask pixel around its own base color (`base x f(noise)`) instead of replacing it; hue/saturation and brightness order preserved |
| `--lum-lo X` | `0.55` | Luminance mode: brightness factor at noise minimum |
| `--lum-hi X` | `1.10` | Luminance mode: brightness factor at noise maximum |
| `--side-y-offset N` | `0` | Shift the side indicator mask down N pixels |

`--keep-base-colors` / `--keep-luminance` and the shade/luminance knobs
are local extensions with no upstream equivalent; everything else mirrors
upstream behavior. Occasional color flashes are skipped in base-color mode,
and per-face delays stay side 4 / top 8 / front 2 / custom 4 with
interpolation on (off for front).

## Examples

```sh
# Classic gray-glow side animation, reproducible
uv run animate.py side.png --mask side --seed 42

# Top frame with traveling glow + purple/green flashes
uv run animate.py top.png --mask top --seed 42

# Front face passthrough (splits any height into 16x16 frames)
uv run animate.py side.png --mask front --seed 42

# Shifted indicators (e.g. computer sides sit 2px lower), recolored
# from the texture's own blues
uv run animate.py computer_side.png --mask side \
    --side-y-offset 2 --keep-base-colors --seed 42

# Tame hot brights while keeping darks
uv run animate.py computer_side.png --mask side \
    --side-y-offset 2 --keep-base-colors --shade-light 0.3 --seed 42

# Custom region from your own mask (white = animate)
uv run animate.py side.png --mask-image my_mask.png --seed 42

# Luminance mode: breathe the texture's own colors (brights stay bright)
uv run animate.py side.png --mask-image my_mask.png --keep-luminance --seed 42

# Larger textures work too, as long as the mask matches the input size
uv run animate.py panel_32.png --mask-image panel_32_mask.png \
    --keep-luminance --ramp-gain 2.0 --seed 42
```

## Verification

All checks performed pixel-by-pixel with NumPy (no eyeballing):

- Side/top outputs byte-identical across the restructure into modules
  (atlas + `.mcmeta`, fixed seed).
- Mask geometry exact: side glow hits exactly 6 indicator pixels; top frame
  exactly 36, overlapping pre-drawn source brights 36/36.
- Base-color mode keeps 100% of animated hues in the source hue family;
  shade swing tunable via `--shade-dark` / `--shade-light` / `--ramp-gain`.
- Determinism: identical bytes across runs for a fixed seed.

## License

BSD-3-Clause (see `LICENSE`) — same as upstream, which this is ported from.
Derived from [sjeulu/advanced-peripherals-util](https://github.com/sjeulu/advanced-peripherals-util)
© 2025 sjeulu; retain that copyright notice per the license terms.
