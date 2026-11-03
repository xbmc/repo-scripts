"""Release names: what the playing file is called, and how close a subtitle is to it.

A subtitle cut for "Film.2010.1080p.BluRay.x264-GROUP" is timed to that exact encode,
so the closer a subtitle's release name is to the file being played, the better its
timing is likely to be. Nothing here leaves the device except through query.py.
"""

from __future__ import annotations

import re
from typing import Iterable, List, Optional, Set, Tuple
from urllib.parse import unquote, urlsplit

VIDEO_EXTENSIONS = {
    ".3gp", ".avi", ".divx", ".flv", ".iso", ".m2ts", ".m4v", ".mkv", ".mov", ".mp4",
    ".mpeg", ".mpg", ".mts", ".ogm", ".rmvb", ".strm", ".ts", ".vob", ".webm", ".wmv",
}
_SUBTITLE_EXTENSIONS = {".ass", ".idx", ".sami", ".smi", ".srt", ".ssa", ".sub", ".sup", ".vtt", ".zip"}

_EPISODE_PATTERNS = (
    re.compile(r"(?<![a-z0-9])s(\d{1,2})[ ._-]?e(\d{1,4})(?![0-9])", re.I),  # S01E02, S01.E02
    re.compile(r"(?<![a-z0-9])(\d{1,2})x(\d{2,3})(?![0-9])", re.I),  # 1x02
    re.compile(r"season[ ._-]*(\d{1,2})[ ._-]*episode[ ._-]*(\d{1,4})", re.I),
)
_EPISODE_ONLY = re.compile(r"(?<![a-z0-9])(?:e|ep|episode)[ ._-]?(\d{1,4})(?![0-9])", re.I)
# "Show - 02 [1080p]": anime packs often number episodes alone. Only ever compared with
# a known episode number, never used to find one.
_BARE_NUMBER = re.compile(r"(?:^|[ ._\-\[(])(\d{2,3})(?:v\d)?(?=$|[ ._\-\])])")
_YEAR = re.compile(r"(?<![0-9])(19[2-9]\d|20\d{2})(?![0-9])")
_BRACKETS = re.compile(r"\[[^\]]*\]|\{[^}]*\}")
_GROUP = re.compile(r"-([a-z0-9]{2,20})$", re.I)
_JOINED = (
    (re.compile(r"web[ ._-]?dl", re.I), "webdl"),
    (re.compile(r"web[ ._-]?rip", re.I), "webrip"),
    (re.compile(r"blu[ ._-]?ray", re.I), "bluray"),
    (re.compile(r"([hx])[ ._-]?(26[45])", re.I), r"\1\2"),
)

_SOURCES = {
    "bluray": "bluray", "bdrip": "bluray", "brrip": "bluray", "bdremux": "bluray", "remux": "bluray",
    "webdl": "web", "webrip": "web", "web": "web",
    "hdtv": "tv", "pdtv": "tv", "dsr": "tv", "sdtv": "tv",
    "dvdrip": "dvd", "dvd": "dvd", "dvdr": "dvd", "dvd9": "dvd", "dvd5": "dvd",
    "hdrip": "hdrip", "cam": "cam", "hdcam": "cam", "telesync": "cam",
}
_SERVICES = {"amzn", "atvp", "crav", "dsnp", "hmax", "hulu", "mubi", "nf", "pcok", "pmtp", "roku", "stan"}
_RESOLUTIONS = {"2160p": "2160p", "4k": "2160p", "uhd": "2160p", "1080p": "1080p", "1080i": "1080p",
                "720p": "720p", "576p": "576p", "480p": "480p"}
_CODECS = {"x264": "avc", "h264": "avc", "avc": "avc", "x265": "hevc", "h265": "hevc",
           "hevc": "hevc", "xvid": "xvid", "divx": "xvid", "av1": "av1"}
_EDITIONS = {"criterion", "dc", "directors", "extended", "imax", "remastered", "theatrical", "uncut", "unrated"}
_FIXES = {"proper", "repack", "rerip"}


def name_from_path(path: str) -> str:
    """The playing file's name without folders or video extension.

    Empty for a stream whose address carries no file name (a plugin, a PVR channel,
    "https://host/play?id=1"): such a name would match nothing and mean nothing.
    """
    if not path:
        return ""
    if path.startswith("stack://"):
        path = path[len("stack://"):].split(" , ")[0]
    lower = path.lower()
    if lower.startswith(("plugin://", "pvr://", "upnp://", "special://")):
        return ""
    if "://" in path:
        # rar:// and zip:// carry the archive in the host part and the file in the path.
        try:
            path = urlsplit(path).path
        except ValueError:
            return ""
    name = unquote(path.replace("\\", "/").rstrip("/").rsplit("/", 1)[-1]).strip()
    stem, dot, ext = name.rpartition(".")
    if dot and "." + ext.lower() in VIDEO_EXTENSIONS:
        name = stem
    return name if len(_words(name)) >= 3 else ""


def strip_extension(name: str) -> str:
    stem, dot, ext = (name or "").rpartition(".")
    if dot and ("." + ext.lower()) in VIDEO_EXTENSIONS | _SUBTITLE_EXTENSIONS:
        return stem
    return name or ""


def parse_episode(name: str) -> Optional[Tuple[int, int]]:
    """(season, episode) written in a name as S01E02, 1x02 or "Season 1 Episode 2"."""
    for pattern in _EPISODE_PATTERNS:
        match = pattern.search(name or "")
        if match:
            return int(match.group(1)), int(match.group(2))
    return None


def parse_year(name: str) -> Optional[int]:
    """The last plausible year in a name ("2001.A.Space.Odyssey.1968" -> 1968)."""
    years = _YEAR.findall(name or "")
    return int(years[-1]) if years else None


def episode_match(name: str, season: Optional[int], episode: int) -> int:
    """How surely a file name belongs to an episode.

    3 when it names this season and episode, 2 when it names the episode alone
    ("E02", "Episode 2"), 1 for a bare number ("Show - 02"), 0 when it says nothing
    usable, and -1 when it names a different episode, which rules it out.
    """
    found = parse_episode(name)
    if found:
        same_season = season is None or found[0] == season
        return 3 if same_season and found[1] == episode else -1
    match = _EPISODE_ONLY.search(name or "")
    if match:
        return 2 if int(match.group(1)) == episode else -1
    if any(int(number) == episode for number in _BARE_NUMBER.findall(_BRACKETS.sub(" ", name or ""))):
        return 1
    return 0


def _canonical(name: str) -> str:
    text = _BRACKETS.sub(" ", strip_extension(name or ""))
    for pattern, replacement in _JOINED:
        text = pattern.sub(replacement, text)
    return text


def _words(name: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", (name or "").lower())


def _squash(name: str) -> str:
    return "".join(_words(_canonical(name)))


def _group(name: str) -> str:
    # Canonical first, so "WEB-DL" is one word and not a release group called "DL".
    match = _GROUP.search(_canonical(name).strip(" ._"))
    return match.group(1).lower() if match else ""


def _first(words: Iterable[str], table: dict) -> str:
    for word in words:
        if word in table:
            return table[word]
    return ""


def _set(words: Iterable[str], allowed: Set[str]) -> Set[str]:
    return {word for word in words if word in allowed}


def is_exact(video: str, candidate: str) -> bool:
    """Same release, ignoring case, separators, extension and [site] tags."""
    a, b = _squash(video), _squash(candidate)
    return bool(a) and a == b


def score(video: str, candidate: str) -> int:
    """0-100: how close a subtitle's release name is to the playing file's name."""
    if not video or not candidate:
        return 0
    if is_exact(video, candidate):
        return 100
    vw, cw = _words(_canonical(video)), _words(_canonical(candidate))
    total = 0
    vg, cg = _group(video), _group(candidate)
    if vg and cg and vg == cg:
        total += 40
    for table, hit, miss in ((_SOURCES, 20, -10), (_RESOLUTIONS, 10, -5), (_CODECS, 5, 0)):
        vs, cs = _first(vw, table), _first(cw, table)
        if vs and cs:
            total += hit if vs == cs else miss
    vs, cs = _set(vw, _SERVICES), _set(cw, _SERVICES)
    if vs and vs & cs:
        total += 10
    ve, ce = _set(vw, _EDITIONS), _set(cw, _EDITIONS)
    if ve or ce:
        total += 5 if ve == ce else -5
    if _set(vw, _FIXES) and _set(vw, _FIXES) == _set(cw, _FIXES):
        total += 3
    vset, cset = set(vw), set(cw)
    if vset and cset:
        total += int(10 * len(vset & cset) / len(vset | cset))
    return max(0, min(99, total))


def best_score(video: str, candidates: Iterable[str]) -> int:
    return max((score(video, name) for name in candidates if name), default=0)
