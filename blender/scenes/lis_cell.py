# 固态锂硫电池结构示意图（参考用户给的示意图版式）
# 运行：blender/.venv/bin/python blender/scenes/lis_cell.py [--final]
# 从下到上：锂金属负极 → SEI → 聚合物电解质（含纤维骨架、Li+）→ 硫正极（S + 碳）→ 铝集流体
import os, sys, math, random
import bpy
from mathutils import Vector

# ================= 可调参数 =================
FINAL = "--final" in sys.argv
RES = (3000, 2000) if FINAL else (1200, 800)    # 草图 / 定稿 分辨率
SAMPLES = 256 if FINAL else 32
SEED = 7

W, D = 8.0, 5.0                     # 电池片长、宽
LAYERS = {                          # 名称: (底 z, 顶 z)
    "anode":     (0.00, 0.50),
    "sei":       (0.50, 0.68),
    "spe":       (0.68, 2.30),
    "cathode":   (2.30, 3.10),
    "collector": (3.10, 3.20),
}
COLORS = {                          # 科研常用低饱和配色 (R,G,B)
    "anode":     (0.72, 0.76, 0.80),   # 锂金属：银灰
    "sei":       (0.22, 0.62, 0.60),   # SEI：青绿
    "spe":       (0.66, 0.80, 0.90),   # 聚合物电解质：浅蓝半透明
    "fiber":     (0.85, 0.75, 0.58),   # 纤维骨架：米色
    "sulfur":    (0.93, 0.77, 0.25),   # 硫：黄
    "carbon":    (0.17, 0.17, 0.19),   # 碳：深灰
    "collector": (0.35, 0.37, 0.40),   # 集流体：深灰
    "li_ion":    (0.48, 0.37, 0.66),   # Li+：紫
    "arrow":     (0.80, 0.30, 0.12),   # 快速动力学箭头：橙红
    "text":      (0.08, 0.08, 0.08),
}
LABELS = [                          # (文字, 指向的层, 文字高度位置 z)
    ("Al current collector", "collector", 4.1),
    ("S/C composite cathode", "cathode", 3.3),
    ("Polymer electrolyte", "spe", 2.0),
    ("Fiber scaffold", "fiber", 1.25),
    ("Stable SEI", "sei", 0.55),
    ("Li metal anode", "anode", -0.2),
]
TITLE_KINETICS = [("Fast Li", ""), ("+", "sup"), (" transport", "")]
TITLE_CONVERSION = "Accelerated S conversion"
TEXT_SIZE = 0.30
# 字体：优先 Arial（本机 Windows），云端用字形等宽的 Liberation Sans
FONTS = [r"C:\Windows\Fonts\arial.ttf", "/usr/share/fonts/truetype/msttcorefonts/Arial.ttf",
         "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"]
# ===========================================

random.seed(SEED)
here = os.path.dirname(os.path.abspath(__file__))
out = os.path.join(os.path.dirname(here), "out")
os.makedirs(out, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene


def mat(name, rgb, alpha=1.0, rough=0.5, metal=0.0, emit=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = (*rgb, 1)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metal
    p.inputs["Alpha"].default_value = alpha
    if emit:
        p.inputs["Emission Color"].default_value = (*rgb, 1)
        p.inputs["Emission Strength"].default_value = emit
    return m


def box(name, z0, z1, m):
    bpy.ops.mesh.primitive_cube_add(location=(0, 0, (z0 + z1) / 2))
    o = bpy.context.object
    o.name = name
    o.scale = (W / 2, D / 2, (z1 - z0) / 2)
    o.data.materials.append(m)
    bpy.ops.object.modifier_add(type="BEVEL")
    o.modifiers["Bevel"].width = 0.02
    return o


def spheres(name, pts, r_range, m, segs=16):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segs, ring_count=segs // 2, radius=1)
    proto = bpy.context.object
    proto.data.materials.append(m)
    bpy.ops.object.shade_smooth()
    mesh = proto.data
    bpy.data.objects.remove(proto)
    for i, p in enumerate(pts):
        o = bpy.data.objects.new(f"{name}_{i}", mesh)
        o.location = p
        o.scale = [random.uniform(*r_range)] * 3
        scene.collection.objects.link(o)


def tube(name, pts, radius, m):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = radius
    cu.bevel_resolution = 4
    sp = cu.splines.new("NURBS")
    sp.points.add(len(pts) - 1)
    for p, q in zip(sp.points, pts):
        p.co = (*q, 1)
    sp.use_endpoint_u = True
    sp.order_u = min(4, len(pts))
    o = bpy.data.objects.new(name, cu)
    o.data.materials.append(m)
    scene.collection.objects.link(o)
    return o


def cone(tip, direction, m, r=0.14, h=0.32):
    d = Vector(direction).normalized()
    bpy.ops.mesh.primitive_cone_add(radius1=r, depth=h, location=Vector(tip) - d * h / 2)
    o = bpy.context.object
    o.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    o.data.materials.append(m)


# ---------- 分层 ----------
M = {k: mat(k, v) for k, v in COLORS.items()}
M["anode"] = mat("anode", COLORS["anode"], rough=0.25, metal=0.9)
M["sei"] = mat("sei", COLORS["sei"], alpha=0.85, rough=0.4)
M["spe"] = mat("spe", COLORS["spe"], alpha=0.25, rough=0.1)
M["cathode_matrix"] = mat("cathode_matrix", COLORS["spe"], alpha=0.30, rough=0.2)
M["collector"] = mat("collector", COLORS["collector"], rough=0.35, metal=0.7)
M["arrow"] = mat("arrow", COLORS["arrow"], emit=0.6)
M["text"] = mat("text", COLORS["text"], emit=1.0)
for k in ("text", "arrow", "li_ion"):   # 文字用纯自发光，颜色不受灯光影响
    M[k + "_txt"] = bpy.data.materials.new(k + "_txt")
    M[k + "_txt"].use_nodes = True
    nt = M[k + "_txt"].node_tree
    nt.nodes.remove(nt.nodes["Principled BSDF"])
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*[c ** 2.2 for c in COLORS[k]], 1)  # sRGB→线性，显示为原色
    nt.links.new(em.outputs[0], nt.nodes["Material Output"].inputs[0])

box("Li_anode", *LAYERS["anode"], M["anode"])
box("SEI", *LAYERS["sei"], M["sei"])
box("SPE", *LAYERS["spe"], M["spe"])
box("Cathode_matrix", *LAYERS["cathode"], M["cathode_matrix"])
box("Collector", *LAYERS["collector"], M["collector"])

# ---------- 正极：硫颗粒 + 碳颗粒 ----------
z0, z1 = LAYERS["cathode"]
s_pts, c_pts = [], []
step = 0.26
for ix in range(int(W / step)):
    for iy in range(int(D / step)):
        for iz in range(3):
            p = (-W / 2 + step * (ix + 0.5) + random.uniform(-0.06, 0.06),
                 -D / 2 + step * (iy + 0.5) + random.uniform(-0.06, 0.06),
                 z0 + 0.15 + iz * 0.25 + random.uniform(-0.04, 0.04))
            (s_pts if random.random() < 0.45 else c_pts).append(p)
spheres("S", s_pts, (0.11, 0.15), M["sulfur"])
spheres("C", c_pts, (0.09, 0.12), M["carbon"])

# ---------- 电解质：纤维骨架 + Li+ ----------
zf = (LAYERS["spe"][0] + LAYERS["spe"][1]) / 2 - 0.15
for k in range(46):
    if k % 2 == 0:  # 沿 x 方向
        y = random.uniform(-D / 2 + 0.1, D / 2 - 0.1)
        pts = [(x, y + 0.12 * math.sin(x * 2 + k), zf + random.uniform(-0.12, 0.12))
               for x in [-W / 2 + 0.05 + i * (W - 0.1) / 10 for i in range(11)]]
    else:           # 沿 y 方向
        x = random.uniform(-W / 2 + 0.1, W / 2 - 0.1)
        pts = [(x + 0.12 * math.sin(y * 2 + k), y, zf + random.uniform(-0.12, 0.12))
               for y in [-D / 2 + 0.05 + i * (D - 0.1) / 7 for i in range(8)]]
    tube(f"fiber_{k}", pts, 0.035, M["fiber"])

li_pts = [(random.uniform(-W / 2 + 0.2, W / 2 - 0.2), random.uniform(-D / 2 + 0.2, D / 2 - 0.2),
           random.uniform(LAYERS["spe"][0] + 0.15, LAYERS["spe"][1] - 0.1)) for _ in range(70)]
spheres("Li", li_pts, (0.06, 0.07), M["li_ion"])

# ---------- 快速动力学箭头（前侧面） ----------
yf = -D / 2 - 0.05
for x in (-2.6, -1.3, 0.0):
    pts = [(x, yf, 0.75), (x + 0.25, yf, 1.3), (x - 0.15, yf, 1.8), (x + 0.1, yf, 2.25)]
    tube("arrow_li", pts, 0.05, M["arrow"])
    cone((x + 0.12, yf, 2.55), (0.05, 0, 1), M["arrow"])
# 正极内的转化：环形箭头
ring = [(1.6 + 0.55 * math.cos(t), yf - 0.02, 2.7 + 0.25 * math.sin(t))
        for t in [i * 2 * math.pi * 0.85 / 16 for i in range(17)]]
tube("arrow_conv", ring, 0.045, M["arrow"])
cone(ring[-1], Vector(ring[-1]) - Vector(ring[-2]), M["arrow"], r=0.11, h=0.25)

# ---------- 相机、灯光、世界 ----------
target = Vector((1.9, 0, 1.4))
bpy.ops.object.camera_add(location=(4.5, -13.5, 7.5))
cam = bpy.context.object
cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
cam.data.lens = 34
scene.camera = cam

for loc, e, s in [((-5, -6, 9), 900, 6), ((8, -4, 5), 400, 4), ((0, 6, 6), 250, 6)]:
    bpy.ops.object.light_add(type="AREA", location=loc)
    l = bpy.context.object
    l.data.energy, l.data.size = e, s
    l.rotation_euler = (Vector((0, 0, 1.5)) - l.location).to_track_quat("-Z", "Y").to_euler()

world = bpy.data.worlds.new("W")
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (1, 1, 1, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.6
# 相机直接看到的背景为纯白，照明仍用 0.6 强度
nt = world.node_tree
lp = nt.nodes.new("ShaderNodeLightPath")
white = nt.nodes.new("ShaderNodeBackground")
white.inputs["Color"].default_value = (1, 1, 1, 1)
mix = nt.nodes.new("ShaderNodeMixShader")
nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs[0])
nt.links.new(nt.nodes["Background"].outputs[0], mix.inputs[1])
nt.links.new(white.outputs[0], mix.inputs[2])
nt.links.new(mix.outputs[0], nt.nodes["World Output"].inputs[0])

# ---------- 文字标注（Arial，正对相机） ----------
font = next((bpy.data.fonts.load(f) for f in FONTS if os.path.exists(f)), None)
cam_rot = cam.rotation_euler.copy()


def text(parts, loc, size=TEXT_SIZE, align="LEFT", color=None):
    """parts 可为字符串，或 [(文字, ""/"sup"/"sub"), ...]；上下标用小字号拼接，避免字体缺字。"""
    if isinstance(parts, str):
        parts = [(parts, "")]
    m = color or M["text_txt"]
    objs, x = [], 0.0
    for s, mode in parts:
        cu = bpy.data.curves.new("t", "FONT")
        cu.body = s
        cu.size = size * (0.62 if mode else 1)
        cu.align_y = "CENTER"
        if font:
            cu.font = font
        o = bpy.data.objects.new("label_" + s[:12], cu)
        o.data.materials.append(m)
        scene.collection.objects.link(o)
        bpy.context.view_layer.update()
        dy = {"sup": 0.38, "sub": -0.28}.get(mode, 0) * size
        objs.append((o, x, dy))
        adv = max(v[0] for v in o.bound_box)          # 含前导空格的宽度
        adv += 0.28 * cu.size * (len(s) - len(s.rstrip(" ")))  # 补上末尾空格
        x += adv + 0.02 * size
    shift = {"LEFT": 0, "CENTER": -x / 2, "RIGHT": -x}[align]
    R = cam_rot.to_matrix()
    for o, ox, dy in objs:
        o.rotation_euler = cam_rot
        o.location = Vector(loc) + R @ Vector((ox + shift, dy, 0))


xl = W / 2 + 1.0                   # 标注文字所在 x
for s, layer, zt in LABELS:
    zl = zf if layer == "fiber" else sum(LAYERS[layer]) / 2
    anchor = (W / 2 - 0.05, -D / 2 + 0.3, zl)
    text(s, (xl + 0.15, -D / 2 + 0.3, zt))
    tube("lead_" + layer, [anchor, ((anchor[0] + xl) / 2, anchor[1], zt), (xl, anchor[1], zt)], 0.012, M["text"])

text(TITLE_KINETICS, (-1.3, yf - 0.1, -0.45), align="CENTER", color=M["arrow_txt"])
text(TITLE_CONVERSION, (1.6, yf - 0.1, 4.75), align="CENTER", color=M["arrow_txt"])
text([("S", ""), ("8", "sub"), (" \u2192 Li", ""), ("2", "sub"), ("S", ""), ("n", "sub"),
      (" \u2192 Li", ""), ("2", "sub"), ("S", "")], (1.6, yf - 0.1, 4.3), size=0.26, align="CENTER",
     color=M["arrow_txt"])
text([("Li", ""), ("+", "sup")], (0.4, yf - 0.1, 1.0), size=0.28, color=M["li_ion_txt"])

# ---------- 渲染 ----------
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = SAMPLES
scene.cycles.use_denoising = True
scene.view_settings.view_transform = "Standard"
scene.render.resolution_x, scene.render.resolution_y = RES
scene.render.filepath = os.path.join(out, "lis_cell.png")
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out, "lis_cell.blend"))
print("OK:", scene.render.filepath)
