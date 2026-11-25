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


# ---------------------------------------------------------------- video codec
_MKV_CODECS = ((b"V_AV1", "av1"), (b"V_MPEGH/ISO/HEVC", "hevc"), (b"V_MPEG4/ISO/AVC", "h264"),
               (b"V_VP9", "vp9"), (b"V_VP8", "vp8"), (b"V_MPEG2", "mpeg2"))
_MP4_CODECS = ((b"av01", "av1"), (b"hvc1", "hevc"), (b"hev1", "hevc"), (b"avc1", "h264"),
               (b"avc3", "h264"), (b"vp09", "vp9"), (b"mp4v", "mpeg4"))


def video_codec(path):
    """Short codec name ('av1', 'hevc', 'h264', 'vp9'...) from the container
    headers, or '' if unknown.  Only reads a small part of the file."""
    try:
        r, close = open_reader(path)
    except Exception:
        return ""
    try:
        head = r.read_at(0, 16)
        if head[4:8] in (b"ftyp", b"moov", b"mdat", b"free", b"wide", b"skip", b"pnot"):
            for typ, s, e in _mp4_boxes(r, 0, r.size):
                if typ == b"moov":
                    data = r.read_at(s, min(e - s, 256 * 1024))
                    for tag, name in _MP4_CODECS:
                        if tag in data:
                            return name
                    return ""
            return ""
        if head[:4] == b"\x1a\x45\xdf\xa3":
            data = r.read_at(0, 512 * 1024)
            for tag, name in _MKV_CODECS:
                if tag in data:
                    return name
        return ""
    except Exception:
        return ""
    finally:
        try:
            close()
        except Exception:
            pass


# ---------------------------------------------------------------- music video details
# Frame rate, whether there's an audio track and the file's own tags, read in
# one read-only pass with the duration (Boombox: frame-rate groups, captions).
_TAG_KEYS = {"artist": "artist", "performer": "artist", "title": "title",
             "album": "album", "label": "label", "publisher": "label", "date_recorded": "date",
             "date_released": "date", "date": "date", "year": "date"}


# Which containers give a frame rate: 1 = MP4/MKV, 2 = also AVI and MPEG-1/2 in PS/TS.
# Caches that saved "no frame rate" with an older reader read the file once more.
FPS_READER = 2


def media_info(path):
    """{"dur", "fps", "audio", "codec", "tags"} or None when unreadable.
    fps is 0 when unknown, audio None when unknown; tags hold artist, title,
    album, label and date as written in the file (missing ones left out)."""
    try:
        r, close = open_reader(path)
    except Exception:
        return None
    info = None
    try:
        if r.size < 32:
            return None
        head = r.read_at(0, 16)
        if head[4:8] in (b"ftyp", b"moov", b"mdat", b"free", b"wide", b"skip", b"pnot"):
            info = _mp4_info(r)
        elif head[:4] == b"\x1a\x45\xdf\xa3":
            info = _mkv_media(r)
        elif head[:4] == b"RIFF" and head[8:12] == b"AVI ":
            info = _avi_info(r)
        elif head[:4] == b"\x00\x00\x01\xba" or head[0:1] == b"\x47" or \
                path.lower().endswith((".mpg", ".mpeg", ".vob", ".m2v", ".ts", ".m2ts", ".mts")):
            info = {"dur": 0, "fps": _mpeg_fps(r), "audio": None, "codec": "", "tags": {}}
    except Exception:
        info = None
    finally:
        try:
            close()
        except Exception:
            pass
    if info is None or not info.get("dur"):
        d = duration(path)          # other containers: the length is all we can read
        if d <= 0:
            return None
        info = info or {"fps": 0, "audio": None, "codec": "", "tags": {}}
        info["dur"] = d
        info["codec"] = info.get("codec") or video_codec(path)
    return info


def _avi_info(r):
    """AVI: frame rate from the video stream header (strh rate / scale: exact,
    24000/1001), else the main header's microseconds per frame; audio from an
    'auds' stream header."""
    head = r.read_at(0, 65536)
    fps, audio = 0.0, False
    i = head.find(b"strh")
    while 0 <= i and i + 36 <= len(head):
        kind = head[i + 8:i + 12]
        if kind == b"vids" and not fps:
            scale, rate = struct.unpack("<II", head[i + 28:i + 36])
            if scale and rate:
                fps = float(rate) / scale
        elif kind == b"auds":
            audio = True
        i = head.find(b"strh", i + 4)
    if not fps:
        j = head.find(b"avih")
        if j >= 0:
            usec, = struct.unpack("<I", head[j + 8:j + 12])
            fps = 1e6 / usec if usec else 0.0
    if not 1 <= fps <= 300:
        fps = 0.0
    return {"dur": _avi(r), "fps": round(fps, 3), "audio": audio, "codec": "", "tags": {}}


# MPEG-1/2 video sequence header frame_rate_code -> frames a second
_MPEG_RATES = {1: 24000 / 1001.0, 2: 24.0, 3: 25.0, 4: 30000 / 1001.0, 5: 30.0, 6: 50.0,
               7: 60000 / 1001.0, 8: 60.0}


def _mpeg_fps(r):
    """MPEG-PS / TS with MPEG-1/2 video: frame_rate_code from the first sequence
    header (00 00 01 B3) in the first 2 MB.  0 for H.264 / HEVC in TS (no such header)."""
    buf = r.read_at(0, 2 * 1024 * 1024)
    i = buf.find(b"\x00\x00\x01\xb3")
    while 0 <= i and i + 12 <= len(buf):
        b = buf[i + 4:i + 12]
        w = (b[0] << 4) | (b[1] >> 4)
        h = ((b[1] & 0x0F) << 8) | b[2]
        aspect, code = b[3] >> 4, b[3] & 0x0F
        marker = (b[6] >> 5) & 1          # after the 18-bit bit_rate
        if w and h and 1 <= aspect <= 4 and code in _MPEG_RATES and marker:
            return round(_MPEG_RATES[code], 3)
        i = buf.find(b"\x00\x00\x01\xb3", i + 4)
    return 0.0


def _tag(tags, name, value):
    key = _TAG_KEYS.get((name or "").strip().lower())
    value = (value or "").strip().strip("\x00").strip()
    if key and value and key not in tags:
        tags[key] = value


# -- Matroska: Info, Tracks and Tags (found directly or through the SeekHead;
#    ffmpeg writes the file's tags after the video, reached with one more read)
_MKV_INFO, _MKV_TRACKS, _MKV_TAGS, _MKV_SEEKHEAD, _MKV_CLUSTER = (
    0x1549A966, 0x1654AE6B, 0x1254C367, 0x114D9B74, 0x1F43B675)


def _ebml_children(buf):
    i = 0
    while i < len(buf):
        try:
            eid, l1, _ = _vint(buf, i, True)
            sz, l2, unknown = _vint(buf, i + l1)
        except (IndexError, ValueError):
            return
        start = i + l1 + l2
        if unknown:
            sz = len(buf) - start
        yield eid, buf[start:start + sz]
        i = start + sz


def _uint(b):
    return int.from_bytes(b, "big") if b else 0


def _mkv_seeks(r, data, size, seg_start, out):
    for eid, body in _ebml_children(r.read_at(data, min(size, 16384))):
        if eid != 0x4DBB:
            continue
        sid = spos = None
        for e2, val in _ebml_children(body):
            if e2 == 0x53AB:
                sid = _uint(val)
            elif e2 == 0x53AC:
                spos = _uint(val)
        if sid is not None and spos is not None:
            out.setdefault(sid, []).append(seg_start + spos)


def _mkv_element(r, pos, want, limit):
    """(data position, size) of the element at pos if it is a `want` element."""
    buf = r.read_at(pos, 16)
    if len(buf) < 2:
        return None
    eid, l1, _ = _vint(buf, 0, True)
    sz, l2, _ = _vint(buf, l1)
    if eid != want:
        return None
    return pos + l1 + l2, min(sz, limit)


def _mkv_tracks(buf):
    """(fps, audio, codec) from a Tracks element."""
    fps, audio, codec = 0.0, False, ""
    for eid, entry in _ebml_children(buf):
        if eid != 0xAE:                       # TrackEntry
            continue
        ttype, ddur, rate, cid = 0, 0, 0.0, b""
        for e3, val in _ebml_children(entry):
            if e3 == 0x83:
                ttype = _uint(val)
            elif e3 == 0x23E383:              # DefaultDuration (ns per frame)
                ddur = _uint(val)
            elif e3 == 0x86:
                cid = val
            elif e3 == 0xE0:                  # Video > FrameRate (old files)
                for e4, v4 in _ebml_children(val):
                    if e4 == 0x2383E3 and len(v4) in (4, 8):
                        rate = struct.unpack(">f" if len(v4) == 4 else ">d", v4)[0]
        if ttype == 1 and not fps:
            fps = 1e9 / ddur if ddur else rate
            for tag, name in _MKV_CODECS:
                if cid.startswith(tag):
                    codec = name
                    break
        elif ttype == 2:
            audio = True
    return fps, audio, codec


def _mkv_tags(buf, tags):
    """The file's own tags (not one track's, chapter's or attachment's)."""
    for eid, tag in _ebml_children(buf):
        if eid != 0x7373:
            continue
        kids = list(_ebml_children(tag))
        bound = any(e3 == 0x63C0 and any(e4 in (0x63C5, 0x63C9, 0x63C4, 0x63C6) and _uint(v4)
                                         for e4, v4 in _ebml_children(val))
                    for e3, val in kids)
        if bound:
            continue
        for e3, val in kids:
            if e3 != 0x67C8:                  # SimpleTag
                continue
            name = value = ""
            for e4, v4 in _ebml_children(val):
                if e4 == 0x45A3:
                    name = v4.decode("utf-8", "replace")
                elif e4 == 0x4487:
                    value = v4.decode("utf-8", "replace")
            _tag(tags, name, value)


def _mkv_media(r):
    for eid, data, size in _ebml_elements(r, 0, r.size):
        if eid != 0x18538067:          # Segment
            continue
        seg_start, seg_end = data, min(r.size, data + size)
        found, seeks = {}, {}
        for cid, cdata, csize in _ebml_elements(r, seg_start, seg_end):
            if cid == _MKV_CLUSTER:
                break
            if cid == _MKV_SEEKHEAD:
                _mkv_seeks(r, cdata, csize, seg_start, seeks)
            elif cid in (_MKV_INFO, _MKV_TRACKS, _MKV_TAGS):
                found.setdefault(cid, []).append((cdata, csize))
        for pos in seeks.get(_MKV_SEEKHEAD, []):      # a second SeekHead (often at the end)
            el = _mkv_element(r, pos, _MKV_SEEKHEAD, 16384)
            if el:
                _mkv_seeks(r, el[0], el[1], seg_start, seeks)
        for want in (_MKV_INFO, _MKV_TRACKS, _MKV_TAGS):
            have = set(p for p, _s in found.get(want, []))
            for pos in seeks.get(want, []):
                el = _mkv_element(r, pos, want, 1 << 20)
                if el and el[0] not in have:
                    have.add(el[0])
                    found.setdefault(want, []).append(el)
        if _MKV_INFO not in found:
            return None
        cdata, csize = found[_MKV_INFO][0]
        dur = _mkv_info(r, cdata, csize)
        title = ""
        for e2, val in _ebml_children(r.read_at(cdata, min(csize, 8192))):
            if e2 == 0x7BA9:                  # the segment's title
                title = val.decode("utf-8", "replace")
        fps, audio, codec = 0.0, None, ""
        if found.get(_MKV_TRACKS):
            cdata, csize = found[_MKV_TRACKS][0]
            fps, audio, codec = _mkv_tracks(r.read_at(cdata, min(csize, 65536)))
        tags = {}
        for cdata, csize in found.get(_MKV_TAGS, []):
            _mkv_tags(r.read_at(cdata, min(csize, 1 << 20)), tags)
        if title:
            _tag(tags, "title", title)
        return {"dur": dur, "fps": round(fps, 3), "audio": audio, "codec": codec, "tags": tags}
    return None


# -- MP4: each trak's handler, timescale and sample durations; udta/meta/ilst tags
_ILST = {b"\xa9ART": "artist", b"\xa9nam": "title", b"\xa9alb": "album",
         b"\xa9day": "date", b"\xa9pub": "label", b"\xa9lab": "label"}


def _mp4_child(r, s, e, path):
    for typ, s2, e2 in _mp4_boxes(r, s, e):
        if typ == path[0]:
            return (s2, e2) if len(path) == 1 else _mp4_child(r, s2, e2, path[1:])
    return None


def _mp4_video_track(r, mdia):
    """(fps, codec) of a video track: its most common sample duration (variable
    frame rate files vary around their nominal rate)."""
    fps, codec = 0.0, ""
    mdhd = _mp4_child(r, mdia[0], mdia[1], [b"mdhd"])
    scale = 0
    if mdhd:
        h = r.read_at(mdhd[0], 32)
        scale = struct.unpack(">I", h[20:24] if h[0] == 1 else h[12:16])[0]
    stbl = _mp4_child(r, mdia[0], mdia[1], [b"minf", b"stbl"])
    if not stbl:
        return fps, codec
    stts = _mp4_child(r, stbl[0], stbl[1], [b"stts"])
    if stts and scale:
        h = r.read_at(stts[0], min(stts[1] - stts[0], 8 + 8 * 4096))
        n = struct.unpack(">I", h[4:8])[0]
        counts = {}
        for k in range(min(n, (len(h) - 8) // 8)):
            c, d = struct.unpack(">II", h[8 + 8 * k:16 + 8 * k])
            if d:
                counts[d] = counts.get(d, 0) + c
        if counts:
            fps = float(scale) / max(counts, key=lambda d: counts[d])
    stsd = _mp4_child(r, stbl[0], stbl[1], [b"stsd"])
    if stsd:
        fmt = r.read_at(stsd[0] + 12, 4)
        codec = next((name for tag, name in _MP4_CODECS if fmt == tag), "")
    return fps, codec


def _mp4_tags(r, moov):
    tags = {}
    meta = _mp4_child(r, moov[0], moov[1], [b"udta", b"meta"])
    # 'meta' is a full box: 4 bytes of version and flags before its children
    ilst = _mp4_child(r, meta[0] + 4, meta[1], [b"ilst"]) if meta else None
    if not ilst:
        return tags
    for typ, s, e in _mp4_boxes(r, ilst[0], ilst[1]):
        name, value, free = _ILST.get(typ), "", None
        for t2, s2, e2 in _mp4_boxes(r, s, e):
            body = r.read_at(s2, min(e2 - s2, 4096))
            if t2 == b"name":                 # '----' freeform, e.g. com.apple.iTunes:LABEL
                free = body[4:].decode("utf-8", "replace")
            elif t2 == b"data":
                value = body[8:].decode("utf-8", "replace")
        if typ == b"----" and free:
            name = _TAG_KEYS.get(free.lower())
        if name:
            _tag(tags, name, value)
    return tags


def _mp4_info(r):
    moov = _mp4_child(r, 0, r.size, [b"moov"])
    if not moov:
        return None
    fps, audio, codec = 0.0, False, ""
    for typ, s, e in _mp4_boxes(r, moov[0], moov[1]):
        if typ != b"trak":
            continue
        mdia = _mp4_child(r, s, e, [b"mdia"])
        hdlr = _mp4_child(r, mdia[0], mdia[1], [b"hdlr"]) if mdia else None
        kind = r.read_at(hdlr[0] + 8, 4) if hdlr else b""
        if kind == b"soun":
            audio = True
        elif kind == b"vide" and not fps:
            fps, codec = _mp4_video_track(r, mdia)
    return {"dur": _mp4(r), "fps": round(fps, 3), "audio": audio, "codec": codec, "tags": _mp4_tags(r, moov)}


# ---------------------------------------------------------------- chapters
# Chapter marks for commercial breaks at act breaks (chapters.py decides what they
# mean).  Read-only, a few small reads: Matroska's Chapters element (found directly
# or through the SeekHead) and MP4's Nero 'chpl' box.  Apple chapter text tracks,
# AVI and TS (no chapters) give [].
_MKV_CHAPTERS = 0x1043A770


def chapters(path):
    """{"dur": seconds, "ch": [[start s, name], ...]} ("ch" empty: no chapters), or
    None when the file can't be read."""
    try:
        r, close = open_reader(path)
    except Exception:
        return None
    try:
        if r.size < 32:
            return None
        head = r.read_at(0, 16)
        if head[4:8] in (b"ftyp", b"moov", b"mdat", b"free", b"wide", b"skip", b"pnot"):
            return {"dur": round(_mp4(r), 2), "ch": _mp4_chapters(r)}
        if head[:4] == b"\x1a\x45\xdf\xa3":
            return {"dur": round(_mkv(r), 2), "ch": _mkv_chapters(r)}
        return {"dur": round(duration(path), 2), "ch": []}
    except Exception:
        return None
    finally:
        try:
            close()
        except Exception:
            pass


def _mkv_chapters(r):
    for eid, data, size in _ebml_elements(r, 0, r.size):
        if eid != 0x18538067:          # Segment
            continue
        seg_start, seg_end = data, min(r.size, data + size)
        found, seeks = [], {}
        for cid, cdata, csize in _ebml_elements(r, seg_start, seg_end):
            if cid == _MKV_CLUSTER:
                break
            if cid == _MKV_SEEKHEAD:
                _mkv_seeks(r, cdata, csize, seg_start, seeks)
            elif cid == _MKV_CHAPTERS:
                found.append((cdata, csize))
        for pos in seeks.get(_MKV_SEEKHEAD, []):
            el = _mkv_element(r, pos, _MKV_SEEKHEAD, 16384)
            if el:
                _mkv_seeks(r, el[0], el[1], seg_start, seeks)
        if not found:
            for pos in seeks.get(_MKV_CHAPTERS, []):
                el = _mkv_element(r, pos, _MKV_CHAPTERS, 1 << 20)
                if el:
                    found.append(el)
                    break
        if not found:
            return []
        cdata, csize = found[0]
        editions = []
        for e1, ed in _ebml_children(r.read_at(cdata, min(csize, 1 << 20))):
            if e1 != 0x45B9:            # EditionEntry
                continue
            default, atoms = False, []
            for e2, val in _ebml_children(ed):
                if e2 == 0x45DB:        # EditionFlagDefault
                    default = _uint(val) == 1
                elif e2 == 0xB6:        # ChapterAtom
                    start, name, show = None, "", True
                    for e3, v3 in _ebml_children(val):
                        if e3 == 0x91:                  # ChapterTimeStart (ns)
                            start = _uint(v3) / 1e9
                        elif e3 == 0x98 and _uint(v3):  # ChapterFlagHidden
                            show = False
                        elif e3 == 0x4598 and v3 and not _uint(v3):   # ChapterFlagEnabled = 0
                            show = False
                        elif e3 == 0x80 and not name:   # ChapterDisplay
                            for e4, v4 in _ebml_children(v3):
                                if e4 == 0x85:          # ChapString
                                    name = v4.decode("utf-8", "replace").strip()
                    if start is not None and show:
                        atoms.append([round(start, 3), name])
            editions.append((default, atoms))
        if not editions:
            return []
        atoms = next((a for d, a in editions if d), editions[0][1])
        return sorted(atoms, key=lambda c: c[0])
    return []


def _mp4_chapters(r):
    chpl = _mp4_child(r, 0, r.size, [b"moov", b"udta", b"chpl"])
    if not chpl:
        return []
    buf = r.read_at(chpl[0], min(chpl[1] - chpl[0], 65536))
    if len(buf) < 5:
        return []
    i = 4 + (4 if buf[0] == 1 else 0)            # version, flags (version 1: 4 more bytes)
    n = buf[i]
    i += 1
    out = []
    for _k in range(n):
        if i + 9 > len(buf):
            break
        start = struct.unpack(">Q", buf[i:i + 8])[0] / 1e7       # 100 ns units
        ln = buf[i + 8]
        name = buf[i + 9:i + 9 + ln].decode("utf-8", "replace").strip()
        out.append([round(start, 3), name])
        i += 9 + ln
    return sorted(out, key=lambda c: c[0])
