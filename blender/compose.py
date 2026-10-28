# 拼版：主图 + 右侧两个局部放大框（上：正极/电解质界面；下：负极/SEI），连接线和文字
# 先跑 blender/scenes/lis_cell.py 和 blender/scenes/lis_zoom.py，再跑：python3 blender/compose.py [--final]
import os, sys
from PIL import Image, ImageDraw, ImageFont

# ================= 可调参数 =================
S = 2 if "--final" in sys.argv else 1            # 定稿时整体放大 2 倍
CANVAS = (2620, 1100)                             # 画布大小（S=1 时）
BG = (217, 219, 244)                              # 与主图背景一致的浅蓝紫
MAIN_POS, MAIN_SIZE = (0, 50), (1500, 1000)       # 主图位置与大小
FRAME_TOP = (1640, 60, 2580, 520)                 # 上框 (左, 上, 右, 下)
FRAME_BOT = (1640, 640, 2580, 1070)               # 下框
FRAME_FILL, FRAME_LINE = (240, 241, 252), (150, 152, 185)
TEXT, RED, BLUE = (35, 35, 45), (148, 20, 30), (25, 50, 140)
# 主图中被放大的位置（主图像素坐标，S=1）：正极/电解质界面、SEI
SPOT_TOP, SPOT_BOT = (640, 345), (640, 650)
FONT = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
FONT_B = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
for f in (r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\arialbd.ttf"):   # 本机用真 Arial
    if os.path.exists(f):
        FONT, FONT_B = r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\arialbd.ttf"
# ===========================================

here = os.path.dirname(os.path.abspath(__file__))
out = os.path.join(here, "out")
zoom = os.path.join(out, "zoom")


def s(v):                                         # 按 S 放大坐标
    return tuple(int(x * S) for x in v) if isinstance(v, tuple) else int(v * S)


def font(size, bold=False):
    return ImageFont.truetype(FONT_B if bold else FONT, s(size))


canvas = Image.new("RGB", s(CANVAS), BG)
d = ImageDraw.Draw(canvas)


def put(name, box):
    """把小图缩放后贴进 box=(左, 上, 右, 下)，四角裁成圆角。"""
    im = Image.open(os.path.join(zoom, name + ".png")).convert("RGB")
    w, h = s(box[2] - box[0]), s(box[3] - box[1])
    im = im.resize((w, h), Image.LANCZOS)
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w - 1, h - 1), radius=s(14), fill=255)
    canvas.paste(im, s(box[:2]), mask)
    d.rounded_rectangle(s(box), radius=s(14), outline=FRAME_LINE, width=s(2))


def label(xy, txt, size=20, color=TEXT, bold=False, anchor="mm", sub=None, sup=None):
    """写字；sub/sup 为紧跟其后的下标/上标（避免字体缺字）。"""
    f = font(size, bold)
    d.text(s(xy), txt, fill=color, font=f, anchor=anchor)
    if sub or sup:
        x1 = d.textbbox(s(xy), txt, font=f, anchor=anchor)[2]
        fs = font(size * 0.62, bold)
        y = s(xy[1]) + (s(size * 0.3) if sub else -s(size * 0.35))
        d.text((x1 + s(1), y), sub or sup, fill=color, font=fs, anchor="lm")


# ---------- 主图 ----------
main = Image.open(os.path.join(out, "lis_cell.png")).convert("RGB").resize(s(MAIN_SIZE), Image.LANCZOS)
canvas.paste(main, s(MAIN_POS))
spot_t = (MAIN_POS[0] + SPOT_TOP[0], MAIN_POS[1] + SPOT_TOP[1])
spot_b = (MAIN_POS[0] + SPOT_BOT[0], MAIN_POS[1] + SPOT_BOT[1])

# ---------- 连接线：从主图放大处引到框的左上、左下角（扇形） ----------
for spot, fr in ((spot_t, FRAME_TOP), (spot_b, FRAME_BOT)):
    for corner in ((fr[0], fr[1] + 14), (fr[0], fr[3] - 14)):
        d.line([s(spot), s(corner)], fill=(255, 255, 255), width=s(3))
        d.line([s(spot), s(corner)], fill=FRAME_LINE, width=s(1))
    r = 26
    d.ellipse(s((spot[0] - r, spot[1] - r, spot[0] + r, spot[1] + r)), outline=(255, 255, 255), width=s(3))

# ---------- 上框：正极/电解质界面 ----------
d.rounded_rectangle(s(FRAME_TOP), radius=s(22), fill=FRAME_FILL, outline=FRAME_LINE, width=s(2))
L, T, R, B = FRAME_TOP
put("interface", (L + 18, T + 18, L + 560, B - 18))
put("molecule", (L + 576, T + 18, R - 18, T + 228))
put("barrier", (L + 576, T + 244, R - 18, B - 18))
label((L + 150, T + 50), "Enhance", 19, bold=True)
label((L + 150, T + 74), "interface contact", 19, bold=True)
label((L + 420, T + 120), "e", 22, RED, True, sup="−")
label((L + 450, T + 345), "Uniform", 19, bold=True)
label((L + 450, T + 369), "carrier transport", 19, bold=True)
label((L + 330, T + 400), "Li", 22, BLUE, True, sup="+")
label((R - 115, B - 45), "Lower E", 20, RED, True, sub="a")

label(((L + R) / 2, (FRAME_TOP[3] + FRAME_BOT[1]) / 2 - 12), "Compatible Cathode/SPE/Anode", 22, bold=True)
label(((L + R) / 2, (FRAME_TOP[3] + FRAME_BOT[1]) / 2 + 14), "Interface", 22, bold=True)

# ---------- 下框：负极/SEI ----------
d.rounded_rectangle(s(FRAME_BOT), radius=s(22), fill=FRAME_FILL, outline=FRAME_LINE, width=s(2))
L, T, R, B = FRAME_BOT
w = (R - L - 18 * 4) / 3
for i, (name, cap) in enumerate([("dendrite", "Li Dendrite"), ("alloy", "Li-LM Alloy"), ("sei", "Stable SEI")]):
    x0 = L + 18 + i * (w + 18)
    put(name, (x0, T + 18, x0 + w, B - 58))
    label((x0 + w / 2, B - 32), cap, 22, bold=True)
x_alloy = L + 18 + (w + 18)
label((x_alloy + w * 0.62, T + 250), "Blocked", 17, bold=True)
label((x_alloy + w * 0.62, T + 270), "Li dendrite", 17, bold=True)

path = os.path.join(out, "lis_full.png")
canvas.save(path)
print("OK:", path, canvas.size)
