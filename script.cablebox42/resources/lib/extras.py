"""Movie Extras: which files the Behind the scenes channel airs, and their titles.

Pure Python (no Kodi imports), so the rules can be tested on any machine.
Classification only looks at names; nothing here touches a file.

Rules, in order:
  1. A subfolder of Extras named Behind the Scenes / Making Of / Interviews /
     Featurettes / Documentaries means Air, whatever the file is called
     (still skipped when shorter than MIN_SECONDS).
  2. A 'never air' word in the file name or a subfolder name: Skipped.
     Never-air words beat air words.
  3. An air word: Air, in that word's group.
  4. A readable title left after cleanup: Air (featurette group).
  5. Nothing readable left: Skipped as 'name not recognised' (Air when the
     'Also air extras with unrecognised names' setting is on).
  Anything measured shorter than MIN_SECONDS is skipped.
"""
import re

MIN_SECONDS = 60

# Segment order inside a block
GROUP_MAKING, GROUP_FEATURETTE, GROUP_INTERVIEW = 0, 1, 2

# reason key -> English label (manager.py shows the translated label)
REASONS = {
    "deleted": "deleted, extended or alternate",
    "bloopers": "bloopers",
    "trailer": "trailer or promo",
    "gallery": "gallery or storyboards",
    "reel": "demo reel",
    "newsreel": "newsreel",
    "music": "music",
    "short": "short film",
    "commentary": "commentary",
    "other": "disc extra",
    "short_length": "under 60 s",
    "unrecognised": "name not recognised",
    "unreadable": "length can't be read",      # set by Check extras, not by classify()
}

_SKIP = [
    # 'extended' anywhere except an extended interview; words run together too
    ("deleted", r"deleted|deletedalternate|extendedalternate|extended(?! interviews?\b)|alternat(?:e|ive)"),
    ("bloopers", r"bloopers?|gag reels?|out?takes?"),
    ("trailer", r"trailers?|teasers?|tv spots?|spots?|promos?|commercials?"),
    ("gallery", r"(?:photo )?galler(?:y|ies)|storyboards?|storyreels?|(?:story|progression|sizzle) reels?|"
                r"reference footage|textless"),
    # a name ending in 'reel' (VFX and presentation reels still air)
    ("reel", r"demo reels?|(?<!vfx )(?<!presentation )reels?$"),
    ("newsreel", r"newsreels?"),
    ("music", r"music videos?|karaoke|sing ?a ?longs?|isolated score"),
    ("short", r"(?:animated |cartoon )?short films?|animated shorts?|shorts?$"),
    ("commentary", r"commentar(?:y|ies)"),
    ("other", r"easter eggs?|recaps?|samples?|menus?"),
]
_SKIP = [(k, re.compile(r"\b(?:%s)\b" % p)) for k, p in _SKIP]

_AIR = [
    (GROUP_MAKING, r"making|behind the scenes|documentar(?:y|ies)|production|the story of|inside"),
    (GROUP_FEATURETTE, r"featurettes?"),
    (GROUP_INTERVIEW, r"interviews?|conversations?|cast|crew"),
]
_AIR = [(g, re.compile(r"\b(?:%s)\b" % p)) for g, p in _AIR]

# Subfolders that always mean Air (rule 1), normalised
_FORCED = {
    "behind the scenes": GROUP_MAKING, "making of": GROUP_MAKING,
    "documentaries": GROUP_MAKING, "documentary": GROUP_MAKING,
    "featurettes": GROUP_FEATURETTE, "featurette": GROUP_FEATURETTE,
    "interviews": GROUP_INTERVIEW, "interview": GROUP_INTERVIEW,
}

_TECH = re.compile(
    r"\b(?:2160p|1080p|1080i|720p|576[pi]|480[pi]|4k|uhd|hdr10\+?|hdr|sdr|x26[45]|h ?26[45]|hevc|avc|xvid|divx|"
    r"aac(?:2 0)?|e?ac3|dts(?: ?hd)?(?: ?ma)?|truehd|atmos|ddp?(?: ?[257] [01])?|[257] 1|"
    r"blu ?ray|bdrip|brrip|bdremux|remux|web[ -]?dl|web[ -]?rip|dvdrip|hdtv)\b", re.I)
_DISC = re.compile(r"\b(?:d\d{1,2} ?t\d{1,3}|t\d{1,3}|(?:disc|disk|cd|dvd) ?\d{1,2}|track ?\d{1,3}|title ?\d{1,3})\b", re.I)
_LEAD_NUM = re.compile(r"^\d{1,3} ?[-.)] +")
_GENERIC = {"bonus", "extra", "extras", "feature", "features", "special", "specials", "clip", "clips",
            "video", "part", "segment", "chapter", "file", "untitled", "unknown", "new", "title", "track",
            "disc", "the", "and", "of"}


def natural_key(s):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s)]


def _norm(s):
    """Lower case, punctuation as single spaces (for word matching)."""
    s = s.lower().replace("&", " and ").replace("'", "")
    return " ".join(re.sub(r"[^0-9a-z]+", " ", s).split())


def _split(rel):
    parts = [p for p in re.split(r"[\\/]+", rel) if p]
    return parts[:-1], (parts[-1] if parts else "")


def _strip_movie(text, movie_title, year):
    """Remove the movie's own title (and year) repeated at the front."""
    words = re.findall(r"[0-9A-Za-z]+", movie_title or "")
    if words:
        pat = r"^\W*" + r"[\W_]*".join(re.escape(w) for w in words)
        if year:
            pat += r"(?:[\W_]*\(?%s\)?)?" % re.escape(str(year))
        m = re.match(pat + r"(?=[\s\-:–—,.(\[]|$)", text, re.I)
        if m:
            text = text[m.end():]
    if year:
        text = re.sub(r"^\W*\(?%s\)?(?=\W|$)" % re.escape(str(year)), "", text)
    return text


def _tidy(text):
    text = re.sub(r"\(\s*[,;]?\s*\)|\[\s*\]", "", text)
    text = re.sub(r"\(\s*,\s*", "(", text)
    text = " ".join(text.split())
    return text.strip(" -_.,:;–—")


def clean_title(filename, movie_title="", year=""):
    """Readable title from a file name, or '' when nothing readable is left."""
    name = re.sub(r"\.[0-9A-Za-z]{2,4}$", "", filename)
    if " " not in name.strip():
        name = name.replace(".", " ")            # scene style: The.Making.Of.mkv
    name = name.replace("_", " ")
    name = _tidy(name)
    name = _strip_movie(name, movie_title, year)
    name = _TECH.sub(" ", name)
    name = _DISC.sub(" ", name)
    name = _LEAD_NUM.sub("", _tidy(name))
    name = _tidy(name)
    words = [w for w in re.findall(r"[A-Za-z]+", name)]
    if not any(len(w) >= 3 and w.lower() not in _GENERIC for w in words):
        return ""
    return name


def classify(rel, movie_title="", year="", dur=0, air_unrecognised=False):
    """rel: path inside the Extras folder ('Interviews/Bob.mkv').
    dur: seconds, 0 when not measured yet.
    Returns {"title", "air", "reason", "group"}; reason is a REASONS key or ''."""
    folders, filename = _split(rel)
    title = clean_title(filename, movie_title, year)
    forced = None
    for f in folders:
        forced = _FORCED.get(_norm(f), forced)
    fallback = (folders and _tidy(folders[-1])) or "Behind the scenes"
    out = {"title": title or fallback, "air": False, "reason": "", "group": GROUP_FEATURETTE}

    if forced is not None:
        out["group"] = forced
        out["air"] = True
    else:
        stem = _strip_movie(re.sub(r"\.[0-9A-Za-z]{2,4}$", "", filename), movie_title, year)
        text = _norm(" ".join(folders + [stem]))
        for key, rx in _SKIP:
            if rx.search(text):
                out["reason"] = key
                return out
        for group, rx in _AIR:
            if rx.search(text):
                out["group"] = group
                out["air"] = True
                break
        if not out["air"]:
            if title or air_unrecognised:
                out["air"] = True
            else:
                out["reason"] = "unrecognised"
                return out
    if dur and dur < MIN_SECONDS:
        out["air"] = False
        out["reason"] = "short_length"
    return out


def segment_order(items):
    """Sort [(rel, info)] for a block: making-of/documentaries, featurettes,
    interviews; file order (natural sort) within each group."""
    return sorted(items, key=lambda it: (it[1]["group"], natural_key(it[0])))
