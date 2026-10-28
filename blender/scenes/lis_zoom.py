# 锂硫示意图右侧的局部放大小图（按参考图版式），每个小图单独渲染成 PNG，再由 blender/compose.py 拼版
# 运行：blender/.venv/bin/python blender/scenes/lis_zoom.py [--final] [小图名 ...]
# 小图：interface（正极/电解质界面接触）、molecule（分子结构）、barrier（能垒）、
#       dendrite（Li 枝晶）、alloy（Li-LM 合金阻挡枝晶）、sei（稳定 SEI）
import os, sys, math, random
import bpy
from mathutils import Vector

# ================= 可调参数 =================
FINAL = "--final" in sys.argv
SIZE = {"interface": (720, 560), "molecule": (480, 270), "barrier": (480, 270),
        "dendrite": (400, 480), "alloy": (400, 480), "sei": (400, 480)}
SCALE = 2.0 if FINAL else 1.0          # 定稿时分辨率翻倍
SAMPLES = 128 if FINAL else 32
BG = (0.86, 0.87, 0.96)                # 小图背景：比主图背景略浅的蓝紫
COLORS = {                             # 与主图一致
    "sulfur": (0.82, 0.68, 0.26), "carbon": (0.27, 0.29, 0.34), "spe": (0.45, 0.70, 0.95),
    "li_ion": (0.50, 0.33, 0.88), "atom_c": (0.55, 0.57, 0.62), "atom_n": (0.10, 0.20, 0.55),
    "atom_o": (0.55, 0.90, 0.95), "sei": (0.10, 0.70, 0.68), "li": (0.95, 0.96, 1.00),
    "e": (0.58, 0.08, 0.12), "arrow_li": (0.10, 0.20, 0.55), "electrolyte": (0.70, 0.85, 0.98),
    "alloy": (0.62, 0.64, 0.70), "barrier_hi": (0.55, 0.55, 0.60), "barrier_lo": (0.58, 0.08, 0.12),
}
# ===========================================

here = os.path.dirname(os.path.abspath(__file__))
out = os.path.join(os.path.dirname(here), "out", "zoom")
os.makedirs(out, exist_ok=True)
random.seed(3)


def lin(rgb):
    return [c ** 2.2 for c in rgb]


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = SAMPLES
    sc.cycles.use_denoising = True
    sc.view_settings.view_transform = "Standard"
    w = bpy.data.worlds.new("W")
    sc.world = w
    w.use_nodes = True
    bgn = w.node_tree.nodes["Background"]
    bgn.inputs["Color"].default_value = (*lin(BG), 1)
    bgn.inputs["Strength"].default_value = 1.0
    for loc, e, s in [((-4, -6, 7), 900, 5), ((6, -4, 3), 300, 6), ((0, 6, 6), 500, 5)]:
        bpy.ops.object.light_add(type="AREA", location=loc)
        l = bpy.context.object
        l.data.energy, l.data.size = e, s
        l.rotation_euler = (Vector((0, 0, 0)) - l.location).to_track_quat("-Z", "Y").to_euler()
    return sc


def mat(name, rgb, rough=0.15, metal=0.3, coat=1.0, alpha=1.0, emit=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = (*lin(rgb), 1)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metal
    p.inputs["Coat Weight"].default_value = coat
    p.inputs["Alpha"].default_value = alpha
    if emit:
        p.inputs["Emission Color"].default_value = (*lin(rgb), 1)
        p.inputs["Emission Strength"].default_value = emit
    return m


def sphere(loc, r, m, seg=32):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=seg // 2, radius=r, location=loc)
    o = bpy.context.object
    bpy.ops.object.shade_smooth()
    o.data.materials.append(m)
    return o


def tube(pts, r, m, order=4):
    cu = bpy.data.curves.new("t", "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = r
    cu.bevel_resolution = 4
    cu.use_fill_caps = True
    sp = cu.splines.new("NURBS")
    sp.points.add(len(pts) - 1)
    for p, q in zip(sp.points, pts):
        p.co = (*q, 1)
    sp.use_endpoint_u = True
    sp.order_u = min(order, len(pts))
    o = bpy.data.objects.new("t", cu)
    o.data.materials.append(m)
    bpy.context.scene.collection.objects.link(o)
    return o


def cone(tip, d, m, r=0.12, h=0.3):
    d = Vector(d).normalized()
    bpy.ops.mesh.primitive_cone_add(radius1=r, depth=h, location=Vector(tip) - d * h / 2)
    o = bpy.context.object
    o.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    o.data.materials.append(m)


def arrow(pts, r, m):
    h = r * 7
    d = (Vector(pts[-1]) - Vector(pts[-2])).normalized()
    base = Vector(pts[-1]) - d * h * 0.9                     # 箭身一直画到箭头底部，二者相连
    tube(list(pts[:-1]) + [tuple(base)], r, m)
    cone(pts[-1], d, m, r=r * 2.6, h=h)


def box(loc, size, m):
    bpy.ops.mesh.primitive_cube_add(location=loc)
    o = bpy.context.object
    o.scale = [s / 2 for s in size]
    o.data.materials.append(m)
    bpy.ops.object.modifier_add(type="BEVEL")
    o.modifiers["Bevel"].width = 0.03
    return o


def camera(loc, target, ortho=None, lens=50):
    bpy.ops.object.camera_add(location=loc)
    c = bpy.context.object
    c.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    if ortho:
        c.data.type = "ORTHO"
        c.data.ortho_scale = ortho
    else:
        c.data.lens = lens
    bpy.context.scene.camera = c


def render(sc, name):
    w, h = SIZE[name]
    sc.render.resolution_x, sc.render.resolution_y = int(w * SCALE), int(h * SCALE)
    sc.render.filepath = os.path.join(out, name + ".png")
    bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out, name + ".blend"))
    print("OK:", sc.render.filepath)


# ---------- ① 正极/电解质界面：硫颗粒与电解质紧密接触，电子与 Li+ 均匀传输 ----------
def panel_interface():
    sc = reset()
    ms = mat("S", COLORS["sulfur"])
    me = mat("SPE", COLORS["spe"], rough=0.08, metal=0.0, alpha=0.75)
    mc = mat("C", COLORS["carbon"])
    mli = mat("Li", COLORS["li_ion"])
    sphere((-1.35, 0, -0.55), 1.55, ms, 64)                  # 硫颗粒（左下）
    sphere((1.35, 0.3, 0.25), 1.75, me, 64)                  # 电解质（右上）
    for k in range(9):                                       # 接触界面上的碳/导电颗粒
        t = -0.9 + k * 0.24
        sphere((0.05 + 0.18 * math.sin(k), -0.9, t), 0.13, mc)
    for p in [(0.9, -1.4, -0.6), (1.4, -1.3, 0.6), (0.5, -1.45, 0.1), (1.8, -1.2, -0.2)]:
        sphere(p, 0.11, mli)
    arrow([(1.6, -1.6, 1.15), (0.9, -1.6, 1.05), (0.25, -1.6, 0.75)], 0.05, mat("e", COLORS["e"], emit=0.3))
    arrow([(-0.3, -1.6, -1.0), (0.4, -1.6, -0.75), (1.1, -1.6, -0.85)], 0.05,
          mat("a", COLORS["arrow_li"], emit=0.3))
    camera((0, -9, 0.3), (0.05, 0, 0), ortho=6.2)
    render(sc, "interface")


# ---------- ② 分子结构 ----------
def panel_molecule():
    sc = reset()
    mc, mn, mo = mat("C", COLORS["atom_c"]), mat("N", COLORS["atom_n"]), mat("O", COLORS["atom_o"])
    ms, mli = mat("S", COLORS["sulfur"]), mat("Li", COLORS["li_ion"])
    mb = mat("bond", (0.72, 0.72, 0.75), rough=0.4, metal=0.0, coat=0.0)
    atoms = []
    for ox, oz, rot in [(-0.9, 0.0, 0.0), (0.0, 0.25, 0.5), (0.9, 0.0, 0.0)]:
        ring = [(ox + 0.42 * math.cos(rot + i * math.pi / 3), 0, oz + 0.42 * math.sin(rot + i * math.pi / 3))
                for i in range(6)]
        for i in range(6):
            tube([ring[i], ring[(i + 1) % 6]], 0.04, mb, order=2)
        atoms += ring
    for a, b in [(atoms[0], atoms[9]), (atoms[6], atoms[15])]:
        tube([a, b], 0.04, mb, order=2)
    for p in atoms:
        sphere(p, 0.12, mc)
    for p, m in [((-1.6, 0, 0.3), mn), ((1.6, 0, 0.35), mn), ((0.0, 0, 0.95), mo), ((-0.6, 0, -0.75), mo),
                 ((0.65, 0, -0.75), ms)]:
        near = min(atoms, key=lambda q: (q[0] - p[0]) ** 2 + (q[2] - p[2]) ** 2)
        tube([near, p], 0.04, mb, order=2)
        sphere(p, 0.16, m)
    for p in [(-2.0, -0.2, -0.6), (2.1, -0.2, -0.4), (1.2, -0.2, 1.0), (-1.3, -0.2, 0.95)]:
        sphere(p, 0.1, mli)
    camera((0, -9, 0), (0, 0, 0.1), ortho=5.0)
    render(sc, "molecule")


# ---------- ③ 能垒：原来的高能垒（灰虚线）与降低后的能垒（深红实线） ----------
def panel_barrier():
    sc = reset()
    mhi, mlo = mat("hi", COLORS["barrier_hi"], emit=0.2), mat("lo", COLORS["barrier_lo"], emit=0.3)
    mli, mx = mat("Li", COLORS["li_ion"]), mat("ax", (0.2, 0.2, 0.25), emit=0.5)

    def curve(h):
        return [(x, 0, h * math.exp(-x * x / 0.35) - 0.25 * math.tanh(x * 1.5)) for x in
                [-1.8 + 0.12 * i for i in range(31)]]
    hi = curve(1.25)
    for i in range(0, len(hi) - 1, 2):                       # 虚线
        tube([hi[i], hi[i + 1]], 0.03, mhi, order=2)
    tube(curve(0.65), 0.045, mlo)
    sphere((-1.75, -0.1, 0.38), 0.17, mli)                   # 反应前
    sphere((1.75, -0.1, -0.1), 0.17, mat("Li2", (0.85, 0.86, 0.95)))
    tube([(-2.1, 0, -0.6), (-2.1, 0, 1.5)], 0.02, mx, order=2)   # 纵轴
    cone((-2.1, 0, 1.6), (0, 0, 1), mx, r=0.06, h=0.18)
    arrow([(0.0, -0.1, 0.72), (0.0, -0.1, 1.15)], 0.025, mx)     # 能垒差
    camera((0, -9, 0), (0, 0, 0.45), ortho=4.6)
    render(sc, "barrier")


# ---------- ④⑤⑥ 负极侧：Li 枝晶 / Li-LM 合金阻挡枝晶 / 稳定 SEI ----------
def anode_base(sc, top_mat=None):
    mli = mat("Limetal", COLORS["li"], rough=0.15, metal=0.0, emit=0.35)   # 亮白色锂金属
    box((0, 0, -1.6), (3.2, 1.6, 0.5), mli)
    box((0, 0.7, 0.3), (3.2, 0.1, 3.3), mat("bg", COLORS["electrolyte"], rough=0.4, metal=0.0, coat=0.0,
                                            alpha=0.55))          # 背后的电解质色块
    ions = [(random.uniform(-1.3, 1.3), -0.3, random.uniform(-0.6, 1.7)) for _ in range(9)]
    return mli, ions


def branch(p, d, length, depth, m, r):
    q = Vector(p) + Vector(d) * length
    tube([p, (Vector(p) + q) / 2 + Vector((random.uniform(-.05, .05), 0, 0)), q], r, m, order=3)
    if depth == 0:
        return
    for ang in (-0.6, 0.55):
        nd = Vector((d[0] * math.cos(ang) - d[2] * math.sin(ang), 0, d[0] * math.sin(ang) + d[2] * math.cos(ang)))
        branch(q, nd, length * 0.68, depth - 1, m, r * 0.75)


def panel_dendrite():
    sc = reset()
    mli, ions = anode_base(sc)
    md = mat("dendrite", (0.97, 0.97, 1.0), rough=0.2, metal=0.2, emit=0.15)
    branch((0, -0.2, -1.35), (0, 0, 1), 0.9, 4, md, 0.07)    # 白色枝晶
    branch((-0.9, -0.2, -1.35), (0.15, 0, 1), 0.5, 3, md, 0.05)
    for p in ions:
        sphere(p, 0.1, mat("ion", COLORS["li_ion"]))
    camera((0, -9, -0.25), (0, 0, -0.25), ortho=3.6)
    render(sc, "dendrite")


def panel_alloy():
    sc = reset()
    mli, ions = anode_base(sc)
    box((0, 0, -1.28), (3.2, 1.6, 0.14), mat("alloy", COLORS["alloy"], rough=0.25, metal=0.8))   # 合金层
    md = mat("dendrite", (0.97, 0.97, 1.0), rough=0.2, metal=0.2, emit=0.15)
    branch((-0.2, -0.2, -1.2), (0, 0, 1), 0.45, 2, md, 0.06)   # 被阻挡的小枝晶
    mx = mat("x", COLORS["e"], emit=0.6)                     # 阻挡标记 ×
    for a in (45, -45):
        r = math.radians(a)
        tube([(-0.2 - 0.25 * math.cos(r), -0.4, -0.35 - 0.25 * math.sin(r)),
              (-0.2 + 0.25 * math.cos(r), -0.4, -0.35 + 0.25 * math.sin(r))], 0.04, mx, order=2)
    for p in ions:
        sphere(p, 0.1, mat("ion", COLORS["li_ion"]))
    camera((0, -9, -0.25), (0, 0, -0.25), ortho=3.6)
    render(sc, "alloy")


def panel_sei():
    sc = reset()
    mli, ions = anode_base(sc)
    box((0, 0, -1.3), (3.2, 1.6, 0.1), mat("sei", COLORS["sei"], rough=0.15, metal=0.0, emit=0.15))   # 稳定 SEI
    for p in ions:
        sphere(p, 0.1, mat("ion", COLORS["li_ion"]))
    for x in (-0.8, 0.0, 0.8):                               # Li+ 均匀穿过 SEI 沉积
        arrow([(x, -0.4, -0.2), (x, -0.4, -0.75), (x, -0.4, -1.1)], 0.03, mat("a", COLORS["arrow_li"], emit=0.3))
    camera((0, -9, -0.25), (0, 0, -0.25), ortho=3.6)
    render(sc, "sei")


PANELS = {"interface": panel_interface, "molecule": panel_molecule, "barrier": panel_barrier,
          "dendrite": panel_dendrite, "alloy": panel_alloy, "sei": panel_sei}
want = [a for a in sys.argv[1:] if a in PANELS] or list(PANELS)
for n in want:
    PANELS[n]()
