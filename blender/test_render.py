# 云端 Blender 自检：搭一个最简单的场景并渲染，确认 bpy 能用、能出图。
# 运行：blender/.venv/bin/python blender/test_render.py
import os
import bpy

here = os.path.dirname(os.path.abspath(__file__))
out = os.path.join(here, "out")
os.makedirs(out, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=(0, 0, 1))
bpy.ops.mesh.primitive_plane_add(size=10)
bpy.ops.object.light_add(type="SUN", location=(4, -4, 8))
bpy.context.object.data.energy = 3
bpy.ops.object.camera_add(location=(6, -6, 4), rotation=(1.1, 0, 0.785))
scene.camera = bpy.context.object

scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 32
scene.render.resolution_x, scene.render.resolution_y = 640, 480
scene.render.filepath = os.path.join(out, "test.png")
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out, "test.blend"))
print("OK:", scene.render.filepath)
