"""
Writes 36 abstract placeholder "photos" into ../photos (pure Python, no deps).
Delete them (placeholder_*.png) once you add your own images, then re-run build.

    python3 tools/make_placeholders.py
"""
import math
import os
import random
import struct
import zlib

W, H, N = 640, 480, 36
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'photos')


def png(path, rows):
    raw = b''.join(b'\x00' + bytes(r) for r in rows)

    def chunk(tag, data):
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)
    with open(path, 'wb') as f:
        f.write(b'\x89PNG\r\n\x1a\n')
        f.write(chunk(b'IHDR', struct.pack('>IIBBBBB', W, H, 8, 2, 0, 0, 0)))
        f.write(chunk(b'IDAT', zlib.compress(raw, 6)))
        f.write(chunk(b'IEND', b''))


def hsv(h, s, v):
    i = int(h * 6) % 6
    f = h * 6 - int(h * 6)
    p, q, t = v * (1 - s), v * (1 - f * s), v * (1 - (1 - f) * s)
    return [(v, t, p), (q, v, p), (p, v, t), (p, q, v), (t, p, v), (v, p, q)][i]


def make(k):
    rnd = random.Random(k)
    hue = k / float(N)
    sky = hsv(hue, 0.45, 0.95)
    ground = hsv((hue + 0.08) % 1, 0.6, 0.35)
    horizon = rnd.uniform(0.45, 0.7) * H
    sun = (rnd.uniform(0.2, 0.8) * W, rnd.uniform(0.15, 0.45) * H, rnd.uniform(30, 70))
    sun_c = hsv((hue + 0.5) % 1, 0.35, 1.0)
    hills = [(rnd.uniform(0, W), rnd.uniform(80, 220), rnd.uniform(30, 110)) for _ in range(4)]
    rows = []
    for y in range(H):
        row = bytearray(W * 3)
        for x in range(W):
            ground_y = horizon - max(h * math.exp(-((x - cx) / w) ** 2) for cx, w, h in hills)
            if y > ground_y:
                shade = 0.7 + 0.3 * (y - ground_y) / max(H - ground_y, 1)
                c = tuple(ch * shade for ch in ground)
            else:
                g = y / horizon
                c = tuple(a * (1 - 0.35 * g) + 0.35 * g for a in sky)
                d = math.hypot(x - sun[0], y - sun[1])
                if d < sun[2]:
                    c = sun_c
                elif d < sun[2] * 2.2:
                    a = 1 - (d - sun[2]) / (sun[2] * 1.2)
                    c = tuple(ci * (1 - a * 0.5) + si * a * 0.5 for ci, si in zip(c, sun_c))
            n = rnd.uniform(-0.02, 0.02)   # a little grain so it reads as a "photo"
            row[x * 3:x * 3 + 3] = bytes(max(0, min(255, int((ch + n) * 255))) for ch in c)
        rows.append(row)
    png(os.path.join(OUT, 'placeholder_%02d.png' % k), rows)


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    for k in range(N):
        make(k)
        print('wrote placeholder_%02d.png' % k)
