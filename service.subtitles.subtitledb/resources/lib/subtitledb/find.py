"""The ladder: from what the host knows about a file to a ranked list of subtitles.

Each rung resolves one identifier to a title bundle and falls through to the next,
strongest evidence first. tmdb is the headline key and leads; imdb sits right behind
it, because media servers identify content by IMDb id and the imdb->tmdb map is only
partial, so an explicit tmdb 404s for many ids and hands off to imdb. An episode with
no id of its own goes by its series' id, drilled to the season and episode. Free
text is the last automatic rung: the server matches the title and drills to the
episode, so no ranked list of titles ever crosses the wire.

Every rung issues lookup-shaped requests only; subtitle bytes are fetched later and
only for the one the viewer picked.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from .client import Client, SubtitleDbError
from .match import Candidate, Hint, Options, Ranked, rank

#: Which rung produced the answer. Reported so a log says why, not just what.
TIER_TMDB = "explicit-tmdb"
TIER_IMDB = "explicit-imdb"
TIER_SERIES_IMDB = "series-imdb"
TIER_TITLE = "title"
TIER_NONE = "manual"

#: The most rows the API returns for one request. More takes ``offset``.
PAGE = 100
#: What a plugin reads per language when its user has not said.
PER_LANGUAGE = 500
#: The most a plugin setting may ask for, in rows per language.
MOST_PER_LANGUAGE = 2000


def per_language(value) -> int:
    """A plugin setting read as rows per language: 100 to 2000, else 500."""
    try:
        n = int(str(value).strip())
    except ValueError:
        return PER_LANGUAGE
    return min(max(n, PAGE), MOST_PER_LANGUAGE)


@dataclass
class Result:
    candidates: list[Candidate] = field(default_factory=list)
    title: dict | None = None
    tier: str = TIER_NONE
    unrenderable: int = 0
    wrong_episode: int = 0

    def __bool__(self) -> bool:
        return bool(self.candidates)


def _scoped_items(bundle: dict) -> list[dict]:
    """The subtitle page that belongs to exactly what was asked for.

    Always the top-level bucket. Every lookup answers with the same three keys, drilled
    or not: a drill narrows what lands in ``subtitles`` rather than moving the page
    under an ``episode`` or ``season`` key. Those keys were never sent. The bucket is a
    page object ``{items, total}``, not a bare list.
    """
    return (bundle.get("subtitles") or {}).get("items") or []


def _bundle_page(fetch_one, languages: list[str], cap: int) -> tuple[dict, list[dict]]:
    """Up to ``cap`` rows per preferred language, merged in the caller's priority order.

    ``fetch_one(lang, offset, limit)`` returns one page of a bundle; ``lang`` is None
    for the unfiltered ask. The API sends at most 100 rows a request, in the order
    they were added rather than how well they match, so the one in sync with a
    popular film's file can sit past the first page. A language is read on until the
    title runs out, ``cap`` is reached, or a page brings nothing new.

    ``lang`` takes up to 16 comma separated codes, so the per-language fan-out is a
    cost we choose rather than one the API forces; collapsing it changes behaviour in
    four language ports at once and is deliberately left alone here.
    """
    title = None
    seen: set[int] = set()
    subtitles: list[dict] = []
    for lang in languages or [None]:
        read = 0
        while read < cap:
            b = fetch_one(lang, read, min(PAGE, cap - read))
            if title is None:
                title = b.get("title") or {}
            items = _scoped_items(b)
            fresh = 0
            for sub in items:
                sid = int(sub.get("id") or 0)
                if sid in seen:
                    continue
                seen.add(sid)
                subtitles.append(sub)
                fresh += 1
            read += len(items)
            # No new row means the offset was ignored or went past the end.
            if not fresh or read >= int((b.get("subtitles") or {}).get("total") or 0):
                break
    return title or {}, subtitles


def _via(verb, hint: Hint, opts: Options, tier: str) -> Result | None:
    """Fetch a bundle through ``verb`` and rank its scoped page, or None on fallthrough.

    ``verb(params)`` issues one lookup with the given query params. A 404 or 400 means
    "this rung does not apply" and returns None so the caller tries the next; any other
    error propagates, because "the API is broken" and "we do not have this" must not
    look the same. A 200 with no usable rows still stops the ladder: the title
    resolved, it simply has nothing in the asked-for language or format.
    """

    def fetch_one(lang, offset, limit):
        params: dict = {"limit": limit}
        if offset:
            params["offset"] = offset
        if lang:
            params["lang"] = lang
        return verb(params)

    try:
        # A full page even for a small limit, so the ranking keeps the best few rows
        # and not the first few.
        title, subs = _bundle_page(fetch_one, opts.languages, max(opts.limit, PAGE))
    except SubtitleDbError as err:
        if err.fallthrough:
            return None
        raise
    # The limit holds per language, so a second language is not crowded out by the
    # first one's long list.
    ranked: Ranked = rank(subs, hint, replace(opts, limit=opts.limit * max(1, len(opts.languages))))
    return Result(
        candidates=ranked.candidates,
        title=title,
        tier=tier,
        unrenderable=ranked.unrenderable,
        wrong_episode=ranked.wrong_episode,
    )


def find(client: Client, hint: Hint, opts: Options | None = None) -> Result:
    """Walk the ladder and return what to show, best first."""
    opts = opts or Options()

    # Rung 1: an explicit TMDB id, the headline key. The imdb->tmdb map is only partial
    # in production, so this 404s for many ids and falls through to imdb.
    if hint.tmdb_id is not None:
        out = _via(
            lambda p: client.by_tmdb(hint.tmdb_id, season=hint.season, episode=hint.episode, **p),
            hint, opts, TIER_TMDB,
        )
        if out is not None:
            return out

    # Rung 2: an explicit IMDb id. Works for films and for TV episodes, which the corpus
    # files under their own episode-level IMDb id. This is the rung media servers hit,
    # since they hand over an IMDb id.
    if hint.imdb_id:
        out = _via(
            lambda p: client.by_imdb(hint.imdb_id, season=hint.season, episode=hint.episode, **p),
            hint, opts, TIER_IMDB,
        )
        if out is not None:
            return out

    # Rung 3: the series' IMDb id, drilled to the season and episode. Sonarr, and so
    # Bazarr, knows a series' id and not its episodes'; so does a Kodi library scraped
    # from TVDB. A name can resolve to another show (the API answers "Friends" with
    # Matlock), and an id cannot.
    if hint.series_imdb_id and hint.series_imdb_id != hint.imdb_id:
        out = _via(
            lambda p: client.by_imdb(
                hint.series_imdb_id, season=hint.season, episode=hint.episode, **p),
            hint, opts, TIER_SERIES_IMDB,
        )
        if out is not None:
            return out

    # Rung 4: free text, drilled to the episode when the numbers are known. The server
    # matches the title (top-1) and narrows by season/episode, so no title list crosses
    # the wire.
    if hint.title and len(hint.title) > 1:
        out = _via(
            lambda p: client.by_title(hint.title, season=hint.season, episode=hint.episode, **p),
            hint, opts, TIER_TITLE,
        )
        if out is not None:
            return out

    return Result()
