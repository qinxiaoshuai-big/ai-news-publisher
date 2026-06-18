"""用 PIL 生成两张架构图：1) 整体架构 2) 完整工作流"""
import os
from PIL import Image, ImageDraw, ImageFont

# 找系统字体
FONT_CANDIDATES = [
    r'C:\Windows\Fonts\msyh.ttc',
    r'C:\Windows\Fonts\msyh.ttf',
    r'C:\Windows\Fonts\msyhl.ttc',
    r'C:\Windows\Fonts\simhei.ttf',
    r'C:\Windows\Fonts\simsun.ttc',
    r'C:\Windows\Fonts\segoeui.ttf',
]
FONT_PATH = None
for f in FONT_CANDIDATES:
    if os.path.exists(f):
        FONT_PATH = f
        break
print('Using font:', FONT_PATH)


def font(size, bold=False):
    if FONT_PATH and bold and 'msyh.ttc' in FONT_PATH:
        return ImageFont.truetype(FONT_PATH, size, index=0)
    if FONT_PATH:
        return ImageFont.truetype(FONT_PATH, size)
    return ImageFont.load_default()


# 颜色
BG = (22, 25, 38)
PANEL_BG = (35, 40, 60)
PANEL_DARK = (28, 32, 48)
BLUE = (88, 144, 255)
PURPLE = (155, 110, 255)
GREEN = (90, 200, 140)
ORANGE = (255, 170, 80)
PINK = (255, 120, 180)
TEXT = (220, 225, 240)
SUB = (150, 160, 190)
GRID = (50, 55, 75)


def rounded(draw, xy, r, fill=None, outline=None, width=1):
    draw.rounded_rectangle(xy, radius=r, fill=fill, outline=outline, width=width)


def text(draw, xy, s, fill=TEXT, fnt=None, anchor='lt'):
    draw.text(xy, s, font=fnt or font(20), fill=fill, anchor=anchor)


def multiline(draw, xy, lines, fill=TEXT, size=20, leading=4, anchor='lt'):
    f = font(size)
    line_h = size + leading
    for i, ln in enumerate(lines):
        draw.text((xy[0], xy[1] + i * line_h), ln, font=f, fill=fill, anchor=anchor)


# === 图 1：架构图 ===
W, H = 1600, 900
im = Image.new('RGB', (W, H), BG)
d = ImageDraw.Draw(im)
f_title = font(34, bold=True)
f_h2 = font(24, bold=True)
f_body = font(20)
f_small = font(16)

# 标题
text(d, (W // 2, 30), 'ai-news-publisher · 整体架构', fill=BLUE, fnt=f_title, anchor='mm')
text(d, (W // 2, 75), '浏览器端 ↔ Python 后端 ↔ 外部 AI/微信服务',
     fill=SUB, fnt=font(18), anchor='mm')

# 三栏背景
COL_W = 480
COL_Y = 130
COL_H = 720
GUTTER = 20
col_x = [60, 60 + COL_W + GUTTER, 60 + 2 * (COL_W + GUTTER)]

# 左侧：浏览器
rounded(d, (col_x[0], COL_Y, col_x[0] + COL_W, COL_Y + COL_H), 12, fill=PANEL_BG)
rounded(d, (col_x[0], COL_Y, col_x[0] + COL_W, COL_Y + 50), 12, fill=(50, 56, 80))
text(d, (col_x[0] + COL_W // 2, COL_Y + 25), '前端（单文件 HTML）', fill=BLUE, fnt=f_h2, anchor='mm')

# 浏览器内容 - 4 个 Step
step_y0 = COL_Y + 90
for i, (label, color) in enumerate([
    ('① 话题 + 素材搜索', BLUE),
    ('② 一键写文章', PURPLE),
    ('③ 配图生成', ORANGE),
    ('④ 上传 + 发布', GREEN),
]):
    y = step_y0 + i * 150
    rounded(d, (col_x[0] + 20, y, col_x[0] + COL_W - 20, y + 120), 8, fill=PANEL_DARK)
    # 左侧色条
    rounded(d, (col_x[0] + 20, y, col_x[0] + 30, y + 120), 8, fill=color)
    text(d, (col_x[0] + 50, y + 28), label, fill=color, fnt=f_h2, anchor='lt')
    sub = [
        '话题输入 + Exa 多角度搜索',
        'Claude 生成 Markdown + 段落编辑',
        'IMAGE: 标记解析 + 逐张生成',
        '转换 HTML + 推送到草稿箱',
    ][i]
    text(d, (col_x[0] + 50, y + 70), sub, fill=SUB, fnt=font(18), anchor='lt')

# 中间：Python 后端
rounded(d, (col_x[1], COL_Y, col_x[1] + COL_W, COL_Y + COL_H), 12, fill=PANEL_BG)
rounded(d, (col_x[1], COL_Y, col_x[1] + COL_W, COL_Y + 50), 12, fill=(90, 60, 160))
text(d, (col_x[1] + COL_W // 2, COL_Y + 25), 'Python 后端 (server.py)', fill=PURPLE, fnt=f_h2, anchor='mm')

apis = [
    ('POST /api/search', 'Exa 代理', BLUE),
    ('POST /api/article', 'Claude 生成', PURPLE),
    ('POST /api/rewrite', '段落重写', PINK),
    ('POST /api/image', 'APImart 生图', ORANGE),
    ('POST /api/upload', '微信上传', GREEN),
    ('POST /api/draft', '草稿发布', GREEN),
    ('GET /api/config', '读写 config.json', BLUE),
]
api_y0 = COL_Y + 80
for i, (path_label, desc, color) in enumerate(apis):
    y = api_y0 + i * 80
    rounded(d, (col_x[1] + 20, y, col_x[1] + COL_W - 20, y + 64), 6, fill=PANEL_DARK)
    rounded(d, (col_x[1] + 20, y, col_x[1] + 28, y + 64), 6, fill=color)
    text(d, (col_x[1] + 45, y + 18), path_label, fill=color, fnt=font(20, bold=True))
    text(d, (col_x[1] + 45, y + 44), desc, fill=SUB, fnt=font(18))

# 右侧：外部服务
rounded(d, (col_x[2], COL_Y, col_x[2] + COL_W, COL_Y + COL_H), 12, fill=PANEL_BG)
rounded(d, (col_x[2], COL_Y, col_x[2] + COL_W, COL_Y + 50), 12, fill=(160, 110, 50))
text(d, (col_x[2] + COL_W // 2, COL_Y + 25), '外部服务', fill=ORANGE, fnt=f_h2, anchor='mm')

ext_services = [
    ('🤖 Claude (OpenAI 兼容)', 'APImart 代理\nclaude-sonnet-4-5', BLUE),
    ('🖼 APImart 图像生成', 'nano-banana\ngpt-image-2 / flux-2-pro', PURPLE),
    ('🔍 Exa 语义搜索', 'exa.ai/search\n返回标题+URL+摘要', GREEN),
    ('📱 微信公众平台 API', 'upload / draft 端点\nAppID + AppSecret', ORANGE),
]
ext_y0 = COL_Y + 80
for i, (label, desc, color) in enumerate(ext_services):
    y = ext_y0 + i * 150
    rounded(d, (col_x[2] + 20, y, col_x[2] + COL_W - 20, y + 130), 8, fill=PANEL_DARK)
    rounded(d, (col_x[2] + 20, y, col_x[2] + 30, y + 130), 8, fill=color)
    text(d, (col_x[2] + 50, y + 30), label, fill=color, fnt=f_h2)
    multiline(d, (col_x[2] + 50, y + 68), desc.split('\n'), fill=SUB, size=18)

# 横向箭头：左 <-> 中
for y in [step_y0 + 60, step_y0 + 210, step_y0 + 360, step_y0 + 510]:
    # 浏览器 -> 后端
    d.line([(col_x[0] + COL_W, y), (col_x[1], y)], fill=BLUE, width=3)
    # 箭头
    d.polygon([(col_x[1], y), (col_x[1] - 12, y - 8), (col_x[1] - 12, y + 8)], fill=BLUE)
    # 后端 -> 浏览器（回包）
    d.line([(col_x[1], y + 6), (col_x[0] + COL_W, y + 6)], fill=(120, 140, 180), width=2)

# 横向箭头：中 <-> 右
for y in [api_y0 + 30, api_y0 + 110, api_y0 + 270, api_y0 + 430]:
    d.line([(col_x[1] + COL_W, y), (col_x[2], y)], fill=PURPLE, width=3)
    d.polygon([(col_x[2], y), (col_x[2] - 12, y - 8), (col_x[2] - 12, y + 8)], fill=PURPLE)
    d.line([(col_x[2], y + 6), (col_x[1] + COL_W, y + 6)], fill=(170, 130, 200), width=2)

# 底部说明
rounded(d, (60, 870 - 5, W - 60, 870 + 5), 0, fill=GRID)
# 略

out = r'd:\程序开发\量化交易\ai-news-publisher\docs\images\arch.png'
im.save(out)
print('wrote', out, os.path.getsize(out), 'bytes')


# === 图 2：工作流 ===
W2, H2 = 1800, 700
im2 = Image.new('RGB', (W2, H2), BG)
d2 = ImageDraw.Draw(im2)

text(d2, (W2 // 2, 30), '公众号文章自动化 · 6 步工作流', fill=BLUE, fnt=f_title, anchor='mm')
text(d2, (W2 // 2, 75), '从话题到草稿箱 · 约 3 分钟', fill=SUB, fnt=font(18), anchor='mm')

# 6 个节点
NODES = [
    ('Step 1', '话题 + 素材', '输入话题\nExa 3 角度搜索\n勾选要用的素材', BLUE),
    ('Step 2', '写文章', 'Claude 生成 Markdown\n可手动编辑\n可段落重写', PURPLE),
    ('Step 3', '生配图', '解析 IMAGE: 标记\nAPImart 逐张生成\n不满意可重画', ORANGE),
    ('Step 4', '上传微信', '封面图 → media_id\n内嵌图 → 微信 URL', GREEN),
    ('Step 5', '转 HTML', 'md_to_html.py\n图片替换为微信 URL', PINK),
    ('Step 6', '发布', '推到草稿箱\n公众号后台预览', GREEN),
]

NODE_W, NODE_H = 240, 280
NODE_GAP = 60
TOTAL_W = len(NODES) * NODE_W + (len(NODES) - 1) * NODE_GAP
START_X = (W2 - TOTAL_W) // 2
NODE_Y = 160

for i, (step, title, desc, color) in enumerate(NODES):
    x = START_X + i * (NODE_W + NODE_GAP)
    # 主框
    rounded(d2, (x, NODE_Y, x + NODE_W, NODE_Y + NODE_H), 12, fill=PANEL_BG)
    # 顶部条
    rounded(d2, (x, NODE_Y, x + NODE_W, NODE_Y + 60), 12, fill=color)
    rounded(d2, (x, NODE_Y + 40, x + NODE_W, NODE_Y + 60), 12, fill=color)
    # step 标签
    text(d2, (x + NODE_W // 2, NODE_Y + 18), step, fill=(255, 255, 255), fnt=f_small, anchor='mm')
    # 标题
    text(d2, (x + NODE_W // 2, NODE_Y + 45), title, fill=(255, 255, 255), fnt=f_h2, anchor='mm')
    # 描述
    multiline(d2, (x + 24, NODE_Y + 90), desc.split('\n'), fill=TEXT, size=18, leading=8)
    # 大数字
    text(d2, (x + NODE_W - 24, NODE_Y + NODE_H - 24), f'0{i+1}',
         fill=(60, 65, 90), fnt=font(36, bold=True), anchor='rb')

# 节点间箭头
for i in range(len(NODES) - 1):
    x0 = START_X + i * (NODE_W + NODE_GAP) + NODE_W
    x1 = START_X + (i + 1) * (NODE_W + NODE_GAP)
    cy = NODE_Y + NODE_H // 2
    d2.line([(x0, cy), (x1 - 14, cy)], fill=BLUE, width=4)
    d2.polygon([(x1, cy), (x1 - 14, cy - 10), (x1 - 14, cy + 10)], fill=BLUE)

# 反馈回路：草稿箱 → 写文章
fb_y0 = NODE_Y + NODE_H + 30
fb_y1 = fb_y0 + 60
# 右边到底部
d2.line([(W2 // 2 + NODE_W // 2, fb_y0), (W2 // 2 + NODE_W // 2, fb_y1)],
        fill=ORANGE, width=3)
# 底部横线
d2.line([(W2 // 2 + NODE_W // 2, fb_y1), (START_X + NODE_W // 2, fb_y1)],
        fill=ORANGE, width=3)
# 左下到 Step 2 底
x_step2 = START_X + 1 * (NODE_W + NODE_GAP) + NODE_W // 2
d2.line([(START_X + NODE_W // 2, fb_y1), (x_step2, fb_y1)],
        fill=ORANGE, width=3)
# 向上箭头到 Step 2 底边
d2.line([(x_step2, fb_y1), (x_step2, NODE_Y + NODE_H + 2)],
        fill=ORANGE, width=3)
d2.polygon([(x_step2, NODE_Y + NODE_H), (x_step2 - 10, NODE_Y + NODE_H - 14),
            (x_step2 + 10, NODE_Y + NODE_H - 14)], fill=ORANGE)
# 标注
text(d2, (W2 // 2, fb_y0 + 30), '不满意 → 改文章 / 重生配图 / 段落重写',
     fill=ORANGE, fnt=font(20, bold=True), anchor='mm')

out2 = r'd:\程序开发\量化交易\ai-news-publisher\docs\images\flow.png'
im2.save(out2)
print('wrote', out2, os.path.getsize(out2), 'bytes')
