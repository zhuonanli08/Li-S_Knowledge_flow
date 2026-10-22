# 固态锂硫电池结构示意图（参考用户给的示意图版式）
# 运行：blender/.venv/bin/python blender/scenes/lis_cell.py [--final]
# 从下到上（各层之间留缝）：锂金属负极 → 起伏的 SEI → 聚合物电解质块（中间纤维骨架，上下有 Li+ 颗粒，
# 骨架上有分子与 Charge/Discharge 箭头）→ 硫/碳颗粒正极 → 集流体；整片向右上弯曲
import os, sys, math, random, colorsys
import bpy, bmesh
from mathutils import Vector, noise

# ================= 可调参数 =================
FINAL = "--final" in sys.argv
RES = (3600, 2400) if FINAL else (1500, 1000)   # 草图 / 定稿 分辨率
SAMPLES = 256 if FINAL else 48
SEED = 7

W, D = 7.0, 7.0                     # 电池片长（左右）、宽（前后）
MX = 1.0                            # 骨架上的分子与充放电示意整体往右移多少
S_RATIO = 0.25                      # 正极中硫颗粒的占比
S_RATIO_BOTTOM = 0.06               # 正极最下层（接触电解质）硫的占比：碳远多于硫，这层看起来更暗
OPEN_TOP = 0.35                     # 正极侧向上弯的比例（1 = 和负极侧一样）
OPEN = 0.55                         # 张开程度：从左到右，上面的层逐渐抬起、下面的层逐渐下沉，露出截面
MID = 1.90                          # 以这个高度为中心张开（电解质块中部，不动）
LAYERS = {                          # 名称: (底 z, 顶 z)，左端（未张开）时的高度
    "anode":     (-0.45, -0.05),
    "sei":       (-0.05, 0.13),      # SEI：近似 2D 薄膜，贴在负极上，只保留轻微起伏
    "spe":       (0.40, 3.40),      # 张开后上下表面分别贴合正极和 SEI      # 聚合物电解质块
    "mat":       (1.20, 1.95),      # 其中的纤维骨架
    "cathode":   (3.47, 4.45),      # 硫/碳颗粒层
    "collector": (4.48, 4.60),
}
SEI_ROUGH = 0.10
VIEW_ROT = 10                       # 视角绕竖直轴转的角度（度），正值 = 相机往右转、露出更多右侧截面
SAT_BOOST = 1.35                    # 颗粒/各层的饱和度倍数
CONTRAST = 1.15                     # 颗粒/各层的明暗对比倍数
BG_COLOR = (0.84, 0.85, 0.95)       # 背景色（参考原图的浅蓝紫）
REFLECT_ENV = 1.0                   # 反射环境亮度：越大，金属和高光越亮
SPE_ALPHA = 0.13                    # 电解质不透明度（越小越透明）
LI_LOWER = 40                       # 纤维骨架下方的 Li+ 数量（大部分放在背光的右后方）                    # SEI 起伏幅度
COLORS = {                          # 参考原图：整体低饱和、明暗接近 (R,G,B，sRGB)
    "anode":     (0.80, 0.80, 0.90),   # 锂金属：浅灰紫
    "sei":       (0.33, 0.64, 0.66),   # SEI：灰青绿
    "spe":       (0.45, 0.78, 1.00),   # 电解质：浅蓝（饱和）
    "fiber":     (0.96, 0.80, 0.52),   # 纤维骨架：暖奶油色（饱和度提高）
    "sulfur":    (0.82, 0.68, 0.26),   # 硫：哑光金黄
    "carbon":    (0.27, 0.29, 0.34),   # 碳：石板灰
    "collector": (0.20, 0.22, 0.28),   # 集流体：深蓝灰
    "li_ion":    (0.50, 0.33, 0.88),   # Li+：紫（饱和度提高）
    "sei_part":  (0.40, 0.38, 0.55),   # SEI 中的颗粒：暗紫灰（原图 SEI 里的深色颗粒）
    "atom_c":    (0.55, 0.57, 0.62),   # 分子：C 灰
    "atom_n":    (0.35, 0.50, 0.82),   # N 蓝
    "atom_o":    (0.82, 0.38, 0.35),   # O 砖红
    "charge":    (0.84, 0.42, 0.22),   # Charge：橙
    "discharge": (0.30, 0.50, 0.80),   # Discharge：蓝
    "dynamics":  (0.42, 0.63, 0.32),   # Accelerated dynamics：草绿
    "text":      (0.15, 0.15, 0.18),
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


def vivid(rgb):                      # 提高饱和度与对比度（亮的更亮、暗的更暗）
    h, l, sat = colorsys.rgb_to_hls(*rgb)
    sat = min(1.0, sat * SAT_BOOST)
    l = min(1.0, max(0.0, 0.5 + (l - 0.5) * CONTRAST))
    return colorsys.hls_to_rgb(h, l, sat)


CUR = None                           # 当前正在搭的层，决定张开时往上还是往下移


GROUP = {"sei": "anode", "collector": "cathode", "mat": "spe"}   # 这些层跟着所贴合的层一起移动


def bend(x, layer=None):             # 该层在 x 处的上下位移：左端 0，向右二次增大
    layer = layer or CUR
    if layer is None:
        return 0.0
    layer = GROUP.get(layer, layer)
    t = (x + W / 2) / W
    d = sum(LAYERS[layer]) / 2 - MID
    return OPEN * t * t * d * (OPEN_TOP if d > 0 else 1.0)


def B(p):                            # 把左端坐标映射到张开后
    return Vector((p[0], p[1], p[2] + bend(p[0])))


def mat(name, rgb, alpha=1.0, rough=0.4, metal=0.0, coat=0.0, glow=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = (*lin(vivid(rgb)), 1)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metal
    p.inputs["Alpha"].default_value = alpha
    p.inputs["Coat Weight"].default_value = coat
    if glow:                         # 微弱自发光：提亮暗部、减少阴影
        p.inputs["Emission Color"].default_value = (*lin(vivid(rgb)), 1)
        p.inputs["Emission Strength"].default_value = glow
    return m


SEI_DARK = (0.45, 0.48, 0.50)       # SEI 背光处：灰
SEI_LIGHT = (0.10, 0.72, 0.70)      # SEI 迎光处：蓝绿
SEI_ALPHA = 0.78                    # SEI 顶部的不透明度（底部为 1，往上渐变到这个值）


def sei_mat():
    """SEI：按表面朝向主光的程度，从灰黑（背光）渐变到蓝绿（迎光），并带一点透明。"""
    m = bpy.data.materials.new("sei")
    m.use_nodes = True
    nt = m.node_tree
    p = nt.nodes["Principled BSDF"]
    p.inputs["Roughness"].default_value = 0.35      # 较粗糙：整体柔和光泽，不出现小块刺眼白斑
    p.inputs["Coat Weight"].default_value = 0.6
    p.inputs["Coat Roughness"].default_value = 0.30
    p.inputs["Alpha"].default_value = SEI_ALPHA
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    dot = nt.nodes.new("ShaderNodeVectorMath")
    dot.operation = "DOT_PRODUCT"
    dot.inputs[1].default_value = Vector((-6, -8, 8.5)).normalized()   # 指向主光
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.15
    ramp.color_ramp.elements[0].color = (*lin(SEI_DARK), 1)
    ramp.color_ramp.elements[1].position = 0.65
    ramp.color_ramp.elements[1].color = (*lin(SEI_LIGHT), 1)
    nt.links.new(geo.outputs["Normal"], dot.inputs[0])
    nt.links.new(dot.outputs["Value"], ramp.inputs["Fac"])
    # 上下渐变：与负极接触的底部为蓝绿、不透明；往上按受光过渡（背光处灰），并逐渐透明
    attr = nt.nodes.new("ShaderNodeAttribute")
    attr.attribute_name = "hfrac"
    mixc = nt.nodes.new("ShaderNodeMix")
    mixc.data_type = "RGBA"
    mixc.inputs["A"].default_value = (*lin(SEI_LIGHT), 1)   # 与负极接触的底部：蓝绿
    nt.links.new(attr.outputs["Fac"], mixc.inputs["Factor"])
    nt.links.new(ramp.outputs["Color"], mixc.inputs["B"])
    nt.links.new(mixc.outputs["Result"], p.inputs["Base Color"])
    nt.links.new(mixc.outputs["Result"], p.inputs["Emission Color"])   # 微弱自发光，整体更亮
    p.inputs["Emission Strength"].default_value = 0.06
    mra = nt.nodes.new("ShaderNodeMapRange")
    mra.inputs["To Min"].default_value = 1.0
    mra.inputs["To Max"].default_value = SEI_ALPHA
    nt.links.new(attr.outputs["Fac"], mra.inputs["Value"])
    nt.links.new(mra.outputs["Result"], p.inputs["Alpha"])
    return m


def tint_mat(name, rgb):
    """电解质：像有色玻璃一样只给透过的光染色，不叠加白色雾层；再加一点镜面反射显出轮廓。"""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    p = nt.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = (*lin(rgb), 1)
    p.inputs["Roughness"].default_value = 0.05
    p.inputs["Coat Weight"].default_value = 1.0
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    tint = [1 - SPE_ALPHA * 0.9 * (1 - c) for c in lin(rgb)]        # 染色强度随 SPE_ALPHA 变
    tr.inputs["Color"].default_value = (*tint, 1)
    mix = nt.nodes.new("ShaderNodeMixShader")
    mix.inputs[0].default_value = SPE_ALPHA * 0.5
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(p.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], nt.nodes["Material Output"].inputs[0])
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


def slab(name, zbot, ztop, m, nx=90, ny=50, smooth=False, cap_mat=None):
    """封闭的弯曲板：zbot/ztop 是 (x, y) → 未弯曲高度 的函数。cap_mat：顶面和底面单独用的材质。"""
    bm = bmesh.new()
    xs = [-W / 2 + W * i / nx for i in range(nx + 1)]
    ys = [-D / 2 + D * j / ny for j in range(ny + 1)]
    top = [[bm.verts.new(B((x, y, ztop(x, y)))) for y in ys] for x in xs]
    bot = [[bm.verts.new(B((x, y, zbot(x, y)))) for y in ys] for x in xs]
    for i in range(nx):
        for j in range(ny):
            bm.faces.new((top[i][j], top[i + 1][j], top[i + 1][j + 1], top[i][j + 1])).material_index = 1 if cap_mat else 0
            bm.faces.new((bot[i][j], bot[i][j + 1], bot[i + 1][j + 1], bot[i + 1][j])).material_index = 1 if cap_mat else 0
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
    hf = me.attributes.new("hfrac", "FLOAT", "POINT")   # 高度比例：顶面 1，底面 0（顶面顶点先建）
    n_top = (nx + 1) * (ny + 1)
    hf.data.foreach_set("value", [1.0] * n_top + [0.0] * (len(me.vertices) - n_top))
    if smooth:
        for f in me.polygons:
            f.use_smooth = True
    o = bpy.data.objects.new(name, me)
    o.data.materials.append(m)
    if cap_mat:
        o.data.materials.append(cap_mat)
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
SHINY = dict(rough=0.15, metal=0.3, coat=1.0)   # 各类原子统一：光滑 + 清漆 + 少量金属感
M = {
    "anode": mat("anode", (0.95, 0.96, 1.00), rough=0.05, metal=1.0, coat=1.0),  # 锂金属：亮白金属、强高光
    "sei": sei_mat(),
    "spe": tint_mat("spe", COLORS["spe"]),
    "fiber": mat("fiber", COLORS["fiber"], rough=0.25, coat=0.7),        # 带光泽
    "sulfur": mat("sulfur", COLORS["sulfur"], **SHINY),
    "carbon": mat("carbon", COLORS["carbon"], **SHINY),
    "collector": mat("collector", COLORS["collector"], rough=0.3, metal=0.8),
    "li_ion": mat("li_ion", COLORS["li_ion"], **SHINY),
    "sei_part": mat("sei_part", COLORS["sei_part"], **SHINY),
    "atom_c": mat("atom_c", COLORS["atom_c"], **SHINY),
    "atom_n": mat("atom_n", COLORS["atom_n"], **SHINY),
    "atom_o": mat("atom_o", COLORS["atom_o"], **SHINY),
    "bond": mat("bond", (0.70, 0.70, 0.72), rough=0.4),
    "charge": mat("charge", COLORS["charge"], rough=0.4),
    "discharge": mat("discharge", COLORS["discharge"], rough=0.4),
    "lead": emit_mat("lead", COLORS["text"]),
    "clear": mat("clear", (1, 1, 1), alpha=0.0),
}
T = {k: emit_mat(k + "_txt", [c * 0.8 for c in COLORS[k]]) for k in ("charge", "discharge", "dynamics")}  # 文字比箭头深一些，更清楚
T["text"] = emit_mat("text_txt", COLORS["text"])

# ---------- 负极 + 起伏的 SEI ----------
CUR = "anode"
bumps = [(random.uniform(-W / 2, W / 2), random.uniform(-D / 2, D / 2), random.uniform(0.35, 0.8),
          random.choice([1, 1, -1]) * random.uniform(0.6, 1.0)) for _ in range(45)]


def sei_top(x, y):
    h = LAYERS["sei"][1] - 0.05 + 0.6 * SEI_ROUGH * noise.noise(Vector((x * 1.3, y * 1.3, 0.5)))
    for bx, by, r, s in bumps:       # 凸起 (+) / 凹陷 (−)
        h += SEI_ROUGH * s * math.exp(-((x - bx) ** 2 + (y - by) ** 2) / (r * r))
    return h


CUR = "anode"                        # 负极顶面跟着 SEI 底面起伏，两者处处贴合
slab("Li_anode", lambda x, y: LAYERS["anode"][0], lambda x, y: sei_top(x, y) - 0.03, M["anode"], nx=180, ny=100,
     smooth=True)
CUR = "sei"
slab("SEI", lambda x, y: sei_top(x, y) - 0.03, sei_top, M["sei"], nx=180, ny=100,
     smooth=True)                     # 底面跟着顶面走：整层只有约 0.03 厚
spheres("SEI_particle", [(x, y, sei_top(x, y) - 0.03) for x, y in
                         [(random.uniform(-W / 2 + 0.2, W / 2 - 0.2), random.uniform(-D / 2 + 0.2, D / 2 - 0.2))
                          for _ in range(90)]], (0.06, 0.09), M["sei_part"])

# ---------- 聚合物电解质块 + 纤维骨架 ----------
CUR = "spe"
CUR = None                           # 电解质块直接用最终高度：底面贴 SEI 顶面，顶面贴正极底面
slab("SPE", lambda x, y: sei_top(x, y) + bend(x, "sei") + 0.005,
     lambda x, y: LAYERS["cathode"][0] + bend(x, "cathode"), M["spe"], nx=120, ny=60,
     cap_mat=M["clear"])              # 与正极、负极接触的上下两面完全透明，只有侧面有颜色
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
for k in range(70):                  # 骨架上方
    x, y = rand_xy()
    li_pts.append((x, y, random.uniform(m1 + 0.1, LAYERS["cathode"][0] + bend(x, "cathode") - 0.1)))
for k in range(LI_LOWER):            # 骨架下方：约 3/4 放在背光的右后方（阴影面）
    if random.random() < 0.75:
        x, y = random.uniform(0.0, W / 2 - 0.2), random.uniform(-0.3, D / 2 - 0.2)
    else:
        x, y = rand_xy()
    li_pts.append((x, y, random.uniform(sei_top(x, y) + bend(x, "sei") + 0.12, m0 - 0.1)))
# 分子、箭头和文字所在的前方区域留空，避免遮挡
li_pts = [p for p in li_pts if not (-4.0 + MX < p[0] < 3.6 + MX and p[1] < -D / 2 + 2.2 and p[2] > m1 - 0.05)
          and not (-4.0 + MX < p[0] < 2.0 + MX and p[2] > m1 + 0.75)]          # 文字后方整条带
spheres("Li", li_pts, (0.08, 0.09), M["li_ion"])
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
        tube("bond", [atoms[a], atoms[b]], 0.032, M["bond"])
    for hx, hy, hz, kind in hetero:   # 杂原子连到最近的环原子
        near = min(atoms, key=lambda p: (p[0] - hx) ** 2 + (p[2] - hz) ** 2)
        tube("bond", [near, (hx, hy, hz)], 0.032, M["bond"])
        spheres("hetero", [(hx, hy, hz)], 0.11, M[kind])
    spheres("atom", atoms, 0.075, M["atom_c"])


zm = m1 + 0.32
for cx, rot in [(-2.9 + MX, 0.2), (-0.6 + MX, 0.6), (1.7 + MX, 0.1)]:
    molecule(cx, zm, rot)

arc_arrow("charge", (-0.70 + MX, yf - 0.1, zm + 0.40), (-2.60 + MX, yf - 0.1, zm + 0.35), 0.38, M["charge"])
arc_arrow("discharge", (0.50 + MX, yf - 0.1, zm + 0.40), (2.40 + MX, yf - 0.1, zm + 0.40), 0.38, M["discharge"])

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
                 LAYERS["collector"][0] - 0.14 - (3 - iz) * 0.24 + random.uniform(-0.02, 0.0))   # 最上层顶到集流体底面
            m_ = 0.17                   # 颗粒不超出集流体边缘（最大半径 0.15 + 余量）
            p = (min(max(p[0], -W / 2 + m_), W / 2 - m_), min(max(p[1], -D / 2 + m_), D / 2 - m_), p[2])
            ratio = S_RATIO_BOTTOM if iz == 0 else S_RATIO
            (s_pts if random.random() < ratio else c_pts).append(p)
spheres("S", s_pts, (0.13, 0.15), M["sulfur"])     # 硫：大
spheres("C", c_pts, (0.08, 0.10), M["carbon"])     # 碳：小
CUR = "collector"
slab("Collector", lambda x, y: LAYERS["collector"][0], lambda x, y: LAYERS["collector"][1], M["collector"],
     nx=60, ny=10)

# ---------- 相机、灯光、世界 ----------
target = Vector((1.1, 0, 1.4))
a = math.radians(VIEW_ROT)           # 绕目标点的竖直轴旋转相机
v = Vector((8.0, -15.0, 5.2)) - target
bpy.ops.object.camera_add(location=target + Vector((v.x * math.cos(a) - v.y * math.sin(a),
                                                    v.x * math.sin(a) + v.y * math.cos(a), v.z)))
cam = bpy.context.object
cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
cam.data.lens = 30
scene.camera = cam

for loc, e, s in [((-6, -8, 10), 1400, 6), ((9, -6, 6), 450, 6), ((2, 8, 8), 900, 6)]:   # 主光略强、补光略弱 → 对比更强
    bpy.ops.object.light_add(type="AREA", location=loc)
    l = bpy.context.object
    l.data.energy, l.data.size = e, s
    l.rotation_euler = (Vector((0, 0, 1.5)) - l.location).to_track_quat("-Z", "Y").to_euler()

world = bpy.data.worlds.new("W")
scene.world = world
world.use_nodes = True
nt = world.node_tree
nt.nodes["Background"].inputs["Color"].default_value = (1, 1, 1, 1)
nt.nodes["Background"].inputs["Strength"].default_value = 0.45
lp = nt.nodes.new("ShaderNodeLightPath")   # 相机看到的背景为纯白，照明只用 0.35
white = nt.nodes.new("ShaderNodeBackground")
white.inputs["Color"].default_value = (*lin(BG_COLOR), 1)   # 相机直接看到的背景：浅蓝紫
mix = nt.nodes.new("ShaderNodeMixShader")
nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs[0])
nt.links.new(nt.nodes["Background"].outputs[0], mix.inputs[1])
nt.links.new(white.outputs[0], mix.inputs[2])
# 反射里看到的环境更亮（只影响高光/金属反射，不改照明和背景）
glossy_bg = nt.nodes.new("ShaderNodeBackground")      # 白色镀铬式反射环境：整体亮白，地平线处一条细暗带，产生亮暗条纹
glossy_bg.inputs["Strength"].default_value = REFLECT_ENV
tc = nt.nodes.new("ShaderNodeTexCoord")
sep = nt.nodes.new("ShaderNodeSeparateXYZ")
mrz = nt.nodes.new("ShaderNodeMapRange")
mrz.inputs["From Min"].default_value = -1.0
env_ramp = nt.nodes.new("ShaderNodeValToRGB")
cr = env_ramp.color_ramp
cr.elements[0].position, cr.elements[0].color = 0.0, (1.2, 1.2, 1.25, 1)     # 地平线以下也保持亮白，负极侧面不再发灰
cr.elements[1].position, cr.elements[1].color = 1.0, (0.70, 0.71, 0.74, 1)
for pos, c in [(0.33, (1.8, 1.8, 1.85)), (0.40, (1.3, 1.3, 1.35)), (0.475, (0.7, 0.7, 0.75)),
               (0.50, (1.8, 1.8, 1.8)), (0.62, (1.2, 1.2, 1.25)), (0.80, (0.45, 0.46, 0.50))]:
    e = cr.elements.new(pos)
    e.color = (*c, 1)
nt.links.new(tc.outputs["Generated"], sep.inputs[0])
nt.links.new(sep.outputs["Z"], mrz.inputs["Value"])
nt.links.new(mrz.outputs["Result"], env_ramp.inputs["Fac"])
nt.links.new(env_ramp.outputs["Color"], glossy_bg.inputs["Color"])
mix2 = nt.nodes.new("ShaderNodeMixShader")
nt.links.new(lp.outputs["Is Glossy Ray"], mix2.inputs[0])
nt.links.new(mix.outputs[0], mix2.inputs[1])
nt.links.new(glossy_bg.outputs[0], mix2.inputs[2])
nt.links.new(mix2.outputs[0], nt.nodes["World Output"].inputs[0])

# 负极专用条形灯：在负极前缘打出一条亮高光
bpy.ops.object.light_add(type="AREA", location=(2.0, -9.0, -3.5))
strip = bpy.context.object
strip.data.shape, strip.data.size, strip.data.size_y = "RECTANGLE", 14, 0.6
strip.data.energy = 900
strip.visible_glossy = False         # 不在反射里出现成白色矩形，只负责照亮
strip.rotation_euler = (Vector((1.0, -1.0, -0.6)) - strip.location).to_track_quat("-Z", "Y").to_euler()

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


R = cam_rot.to_matrix()
HUD = 6.0                           # 标注/图例放在离相机 HUD 远的平面上（在电池前面，不会被挡）
TAN = 18.0 / cam.data.lens           # 画面半宽对应的 tan 值（36 mm 传感器）


def scr(u, v):                       # 画面坐标 → 世界坐标：u 左-1 右+1，v 下 -1/1.5 上 +1/1.5
    return cam.location + R @ Vector((u * TAN * HUD, v * TAN * HUD, -HUD))


def to_uv(p):                        # 世界坐标 → 画面坐标
    c = R.transposed() @ (Vector(p) - cam.location)
    return c.x / (-c.z) / TAN, c.y / (-c.z) / TAN


K = HUD / 12.0                       # 画面平面上的尺寸系数
LABEL_U = 0.62                       # 右侧标注列在画面中的横向位置
xr = W / 2                           # 右侧引线标注：从右前角各层引出
for s, layer, dz in LABELS:
    CUR = "spe" if layer == "mat" else layer
    zl = sum(LAYERS[layer]) / 2
    anchor = B((xr - 0.02, -D / 2 + 0.02, zl))
    u, v = to_uv(anchor)
    end = scr(LABEL_U, v + dz * 0.06)
    tube("lead_" + layer, [anchor, end], 0.006 * K, M["lead"], bent=False)
    text(s, end + R @ Vector((0.06 * K, 0, 0)), size=TEXT_SIZE * 0.62 * K)

CUR = "spe"
front = -D / 2 - 0.1                 # 图中文字放在电解质块前面
HS = TEXT_SIZE * 0.62 * K                # 画面平面上的字号


def near(p, du, dv):                 # 某个 3D 点在画面上偏移 (du, dv) 处
    u, v = to_uv(B(p))
    return scr(u + du, v + dv)


text("Charge", near((-2.60 + MX, yf, zm + 0.35), -0.03, 0.0), size=HS * 1.1, color=T["charge"], align="RIGHT")
text("Discharge", near((2.40 + MX, yf, zm + 0.40), 0.04, 0.05), size=HS * 1.1, color=T["discharge"], align="LEFT")
text("Accelerated dynamics", near((-0.1 + MX, yf, zm + 0.80), 0.0, 0.035), size=HS * 1.1, color=T["dynamics"],
     align="CENTER")
text([("Li", ""), ("+", "sup")], near((-W / 2 + 0.3, -D / 2, s0 + 0.45), 0.0, 0.0), size=HS * 0.85)

# ---------- 图例（底部一行，正对相机） ----------
CUR = None
LEGEND = [("S", "sulfur", 0.14), ("C", "carbon", 0.09), ([("Li", ""), ("+", "sup")], "li_ion", 0.085),
          ("SEI particle", "sei_part", 0.075), ("Polymer C", "atom_c", 0.075), ("N", "atom_n", 0.11),
          ("O", "atom_o", 0.11)]
GAPS = [0.9, 0.9, 1.0, 1.9, 1.8, 0.8, 0.8]          # 每项占的宽度
dx = 0.0
for (name, key, r), g in zip(LEGEND, GAPS):
    pos = scr(-0.92, -0.58) + R @ Vector((dx * 0.62 * K, 0, 0))
    o = bpy.data.objects.new("legend", _sphere_mesh.get(M[key].name) or _sphere_mesh[M["li_ion"].name])
    if M[key].name not in _sphere_mesh:
        spheres("legend_tmp", [(0, 0, -50)], 0.01, M[key])
        o.data = _sphere_mesh[M[key].name]
    o.location, o.scale = pos, [r * 0.9 * K] * 3
    scene.collection.objects.link(o)
    text(name, pos + R @ Vector((0.15 * K, 0, 0)), size=0.15 * K)
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
