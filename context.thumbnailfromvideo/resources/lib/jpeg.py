"""Minimal baseline JPEG encoder in pure Python (Kodi has no PIL).

encode_bgra(width, height, bgra_bytes, quality) -> JPEG bytes
YCbCr 4:2:0, standard Huffman tables, float AAN DCT (as in libjpeg's jfdctflt).
"""
import struct

_ZIGZAG = [0, 1, 8, 16, 9, 2, 3, 10, 17, 24, 32, 25, 18, 11, 4, 5,
           12, 19, 26, 33, 40, 48, 41, 34, 27, 20, 13, 6, 7, 14, 21, 28,
           35, 42, 49, 56, 57, 50, 43, 36, 29, 22, 15, 23, 30, 37, 44, 51,
           58, 59, 52, 45, 38, 31, 39, 46, 53, 60, 61, 54, 47, 55, 62, 63]

_LUMA_Q = [16, 11, 10, 16, 24, 40, 51, 61, 12, 12, 14, 19, 26, 58, 60, 55,
           14, 13, 16, 24, 40, 57, 69, 56, 14, 17, 22, 29, 51, 87, 80, 62,
           18, 22, 37, 56, 68, 109, 103, 77, 24, 35, 55, 64, 81, 104, 113, 92,
           49, 64, 78, 87, 103, 121, 120, 101, 72, 92, 95, 98, 112, 100, 103, 99]
_CHROMA_Q = [17, 18, 24, 47, 99, 99, 99, 99, 18, 21, 26, 66, 99, 99, 99, 99,
             24, 26, 56, 99, 99, 99, 99, 99, 47, 66, 99, 99, 99, 99, 99, 99] + [99] * 32

_DC_LUMA_BITS = [0, 1, 5, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0]
_DC_CHROMA_BITS = [0, 3, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0]
_DC_VALS = list(range(12))
_AC_LUMA_BITS = [0, 2, 1, 3, 3, 2, 4, 3, 5, 5, 4, 4, 0, 0, 1, 0x7d]
_AC_LUMA_VALS = bytes.fromhex(
    '01020300041105122131410613516107227114328191a1082342b1c11552d1f0'
    '2433627282090a161718191a25262728292a3435363738393a43444546474849'
    '4a535455565758595a636465666768696a737475767778797a83848586878889'
    '8a92939495969798999aa2a3a4a5a6a7a8a9aab2b3b4b5b6b7b8b9bac2c3c4c5'
    'c6c7c8c9cad2d3d4d5d6d7d8d9dae1e2e3e4e5e6e7e8e9eaf1f2f3f4f5f6f7f8'
    'f9fa')
_AC_CHROMA_BITS = [0, 2, 1, 2, 4, 4, 3, 4, 7, 5, 4, 4, 0, 1, 2, 0x77]
_AC_CHROMA_VALS = bytes.fromhex(
    '00010203110405213106124151076171132232810814429' + '1a1b1c109233352f0'
    '156272d10a162434e125f11718191a262728292a35363738393a434445464748'
    '494a535455565758595a636465666768696a737475767778797a828384858687'
    '88898a92939495969798999aa2a3a4a5a6a7a8a9aab2b3b4b5b6b7b8b9bac2c3'
    'c4c5c6c7c8c9cad2d3d4d5d6d7d8d9dae2e3e4e5e6e7e8e9eaf2f3f4f5f6f7f8'
    'f9fa')

_AAN = [1.0, 1.387039845, 1.306562965, 1.175875602,
        1.0, 0.785694958, 0.541196100, 0.275899379]


def _scaled_table(base, quality):
    quality = max(1, min(100, int(quality)))
    s = 5000 // quality if quality < 50 else 200 - 2 * quality
    return [max(1, min(255, (q * s + 50) // 100)) for q in base]


def _huff_codes(bits, vals):
    codes, code, k = {}, 0, 0
    for length in range(1, 17):
        for _ in range(bits[length - 1]):
            codes[vals[k]] = (code, length)
            code += 1
            k += 1
        code <<= 1
    return codes


def _fdct_quant(blk, fdiv):
    """In-place float AAN DCT of 64 values (natural order), then quantize.
    Returns the 64 quantized coefficients in zigzag order."""
    for i in range(0, 64, 8):
        d0, d1, d2, d3, d4, d5, d6, d7 = blk[i:i + 8]
        t0 = d0 + d7; t7 = d0 - d7; t1 = d1 + d6; t6 = d1 - d6
        t2 = d2 + d5; t5 = d2 - d5; t3 = d3 + d4; t4 = d3 - d4
        t10 = t0 + t3; t13 = t0 - t3; t11 = t1 + t2; t12 = t1 - t2
        blk[i] = t10 + t11; blk[i + 4] = t10 - t11
        z1 = (t12 + t13) * 0.707106781
        blk[i + 2] = t13 + z1; blk[i + 6] = t13 - z1
        t10 = t4 + t5; t11 = t5 + t6; t12 = t6 + t7
        z5 = (t10 - t12) * 0.382683433
        z2 = 0.541196100 * t10 + z5; z4 = 1.306562965 * t12 + z5
        z3 = t11 * 0.707106781
        z11 = t7 + z3; z13 = t7 - z3
        blk[i + 5] = z13 + z2; blk[i + 3] = z13 - z2
        blk[i + 1] = z11 + z4; blk[i + 7] = z11 - z4
    for i in range(8):
        d0 = blk[i]; d1 = blk[i + 8]; d2 = blk[i + 16]; d3 = blk[i + 24]
        d4 = blk[i + 32]; d5 = blk[i + 40]; d6 = blk[i + 48]; d7 = blk[i + 56]
        t0 = d0 + d7; t7 = d0 - d7; t1 = d1 + d6; t6 = d1 - d6
        t2 = d2 + d5; t5 = d2 - d5; t3 = d3 + d4; t4 = d3 - d4
        t10 = t0 + t3; t13 = t0 - t3; t11 = t1 + t2; t12 = t1 - t2
        blk[i] = t10 + t11; blk[i + 32] = t10 - t11
        z1 = (t12 + t13) * 0.707106781
        blk[i + 16] = t13 + z1; blk[i + 48] = t13 - z1
        t10 = t4 + t5; t11 = t5 + t6; t12 = t6 + t7
        z5 = (t10 - t12) * 0.382683433
        z2 = 0.541196100 * t10 + z5; z4 = 1.306562965 * t12 + z5
        z3 = t11 * 0.707106781
        z11 = t7 + z3; z13 = t7 - z3
        blk[i + 40] = z13 + z2; blk[i + 24] = z13 - z2
        blk[i + 8] = z11 + z4; blk[i + 56] = z11 - z4
    # int(x + 16384.5) - 16384 == round half up, much faster than round()
    return [int(blk[z] * fdiv[z] + 16384.5) - 16384 for z in _ZIGZAG]


class _BitWriter:
    def __init__(self):
        self.out = bytearray()
        self.acc = 0
        self.n = 0

    def write(self, code, length):
        self.acc = (self.acc << length) | code
        self.n += length
        while self.n >= 8:
            self.n -= 8
            b = (self.acc >> self.n) & 0xFF
            self.out.append(b)
            if b == 0xFF:
                self.out.append(0)
        self.acc &= (1 << self.n) - 1

    def flush(self):
        if self.n:
            self.write((1 << (8 - self.n)) - 1, 8 - self.n)  # pad with 1-bits


def _encode_block(bw, coefs, prev_dc, dc_codes, ac_codes):
    dc = coefs[0]
    diff = dc - prev_dc
    if diff == 0:
        bw.write(*dc_codes[0])
    else:
        a = -diff if diff < 0 else diff
        cat = a.bit_length()
        bw.write(*dc_codes[cat])
        bw.write(diff if diff > 0 else diff + (1 << cat) - 1, cat)
    run = 0
    last = 63
    while last > 0 and coefs[last] == 0:
        last -= 1
    for k in range(1, last + 1):
        v = coefs[k]
        if v == 0:
            run += 1
            continue
        while run > 15:
            bw.write(*ac_codes[0xF0])  # ZRL
            run -= 16
        a = -v if v < 0 else v
        cat = a.bit_length()
        bw.write(*ac_codes[(run << 4) | cat])
        bw.write(v if v > 0 else v + (1 << cat) - 1, cat)
        run = 0
    if last < 63:
        bw.write(*ac_codes[0x00])  # EOB
    return dc


def encode_bgra(width, height, data, quality=90, comment=None):
    w, h = width, height
    # planes (level-shifted by -128); pad to a multiple of 16 by repeating edges
    pw, ph = (w + 15) // 16 * 16, (h + 15) // 16 * 16
    B = data[0::4]
    G = data[1::4]
    R = data[2::4]
    Y = [(19595 * r + 38470 * g + 7471 * b) * (1.0 / 65536) - 128.0 for r, g, b in zip(R, G, B)]
    # chroma from 2x2-summed RGB (4:2:0); rows padded to the padded width
    cw, ch = pw // 2, ph // 2
    pad = pw - w

    def plane_row(P, yy):
        yy = min(yy, h - 1)
        row = P[yy * w:(yy + 1) * w]
        return row + bytes([row[-1]]) * pad if pad else row

    Cb, Cr = [], []
    for y in range(ch):
        r0 = plane_row(R, 2 * y); r1 = plane_row(R, 2 * y + 1)
        g0 = plane_row(G, 2 * y); g1 = plane_row(G, 2 * y + 1)
        b0 = plane_row(B, 2 * y); b1 = plane_row(B, 2 * y + 1)
        rs = [a + b + c + d for a, b, c, d in zip(r0[0::2], r0[1::2], r1[0::2], r1[1::2])]
        gs = [a + b + c + d for a, b, c, d in zip(g0[0::2], g0[1::2], g1[0::2], g1[1::2])]
        bs = [a + b + c + d for a, b, c, d in zip(b0[0::2], b0[1::2], b1[0::2], b1[1::2])]
        # coefficients already divided by 4 (the 2x2 average)
        Cb.append([-0.042184 * r - 0.082816 * g + 0.125 * b for r, g, b in zip(rs, gs, bs)])
        Cr.append([0.125 * r - 0.104672 * g - 0.020328 * b for r, g, b in zip(rs, gs, bs)])

    yq = _scaled_table(_LUMA_Q, quality)
    cq = _scaled_table(_CHROMA_Q, quality)
    ydiv = [1.0 / (yq[i] * _AAN[i // 8] * _AAN[i % 8] * 8.0) for i in range(64)]
    cdiv = [1.0 / (cq[i] * _AAN[i // 8] * _AAN[i % 8] * 8.0) for i in range(64)]
    dcl = _huff_codes(_DC_LUMA_BITS, _DC_VALS)
    acl = _huff_codes(_AC_LUMA_BITS, _AC_LUMA_VALS)
    dcc = _huff_codes(_DC_CHROMA_BITS, _DC_VALS)
    acc = _huff_codes(_AC_CHROMA_BITS, _AC_CHROMA_VALS)

    # padded luma rows
    def yrow(yy):
        yy = min(yy, h - 1)
        row = Y[yy * w:(yy + 1) * w]
        if pw > w:
            row = row + [row[-1]] * (pw - w)
        return row

    bw = _BitWriter()
    pdy = pdb = pdr = 0
    for my in range(0, ph, 16):
        rows = [yrow(my + i) for i in range(16)]
        for mx in range(0, pw, 16):
            for by, bx in ((0, 0), (0, 8), (8, 0), (8, 8)):
                blk = []
                for i in range(8):
                    blk.extend(rows[by + i][mx + bx:mx + bx + 8])
                pdy = _encode_block(bw, _fdct_quant(blk, ydiv), pdy, dcl, acl)
            cy, cx = my // 2, mx // 2
            blk = []
            for i in range(8):
                blk.extend(Cb[cy + i][cx:cx + 8])
            pdb = _encode_block(bw, _fdct_quant(blk, cdiv), pdb, dcc, acc)
            blk = []
            for i in range(8):
                blk.extend(Cr[cy + i][cx:cx + 8])
            pdr = _encode_block(bw, _fdct_quant(blk, cdiv), pdr, dcc, acc)
    bw.flush()

    out = bytearray(b'\xff\xd8')
    out += b'\xff\xe0' + struct.pack('>H5sBBBHHBB', 16, b'JFIF\0', 1, 1, 0, 1, 1, 0, 0)
    if comment:  # COM segment (e.g. the video time of this frame)
        out += b'\xff\xfe' + struct.pack('>H', 2 + len(comment)) + comment
    for tid, table in ((0, yq), (1, cq)):
        out += b'\xff\xdb' + struct.pack('>HB', 67, tid) + bytes(table[z] for z in _ZIGZAG)
    out += b'\xff\xc0' + struct.pack('>HBHHB', 17, 8, h, w, 3)
    out += bytes([1, 0x22, 0, 2, 0x11, 1, 3, 0x11, 1])
    for cls_id, bits, vals in ((0x00, _DC_LUMA_BITS, _DC_VALS), (0x10, _AC_LUMA_BITS, _AC_LUMA_VALS),
                               (0x01, _DC_CHROMA_BITS, _DC_VALS), (0x11, _AC_CHROMA_BITS, _AC_CHROMA_VALS)):
        out += b'\xff\xc4' + struct.pack('>HB', 3 + 16 + len(vals), cls_id) + bytes(bits) + bytes(vals)
    out += b'\xff\xda' + struct.pack('>HB', 12, 3) + bytes([1, 0x00, 2, 0x11, 3, 0x11]) + b'\x00\x3f\x00'
    out += bw.out
    out += b'\xff\xd9'
    return bytes(out)


def write_bgra(path, width, height, data, quality=90, comment=None):
    with open(path, 'wb') as f:
        f.write(encode_bgra(width, height, data, quality, comment))
