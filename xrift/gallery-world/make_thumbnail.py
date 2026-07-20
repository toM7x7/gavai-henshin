# -*- coding: utf-8 -*-
"""蒸着庫サムネイル生成 — 実スーツレンダ3体をアルコーブ風に構成した1280x720。

WebGLスクショが環境依存で不安定なため、カタログレンダから決定論的に合成する。
実行: リポジトリルートで python xrift/gallery-world/make_thumbnail.py
"""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = os.path.join(os.path.dirname(__file__), '..', '..')
OUT = os.path.join(os.path.dirname(__file__), 'public', 'thumbnail.png')

SUITS = [
    ('output/blueprint-armor/chuuni/c3_raitei/c3_raitei_front.png', (95, 220, 255)),
    ('output/blueprint-armor/chuuni/c5_haou/c5_haou_front.png', (255, 200, 90)),
    ('output/blueprint-armor/chuuni/c1_datenshi/c1_datenshi_front.png', (170, 130, 255)),
]

W, H = 1280, 720
img = Image.new('RGB', (W, H), (7, 13, 19))
d = ImageDraw.Draw(img)

# 床グリッド(奥行きのある格納庫床)
horizon = 430
for i in range(14):  # 放射線
    x = -600 + i * 190
    d.line([(W // 2 + (x - W // 2) // 6, horizon), (x, H)], fill=(22, 46, 58), width=2)
for i in range(8):   # 水平線(奥ほど密)
    t = i / 7.0
    y = horizon + int((H - horizon) * (t ** 1.7))
    d.line([(0, y), (W, y)], fill=(20, 40, 50), width=1 if i else 2)

# アルコーブ3基(中央を主役に、左右をやや奥へ)
panels = [
    (180, 150, 250, 470, 0),   # x, y, w, h — 左
    (515, 100, 280, 540, 1),   # 中央(大きく)
    (880, 150, 250, 470, 2),   # 右
]
for (px, py, pw, ph, idx) in panels:
    path, accent = SUITS[idx][0], SUITS[idx][1]
    src = Image.open(os.path.join(ROOT, path)).convert('RGB')
    # 中央列をクロップ(720x1280 → スーツ主体の縦長)
    sw, sh = src.size
    crop = src.crop((int(sw * 0.18), int(sh * 0.04), int(sw * 0.82), int(sh * 0.96)))
    crop = crop.resize((pw, ph))
    # アルコーブ背光(アクセント色のグロー)
    glow = Image.new('RGB', (pw + 60, ph + 60), (7, 13, 19))
    gd = ImageDraw.Draw(glow)
    gd.rectangle([20, 20, pw + 40, ph + 40], outline=accent, width=8)
    glow = glow.filter(ImageFilter.GaussianBlur(14))
    img.paste(glow, (px - 30, py - 30))
    img.paste(crop, (px, py))
    # フレーム
    d.rectangle([px - 2, py - 2, px + pw + 2, py + ph + 2], outline=accent, width=3)
    d.rectangle([px - 8, py - 8, px + pw + 8, py + ph + 8], outline=(30, 50, 62), width=2)
    # 足元の台座リング
    cx = px + pw // 2
    d.ellipse([cx - 90, py + ph - 6, cx + 90, py + ph + 26], outline=accent, width=4)

# タイトル
def font(size, bold=True):
    for name in ('meiryob.ttc', 'meiryo.ttc', 'YuGothB.ttc', 'YuGothM.ttc', 'msgothic.ttc'):
        try:
            return ImageFont.truetype(os.path.join('C:/Windows/Fonts', name), size)
        except OSError:
            continue
    return ImageFont.load_default()

d.text((44, 30), '蒸着庫', font=font(64), fill=(159, 220, 255))
d.text((46, 108), 'GAVAI SUIT GALLERY', font=font(30), fill=(120, 160, 185))
d.text((44, 660), '言葉から生まれたヒーロースーツの保管庫', font=font(26), fill=(140, 170, 190))

img.save(OUT)
print('saved:', OUT, img.size)
