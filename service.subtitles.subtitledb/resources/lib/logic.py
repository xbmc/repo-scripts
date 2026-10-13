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


#: A stream rather than a file: its name is no release name, and its title is
#: whatever the page called it.
_STREAM = re.compile(r"^(?:https?|rtmpe?|rtsp|mms|udp|plugin)://", re.I)
#: Shorter than this is a trailer or a clip, not the film or episode it is labelled as.
SHORTEST = 300
#: What Kodi calls a subtitle stream whose language nobody wrote down.
_UNKNOWN = {"", "und", "unk", "unknown", "undetermined"}


def worth_looking_up(hint, path="", seconds=0):
    """True when enough is known about a video to load a subtitle for it unasked.

    An id is enough. Without one, a title is enough when it came with a year, or with
    a season and an episode, and when it came from a file: a stream's title is
    whatever the site called it, and a guess there loads a stranger's subtitles.
    """
    if 0 < seconds < SHORTEST:
        return False
    if hint.imdb_id or hint.tmdb_id or hint.series_imdb_id:
        return True
    if not hint.title or _STREAM.match(path or ""):
        return False
    return bool(hint.year or (hint.season and hint.episode))


def covered(streams, languages):
    """True when the video already carries a subtitle the viewer may want.

    ``streams`` are the English names of the subtitle streams Kodi has for the video,
    and ``languages`` the viewer's. A stream with no language is most often a file the
    viewer put beside the video themselves, so it counts too.
    """
    wanted = {str(name).strip().lower() for name in languages}
    for name in streams:
        name = str(name or "").strip().lower()
        if name in _UNKNOWN or name in wanted:
            return True
    return False


def instant(client, info, languages, streams, limit=PER_LANGUAGE, seconds=0, log=None):
    """The subtitle to load the moment a video starts, and why; or None and why not.

    The viewer's languages are tried in their order, one at a time, and the first that
    has a match gives the best of its list, so a viewer with English first and
    Spanish second gets English whenever there is any.
    """
    languages = [name for name in languages if name]
    if not languages:
        return None, "no subtitle languages are set in Kodi"
    if covered(streams, languages):
        return None, "the video already has subtitles"
    hint = hint_from(info)
    if not worth_looking_up(hint, info.get("path") or "", seconds):
        return None, "not enough is known about the video"
    for language in languages:
        codes = to_codes([language])
        if not codes:
            continue
        result = find(client, hint, Options(languages=codes, formats=FORMATS, limit=limit))
        if log:
            log(resolved(result))
        if result.candidates:
            return list_item(result.candidates[0], result.tier), answered(result)
        if not result.title:
            # No title, so no other language will find one either.
            return None, "no title for it: %s" % answered(result)
    return None, "no subtitles in %s" % ", ".join(languages)


def resolved(result):
    """One line for the log saying which title the search was answered for.

    A file played from outside the library is known by its name alone, and the name
    can resolve to the wrong title. The list gives no sign of that; this line does.
    """
    return "resolved to " + answered(result)


def answered(result):
    """The title a search was answered for, by which rung, and how many it found."""
    title = result.title or {}
    if not title:
        return "nothing via %s" % result.tier
    return "%s (%s) %s via %s, %d candidates" % (
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
    subtitle saved as .srt that is actually ASS renders as a screen of tag soup. The
    language code before it is where Kodi reads the language of a file handed
    straight to the player, as the lookup on play does; without it the subtitle
    menu calls the stream unknown.
    """
    ext = (item.get("format") or "srt").lower()
    if ext not in FORMATS:
        ext = "srt"
    code = str(item.get("language_code") or "").lower()
    if re.fullmatch(r"[a-z]{2,3}", code):
        return "subtitledb-%d.%s.%s" % (item.get("id") or 0, code, ext)
    return "subtitledb-%d.%s" % (item.get("id") or 0, ext)


#: Kodi kills a service still running 5 s after it asks it to stop, and a request
#: waiting on a socket cannot be interrupted, so the lookup on play waits less.
ON_PLAY_TIMEOUT_S = 4.0


def make_client(api_base=None, **options):
    return Client(api_base=api_base or "https://api.thesubtitledb.org", client="kodi", **options)
