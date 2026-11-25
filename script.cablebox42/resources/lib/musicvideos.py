"""Music videos for Boombox: names, captions, frame-rate groups and rotation.

No Kodi imports, so all of this can be tested outside Kodi.  Each caption line
comes from the first place that has it: Kodi's library, the file's own tags,
then the file name read as "Artist - Title (Year)".
"""
import random
import re

MIN_VIDEOS = 30            # Build my lineup offers Boombox from this many videos
MIN_SECONDS = 30           # anything shorter is skipped
GROUP_MIN = 20 * 60        # a frame-rate group shorter than this joins the nearest one
CAPTION_IN, CAPTION_FOR, CAPTION_END = 2.0, 8.0, 10.0      # seconds
CAPTION_SHORT = 60.0       # shorter videos: the opening caption only

_SKIP_WORDS = re.compile(r"(^|[\s._\-(\[])(trailer|sample)([\s._\-)\]]|$)", re.I)
_NAME = re.compile(r"^(?P<artist>.+?) - (?P<title>.+?)(?:\s*[(\[](?P<year>(?:19|20)\d\d)[)\]])?$")
_YEAR = re.compile(r"(?:^|\D)((?:19|20)\d\d)(?:\D|$)")
# '(Official Video)', '[HD]', '(Lyric Video)', '(Remastered 2009)'... at the end of a title
_NOISE = re.compile(r"\s*[(\[][^)\]]*\b(official|video|hd|hq|4k|1080p|720p|remaster(ed)?|lyrics?|audio|"
                    r"explicit|clean|uncensored|visuali[sz]er)\b[^)\]]*[)\]]\s*$", re.I)


def stem(path):
    name = re.split(r"[\\/]", path.rstrip("/\\"))[-1]
    return re.sub(r"\.[A-Za-z0-9]{2,4}$", "", name)


def clean(text):
    """A title without download leftovers ('_', '.', '(Official Video)')."""
    t = (text or "").strip()
    if " " not in t and ("_" in t or "." in t):
        t = t.replace("_", " ").replace(".", " ")
    prev = None
    while prev != t:
        prev = t
        t = _NOISE.sub("", t).strip()
    return re.sub(r"\s{2,}", " ", t).strip(" -")


def parse_name(path):
    """{"artist", "title", "year"} from "Artist - Title (Year)" (the space on each
    side of the hyphen matters; the year is optional), or {"title"} with the
    cleaned file name when the name doesn't follow it."""
    s = stem(path).strip()
    m = _NAME.match(s)
    if m and m.group("artist").strip() and clean(m.group("title")):
        out = {"artist": m.group("artist").strip(), "title": clean(m.group("title"))}
        if m.group("year"):
            out["year"] = m.group("year")
        return out
    return {"title": clean(s) or s}


def year_of(value):
    if isinstance(value, int):
        return str(value) if 1900 <= value <= 2100 else ""
    m = _YEAR.search(str(value or ""))
    return m.group(1) if m else ""


def _joined(v):
    if isinstance(v, (list, tuple)):
        return ", ".join(x.strip() for x in v if x and x.strip())
    return (v or "").strip()


def merge(lib=None, tags=None, path=""):
    """The caption's facts: artist, title, album, label, year - each from the
    library, else the file's tags, else the file name.  Missing ones are left out.
    A title tag counts only next to an artist tag: on its own it is usually
    whatever the downloader saw (a film's name, 'Artist - Title (Official Video)')."""
    lib, tags, name = lib or {}, tags or {}, parse_name(path)
    tag_title = clean(tags.get("title", "")) if tags.get("artist") else ""
    out = {
        "artist": _joined(lib.get("artist")) or (tags.get("artist") or "").strip() or name.get("artist", ""),
        "title": (lib.get("title") or "").strip() or tag_title or name.get("title", ""),
        "album": (lib.get("album") or "").strip() or (tags.get("album") or "").strip(),
        "label": _joined(lib.get("studio")) or (tags.get("label") or "").strip(),
        "year": year_of(lib.get("year")) or year_of(tags.get("date")) or name.get("year", ""),
    }
    if not out["artist"] and not lib and not tag_title:
        # no recognisable name and no tags: just the title
        out = {"title": out["title"]}
    return dict((k, v) for k, v in out.items() if v)


def caption(info):
    """[(role, text)] in order - artist, "title", album, label, year - with every
    line that has nothing left out."""
    lines = []
    for role in ("artist", "title", "album", "label", "year"):
        v = (info.get(role) or "").strip()
        if v:
            lines.append((role, u"“%s”" % v if role == "title" else v))
    return lines


def caption_times(dur):
    """[(from, to)] seconds into the video: shortly after it starts and again
    shortly before it ends (short videos: the first only)."""
    first = (CAPTION_IN, CAPTION_IN + CAPTION_FOR)
    if dur < CAPTION_SHORT:
        return [first] if dur > CAPTION_IN + 2 else []
    return [first, (dur - CAPTION_END, dur - CAPTION_END + CAPTION_FOR)]


def label(info):
    """One line for lists and the player: Artist - Title."""
    if info.get("artist"):
        return u"%s - %s" % (info["artist"], info.get("title", ""))
    return info.get("title", "")


def skip_reason(path, dur=None, audio=None):
    """Why a file doesn't air on Boombox ('' when it does).  dur/audio None = not known yet."""
    if _SKIP_WORDS.search(stem(path)):
        return "trailer or sample"
    if dur is not None and 0 < dur < MIN_SECONDS:
        return "shorter than %d s" % MIN_SECONDS
    if audio is False:
        return "no audio track"
    return ""


# ------------------------------------------------------------------ frame rates
def family(fps):
    """A video's frame-rate group: 24.000 rides along with 23.976 and 30 with
    29.97 (the TV switches once for either); other rates are groups of their own."""
    if not fps:
        return ""
    for name, lo, hi in (("23.976", 23.9, 24.05), ("29.97", 29.9, 30.05), ("25", 24.9, 25.1),
                         ("50", 49.9, 50.1), ("59.94", 59.8, 60.05), ("47.952", 47.9, 48.05)):
        if lo <= fps <= hi:
            return name
    return ("%.3f" % fps).rstrip("0").rstrip(".")


def _rate(name):
    try:
        return float(name)
    except ValueError:
        return 0.0


def groups(videos):
    """{path: group} for [(path, fps, seconds)].  A group too short to fill a
    block joins the one with the nearest rate; videos whose rate isn't known
    yet join the largest group."""
    total, members = {}, {}
    unknown = []
    for path, fps, dur in videos:
        g = family(fps)
        if not g:
            unknown.append(path)
            continue
        total[g] = total.get(g, 0.0) + float(dur or 0)
        members.setdefault(g, []).append(path)
    if not total:
        return dict((p, "any") for p in unknown)
    big = [g for g in total if total[g] >= GROUP_MIN] or [max(total, key=lambda g: total[g])]
    into = {}
    for g in total:
        into[g] = g if g in big else min(big, key=lambda b: (abs(_rate(b) - _rate(g)), -total[b]))
    out = {}
    for g, paths in members.items():
        for p in paths:
            out[p] = into[g]
    sizes = {}
    for g in total:
        sizes[into[g]] = sizes.get(into[g], 0.0) + total[g]
    largest = max(sizes, key=lambda g: sizes[g])
    for p in unknown:
        out[p] = largest
    return out


def next_group(state, sizes):
    """The frame-rate group for the next block: each group keeps pace with its
    share of the library (60% of the videos at 23.976 -> about 6 blocks in 10)."""
    credit = state.setdefault("credit", {})
    total = float(sum(sizes.values())) or 1.0
    for g in list(credit):
        if g not in sizes:
            del credit[g]
    for g, n in sizes.items():
        credit[g] = credit.get(g, 0.0) + n / total
    g = max(sorted(sizes), key=lambda k: credit[k])
    credit[g] -= 1.0
    return g


# ------------------------------------------------------------------ rotation
def artist_key(info, path):
    a = (info.get("artist") or "").strip().lower()
    return a or "#" + path          # unknown artist: never counts as a repeat


def next_video(state, group, videos, seed):
    """The next video of a group.  videos = {path: artist key} of the group.
    Every video once per round, each round shuffled into a new order; never the
    same artist as the video before (state["last"], across blocks too) unless the
    group has nothing else.  Videos new since the round began join its end."""
    qs, done, rounds = state.setdefault("q", {}), state.setdefault("done", {}), state.setdefault("round", {})
    q = [p for p in qs.get(group, []) if p in videos]
    seen = set(done.get(group, []))
    if q or seen:
        q += sorted(p for p in videos if p not in seen and p not in q)
    if not q:
        rounds[group] = rounds.get(group, 0) + 1
        q = sorted(videos)
        random.Random("%s|%s|%d" % (seed, group, rounds[group])).shuffle(q)
        done[group] = []
    last = state.get("last")
    # the artist with the most videos left goes first when the others couldn't
    # keep them apart any more (standard 'no two alike in a row' rearranging)
    count = {}
    for p in q:
        count[videos[p]] = count.get(videos[p], 0) + 1
    top = max(count, key=lambda a: count[a])
    pick = None
    if top != last and count[top] * 2 >= len(q):
        pick = next(p for p in q if videos[p] == top)
    if pick is None:
        pick = next((p for p in q if videos[p] != last), None)
    if pick is None:
        pick = q[0]                 # this group has only that artist left
    q.remove(pick)
    qs[group] = q
    done.setdefault(group, []).append(pick)
    state["last"] = videos[pick]
    return pick
