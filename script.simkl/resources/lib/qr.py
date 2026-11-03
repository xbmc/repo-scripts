#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""A QR code for the login dialog, drawn here so the login code never leaves the box: byte mode, error correction
level M, versions 1 to 10 (up to 213 bytes), rendered as a PNG. Module placement follows ISO/IEC 18004."""

import struct
import zlib

# level M, per version: (ec codewords per block, blocks in group 1, data codewords per block, blocks in group 2, data codewords per block)
BLOCKS = {
    1: (10, 1, 16, 0, 0),
    2: (16, 1, 28, 0, 0),
    3: (26, 1, 44, 0, 0),
    4: (18, 2, 32, 0, 0),
    5: (24, 2, 43, 0, 0),
    6: (16, 4, 27, 0, 0),
    7: (18, 4, 31, 0, 0),
    8: (22, 2, 38, 2, 39),
    9: (22, 3, 36, 2, 37),
    10: (26, 4, 43, 1, 44),
}
ALIGNMENT = {1: [], 2: [6, 18], 3: [6, 22], 4: [6, 26], 5: [6, 30], 6: [6, 34], 7: [6, 22, 38], 8: [6, 24, 42], 9: [6, 26, 46], 10: [6, 28, 50]}
VERSION_INFO = {7: 0x07C94, 8: 0x085BC, 9: 0x09A99, 10: 0x0A4D3}
FORMAT_LEVEL_M = 0
MASKS = (
    lambda r, c: (r + c) % 2 == 0,
    lambda r, c: r % 2 == 0,
    lambda r, c: c % 3 == 0,
    lambda r, c: (r + c) % 3 == 0,
    lambda r, c: (r // 2 + c // 3) % 2 == 0,
    lambda r, c: (r * c) % 2 + (r * c) % 3 == 0,
    lambda r, c: ((r * c) % 2 + (r * c) % 3) % 2 == 0,
    lambda r, c: ((r * c) % 3 + (r + c) % 2) % 2 == 0,
)

_EXP = [0] * 512
_LOG = [0] * 256
_value = 1
for _i in range(255):
    _EXP[_i] = _value
    _LOG[_value] = _i
    _value <<= 1
    if _value & 0x100:
        _value ^= 0x11D
for _i in range(255, 512):
    _EXP[_i] = _EXP[_i - 255]


def _multiply(a, b):
    return 0 if a == 0 or b == 0 else _EXP[_LOG[a] + _LOG[b]]


def _generator(count):
    poly = [1]
    for i in range(count):
        poly = [(poly[j] if j < len(poly) else 0) ^ (_multiply(poly[j - 1], _EXP[i]) if j else 0) for j in range(len(poly) + 1)]
    return poly


def _ec_codewords(block, count):
    generator = _generator(count)
    remainder = list(block) + [0] * count
    for i in range(len(block)):
        factor = remainder[i]
        if factor:
            for j in range(1, len(generator)):
                remainder[i + j] ^= _multiply(generator[j], factor)
    return remainder[len(block):]


def _version_for(length):
    for version in range(1, 11):
        ec, blocks1, data1, blocks2, data2 = BLOCKS[version]
        if 4 + (16 if version >= 10 else 8) + 8 * length <= 8 * (blocks1 * data1 + blocks2 * data2):
            return version
    raise ValueError('too long for a QR code of version 10')


def _codewords(data, version):
    ec, blocks1, data1, blocks2, data2 = BLOCKS[version]
    capacity = blocks1 * data1 + blocks2 * data2
    bits = []

    def put(value, count):
        for i in range(count - 1, -1, -1):
            bits.append((value >> i) & 1)

    put(0b0100, 4)
    put(len(data), 16 if version >= 10 else 8)
    for byte in data:
        put(byte, 8)
    put(0, min(4, capacity * 8 - len(bits)))
    while len(bits) % 8:
        bits.append(0)
    words = [int(''.join(str(bit) for bit in bits[i:i + 8]), 2) for i in range(0, len(bits), 8)]
    for i in range(capacity - len(words)):
        words.append(0xEC if i % 2 == 0 else 0x11)
    blocks = []
    offset = 0
    for count, size in ((blocks1, data1), (blocks2, data2)):
        for _ in range(count):
            blocks.append(words[offset:offset + size])
            offset += size
    interleaved = [block[i] for i in range(max(data1, data2)) for block in blocks if i < len(block)]
    ec_blocks = [_ec_codewords(block, ec) for block in blocks]
    interleaved += [block[i] for i in range(ec) for block in ec_blocks]
    return interleaved


def _format_bits(mask):
    data = (FORMAT_LEVEL_M << 3) | mask
    remainder = data << 10
    for i in range(14, 9, -1):
        if remainder & (1 << i):
            remainder ^= 0x537 << (i - 10)
    return ((data << 10) | remainder) ^ 0x5412


def _place_fixed(modules, version):
    size = len(modules)
    for row, col in ((0, 0), (size - 7, 0), (0, size - 7)):
        for r in range(-1, 8):
            for c in range(-1, 8):
                if 0 <= row + r < size and 0 <= col + c < size:
                    modules[row + r][col + c] = (0 <= r <= 6 and c in (0, 6)) or (0 <= c <= 6 and r in (0, 6)) or (2 <= r <= 4 and 2 <= c <= 4)
    # alignment patterns before the timing patterns: from version 7 on, one of them is centred on the timing row and column
    centres = ALIGNMENT[version]
    for row in centres:
        for col in centres:
            if modules[row][col] is not None:
                continue
            for r in range(-2, 3):
                for c in range(-2, 3):
                    modules[row + r][col + c] = r in (-2, 2) or c in (-2, 2) or (r == 0 and c == 0)
    for i in range(8, size - 8):
        if modules[i][6] is None:
            modules[i][6] = i % 2 == 0
        if modules[6][i] is None:
            modules[6][i] = i % 2 == 0
    if version >= 7:
        info = VERSION_INFO[version]
        for i in range(18):
            bit = (info >> i) & 1 == 1
            modules[i // 3][i % 3 + size - 11] = bit
            modules[i % 3 + size - 11][i // 3] = bit


def _place_format(modules, mask):
    size = len(modules)
    bits = _format_bits(mask)
    for i in range(15):
        bit = (bits >> i) & 1 == 1
        if i < 6:
            modules[i][8] = bit
        elif i < 8:
            modules[i + 1][8] = bit
        else:
            modules[size - 15 + i][8] = bit
        if i < 8:
            modules[8][size - i - 1] = bit
        elif i < 9:
            modules[8][15 - i] = bit
        else:
            modules[8][14 - i] = bit
    modules[size - 8][8] = True


def _place_data(modules, codewords, mask):
    size = len(modules)
    masked = MASKS[mask]
    bit_index = 7
    byte_index = 0
    row = size - 1
    step = -1
    for col in range(size - 1, 0, -2):
        if col <= 6:
            col -= 1
        while True:
            for c in (col, col - 1):
                if modules[row][c] is not None:
                    continue
                dark = byte_index < len(codewords) and (codewords[byte_index] >> bit_index) & 1 == 1
                modules[row][c] = dark != masked(row, c)
                bit_index -= 1
                if bit_index < 0:
                    byte_index += 1
                    bit_index = 7
            row += step
            if row < 0 or row >= size:
                row -= step
                step = -step
                break


def _penalty(modules):
    size = len(modules)
    score = 0
    for lines in (modules, list(zip(*modules))):
        for line in lines:
            run = 1
            for i in range(1, size):
                if line[i] == line[i - 1]:
                    run += 1
                    continue
                if run >= 5:
                    score += run - 2
                run = 1
            if run >= 5:
                score += run - 2
            for i in range(size - 6):
                if line[i] and not line[i + 1] and line[i + 2] and line[i + 3] and line[i + 4] and not line[i + 5] and line[i + 6]:
                    before = i >= 4 and not any(line[i - 4:i])
                    after = i + 11 <= size and not any(line[i + 7:i + 11])
                    if before or after:
                        score += 40
    for r in range(size - 1):
        for c in range(size - 1):
            if modules[r][c] == modules[r][c + 1] == modules[r + 1][c] == modules[r + 1][c + 1]:
                score += 3
    dark = sum(sum(1 for cell in row if cell) for row in modules)
    score += 10 * (abs(dark * 100 // (size * size) - 50) // 5)
    return score


def _reserve_format(modules):
    """The format areas: nine cells along the top-left finder on each axis, eight along the other two (seven bits and
    the fixed dark module); kept out of the data placement, written by _place_format afterwards."""
    size = len(modules)
    cells = [(i, 8) for i in range(9)] + [(8, i) for i in range(9)] + [(size - 1 - i, 8) for i in range(8)] + [(8, size - 1 - i) for i in range(8)]
    for r, c in cells:
        if modules[r][c] is None:
            modules[r][c] = False


def matrix(text, version=None, mask=None):
    """The modules of the code for text as rows of booleans (True = dark), no quiet zone. version and mask are picked
    automatically when not given (the smallest version that fits, the mask with the lowest penalty)."""
    data = text.encode('utf-8')
    version = version or _version_for(len(data))
    size = 17 + 4 * version
    codewords = _codewords(data, version)
    best = None
    for candidate in ([mask] if mask is not None else range(8)):
        modules = [[None] * size for _ in range(size)]
        _place_fixed(modules, version)
        _reserve_format(modules)
        _place_data(modules, codewords, candidate)
        _place_format(modules, candidate)
        score = _penalty(modules) if mask is None else 0
        if best is None or score < best[0]:
            best = (score, modules)
    return best[1]


def png(text, scale=6, quiet=4):
    """The code as a PNG (grayscale, scale pixels per module, a quiet zone of quiet modules around it)."""
    modules = matrix(text)
    size = (len(modules) + 2 * quiet) * scale
    blank = bytes([255]) * size
    raw = bytearray()
    for row in modules:
        line = bytes([255]) * (quiet * scale) + b''.join(bytes([0 if dark else 255]) * scale for dark in row) + bytes([255]) * (quiet * scale)
        for _ in range(scale):
            raw += b'\x00' + line
    body = (b'\x00' + blank) * (quiet * scale) + bytes(raw) + (b'\x00' + blank) * (quiet * scale)

    def chunk(tag, payload):
        return struct.pack('>I', len(payload)) + tag + payload + struct.pack('>I', zlib.crc32(tag + payload) & 0xFFFFFFFF)

    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', size, size, 8, 0, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(body, 9)) + chunk(b'IEND', b''))
