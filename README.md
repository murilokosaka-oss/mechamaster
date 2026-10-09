# NOMAD MK.07 · Mechamaster

An original, fully modeled expedition mech with layered armor, exposed hydraulic
actuators, fluid lines, articulated fingers, radiator fins, optical sensors,
machined fasteners, and custom stencil markings.

## Open the model

- `artifacts/nomad-mk07.blend` — editable Blender 4.3 scene, organized into nine
  assemblies, with a studio lighting setup and Cycles hero camera. The assemblies
  are object groups, not a skeletal animation rig.
- `public/models/nomad-mk07.glb` — self-contained, textured glTF 2.0 model,
  approximately 9 MB, with embedded textures and preserved assembly hierarchy.
- `artifacts/nomad-hero.png` — ray-traced studio render.
- `public/textures/` — original color, packed roughness/metalness, and tangent-space
  normal maps. All textures and geometry are generated locally; no external asset
  services or credentials are required.

The model has **477 meshes, 148,992 triangles, and ten materials**. Its fictional
full-scale height is approximately 8.1 meters. The material set includes weathered
ceramic green, graphite titanium, brushed steel, ochre enamel, rubber, smoked
optics, stencil ink, recessed cavities, and emissive amber and blue sensors.

## Interactive viewer

Requires Node.js 22.12+ (tested with 24.19).

```sh
npm ci
npm run dev -- --port 5173
```

Drag to orbit, scroll to zoom, and use right-drag to pan. Focus the canvas to orbit
with the arrow keys. The viewer includes three lighting environments, four camera
presets, an exploded assembly view, four armor finishes, roughness and exposure
controls, wireframe mode, a turntable, PNG capture, and GLB download. Reset returns
all scene controls to their defaults. Material changes affect the live view;
the GLB download contains the original field finish.

The browser uses real-time physically based rasterization, environment reflections,
soft shadows, and tone mapping. The Blender scene uses Cycles ray tracing for the
still render. Visual results depend on the graphics hardware and lighting.

```sh
npm run build
npm run preview -- --port 4173
```

No runtime network calls are needed beyond the locally served application assets.
The viewer batches render geometry by assembly and material for performance;
the downloadable asset retains all editable parts.

## Regenerate the assets

Requires Blender 4.3+, Python 3.12, Pillow, and NumPy.

```sh
npm run model
npm run render
```

The generator uses a fixed random seed. It builds all geometry and PBR textures,
exports the GLB, writes `public/models/manifest.json`, and saves the Blender scene.
The render uses 256 samples at 1400 × 1400 with five CPU threads. Denoising is
disabled because this environment's Blender build does not include OpenImageDenoise.

The Blender scene packs its texture resources and can be moved independently.
The GLB also embeds its own texture resources.

## Validation

`npm run build` verifies the production bundle. A browser smoke check loads the
actual GLB, checks for runtime errors, exercises the viewer controls, verifies
the GLB download and PNG capture, and checks desktop/mobile layouts:

```sh
npm run test:smoke
```

The check uses an installed Chromium (`/usr/bin/chromium` by default); set
`CHROMIUM_PATH` for a different executable. Start the dev or preview server first;
set `APP_URL` to its origin if it differs from the default dev port.
