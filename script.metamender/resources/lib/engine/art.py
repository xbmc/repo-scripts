"""Rules for Kodi art: classify what Kodi holds, pick an image for any art
type, and decide whether MetaMender may touch an art slot or a name.

Logging:
    Logger: none (pure functions)
"""
from __future__ import annotations

import os
import string
import urllib.parse
from typing import Any, Callable, Dict, List, NamedTuple, Optional, Tuple

from resources.lib.engine.chain import TRANSIENT

# The art types besides poster and thumb, as covered by the "other_art" tick
# (data/libraries.FIELD_TOGGLES).
OTHER_ART_FIELDS = frozenset({
    "clearlogo", "keyart", "landscape", "banner", "discart", "clearart", "characterart",
})
ART_FIELDS = frozenset({"poster", "thumb", "fanart"}) | OTHER_ART_FIELDS
# Art types both sites offer, which the library's Art source orders.
TMDB_ART_FIELDS = frozenset({"poster", "fanart", "clearlogo", "keyart"})
FANART_ONLY_FIELDS = frozenset({"landscape", "banner", "discart", "clearart", "characterart"})
# Art types whose images can carry text in a language.
TEXT_ART_FIELDS = ART_FIELDS - {"thumb", "keyart"}

EMPTY = "empty"
FRAME_GRAB = "frame_grab"
BROKEN = "broken"
WEB_TMDB = "web_tmdb"
WEB_FANART = "web_fanart"
WEB_OTHER = "web_other"
LOCAL = "local"
OTHER = "other"

GATE_LOCAL = "local"
GATE_OTHER = "other"
GATE_CHANGED = "changed"

TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/original"
_IMAGE_PREFIX = "image://"
_FRAME_GRAB_PREFIX = "image://video@"
_LOCAL_PREFIXES = ("smb:", "nfs:", "special:", "/", "\\\\")

# An image only displaces the one already set when it leads by more than this
# on the provider's own first score (TMDB: the weighted score; fanart.tv:
# likes), so near-ties do not make the artwork flip between refreshes.
POSTER_SWITCH_MARGIN = {"tmdb": 0.15, "fanart": 1}

# Pseudo-votes at the tier mean that pull an image with few votes toward it.
TMDB_PRIOR_VOTES = 10
_DEFAULT_PRIOR_MEAN = 5.0

ENGLISH = "en"

# Season posters uploaded to fanart.tv within this many seconds of each other
# count as one batch (season_tie_break).
BATCH_WINDOW_SECONDS = 86400
_UNIQID_LENGTH = 13
_UNIQID_SECONDS_LENGTH = 8


class Poster(NamedTuple):
    """One candidate image of any art type. ``score`` is
    ``(vote_average, vote_count)`` for TMDB and ``(likes,)`` for fanart.tv.
    ``sd`` marks fanart.tv's SD types, candidates only when their tier has no
    HD image."""
    url: str
    provider: str
    lang: Optional[str]
    score: Tuple[Any, ...]
    sd: bool = False


class PosterPick(NamedTuple):
    url: str
    provider: str
    from_fallback: bool
    textless: bool
    english: bool


# Appended to a textless pick's provider in field_status.source, so
# Details can tell it from one in the fallback language: both carry
# from_fallback, which drives the monthly recheck.
TEXTLESS_SOURCE_SUFFIX = ":textless"
# Appended to a pick from the English last resort, which may only fill an
# empty slot: the scan reads it back to know Kodi still holds its own
# English pick rather than existing art.
ENGLISH_SOURCE_SUFFIX = ":english"

ORDER_TEXT_FIRST = "text_first"
ORDER_TEXTLESS_FIRST = "textless_first"
ORDER_TEXTLESS_ONLY = "textless_only"


class ArtRule(NamedTuple):
    """How one art type is picked: the order of its language steps, and
    whether both sites offer it (else fanart.tv only, Art source ignored)."""
    order: str
    both_sites: bool


ART_RULES: Dict[str, ArtRule] = {
    "poster": ArtRule(ORDER_TEXT_FIRST, True),
    "clearlogo": ArtRule(ORDER_TEXT_FIRST, True),
    "fanart": ArtRule(ORDER_TEXTLESS_FIRST, True),
    "keyart": ArtRule(ORDER_TEXTLESS_ONLY, True),
    **{field: ArtRule(ORDER_TEXT_FIRST, False) for field in FANART_ONLY_FIELDS},
}


def unwrap(value: Optional[str]) -> str:
    """The URL inside Kodi's ``image://<urlencoded>/`` wrapper.

    A frame grab (``image://video@...``) is not a URL Kodi fetched, so it is
    returned unchanged for ``classify`` to recognise.
    """
    if not value:
        return ""
    text = value.strip()
    if text.startswith(_FRAME_GRAB_PREFIX):
        return text
    if text.startswith(_IMAGE_PREFIX):
        inner = text[len(_IMAGE_PREFIX):]
        # Not str.removesuffix: the official repository's checker assumes
        # Kodi 21 may run Python 3.8.
        inner = inner[:-1] if inner.endswith("/") else inner  # noqa: FURB188
        return urllib.parse.unquote(inner)
    return text


def _is_windows_path(url: str) -> bool:
    return len(url) > 2 and url[0].isalpha() and url[1] == ":" and url[2] in "\\/"


def classify(url: str) -> str:
    """What kind of art an unwrapped value is."""
    if not url:
        return EMPTY
    if url.startswith(_FRAME_GRAB_PREFIX):
        return FRAME_GRAB
    if url.startswith(_LOCAL_PREFIXES) or _is_windows_path(url):
        return LOCAL
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme in ("http", "https"):
        # TheTVDB stores an empty banner link for episodes without an image.
        if parsed.path.endswith("/"):
            return BROKEN
        host = (parsed.hostname or "").lower()
        if host == "image.tmdb.org":
            return WEB_TMDB
        if host == "assets.fanart.tv":
            return WEB_FANART
        return WEB_OTHER
    return OTHER


def is_placeholder_art(value: str) -> bool:
    return classify(unwrap(value)) in (EMPTY, FRAME_GRAB, BROKEN)


def tmdb_image_url(path: str) -> str:
    return TMDB_IMAGE_BASE + path


def _image_key(url: str) -> str:
    """What identifies an image: TMDB serves one file at several sizes
    (``/t/p/w500/abc.jpg``, ``/t/p/original/abc.jpg``), so its key is the
    file path after the size segment; any other URL is its own key."""
    if classify(url) == WEB_TMDB:
        parts = urllib.parse.urlparse(url).path.split("/")
        # ["", "t", "p", "<size>", "<file path>"...]
        if len(parts) > 4 and parts[1:3] == ["t", "p"]:
            return "tmdb:" + "/".join(parts[4:])
    return url


def weighted_score(avg: float, count: int, prior_mean: float) -> float:
    return (count * avg + TMDB_PRIOR_VOTES * prior_mean) / (count + TMDB_PRIOR_VOTES)


def _prior_mean(posters: List[Poster]) -> float:
    votes = sum(p.score[1] for p in posters)
    if votes <= 0:
        return _DEFAULT_PRIOR_MEAN
    return sum(p.score[1] * p.score[0] for p in posters) / votes


def _is_rated(poster: Poster) -> bool:
    return (poster.score[1] if poster.provider == "tmdb" else poster.score[0]) > 0


def _rank(
    posters: List[Poster], tie_break: Optional[Callable[[Poster], int]] = None,
) -> List[Tuple[Poster, float]]:
    """Images of one provider, best first, with their primary score.

    ``tie_break`` orders fanart.tv images with equal likes; the sort is
    stable, so images still tied keep the API's order.
    """
    if posters[0].provider == "tmdb":
        prior = _prior_mean(posters)
        scored = [(p, weighted_score(p.score[0], p.score[1], prior)) for p in posters]
        scored.sort(key=lambda item: (item[1], item[0].score[1]), reverse=True)
    else:
        scored = [(p, float(p.score[0])) for p in posters]
        if tie_break is None:
            scored.sort(key=lambda item: item[1], reverse=True)
        else:
            scored.sort(key=lambda item: (item[1], tie_break(item[0])), reverse=True)
    return scored


def _text_languages(lang: str, fallback: Optional[str]) -> List[Optional[str]]:
    langs: List[Optional[str]] = [lang]
    if fallback is not None and fallback != lang:
        langs.append(fallback)
    return langs


def art_tiers(
    rule: ArtRule, source: str, lang: str, fallback: Optional[str], english: bool,
) -> List[Tuple[Optional[str], str]]:
    """The (language, provider) steps of one art type, first step first.

    ``None`` is no text. English is the last step only when ``english``
    allows it (the slot holds no art worth keeping) and it is not already one
    of the language steps. Within a language the Art source comes before the
    other site; a fanart.tv-only type has one provider per step.
    """
    langs = _text_languages(lang, fallback)
    last_resort: List[Optional[str]] = [ENGLISH] if english and ENGLISH not in langs else []
    if rule.order == ORDER_TEXTLESS_ONLY:
        codes: List[Optional[str]] = [None]
    elif rule.order == ORDER_TEXTLESS_FIRST:
        codes = [None] + langs + last_resort
    else:
        codes = langs + [None] + last_resort
    if rule.both_sites:
        providers: Tuple[str, ...] = (source, "fanart" if source == "tmdb" else "tmdb")
    else:
        providers = ("fanart",)
    return [(code, provider) for code in codes for provider in providers]


def _in_first_group(rule: ArtRule, poster_lang: Optional[str], lang: str) -> bool:
    if rule.order == ORDER_TEXTLESS_ONLY:
        return True
    if rule.order == ORDER_TEXTLESS_FIRST:
        return poster_lang is None
    return poster_lang == lang


def _hd_first(tier: List[Poster]) -> List[Poster]:
    hd = [p for p in tier if not p.sd]
    return hd or tier


def pick_art(
    field: str,
    tmdb: List[Poster],
    fanart: Callable[[], Any],
    source: str,
    lang: str,
    fallback: Optional[str],
    current: str,
    english: bool = False,
    tie_break: Optional[Callable[[Poster], int]] = None,
) -> Any:
    """Best image for an art field, or None when there is none, or TRANSIENT
    when fanart.tv could not answer and the pick might change once it does.

    The first tier of ``art_tiers`` with candidates wins. An unrated pick
    does not replace a rated current image in the same language group.
    ``fanart`` is called at most once, and only when a tier or the unrated
    check needs it; ``tmdb`` is ignored for a fanart.tv-only type.
    ``tie_break`` only orders fanart.tv images with equal likes and never
    unseats a current image the switch margin keeps.
    """
    rule = ART_RULES[field]
    fetched: List[Any] = []

    def fanart_posters() -> Any:
        if not fetched:
            fetched.append(fanart())
        return fetched[0]

    current_url = unwrap(current)
    current_key = _image_key(current_url) if current_url else ""
    text_langs = _text_languages(lang, fallback)

    def is_current(poster: Poster) -> bool:
        return bool(current_key) and _image_key(poster.url) == current_key

    def pick_from(poster: Poster) -> PosterPick:
        # The current image at another size is still the current image, so
        # it is kept as Kodi holds it rather than rewritten.
        url = current_url if is_current(poster) else poster.url
        return PosterPick(
            url, poster.provider,
            from_fallback=not _in_first_group(rule, poster.lang, lang),
            textless=poster.lang is None,
            english=poster.lang == ENGLISH and ENGLISH not in text_langs,
        )

    pick: Optional[Poster] = None
    for code, provider in art_tiers(rule, source, lang, fallback, english):
        if provider == "tmdb":
            pool = tmdb
        else:
            pool = fanart_posters()
            if pool is TRANSIENT:
                return TRANSIENT
        tier = [p for p in pool if p.lang == code]
        if not tier:
            continue
        ranked = _rank(_hd_first(tier), tie_break)
        best, best_score = ranked[0]
        pick = best
        for poster, score in ranked:
            if is_current(poster) and best_score - score <= POSTER_SWITCH_MARGIN[provider]:
                pick = poster
                break
        break

    if pick is None:
        return None

    if not _is_rated(pick) and current_url and not is_current(pick):
        # An unrated image says nothing against a rated one already set in
        # the same language group. A pick from a better group (library
        # language over fallback over textless) still wins: language first.
        group = pick.lang

        def keeps_current(poster: Poster) -> bool:
            return is_current(poster) and poster.lang == group and _is_rated(poster)

        if rule.both_sites:
            for poster in tmdb:
                if keeps_current(poster):
                    return pick_from(poster)
        # Fanart is consulted only when it already answered or the current
        # image could be one of its images; otherwise its failure must not
        # unsettle a pick that does not depend on it.
        if fetched or classify(current_url) == WEB_FANART:
            pool = fanart_posters()
            if pool is TRANSIENT:
                return TRANSIENT
            for poster in pool:
                if keeps_current(poster):
                    return pick_from(poster)
    return pick_from(pick)


def upload_time(url: str) -> Optional[int]:
    """When fanart.tv received an image, in seconds since 1970, or None.

    fanart.tv names its files ``<name>-<uniqid>``, PHP's 13 hex character
    uniqid whose first 8 characters are the upload's seconds.
    """
    path = urllib.parse.urlparse(url).path
    stem = os.path.splitext(path.rsplit("/", 1)[-1])[0]
    if "-" not in stem:
        return None
    uniqid = stem.rsplit("-", 1)[1]
    if len(uniqid) != _UNIQID_LENGTH or not all(c in string.hexdigits for c in uniqid):
        return None
    return int(uniqid[:_UNIQID_SECONDS_LENGTH], 16)


def season_tie_break(others: List[List[Poster]]) -> Callable[[Poster], int]:
    """A tie-break for one season's fanart.tv posters: how many of the show's
    other seasons (``others``, one list of candidates each) have a fanart.tv
    poster uploaded within BATCH_WINDOW_SECONDS of it. A poster without an
    upload time is in no batch."""
    season_times = [
        [t for t in (upload_time(p.url) for p in season if p.provider == "fanart")
         if t is not None]
        for season in others
    ]

    def batch_size(poster: Poster) -> int:
        when = upload_time(poster.url)
        if when is None:
            return 0
        return sum(
            1 for times in season_times
            if any(abs(when - t) <= BATCH_WINDOW_SECONDS for t in times)
        )
    return batch_size


def drop_show_copies(season: List[Poster], show: List[Poster]) -> List[Poster]:
    """A season's candidates without the TMDB images that are the same file
    as one of the show's TMDB posters, at whatever size."""
    show_keys = {_image_key(p.url) for p in show if classify(p.url) == WEB_TMDB}
    return [
        p for p in season
        if classify(p.url) != WEB_TMDB or _image_key(p.url) not in show_keys
    ]


def name_gate(current_fp: str, first_fp: Optional[str], written_fp: Optional[str]) -> Optional[str]:
    """None when MetaMender may change a name, or GATE_CHANGED when it was
    changed outside MetaMender since first seen. A name MetaMender wrote
    last is its own."""
    if written_fp is not None and current_fp == written_fp:
        return None
    if first_fp is None or first_fp == current_fp:
        return None
    return GATE_CHANGED


def art_gate(
    field: str,
    current: str,
    current_fp: str,
    first_fp: Optional[str],
    written_fp: Optional[str],
    missing: bool = False,
) -> Optional[str]:
    """None when MetaMender may work on this art slot, otherwise why not.

    Placeholders (empty, frame grab, broken link) are always fair game, and so
    is a local file that no longer exists (``missing``) and a value whose
    fingerprint is the one MetaMender last wrote. A local file that exists is
    always left alone: MetaMender never writes a local path, so a written
    fingerprint equal to one is only the record of a refill that found
    nothing for a missing file, which must not outlive the file coming back.
    A thumb that is anything else came from a scraper or the user. Any other
    art type is left alone when it is from a host other than TMDB and
    fanart.tv, or when it was changed since MetaMender first saw it
    (``first_fp``).
    """
    kind = classify(unwrap(current))
    if kind in (EMPTY, FRAME_GRAB, BROKEN):
        return None
    if kind == LOCAL:
        return None if missing else GATE_LOCAL
    if written_fp is not None and current_fp == written_fp:
        return None
    if field == "thumb" or kind not in (WEB_TMDB, WEB_FANART):
        return GATE_OTHER
    if first_fp is None or first_fp == current_fp:
        return None
    return GATE_CHANGED
