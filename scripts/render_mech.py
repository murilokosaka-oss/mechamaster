"""Render the saved studio camera to a stable, frame-number-free file path."""
import bpy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
bpy.context.scene.render.filepath=str(ROOT/'artifacts/nomad-hero.png')
bpy.ops.render.render(write_still=True)
