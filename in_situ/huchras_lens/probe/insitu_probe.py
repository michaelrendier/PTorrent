# feasibility probe, scratchpad only: evaluate a cutout of a MAST FITS file WITHOUT downloading it
import os, sys, time, math, urllib.request
import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
UA = os.environ['CLAUDE_UA']
URL = sys.argv[1]
RA, DEC = 340.125975, 3.3585083
bytes_in = 0; reqs = 0
def rng(a, b):
    global bytes_in, reqs
    r = urllib.request.Request(URL, headers={'User-Agent': UA, 'Range': f'bytes={a}-{b}'})
    d = urllib.request.urlopen(r, timeout=60).read(); bytes_in += len(d); reqs += 1; return d
t0 = time.time()
# walk HDU headers only
pos, hdus = 0, []
total = int(urllib.request.urlopen(urllib.request.Request(URL, method='HEAD', headers={'User-Agent': UA})).headers['Content-Length'])
while pos < total:
    buf = b''; 
    while True:
        buf += rng(pos + len(buf), pos + len(buf) + 2880 * 4 - 1)
        i = buf.find(b'END' + b' ' * 77)
        while i != -1 and i % 80: i = buf.find(b'END' + b' ' * 77, i + 1)
        if i != -1: break
    hlen = ((i + 80 + 2879) // 2880) * 2880
    h = fits.Header.fromstring(buf[:hlen].decode('ascii'))
    n = h.get('NAXIS', 0); dims = [h[f'NAXIS{k}'] for k in range(1, n + 1)]
    dbytes = abs(h['BITPIX']) // 8 * (math.prod(dims) if dims else 0)
    dbytes = ((dbytes + 2879) // 2880) * 2880
    hdus.append((h, pos + hlen, dims)); pos += hlen + dbytes
print(f'file {total} bytes, {len(hdus)} HDUs, header walk used {reqs} requests, {bytes_in} bytes')
# find the SCI extension containing the target
hit = None
for k, (h, off, dims) in enumerate(hdus):
    if h.get('EXTNAME') == 'SCI' and len(dims) == 2:
        x, y = WCS(h).all_world2pix(RA, DEC, 0)
        if 0 <= x < dims[0] and 0 <= y < dims[1]: hit = (k, h, off, dims, float(x), float(y)); break
if not hit: print('target not on this file'); sys.exit()
k, h, off, dims, x, y = hit
print(f"target in HDU {k} EXTVER {h.get('EXTVER')} at pixel x={x:.1f} y={y:.1f} of {dims}; BITPIX {h['BITPIX']}")
half = 32; x0 = int(round(x)) - half; y0 = int(round(y)) - half
x0 = max(0, min(x0, dims[0] - 2 * half)); y0 = max(0, min(y0, dims[1] - 2 * half))
bp = abs(h['BITPIX']) // 8; before = bytes_in; rows = []
for r_ in range(y0, y0 + 2 * half):
    a = off + (r_ * dims[0] + x0) * bp
    rows.append(np.frombuffer(rng(a, a + 2 * half * bp - 1), dtype='>f4'))
cut = np.array(rows, dtype=float)
print(f'cutout {cut.shape} read with {2*half} requests, {bytes_in-before} bytes; total transferred {bytes_in} bytes '
      f'= {100*bytes_in/total:.4f}% of the file, {time.time()-t0:.1f} s')
bg = float(np.median(cut)); pk = float(cut.max()); iy, ix = np.unravel_index(cut.argmax(), cut.shape)
print(f'on-the-server evaluation: median {bg:.3f}, peak {pk:.3f} at cutout ({ix},{iy}), sum(cut-median) {float((cut-bg).sum()):.1f} e-/s, units {h.get("BUNIT")}')
np.save('/tmp/claude-1000/probe/cutout.npy', cut)
