"""Deterministic, seamless PBR surface maps. No downloaded assets required."""
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'public' / 'textures'
OUT.mkdir(parents=True, exist_ok=True)
SIZE = 1024
rng = np.random.default_rng(704)

def noise(size, scale):
    small = rng.integers(0, 256, (scale, scale), dtype=np.uint8)
    return np.asarray(Image.fromarray(small).resize((size, size), Image.Resampling.BICUBIC), dtype=float) / 255

grain = rng.normal(0, 1, (SIZE, SIZE))
large = noise(SIZE, 32)
medium = noise(SIZE, 160)
scratches = Image.new('L', (SIZE, SIZE), 0)
draw = ImageDraw.Draw(scratches)
for _ in range(620):
    x, y = rng.integers(0, SIZE, 2)
    length = int(rng.integers(2, 65))
    draw.line((int(x), int(y), int(x + length), int(y + rng.integers(-8, 8))), fill=int(rng.integers(40, 230)), width=1)
scratch = np.asarray(scratches, dtype=float) / 255
height = medium * .025 + grain * .002 - scratch * .016
dy, dx = np.gradient(height)
normal = np.dstack((-dx * 7, -dy * 7, np.ones_like(dx)))
normal /= np.linalg.norm(normal, axis=2, keepdims=True)
Image.fromarray(((normal * .5 + .5) * 255).astype(np.uint8)).save(OUT / 'surface-normal.png')

surfaces = {
    'ceramic': ((158, 166, 148), .43, .03),
    'dark': ((38, 45, 46), .55, .88),
    'steel': ((105, 114, 117), .3, 1.0),
    'ochre': ((207, 112, 27), .42, .02),
    'rubber': ((19, 23, 23), .78, .0),
    'ground': ((53, 55, 55), .76, .05),
}
for name, (color, roughness, metallic) in surfaces.items():
    variation = (large - .5) * 14 + (medium - .5) * 7 + grain * 1.7
    if name == 'steel':
        variation += np.sin(np.arange(SIZE)[None, :] * 2.4) * 3
    base = np.clip(np.array(color)[None, None, :] + variation[:, :, None], 0, 255)
    wear = scratch * (.35 if name != 'rubber' else .07)
    base = base * (1 - wear[:, :, None]) + np.array([110, 114, 110]) * wear[:, :, None]
    Image.fromarray(base.astype(np.uint8)).save(OUT / f'{name}-color.jpg', quality=94)
    r = np.clip(roughness + (large - .5) * .13 + (medium - .5) * .09 - scratch * .16, .06, .98)
    # glTF uses green for roughness and blue for metalness.
    metal_map = np.full_like(r, metallic)
    if name in ('ceramic','ochre'):
        metal_map = np.clip(metal_map + scratch * .95,0,1)
    orm = np.dstack((np.ones_like(r), r, metal_map))
    Image.fromarray((orm * 255).astype(np.uint8)).save(OUT / f'{name}-orm.png')
    if name == 'ceramic':
        for finish, palette in {'arctic':(208,214,213), 'desert':(165,137,94), 'stealth':(64,74,78)}.items():
            alternate = np.clip(np.array(palette)[None,None,:] + variation[:,:,None],0,255)
            alternate = alternate * (1-wear[:,:,None]) + np.array([110,114,110]) * wear[:,:,None]
            Image.fromarray(alternate.astype(np.uint8)).save(OUT / f'ceramic-{finish}.jpg',quality=94)
print(f'Created {len(surfaces) * 2 + 1} PBR maps in {OUT}')
