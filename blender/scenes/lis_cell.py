# 固态锂硫电池结构示意图（参考用户给的示意图版式）
# 运行：blender/.venv/bin/python blender/scenes/lis_cell.py [--final]
# 从下到上（各层之间留缝）：锂金属负极 → 起伏的 SEI → 聚合物电解质块（中间纤维骨架，上下有 Li+ 颗粒，
# 骨架上有分子与 Charge/Discharge 箭头）→ 硫/碳颗粒正极 → 集流体；整片向右上弯曲
import os, sys, math, random
import bpy, bmesh
from mathutils import Vector, noise

# ================= 可调参数 =================
FINAL = "--final" in sys.argv
RES = (3600, 2400) if FINAL else (1500, 1000)   # 草图 / 定稿 分辨率
SAMPLES = 256 if FINAL else 48
SEED = 7

W, D = 9.0, 5.0                     # 电池片长、宽
OPEN = 0.55                         # 张开程度：从左到右，上面的层逐渐抬起、下面的层逐渐下沉，露出截面
MID = 1.90                          # 以这个高度为中心张开（电解质块中部，不动）
LAYERS = {                          # 名称: (底 z, 顶 z)，左端（未张开）时的高度
    "anode":     (-0.45, -0.05),
    "sei":       (-0.05, 0.45),      # SEI 顶面另加起伏
    "spe":       (0.40, 3.40),      # 张开后上下表面分别贴合正极和 SEI      # 聚合物电解质块
    "mat":       (1.20, 1.95),      # 其中的纤维骨架
    "cathode":   (3.47, 4.45),      # 硫/碳颗粒层
    "collector": (4.48, 4.60),
}
SEI_ROUGH = 0.10                    # SEI 起伏幅度
COLORS = {                          # 饱和度较高的论文配色 (R,G,B，sRGB)
    "anode":     (0.80, 0.80, 0.90),   # 锂金属：浅银紫
    "sei":       (0.05, 0.62, 0.62),   # SEI：青绿
    "spe":       (0.60, 0.76, 0.96),   # 电解质：浅蓝半透明
    "fiber":     (0.95, 0.80, 0.55),   # 纤维骨架：米黄
    "sulfur":    (0.98, 0.80, 0.10),   # 硫：亮黄
    "carbon":    (0.12, 0.13, 0.16),   # 碳：深灰
    "collector": (0.12, 0.13, 0.16),   # 集流体：深灰
    "li_ion":    (0.55, 0.30, 0.82),   # Li+：紫色小球
    "sei_part":  (0.92, 0.93, 0.96),   # SEI 中的无机颗粒：银白
    "atom_c":    (0.45, 0.47, 0.52),   # 分子：C 灰
    "atom_n":    (0.15, 0.35, 0.90),   # N 蓝
    "atom_o":    (0.90, 0.15, 0.15),   # O 红
    "charge":    (0.88, 0.25, 0.10),   # Charge 箭头：橙红
    "discharge": (0.10, 0.40, 0.85),   # Discharge 箭头：蓝
    "dynamics":  (0.15, 0.60, 0.20),   # Accelerated dynamics：绿
    "text":      (0.05, 0.05, 0.05),
}
LABELS = [                          # 右侧引线标注：(文字, 指向的层, 文字相对层中心的上下偏移)
    ("Current collector", "collector", 0.55),
    ("S/C cathode", "cathode", 0.05),
    ("Polymer electrolyte", "spe", 0.50),
    ("Fiber scaffold", "mat", -0.10),
    ("Stable SEI", "sei", 0.05),
    ("Li metal anode", "anode", -0.40),
]
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


def lin(rgb):                        # sRGB → 线性，让渲染出的颜色就是上面写的颜色
    return [c ** 2.2 for c in rgb]


CUR = None                           # 当前正在搭的层，决定张开时往上还是往下移


GROUP = {"sei": "anode", "collector": "cathode", "mat": "spe"}   # 这些层跟着所贴合的层一起移动


def bend(x, layer=None):             # 该层在 x 处的上下位移：左端 0，向右二次增大
    layer = layer or CUR
    if layer is None:
        return 0.0
    layer = GROUP.get(layer, layer)
    t = (x + W / 2) / W
    return OPEN * t * t * (sum(LAYERS[layer]) / 2 - MID)


def B(p):                            # 把左端坐标映射到张开后
    return Vector((p[0], p[1], p[2] + bend(p[0])))


def mat(name, rgb, alpha=1.0, rough=0.4, metal=0.0, coat=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = (*lin(rgb), 1)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metal
    p.inputs["Alpha"].default_value = alpha
    p.inputs["Coat Weight"].default_value = coat
    return m


def emit_mat(name, rgb):             # 文字用纯自发光，颜色不受灯光影响
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.remove(nt.nodes["Principled BSDF"])
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*lin(rgb), 1)
    nt.links.new(em.outputs[0], nt.nodes["Material Output"].inputs[0])
    return m


def slab(name, zbot, ztop, m, nx=90, ny=50, smooth=False):
    """封闭的弯曲板：zbot/ztop 是 (x, y) → 未弯曲高度 的函数。"""
    bm = bmesh.new()
    xs = [-W / 2 + W * i / nx for i in range(nx + 1)]
    ys = [-D / 2 + D * j / ny for j in range(ny + 1)]
    top = [[bm.verts.new(B((x, y, ztop(x, y)))) for y in ys] for x in xs]
    bot = [[bm.verts.new(B((x, y, zbot(x, y)))) for y in ys] for x in xs]
    for i in range(nx):
        for j in range(ny):
            bm.faces.new((top[i][j], top[i + 1][j], top[i + 1][j + 1], top[i][j + 1]))
            bm.faces.new((bot[i][j], bot[i][j + 1], bot[i + 1][j + 1], bot[i + 1][j]))
    for i in range(nx):              # 前后侧面
        bm.faces.new((bot[i][0], bot[i + 1][0], top[i + 1][0], top[i][0]))
        bm.faces.new((top[i][ny], top[i + 1][ny], bot[i + 1][ny], bot[i][ny]))
    for j in range(ny):              # 左右侧面
        bm.faces.new((bot[0][j], top[0][j], top[0][j + 1], bot[0][j + 1]))
        bm.faces.new((bot[nx][j + 1], top[nx][j + 1], top[nx][j], bot[nx][j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    if smooth:
        for f in me.polygons:
            f.use_smooth = True
    o = bpy.data.objects.new(name, me)
    o.data.materials.append(m)
    scene.collection.objects.link(o)
    return o


_sphere_mesh = {}


def spheres(name, pts, r_range, m):
    """在未弯曲坐标 pts 处放小球（共用同一个网格，渲染快）。"""
    if m.name not in _sphere_mesh:
        bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=1)
        proto = bpy.context.object
        proto.data.materials.append(m)
        bpy.ops.object.shade_smooth()
        _sphere_mesh[m.name] = proto.data
        bpy.data.objects.remove(proto)
    for i, p in enumerate(pts):
        o = bpy.data.objects.new(f"{name}_{i}", _sphere_mesh[m.name])
        o.location = B(p)
        r = random.uniform(*r_range) if isinstance(r_range, tuple) else r_range
        o.scale = [r] * 3
        scene.collection.objects.link(o)


def tube(name, pts, radius, m, bent=True):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = radius
    cu.bevel_resolution = 4
    cu.use_fill_caps = True
    sp = cu.splines.new("NURBS")
    sp.points.add(len(pts) - 1)
    for p, q in zip(sp.points, pts):
        p.co = (*(B(q) if bent else Vector(q)), 1)
    sp.use_endpoint_u = True
    sp.order_u = min(4, len(pts))
    o = bpy.data.objects.new(name, cu)
    o.data.materials.append(m)
    scene.collection.objects.link(o)
    return o


def cone(tip, direction, m, r=0.13, h=0.30):
    d = Vector(direction).normalized()
    bpy.ops.mesh.primitive_cone_add(radius1=r, depth=h, location=Vector(tip) - d * h / 2)
    o = bpy.context.object
    o.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    o.data.materials.append(m)


def arc_arrow(name, p0, p1, height, m, radius=0.075):
    """从 p0 到 p1 的拱形箭头（未弯曲坐标），箭头在 p1。"""
    p0, p1 = Vector(p0), Vector(p1)
    pts = [p0.lerp(p1, t) + Vector((0, 0, height * 4 * t * (1 - t))) for t in [i / 12 for i in range(13)]]
    tube(name, pts[:-1], radius, m)
    a, b = B(pts[-3]), B(pts[-1])
    cone(b, b - a, m, r=0.18, h=0.40)


# ---------- 材质 ----------
M = {
    "anode": mat("anode", COLORS["anode"], rough=0.3, metal=0.6),
    "sei": mat("sei", COLORS["sei"], rough=0.35, coat=0.5),
    "spe": mat("spe", COLORS["spe"], alpha=0.22, rough=0.05, coat=1.0),
    "fiber": mat("fiber", COLORS["fiber"], rough=0.55),
    "sulfur": mat("sulfur", COLORS["sulfur"], rough=0.3, coat=0.6),
    "carbon": mat("carbon", COLORS["carbon"], rough=0.25, coat=0.6),
    "collector": mat("collector", COLORS["collector"], rough=0.3, metal=0.8),
    "li_ion": mat("li_ion", COLORS["li_ion"], rough=0.2, coat=0.8),
    "sei_part": mat("sei_part", COLORS["sei_part"], rough=0.15, metal=0.5),
    "atom_c": mat("atom_c", COLORS["atom_c"], rough=0.3, coat=0.5),
    "atom_n": mat("atom_n", COLORS["atom_n"], rough=0.3, coat=0.5),
    "atom_o": mat("atom_o", COLORS["atom_o"], rough=0.3, coat=0.5),
    "bond": mat("bond", (0.70, 0.70, 0.72), rough=0.4),
    "charge": mat("charge", COLORS["charge"], rough=0.4),
    "discharge": mat("discharge", COLORS["discharge"], rough=0.4),
    "lead": emit_mat("lead", COLORS["text"]),
}
T = {k: emit_mat(k + "_txt", COLORS[k]) for k in ("text", "charge", "discharge", "dynamics")}

# ---------- 负极 + 起伏的 SEI ----------
CUR = "anode"
slab("Li_anode", lambda x, y: LAYERS["anode"][0], lambda x, y: LAYERS["anode"][1], M["anode"])
bumps = [(random.uniform(-W / 2, W / 2), random.uniform(-D / 2, D / 2), random.uniform(0.25, 0.6),
          random.choice([1, 1, -1]) * random.uniform(0.6, 1.0)) for _ in range(45)]


def sei_top(x, y):
    h = LAYERS["sei"][1] + 0.35 * SEI_ROUGH * noise.noise(Vector((x * 1.3, y * 1.3, 0.5)))
    for bx, by, r, s in bumps:       # 凸起 (+) / 凹陷 (−)
        h += SEI_ROUGH * s * math.exp(-((x - bx) ** 2 + (y - by) ** 2) / (r * r))
    return h


CUR = "sei"
slab("SEI", lambda x, y: LAYERS["sei"][0], sei_top, M["sei"], nx=180, ny=100, smooth=True)
spheres("SEI_particle", [(x, y, sei_top(x, y) - 0.03) for x, y in
                         [(random.uniform(-W / 2 + 0.2, W / 2 - 0.2), random.uniform(-D / 2 + 0.2, D / 2 - 0.2))
                          for _ in range(70)]], (0.045, 0.06), M["sei_part"])

# ---------- 聚合物电解质块 + 纤维骨架 ----------
CUR = "spe"
CUR = None                           # 电解质块直接用最终高度：底面贴 SEI 顶面，顶面贴正极底面
slab("SPE", lambda x, y: sei_top(x, y) + bend(x, "sei") + 0.005,
     lambda x, y: LAYERS["cathode"][0] + bend(x, "cathode"), M["spe"], nx=120, ny=60)
CUR = "spe"
m0, m1 = LAYERS["mat"]
for k in range(280):
    zc = random.uniform(m0, m1)
    if k % 2 == 0:  # 沿 x 方向
        y = random.uniform(-D / 2 + 0.03, D / 2 - 0.03)
        pts = [(x, y + 0.10 * math.sin(x * 2.5 + k), zc + 0.07 * math.sin(x * 3 + k * 1.7))
               for x in [-W / 2 + 0.03 + i * (W - 0.06) / 16 for i in range(17)]]
    else:           # 沿 y 方向
        x = random.uniform(-W / 2 + 0.03, W / 2 - 0.03)
        pts = [(x + 0.10 * math.sin(y * 2.5 + k), y, zc + 0.07 * math.sin(y * 3 + k * 1.7))
               for y in [-D / 2 + 0.03 + i * (D - 0.06) / 9 for i in range(10)]]
    tube(f"fiber_{k}", pts, 0.028, M["fiber"])

# Li+ 颗粒：骨架上方和下方都有
s0, s1 = LAYERS["spe"]
rand_xy = lambda: (random.uniform(-W / 2 + 0.2, W / 2 - 0.2), random.uniform(-D / 2 + 0.2, D / 2 - 0.2))
CUR = None                           # Li+ 填满张开后的电解质（用最终高度）
li_pts = []
for k in range(140):
    x, y = rand_xy()
    if k % 2:
        li_pts.append((x, y, random.uniform(sei_top(x, y) + bend(x, "sei") + 0.12, m0 - 0.1)))
    else:
        li_pts.append((x, y, random.uniform(m1 + 0.1, LAYERS["cathode"][0] + bend(x, "cathode") - 0.1)))
# 分子、箭头和文字所在的前方区域留空，避免遮挡
li_pts = [p for p in li_pts if not (-4.0 < p[0] < 3.6 and p[1] < -D / 2 + 2.2 and p[2] > m1 - 0.05)
          and not (-4.0 < p[0] < 2.0 and p[2] > m1 + 0.75)]          # 文字后方整条带
spheres("Li", li_pts, (0.065, 0.075), M["li_ion"])
CUR = "spe"

# ---------- 骨架上的分子（球棍模型）与动力学箭头 ----------
yf = -D / 2 + 0.55                   # 放在靠前的位置，便于看清


def molecule(cx, cz, rot):
    """两个相连的六元环 + 杂原子，大致示意聚合物链段。"""
    atoms = []
    for ring, (ox, oz) in enumerate([(0, 0), (0.62, 0.18)]):
        for i in range(6):
            t = rot + i * math.pi / 3
            atoms.append((cx + ox + 0.22 * math.cos(t), yf + 0.08 * math.sin(t * 2), cz + oz + 0.22 * math.sin(t)))
    hetero = [(cx - 0.45, yf, cz - 0.10, "atom_o"), (cx + 1.05, yf, cz + 0.32, "atom_n"),
              (cx + 0.30, yf, cz + 0.45, "atom_o")]
    bonds = [(i, (i + 1) % 6) for i in range(6)] + [(6 + i, 6 + (i + 1) % 6) for i in range(6)] + [(0, 9)]
    for a, b in bonds:
        tube("bond", [atoms[a], atoms[b]], 0.025, M["bond"])
    for hx, hy, hz, kind in hetero:   # 杂原子连到最近的环原子
        near = min(atoms, key=lambda p: (p[0] - hx) ** 2 + (p[2] - hz) ** 2)
        tube("bond", [near, (hx, hy, hz)], 0.025, M["bond"])
        spheres("hetero", [(hx, hy, hz)], 0.085, M[kind])
    spheres("atom", atoms, 0.055, M["atom_c"])


zm = m1 + 0.32
for cx, rot in [(-2.9, 0.2), (-0.6, 0.6), (1.7, 0.1)]:
    molecule(cx, zm, rot)

arc_arrow("charge", (-0.70, yf - 0.1, zm + 0.40), (-2.60, yf - 0.1, zm + 0.35), 0.38, M["charge"])
arc_arrow("discharge", (0.50, yf - 0.1, zm + 0.40), (2.40, yf - 0.1, zm + 0.40), 0.38, M["discharge"])

# ---------- 正极颗粒 + 集流体 ----------
CUR = "cathode"
c0, c1 = LAYERS["cathode"]
s_pts, c_pts = [], []
step = 0.24
for ix in range(int(W / step)):
    for iy in range(int(D / step)):
        for iz in range(4):             # 颗粒层数
            p = (-W / 2 + step * (ix + 0.5) + random.uniform(-0.05, 0.05),
                 -D / 2 + step * (iy + 0.5) + random.uniform(-0.05, 0.05),
                 c0 + 0.13 + iz * 0.24 + random.uniform(-0.03, 0.03))
            (s_pts if random.random() < 0.5 else c_pts).append(p)
spheres("S", s_pts, (0.13, 0.15), M["sulfur"])     # 硫：大
spheres("C", c_pts, (0.08, 0.10), M["carbon"])     # 碳：小
CUR = "collector"
slab("Collector", lambda x, y: LAYERS["collector"][0], lambda x, y: LAYERS["collector"][1], M["collector"],
     nx=60, ny=10)

# ---------- 相机、灯光、世界 ----------
target = Vector((1.1, 0, 1.6))
bpy.ops.object.camera_add(location=(8.0, -15.0, 5.2))
cam = bpy.context.object
cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
cam.data.lens = 33
scene.camera = cam

for loc, e, s in [((-6, -8, 10), 1500, 5), ((9, -6, 6), 600, 4), ((2, 8, 8), 900, 6)]:
    bpy.ops.object.light_add(type="AREA", location=loc)
    l = bpy.context.object
    l.data.energy, l.data.size = e, s
    l.rotation_euler = (Vector((0, 0, 1.5)) - l.location).to_track_quat("-Z", "Y").to_euler()

world = bpy.data.worlds.new("W")
scene.world = world
world.use_nodes = True
nt = world.node_tree
nt.nodes["Background"].inputs["Color"].default_value = (1, 1, 1, 1)
nt.nodes["Background"].inputs["Strength"].default_value = 0.35
lp = nt.nodes.new("ShaderNodeLightPath")   # 相机看到的背景为纯白，照明只用 0.35
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


def text(parts, loc, size=TEXT_SIZE, align="LEFT", color=None, pull=1.0):
    """parts 可为字符串，或 [(文字, ""/"sup"/"sub"), ...]；上下标用小字号拼接，避免字体缺字。loc 为最终坐标。
    pull<1 时沿视线把文字拉近相机并等比缩小：画面上位置、大小不变，但保证挡在颗粒前面。"""
    loc = cam.location + (Vector(loc) - cam.location) * pull
    size *= pull
    if isinstance(parts, str):
        parts = [(parts, "")]
    m = color or T["text"]
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


xr = W / 2                           # 右侧引线标注
for s, layer, dz in LABELS:
    CUR = "spe" if layer == "mat" else layer
    zl = sum(LAYERS[layer]) / 2
    anchor = B((xr - 0.02, -D / 2 + 0.02, zl))
    end = anchor + Vector((1.5, 0, dz))
    tube("lead_" + layer, [anchor, anchor + Vector((0.75, 0, dz * 0.8)), end], 0.012, M["lead"], bent=False)
    text(s, end + Vector((0.12, 0, 0)))

CUR = "spe"
front = -D / 2 - 0.1                 # 图中文字放在电解质块前面
text("Charge", B((-3.0, front, zm + 0.30)), color=T["charge"], align="RIGHT", pull=0.6)
text("Discharge", B((2.6, front, zm + 0.75)), color=T["discharge"], align="LEFT", pull=0.6)
text("Accelerated dynamics", B((-0.3, front, zm + 1.12)), color=T["dynamics"], align="CENTER", pull=0.6)
text([("Li", ""), ("+", "sup")], B((-3.9, front, s0 + 0.45)), size=0.28)

# ---------- 图例（底部一行，正对相机） ----------
CUR = None
LEGEND = [("S", "sulfur", 0.14), ("C", "carbon", 0.09), ([("Li", ""), ("+", "sup")], "li_ion", 0.07),
          ("SEI particle", "sei_part", 0.06), ("Polymer C", "atom_c", 0.055), ("N", "atom_n", 0.085),
          ("O", "atom_o", 0.085)]
GAPS = [0.9, 0.9, 1.0, 1.9, 1.8, 0.8, 0.8]          # 每项占的宽度
R = cam_rot.to_matrix()
origin = Vector((-W / 2 - 0.3, -D / 2 - 1.5, LAYERS["anode"][0] - 1.9))
dx = 0.0
for (name, key, r), g in zip(LEGEND, GAPS):
    pos = origin + R @ Vector((dx, 0, 0))
    o = bpy.data.objects.new("legend", _sphere_mesh.get(M[key].name) or _sphere_mesh[M["li_ion"].name])
    if M[key].name not in _sphere_mesh:
        spheres("legend_tmp", [(0, 0, -50)], 0.01, M[key])
        o.data = _sphere_mesh[M[key].name]
    o.location, o.scale = pos, [r * 1.4] * 3
    scene.collection.objects.link(o)
    text(name, pos + R @ Vector((0.25, 0, 0)), size=0.24)
    dx += g

# ---------- 渲染 ----------
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = SAMPLES
scene.cycles.use_denoising = True
scene.cycles.transparent_max_bounces = 16
scene.view_settings.view_transform = "Standard"
scene.view_settings.look = "None"
scene.render.resolution_x, scene.render.resolution_y = RES
scene.render.filepath = os.path.join(out, "lis_cell.png")
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out, "lis_cell.blend"))
print("OK:", scene.render.filepath)
