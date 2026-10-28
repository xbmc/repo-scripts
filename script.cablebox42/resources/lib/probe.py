"""Pure-python media duration probing.

Many Kodi devices have no ffprobe, and Kodi only knows durations of items that were
scanned into the library.  To schedule commercials and folder-based content
we read the container headers directly: MP4/MOV/M4V, MKV/WebM, AVI and
MPEG-TS are covered.  Only a few small reads are needed, so this works over
SMB/NFS too.
"""
import struct


class _Reader(object):
    """Adapter over xbmcvfs.File or a regular binary file object."""

    def __init__(self, fobj, size, vfs=False):
        self.f = fobj
        self.size = size
        self.vfs = vfs

    def read_at(self, pos, n):
        if pos < 0 or pos >= self.size:
            return b""
        self.f.seek(pos, 0)
        if self.vfs:
            return bytes(self.f.readBytes(n))
        return self.f.read(n)


def open_reader(path):
    """Return (_Reader, closer).  Uses xbmcvfs when available."""
    try:
        import xbmcvfs  # noqa
        f = xbmcvfs.File(path, "rb")
        size = f.size()
        return _Reader(f, size, vfs=True), f.close
    except ImportError:
        f = open(path, "rb")
        f.seek(0, 2)
        size = f.tell()
        return _Reader(f, size), f.close


def duration(path):
    """Duration in seconds (float) or 0 if it cannot be determined."""
    try:
        r, close = open_reader(path)
    except Exception:
        return 0
    try:
        if r.size < 32:
            return 0
        head = r.read_at(0, 16)
        if head[4:8] in (b"ftyp", b"moov", b"mdat", b"free", b"wide", b"skip", b"pnot"):
            return _mp4(r)
        if head[:4] == b"\x1a\x45\xdf\xa3":
            return _mkv(r)
        if head[:4] == b"RIFF" and head[8:12] == b"AVI ":
            return _avi(r)
        if head[:16] == ASF_HEADER:
            return _asf(r)
        if head[:3] == b"FLV":
            return _flv(r)
        if head[:4] == b"\x00\x00\x01\xba":
            return _ps(r)
        if head[0:1] == b"\x47" or path.lower().endswith((".ts", ".m2ts", ".mts")):
            return _ts(r)
        if path.lower().endswith((".mpg", ".mpeg", ".vob", ".m2v")):
            return _ps(r)
        return 0
    except Exception:
        return 0
    finally:
        try:
            close()
        except Exception:
            pass


# ---------------------------------------------------------------- MP4 / MOV
def _mp4_boxes(r, start, end):
    pos = start
    while pos + 8 <= end:
        h = r.read_at(pos, 16)
        if len(h) < 8:
            return
        size = struct.unpack(">I", h[:4])[0]
        typ = h[4:8]
        hdr = 8
        if size == 1:
            size = struct.unpack(">Q", h[8:16])[0]
            hdr = 16
        elif size == 0:
            size = end - pos
        if size < hdr:
            return
        yield typ, pos + hdr, pos + size
        pos += size


def _mp4(r):
    for typ, s, e in _mp4_boxes(r, 0, r.size):
        if typ == b"moov":
            for t2, s2, e2 in _mp4_boxes(r, s, e):
                if t2 == b"mvhd":
                    d = r.read_at(s2, 32)
                    if d[0] == 1:
                        scale, dur = struct.unpack(">IQ", d[20:32])
                    else:
                        scale, dur = struct.unpack(">II", d[12:20])
                    return float(dur) / scale if scale else 0
    return 0


# ---------------------------------------------------------------- Matroska
def _vint(buf, i, keep_marker=False):
    b = buf[i]
    mask = 0x80
    length = 1
    while length <= 8 and not (b & mask):
        mask >>= 1
        length += 1
    if length > 8:
        raise ValueError("bad vint")
    val = b if keep_marker else (b & (mask - 1))
    unknown = (b & (mask - 1)) == (mask - 1)
    for k in range(1, length):
        nb = buf[i + k]
        val = (val << 8) | nb
        unknown = unknown and nb == 0xFF
    return val, length, unknown


def _ebml_elements(r, start, end, chunk=64):
    pos = start
    while pos < end:
        buf = r.read_at(pos, chunk)
        if len(buf) < 2:
            return
        eid, l1, _ = _vint(buf, 0, keep_marker=True)
        size, l2, unknown = _vint(buf, l1)
        data = pos + l1 + l2
        if unknown:
            size = end - data
        yield eid, data, size
        pos = data + size


def _mkv(r):
    for eid, data, size in _ebml_elements(r, 0, r.size):
        if eid == 0x18538067:  # Segment
            seg_start = data
            seg_end = min(r.size, data + size)
            info_pos = None
            for cid, cdata, csize in _ebml_elements(r, seg_start, seg_end):
                if cid == 0x1549A966:  # Info
                    return _mkv_info(r, cdata, csize)
                if cid == 0x114D9B74 and info_pos is None:  # SeekHead
                    info_pos = _mkv_seek_info(r, cdata, csize, seg_start)
                    if info_pos is not None:
                        buf = r.read_at(info_pos, 16)
                        iid, l1, _ = _vint(buf, 0, True)
                        isz, l2, _ = _vint(buf, l1)
                        if iid == 0x1549A966:
                            return _mkv_info(r, info_pos + l1 + l2, isz)
                if cid == 0x1F43B675:  # Cluster reached - give up
                    break
            break
    return 0


def _mkv_seek_info(r, data, size, seg_start):
    buf = r.read_at(data, min(size, 4096))
    i = 0
    while i < len(buf):
        eid, l1, _ = _vint(buf, i, True)
        sz, l2, _ = _vint(buf, i + l1)
        body = buf[i + l1 + l2:i + l1 + l2 + sz]
        if eid == 0x4DBB:  # Seek
            j = 0
            sid = None
            spos = None
            while j < len(body):
                e2, m1, _ = _vint(body, j, True)
                s2, m2, _ = _vint(body, j + m1)
                val = body[j + m1 + m2:j + m1 + m2 + s2]
                if e2 == 0x53AB:
                    sid = int.from_bytes(val, "big")
                elif e2 == 0x53AC:
                    spos = int.from_bytes(val, "big")
                j += m1 + m2 + s2
            if sid == 0x1549A966 and spos is not None:
                return seg_start + spos
        i += l1 + l2 + sz
    return None


def _mkv_info(r, data, size):
    buf = r.read_at(data, min(size, 8192))
    scale = 1000000
    dur = None
    i = 0
    while i < len(buf):
        eid, l1, _ = _vint(buf, i, True)
        sz, l2, _ = _vint(buf, i + l1)
        val = buf[i + l1 + l2:i + l1 + l2 + sz]
        if eid == 0x2AD7B1:
            scale = int.from_bytes(val, "big")
        elif eid == 0x4489:
            if sz == 4:
                dur = struct.unpack(">f", val)[0]
            elif sz == 8:
                dur = struct.unpack(">d", val)[0]
        i += l1 + l2 + sz
    if dur is None:
        return 0
    return dur * scale / 1e9


# ---------------------------------------------------------------- AVI
def _avi(r):
    head = r.read_at(0, 65536)
    i = head.find(b"avih")
    if i < 0:
        return 0
    usec, = struct.unpack("<I", head[i + 8:i + 12])
    frames, = struct.unpack("<I", head[i + 24:i + 28])
    j = head.find(b"dmlh")
    if j >= 0:
        frames = max(frames, struct.unpack("<I", head[j + 8:j + 12])[0])
    return usec * frames / 1e6


# ---------------------------------------------------------------- MPEG-TS
def _ts_pcrs(buf):
    out = []
    start = buf.find(b"\x47")
    while start >= 0 and start + 188 <= len(buf):
        if buf[start] != 0x47:
            start = buf.find(b"\x47", start + 1)
            continue
        pkt = buf[start:start + 188]
        pid = ((pkt[1] & 0x1F) << 8) | pkt[2]
        afc = (pkt[3] >> 4) & 0x3
        if afc in (2, 3) and pkt[4] >= 7 and (pkt[5] & 0x10):
            b = pkt[6:12]
            base = (b[0] << 25) | (b[1] << 17) | (b[2] << 9) | (b[3] << 1) | (b[4] >> 7)
            ext = ((b[4] & 1) << 8) | b[5]
            out.append((pid, base * 300 + ext))
        start += 188
    return out


def _ts(r):
    span = 2 * 1024 * 1024
    first = _ts_pcrs(r.read_at(0, span))
    last = _ts_pcrs(r.read_at(max(0, r.size - span), span))
    if not first or not last:
        return 0
    pid, p0 = first[0]
    tail = [p for (pp, p) in last if pp == pid]
    if not tail:
        return 0
    d = (tail[-1] - p0) / 27e6
    return d if d > 0 else 0


# ---------------------------------------------------------------- MPEG-PS (.mpg .vob)
def _scrs(buf):
    out = []
    i = buf.find(b"\x00\x00\x01\xba")
    while i >= 0 and i + 10 <= len(buf):
        b = buf[i + 4:i + 9]
        if (b[0] & 0xC0) == 0x40:      # MPEG-2 pack header
            scr = (((b[0] >> 3) & 7) << 30) | ((b[0] & 3) << 28) | (b[1] << 20) | \
                  (((b[2] >> 3) & 0x1F) << 15) | ((b[2] & 3) << 13) | (b[3] << 5) | (b[4] >> 3)
            out.append(scr)
        elif (b[0] & 0xF0) == 0x20:    # MPEG-1 pack header
            scr = (((b[0] >> 1) & 7) << 30) | (b[1] << 22) | ((b[2] >> 1) << 15) | \
                  (b[3] << 7) | (b[4] >> 1)
            out.append(scr)
        i = buf.find(b"\x00\x00\x01\xba", i + 4)
    return out


def _ps(r):
    span = 2 * 1024 * 1024
    first = _scrs(r.read_at(0, span))
    last = _scrs(r.read_at(max(0, r.size - span), span))
    if not first or not last:
        return 0
    d = (last[-1] - first[0]) / 90000.0
    return d if d > 0 else 0


# ---------------------------------------------------------------- ASF (.wmv .wma .asf)
ASF_HEADER = bytes.fromhex("3026b2758e66cf11a6d900aa0062ce6c")
ASF_FILEPROPS = bytes.fromhex("a1dcab8c47a9cf118ee400c00c205365")


def _asf(r):
    head = r.read_at(0, 65536)
    i = head.find(ASF_FILEPROPS)
    if i < 0:
        return 0
    base = i + 24  # GUID + object size
    play, = struct.unpack("<Q", head[base + 40:base + 48])
    preroll, = struct.unpack("<Q", head[base + 56:base + 64])
    d = play / 1e7 - preroll / 1000.0
    return d if d > 0 else 0


# ---------------------------------------------------------------- FLV
def _flv(r):
    head = r.read_at(0, 65536)
    i = head.find(b"duration")
    if i >= 0 and head[i + 8:i + 9] == b"\x00":
        d, = struct.unpack(">d", head[i + 9:i + 17])
        if d > 0:
            return d
    tail = r.read_at(r.size - 4, 4)
    if len(tail) == 4:
        prev, = struct.unpack(">I", tail)
        tag = r.read_at(r.size - 4 - prev, 8)
        if len(tag) == 8:
            ts = (tag[4] << 16) | (tag[5] << 8) | tag[6] | (tag[7] << 24)
            return ts / 1000.0
    return 0
