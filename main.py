#!/usr/bin/env python3
"""Meme Sprint 3: AI Agent Goes Rogue -- "My Agent's Intern".

Draws one 1024x1024 PNG meme, deterministically, with the Python standard
library only (no network, no external files, no randomness, no clock).

The joke, in one glance: a robot sits behind the boss's desk wearing a tie
under an "EMPLOYEE OF THE MONTH" poster, while its human stands next to it
holding a tray of coffee with an "INTERN" badge.

    MY AI AGENT
    WENT ROGUE

    I BUILT IT TO DO MY JOB.
    NOW I WORK FOR IT.

Output: $MAKEFUN_OUTPUT_DIR/entry.png (default /output/entry.png).
Run locally: mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
"""

import os
import struct
import zlib
from binascii import crc32

W, H = 1024, 1024

# ---- palette -----------------------------------------------------------
NAVY = (22, 33, 58)        # top/bottom bands
CREAM = (243, 231, 200)    # office wall
YELLOW = (255, 210, 62)    # punch-line yellow
WHITE = (255, 255, 255)
INK = (30, 30, 40)         # outlines / small text
SKY_TOP = (255, 154, 61)   # dusk gradient, window
SKY_BOT = (255, 107, 129)
SUN = (255, 210, 62)
CITY = (74, 43, 90)        # skyline silhouette
DESK_TOP = (160, 106, 50)
DESK = (124, 74, 33)
FLOOR = (138, 90, 51)
ROBOT = (223, 227, 232)    # robot light grey
ROBOT_DARK = (185, 190, 199)
ROBOT_PANEL = (154, 160, 171)
EYE = (25, 211, 230)       # robot eyes
RED = (214, 48, 49)        # tie / poster header
GOLD = (217, 164, 65)      # nameplate
SKIN = (242, 199, 155)
HAIR = (90, 55, 30)
SHIRT = (47, 111, 178)
PANTS = (38, 52, 84)
SILVER = (192, 196, 204)
COFFEE = (111, 66, 32)

# ---- pixel buffer ------------------------------------------------------
px = bytearray(W * H * 3)


def set_pixel(x, y, c):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        px[i] = c[0]
        px[i + 1] = c[1]
        px[i + 2] = c[2]


def fill_rect(x0, y0, x1, y1, c):
    x0 = max(0, x0)
    y0 = max(0, y0)
    x1 = min(W, x1)
    y1 = min(H, y1)
    for y in range(y0, y1):
        base = (y * W + x0) * 3
        for x in range(x0, x1):
            i = base + (x - x0) * 3
            px[i] = c[0]
            px[i + 1] = c[1]
            px[i + 2] = c[2]


def border_rect(x0, y0, x1, y1, c, bw=3):
    fill_rect(x0, y0, x1, y0 + bw, c)
    fill_rect(x0, y1 - bw, x1, y1, c)
    fill_rect(x0, y0, x0 + bw, y1, c)
    fill_rect(x1 - bw, y0, x1, y1, c)


def disc(cx, cy, r, c):
    for y in range(cy - r, cy + r + 1):
        for x in range(cx - r, cx + r + 1):
            if (x - cx) * (x - cx) + (y - cy) * (y - cy) <= r * r:
                set_pixel(x, y, c)


def rrect(x0, y0, x1, y1, r, c):
    fill_rect(x0 + r, y0, x1 - r, y1, c)
    fill_rect(x0, y0 + r, x1, y1 - r, c)
    disc(x0 + r, y0 + r, r, c)
    disc(x1 - r, y0 + r, r, c)
    disc(x0 + r, y1 - r, r, c)
    disc(x1 - r, y1 - r, r, c)


def line(x0, y0, x1, y1, w, c):
    dx = x1 - x0
    dy = y1 - y0
    steps = max(abs(dx), abs(dy), 1)
    half = w // 2
    for i in range(steps + 1):
        t = i / steps
        x = int(round(x0 + dx * t))
        y = int(round(y0 + dy * t))
        fill_rect(x - half, y - half, x + half + 1, y + half + 1, c)


def vgrad(x0, y0, x1, y1, top, bot):
    for y in range(y0, y1):
        t = (y - y0) / max(1, y1 - y0 - 1)
        c = tuple(int(round(top[k] + (bot[k] - top[k]) * t)) for k in range(3))
        fill_rect(x0, y, x1, y + 1, c)


# ---- 5x7 bitmap font ---------------------------------------------------
# Each glyph is 7 rows of 5 bits, "1" = ink.
FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    "3": ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "?": ("01110", "10001", "00001", "00010", "00100", "00000", "00100"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
}


def text_width(s, scale):
    return (len(s) * 6 - 1) * scale if s else 0


def draw_text(s, x, y, scale, c):
    cx = x
    for ch in s:
        glyph = FONT.get(ch, FONT[" "])
        for row in range(7):
            bits = glyph[row]
            for col in range(5):
                if bits[col] == "1":
                    fill_rect(cx + col * scale, y + row * scale,
                              cx + (col + 1) * scale, y + (row + 1) * scale, c)
        cx += 6 * scale


def draw_text_center(s, y, scale, c, cx=512):
    draw_text(s, cx - text_width(s, scale) // 2, y, scale, c)


# ---- scene -------------------------------------------------------------
def draw_window():
    # frame
    rrect(56, 236, 304, 564, 8, (101, 67, 33))
    # dusk sky
    vgrad(68, 248, 292, 552, SKY_TOP, SKY_BOT)
    # sun + halo
    disc(180, 330, 46, (255, 224, 130))
    disc(180, 330, 34, SUN)
    # skyline silhouettes
    for (bx, bw, bh) in ((72, 46, 62), (124, 42, 92), (172, 48, 70),
                         (226, 40, 100), (270, 22, 58)):
        fill_rect(bx, 552 - bh, bx + bw, 552, CITY)
    # lit windows on the skyline
    for (wx, wy) in ((84, 500), (100, 520), (140, 480), (156, 510),
                     (188, 505), (240, 470), (252, 500), (278, 515)):
        fill_rect(wx, wy, wx + 6, wy + 8, YELLOW)
    border_rect(56, 236, 304, 564, INK, 4)


def draw_poster():
    # on the wall between the window and the robot -- clear of both
    rrect(330, 230, 540, 432, 6, WHITE)
    border_rect(330, 230, 540, 432, INK, 4)
    fill_rect(330, 230, 540, 274, RED)
    draw_text_center("EMPLOYEE", 240, 3, WHITE, cx=435)
    draw_text_center("OF THE MONTH", 284, 2, NAVY, cx=435)
    # mini robot face, employee of the month
    disc(435, 356, 40, ROBOT)
    border_rect(395, 316, 475, 396, INK, 3)  # square-ish frame around face
    disc(420, 350, 6, EYE)
    disc(450, 350, 6, EYE)
    line(424, 374, 446, 374, 4, INK)


def draw_robot():
    # antenna
    line(715, 256, 715, 206, 8, INK)
    disc(715, 194, 14, RED)
    # ears
    fill_rect(584, 306, 602, 352, ROBOT_DARK)
    fill_rect(828, 306, 846, 352, ROBOT_DARK)
    # head
    rrect(598, 252, 832, 408, 26, INK)
    rrect(606, 260, 824, 400, 20, ROBOT)
    # eyes (glowing cyan) + glints
    rrect(638, 298, 702, 342, 8, EYE)
    rrect(728, 298, 792, 342, 8, EYE)
    disc(652, 310, 6, WHITE)
    disc(742, 310, 6, WHITE)
    # confident smirk
    line(652, 366, 690, 380, 5, INK)
    line(690, 380, 742, 380, 5, INK)
    line(742, 380, 778, 364, 5, INK)
    # neck
    fill_rect(688, 404, 742, 432, ROBOT_DARK)
    # torso (lower half hidden behind the desk, drawn later)
    rrect(556, 428, 874, 664, 30, INK)
    rrect(564, 436, 866, 656, 24, ROBOT_DARK)
    # chest panel: buttons in a column left of the tie, gauge right of it
    rrect(636, 468, 794, 566, 10, ROBOT_PANEL)
    disc(665, 492, 11, (46, 160, 67))
    disc(665, 522, 11, YELLOW)
    disc(665, 552, 11, RED)
    fill_rect(736, 504, 784, 546, NAVY)
    fill_rect(743, 511, 777, 539, EYE)
    # red tie
    fill_rect(700, 440, 730, 468, RED)
    line(715, 462, 715, 566, 30, RED)
    disc(715, 566, 15, RED)


def draw_desk():
    # floor strip
    fill_rect(0, 780, W, 810, FLOOR)
    # desk top slab + front
    fill_rect(28, 638, 996, 666, DESK_TOP)
    fill_rect(40, 666, 984, 810, DESK)
    border_rect(40, 666, 984, 810, INK, 3)
    # drawer seams + handles
    line(300, 690, 300, 786, 3, (90, 52, 22))
    line(724, 690, 724, 786, 3, (90, 52, 22))
    fill_rect(150, 724, 210, 736, GOLD)
    fill_rect(814, 724, 874, 736, GOLD)
    # plant on the desk, left side
    fill_rect(118, 606, 178, 640, (168, 74, 44))
    disc(148, 596, 22, (46, 125, 50))
    disc(128, 606, 16, (64, 150, 62))
    disc(168, 606, 16, (64, 150, 62))


def draw_robot_hands():
    # hands resting on the desk top, beside the nameplate
    disc(606, 650, 20, ROBOT)
    disc(824, 650, 20, ROBOT)
    # gold nameplate: BOSS
    rrect(636, 592, 794, 640, 6, GOLD)
    border_rect(636, 592, 794, 640, INK, 3)
    draw_text_center("BOSS", 604, 4, NAVY, cx=715)


def draw_human():
    # worried intern, standing in front of the desk, tray of coffee
    # hair cap
    disc(255, 580, 46, HAIR)
    # head
    disc(255, 592, 42, SKIN)
    # worried eyebrows + eyes + frown
    line(226, 572, 244, 580, 4, INK)
    line(264, 580, 282, 572, 4, INK)
    disc(238, 590, 5, INK)
    disc(272, 590, 5, INK)
    line(244, 616, 254, 610, 4, INK)
    line(254, 610, 266, 616, 4, INK)
    # sweat drop
    disc(304, 556, 7, (120, 200, 235))
    fill_rect(299, 548, 309, 558, (120, 200, 235))
    # shirt + pants + shoes
    rrect(204, 632, 306, 742, 12, SHIRT)
    fill_rect(214, 742, 296, 806, PANTS)
    fill_rect(206, 800, 250, 810, INK)
    fill_rect(260, 800, 304, 810, INK)
    # INTERN badge (above the cup, no overlap)
    fill_rect(216, 646, 294, 672, WHITE)
    border_rect(216, 646, 294, 672, INK, 2)
    draw_text_center("INTERN", 652, 2, NAVY, cx=255)
    # arms to the tray
    line(210, 660, 226, 726, 10, SHIRT)
    line(300, 660, 284, 726, 10, SHIRT)
    # tray + coffee cup + steam
    rrect(192, 716, 318, 738, 6, SILVER)
    border_rect(192, 716, 318, 738, INK, 2)
    fill_rect(236, 688, 274, 716, WHITE)
    border_rect(236, 688, 274, 716, INK, 2)
    fill_rect(240, 692, 270, 700, COFFEE)
    fill_rect(274, 694, 282, 706, WHITE)


def draw_meme():
    fill_rect(0, 0, W, H, CREAM)
    draw_window()
    draw_poster()
    draw_robot()
    draw_desk()
    draw_robot_hands()
    draw_human()
    # top band + title
    fill_rect(0, 0, W, 190, NAVY)
    draw_text_center("MY AI AGENT", 26, 9, WHITE)
    draw_text_center("WENT ROGUE", 106, 9, YELLOW)
    # bottom band + punchline
    fill_rect(0, 810, W, H, NAVY)
    draw_text_center("I BUILT IT TO DO MY JOB.", 848, 6, WHITE)
    draw_text_center("NOW I WORK FOR IT.", 928, 6, YELLOW)


# ---- PNG writer (deterministic) ----------------------------------------
def chunk(ctype, data):
    out = struct.pack(">I", len(data)) + ctype + data
    out += struct.pack(">I", crc32(ctype + data) & 0xFFFFFFFF)
    return out


def write_png(path):
    raw = bytearray()
    for y in range(H):
        raw.append(0)  # filter: none
        raw += px[y * W * 3:(y + 1) * W * 3]
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 6))
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    draw_meme()
    path = os.path.join(out_dir, "entry.png")
    size = write_png(path)
    print("wrote %s (%d bytes)" % (path, size))


if __name__ == "__main__":
    main()
