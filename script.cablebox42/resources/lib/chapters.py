"""Chapter marks -> where an episode's commercial breaks go (and where its end
credits start), without Kodi imports so it can be tested anywhere.

An episode's chapters (read from the file by probe.chapters, cached by library)
get one of four verdicts:
  act    - act breaks (the broadcast's): breaks go on the marks
  dense  - scene chapters: today's breaks, each moved to the nearest mark within 2 min
  auto   - evenly spaced automatic chapters (every 5:00...): ignored
  none   - no usable marks (none at all, one chapter, nothing left after cleanup)
Every doubtful case falls back to today's timed breaks.
"""
import re

EDGE = 15.0            # marks in the first 15 s (or the last) mean nothing
COLD_MIN = 20.0        # a cold open counts from 20 s
TAG_MIN, TAG_MAX = 20.0, 180.0     # an end tag: 20 s - 3 min
MERGE = 120.0          # marks closer than 2 min merge (cold open + main title)
ACT_PART = 6 * 60.0    # act breaks: the body's parts average 6 min or more
NUDGE = 120.0          # dense chapters: a timed break moves to a mark within 2 min
BREAK_MIN = 60.0       # each break gets at least this much of the leftover time

ACT_NAMES = re.compile(r"\b(teaser|prologue|cold open|act\s*(one|two|three|four|five|six|[1-9]|[ivx]+)|"
                       r"part\s*(one|two|three|four|[1-9])|epilogue|tag)\b", re.I)
AD_NAMES = re.compile(r"\b(advert(isement)?s?|commercials?|ad break)\b", re.I)
CREDIT_NAMES = re.compile(r"\b(end\s*credits?|credits?|end\s*titles?|closing(\s*credits)?)\b", re.I)


def _named(chs, rx):
    return any(rx.search(n or "") for _t, n in chs)


def analyze(dur, chs):
    """{"v": verdict, "m": [break marks in s], "cr": end credits start (s) or None,
    "why": a few words for the log / Check chapters}.  chs: [[start s, name], ...]."""
    dur = float(dur or 0)
    chs = sorted([[float(t), n or ""] for t, n in (chs or []) if t is not None], key=lambda c: c[0])
    cr, cr_kind = credits_start(dur, chs)
    out = {"v": "none", "m": [], "cr": cr, "why": ""}
    if dur <= 0 or len(chs) < 2:
        out["why"] = "no chapters" if not chs else "one chapter"
        return out
    # an advertisement chapter baked into the file: its edges are not act breaks
    ads = [(chs[i][0], chs[i + 1][0] if i + 1 < len(chs) else dur)
           for i, (_t, n) in enumerate(chs) if AD_NAMES.search(n or "")]
    marks = [t for t, _n in chs if EDGE <= t <= dur - EDGE]
    marks = [t for t in marks if not any(a - 1 <= t <= b + 1 for a, b in ads)]
    if _automatic(dur, [t for t, _n in chs if t > 0]):
        out.update(v="auto", why="evenly spaced (automatic)")
        return out
    # cleanup: cold open from 20 s, an end tag from 20 s, never a break at the end
    # credits; close marks merge - the later wins near the start (cold open + main
    # title), the earlier near the end (the tag before the credits)
    if cr is not None and cr_kind == "separate":
        marks = [t for t in marks if t < cr - 1]     # a credits chapter of its own: no break before it
    marks = [t for t in marks if t >= COLD_MIN]
    if marks and dur - marks[-1] < TAG_MIN:
        marks.pop()
    merged = []
    for t in marks:
        if merged and t - merged[-1] < MERGE:
            if dur - t > TAG_MAX:
                merged[-1] = t
        else:
            merged.append(t)
    marks = merged
    if not marks:
        out["why"] = "nothing left after cleanup"
        return out
    # the body: without a cold open and an end tag of up to 3 minutes
    body_s = marks[0] if marks[0] <= TAG_MAX else 0.0
    body_e = marks[-1] if dur - marks[-1] <= TAG_MAX else dur
    inner = [t for t in marks if body_s < t < body_e]
    avg = (body_e - body_s) / (len(inner) + 1)
    named = _named(chs, ACT_NAMES)
    if avg >= ACT_PART or named:
        out.update(v="act", m=marks, why="act breaks" + (" (named)" if named and avg < ACT_PART else ""))
    else:
        out.update(v="dense", m=marks, why="scene chapters (%.1f min apart)" % (avg / 60))
    return out


def _automatic(dur, starts):
    """Evenly spaced marks (every 5:00 and so on): at least 3 gaps within 2 s of each other."""
    starts = sorted(starts)
    if len(starts) < 3:
        return False
    gaps = [b - a for a, b in zip([0.0] + starts, starts)]
    gaps = gaps[:-1] if len(gaps) > 3 else gaps        # the first may be shorter after a logo
    body = gaps[1:] if len(gaps) > 3 else gaps
    return len(body) >= 3 and max(body) - min(body) <= 2.0 and min(body) >= 60


SQUEEZE_TAIL = 30.0     # tag and credits in one last chapter: squeeze its last 30 s...
SQUEEZE_WHOLE = 40.0    # ...or all of it when it's under 40 s


def credits_start(dur, chs):
    """(where the squeeze starts, "separate" | "tail") or (None, None).
    - a last chapter named like credits: all of it ("separate");
    - two short chapters at the end (a tag of 20 s - 3 min, then a last one of
      20 s - 2 min): the last one ("separate");
    - one short last chapter of 20 s - 3 min (tag and credits together, as on most
      sitcom and drama discs): its last 30 s, or all of it under 40 s ("tail") -
      the tag keeps playing in the window with its sound, so nothing is hidden.
    A last chapter over 3 min (a final act, a film's finale) is no answer."""
    dur = float(dur or 0)
    if dur <= 0 or len(chs) < 2:
        return None, None
    last_t, last_n = chs[-1]
    if CREDIT_NAMES.search(last_n or "") and dur - last_t >= 10:
        return float(last_t), "separate"
    if len(chs) >= 3:
        tag_t = chs[-2][0]
        tag, cred = last_t - tag_t, dur - last_t
        if TAG_MIN <= tag <= TAG_MAX and TAG_MIN <= cred <= 120.0:
            return float(last_t), "separate"
    tail = dur - last_t
    if TAG_MIN <= tail <= TAG_MAX:
        return (float(last_t) if tail < SQUEEZE_WHOLE else round(dur - SQUEEZE_TAIL, 2)), "tail"
    return None, None


def points(info, dur, o0, gap, timed_k, midroll=True, mode="auto"):
    """Break points (seconds into the part that airs, which starts o0 into the file
    and lasts dur) for an episode with chapter info `info` (analyze()).  None: use
    today's evenly spaced breaks.  timed_k: today's mid-show break count.
    mode: the show's choice - "auto", "always" (any marks are act breaks), "never"."""
    if not info or mode == "never" or not midroll:
        return None
    v = info.get("v")
    marks = [t - o0 for t in info.get("m") or [] if o0 + EDGE <= t <= o0 + dur - EDGE]
    if not marks:
        return None
    if mode == "always" and v in ("act", "dense"):
        v = "act"
    if v == "act":
        most = int(gap // BREAK_MIN) - 1           # every break, the end one too, gets a minute
        if most < 1:
            return None
        return _evenest(marks, dur, most)
    if v == "dense":
        if timed_k < 1:
            return None
        out = []
        for i in range(1, timed_k + 1):
            want = dur * i / (timed_k + 1)
            near = min(marks, key=lambda t: abs(t - want))
            out.append(near if abs(near - want) <= NUDGE and near not in out else want)
        return sorted(out)
    return None


def _evenest(marks, dur, k):
    """At most k of the marks, splitting the episode most evenly (a cold open kept
    when it can be)."""
    if len(marks) <= k:
        return list(marks)
    keep = []
    if marks[0] <= TAG_MAX and k >= 2:
        keep.append(marks[0])
    rest = [t for t in marks if t not in keep]
    start = keep[-1] if keep else 0.0
    n = k - len(keep)
    for i in range(1, n + 1):
        want = start + (dur - start) * i / (n + 1)
        pick = min((t for t in rest if t not in keep), key=lambda t: abs(t - want))
        keep.append(pick)
    return sorted(keep)
