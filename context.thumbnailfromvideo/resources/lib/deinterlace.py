"""Comb detection and removal for frames captured from interlaced video.

Kodi's RenderCapture of a paused interlaced video (e.g. DVD / MPEG-2 576i)
returns both fields woven together, which shows as horizontal lines wherever
something moved. The frame has to be captured at the video's own height so
each image row is one video line; then:

comb_score()   > COMB_THRESHOLD means the frame is combed
deinterlace()  replaces combed pixels on odd lines by the average of the lines
               above and below (static areas keep full detail)
"""

COMB_THRESHOLD = 1.6


def comb_score(data, width, height, xstep=8):
    """Ratio of line-to-line roughness to field-to-field roughness (green
    channel). Progressive pictures are smoother between neighbouring lines
    (ratio well below 1); woven fields make neighbouring lines differ."""
    if height < 8:
        return 0.0
    g = data[1::4]
    near = far = 0
    for y in range(2, height - 2):
        r0 = y * width
        rm2, rm1, rp1, rp2 = r0 - 2 * width, r0 - width, r0 + width, r0 + 2 * width
        for x in range(0, width, xstep):
            c2 = 2 * g[r0 + x]
            d = c2 - g[rm1 + x] - g[rp1 + x]
            near += d if d >= 0 else -d
            d = c2 - g[rm2 + x] - g[rp2 + x]
            far += d if d >= 0 else -d
    return near / (far + 1.0)


def deinterlace(data, width, height, threshold=3):
    """Motion-adaptive line interpolation: on every odd line, a pixel whose
    green value sticks out above or below BOTH neighbouring lines by more than
    `threshold` is replaced by the average of those lines."""
    out = bytearray(data)
    stride = width * 4
    for y in range(1, height - 1, 2):
        a0 = (y - 1) * stride
        c0 = y * stride
        b0 = (y + 1) * stride
        above = data[a0:a0 + stride]
        cur = data[c0:c0 + stride]
        below = data[b0:b0 + stride]
        for i in range(0, stride, 4):
            ga = above[i + 1]
            gc = cur[i + 1]
            gb = below[i + 1]
            if (gc - ga > threshold and gc - gb > threshold) or \
               (ga - gc > threshold and gb - gc > threshold):
                o = c0 + i
                out[o] = (above[i] + below[i]) >> 1
                out[o + 1] = (ga + gb) >> 1
                out[o + 2] = (above[i + 2] + below[i + 2]) >> 1
    if height % 2 == 0:  # last line (odd) has no line below: copy the one above
        last = (height - 1) * stride
        out[last:last + stride] = data[last - stride:last]
    return bytes(out)
