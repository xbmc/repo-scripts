"""Everything the Kodi addon does that does not need Kodi.

service.py reads the player and draws the list; this decides what to ask for and
what the list should say. Kept apart so it can be tested without a media centre:
the addon's own tests import this module and never import xbmc.
"""


import os
import re

from subtitledb import (
    PER_LANGUAGE,
    Client,
    Hint,
    Options,
    find,
    language_name,
    to_codes,
)

#: Kodi renders these itself. Anything else would be handed over and never drawn.
FORMATS = ["srt", "ass", "ssa", "sub", "vtt"]

#: A stacked file, and the trailing junk a scraper leaves on a path.
_STACK = re.compile(r"^stack://")
_RAR = re.compile(r"^(?:rar|zip)://")

#: How a release name marks an episode (S01E01, S01.E01, 1x01), a year, and the tags
#: that start where the title ends when there is no year.
_EPISODE = re.compile(r"(?<![a-z0-9])(?:s(\d{1,2})[ ._-]?e(\d{1,3})|(\d{1,2})x(\d{2,3}))(?!\d)",
                      re.I)
_YEAR = re.compile(r"(?<![a-z0-9])((?:19|20)\d\d)(?![a-z0-9])", re.I)
_TAG = re.compile(r"(?<![a-z0-9])(?:\d{3,4}[pi]|4k|uhd|bluray|blu-ray|bdrip|brrip|"
                  r"web-?dl|webrip|hdtv|dvdrip|hdrip|remux|[xh]\.?26[45]|hevc|xvid)(?![a-z0-9])",
                  re.I)


def video_name(path):
    """The release name, out of whatever Kodi is playing.

    A stack is several files playing as one; the first is the one whose name means
    anything. An archive path has the real name inside it, url-encoded, and taking
    the last segment is what gets at it.
    """
    if not path:
        return None
    if _STACK.match(path):
        path = path[len("stack://") :].split(" , ")[0]
    if _RAR.match(path):
        try:
            from urllib.parse import unquote
        except ImportError:  # pragma: no cover - Kodi 18 and older
            from urllib import unquote  # type: ignore[no-redef,attr-defined]
        path = unquote(path).rstrip("/").split("/")[-1]
    base = os.path.basename(path.replace("\\", "/").rstrip("/"))
    stem = os.path.splitext(base)[0]
    return stem or None


def clean_imdb(value, typed=True):
    """An IMDb id, or None.

    A ``typed`` value is one Kodi files under "imdb", which an old NFO may write
    without its tt. IMDBNumber is the item's default id instead, and Kodi's own TMDB
    and TVDB scrapers make theirs the default: a bare number there is a TMDB or TVDB
    id, and sent as an IMDb id it resolves to another title.
    """
    if not value:
        return None
    text = str(value).strip().lower()
    if text.startswith("tt") and text[2:].isdigit():
        return text
    if typed and text.isdigit() and len(text) >= 7:
        return "tt" + text
    return None


def imdb_of(info):
    """The IMDb id Kodi holds for the item, from its "imdb" id or a default that is one."""
    return clean_imdb(info.get("imdb")) or clean_imdb(info.get("imdb_number"), typed=False)


def to_int(value):
    try:
        number = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _words(text):
    return re.sub(r"[ ._]+", " ", text).strip(" -([") or None


def from_name(name):
    """Show, season and episode, or title and year, read off a release name."""
    if not name:
        return {}
    found = _EPISODE.search(name)
    if found:
        return {"tvshow": _words(name[: found.start()]), "title": None, "year": None,
                "season": int(found.group(1) or found.group(3)),
                "episode": int(found.group(2) or found.group(4))}
    tag = _TAG.search(name)
    head = name[: tag.start()] if tag else name
    # The last year, not the first: 2001.A.Space.Odyssey.1968 is a film from 1968.
    years = [y for y in _YEAR.finditer(head) if y.start() > 0]
    if years:
        head = name[: years[-1].start()]
    return {"tvshow": None, "season": None, "episode": None, "title": _words(head),
            "year": int(years[-1].group(1)) if years else None}


def _only_the_file_name(info):
    """True when Kodi knows nothing about what is playing but the file's name.

    That is a file played from outside the library: no IMDb id, no year, and the
    file name as the title, which matches no title the API has.
    """
    if imdb_of(info) or to_int(info.get("tmdb")):
        return False
    if info.get("tvshow") and to_int(info.get("season")) and to_int(info.get("episode")):
        return False
    title = info.get("title") or info.get("original_title")
    if not title:
        return True
    name = video_name(info.get("path"))

    def squash(value):
        return re.sub(r"[^a-z0-9]", "", value.lower())

    return bool(name) and squash(name) in (squash(title), squash(os.path.splitext(title)[0]))


def hint_from(info):
    """Build the shared hint from Kodi's info labels.

    `info` is a plain dict so the caller can read the labels however its Kodi
    version prefers, and so this is testable. When the labels hold nothing but the
    file's own name, the title and numbers are read off that name instead.
    """
    if _only_the_file_name(info):
        info = dict(info, **from_name(video_name(info.get("path"))))
    season = to_int(info.get("season"))
    episode = to_int(info.get("episode"))
    is_episode = bool(info.get("tvshow")) and season is not None and episode is not None

    if is_episode:
        return Hint(
            # The episode's own id when the scraper had one, and the show's, which
            # the ladder drills to the season and episode, when it did not.
            imdb_id=imdb_of(info),
            series_imdb_id=clean_imdb(info.get("tvshow_imdb")),
            title=info.get("tvshow"),
            episode_title=info.get("title") or None,
            season=season,
            episode=episode,
            release=video_name(info.get("path")),
        )
    return Hint(
        imdb_id=imdb_of(info),
        # Only for a film: an episode's TMDB id is the episode's, and the map the API
        # reads is keyed by the film's.
        tmdb_id=to_int(info.get("tmdb")),
        title=info.get("title") or info.get("original_title") or None,
        year=to_int(info.get("year")),
        release=video_name(info.get("path")),
    )


def search(client, info, languages, limit=PER_LANGUAGE, log=None):
    """Ask, and return rows ready to be drawn as a list. ``limit`` is per language."""
    opts = Options(languages=to_codes(languages), formats=FORMATS, limit=limit)
    result = find(client, hint_from(info), opts)
    if log:
        log(resolved(result))
    return [list_item(c, result.tier) for c in result.candidates]


def resolved(result):
    """One line for the log saying which title the search was answered for.

    A file played from outside the library is known by its name alone, and the name
    can resolve to the wrong title. The list gives no sign of that; this line does.
    """
    title = result.title or {}
    if not title:
        return "resolved to nothing via %s" % result.tier
    return "resolved to %s (%s) %s via %s, %d candidates" % (
        title.get("name"), title.get("year"), title.get("imdb"), result.tier,
        len(result.candidates))


def list_item(candidate, tier=""):
    """One row of the subtitle list, as plain data.

    Kodi draws two lines: the language on the left, a description on the right. The
    star rating is the only other thing it shows, and it is the wrong shape for what
    we know, so it carries the same signal the label does rather than an invention:
    a subtitle recorded against this exact release is what "5 stars" should mean.
    """
    row = candidate.subtitle
    code = str(row.get("language") or "")
    exact = "same release" in candidate.reason
    return {
        "id": int(row.get("id") or 0),
        "language_name": language_name(code) or code.upper(),
        "language_code": code,
        "release": str(row.get("release_name") or "").strip(),
        "cues": int(row.get("cues") or 0),
        "reason": candidate.reason,
        "tier": tier,
        "format": str(row.get("format") or ""),
        "download_url": row.get("download_url") or "",
        "hearing_impaired": bool(row.get("hearing_impaired")),
        "sync": exact,
        "rating": 5 if exact else 0,
    }


def describe(item, lines):
    """The right-hand column: the release name, else the line count.

    Kodi draws the language on the left and hearing impaired as an icon, so neither is
    repeated here. ``lines`` is the translated "{0} lines" from strings.po: Kodi's
    add-on rules want every word a viewer reads to be translatable.
    """
    if item["release"]:
        return item["release"]
    return lines.format(item["cues"]) if item["cues"] else ""


def filename_for(item):
    """What the downloaded file is called.

    The extension has to be the real one: Kodi picks its parser from it, and a
    subtitle saved as .srt that is actually ASS renders as a screen of tag soup.
    """
    ext = (item.get("format") or "srt").lower()
    if ext not in FORMATS:
        ext = "srt"
    return "subtitledb-%d.%s" % (item.get("id") or 0, ext)


def make_client(api_base=None):
    return Client(api_base=api_base or "https://api.thesubtitledb.org", client="kodi")
