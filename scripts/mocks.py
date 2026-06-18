"""生成 4 张占位 PNG 到 server workspace 目录的 images 子目录"""
import os
import zlib
import struct
import urllib.request
import json

r = urllib.request.urlopen('http://localhost:8765/api/status').read().decode()
ws = json.loads(r)['workspace']
img_dir = os.path.join(ws, 'images')
os.makedirs(img_dir, exist_ok=True)
print('image dir =', img_dir)


def make_png(w, h, rgb):
    sig = b'\x89PNG\r\n\x1a\n'

    def chunk(t, d):
        return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)

    ihdr = struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)
    raw = b''
    for _ in range(h):
        raw += b'\x00' + bytes(rgb) * w
    idat = zlib.compress(raw, 9)
    return sig + chunk(b'IHDR', ihdr) + chunk(b'IDAT', idat) + chunk(b'IEND', b'')


for i, rgb in enumerate([(26, 37, 64), (42, 26, 64), (26, 64, 42)]):
    p = os.path.join(img_dir, f'img_{i}.png')
    with open(p, 'wb') as f:
        f.write(make_png(800, 450, rgb))
    print('  wrote', p)
p = os.path.join(img_dir, 'cover_0.png')
with open(p, 'wb') as f:
    f.write(make_png(800, 450, (58, 26, 48)))
print('  wrote', p)
