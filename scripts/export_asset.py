"""Refresh the GLB from the editable blend without including the studio."""
import bpy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
root=bpy.data.objects.get('NOMAD MK.07 · Expedition chassis')
assert root, 'Mech root missing'
bpy.ops.object.select_all(action='DESELECT')
root.select_set(True)
for obj in root.children_recursive:
    obj.select_set(True)
bpy.context.view_layer.objects.active=root
bpy.ops.export_scene.gltf(filepath=str(ROOT/'public/models/nomad-mk07.glb'),export_format='GLB',use_selection=True,export_yup=True,export_apply=True,export_materials='EXPORT')
