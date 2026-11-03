"""Live TV programme matching: a programme's TMDB title from what the EPG gives."""
from __future__ import annotations

import re
import unicodedata
from typing import Callable, Dict, Final, FrozenSet, List, NamedTuple, Optional, Tuple

import xbmc

from lib.data.database.pvr import PvrMatchKey
from lib.kodi.utilities import LabelSnapshot

# JSON-RPC notification the match picker sends once it saves a match
MATCH_CHANGED: Final = "pvr_match_changed"
_PROGRAMME_FIELDS: Final = ("OriginalTitle", "Year", "Season", "Episode", "EpisodeName", "Genre",
                            "IMDBNumber", "Plot")

_LEADING = re.compile(r'^(?:new|premiere|movie|film|live)\s*[:\-]\s*', re.IGNORECASE)
_TRAILING = re.compile(
    r'(?:\s*[\(\[](?:hd|uhd|4k|sd|new|live|repeat|r)[\)\]]|\s+(?:hd|uhd)|\s*\*+'
    r'|\s+s\d{1,2}\s*e\d{1,3})$', re.IGNORECASE)
_TRAILING_YEAR = re.compile(r'\s*\(((?:19|20)\d{2})\)$')
_NOT_WORD = re.compile(r'[^\w\s]')

# Kodi's labels for the EPG genre types, by string id
_SKIP_GENRE_IDS = (19516, 19517, 19518, 19520) + tuple(range(19548, 19560))
_MOVIE_GENRE_IDS = tuple(range(19500, 19509))

_DOMINANT_VOTES = 50
_DOMINANT_RATIO = 10

_WORD = re.compile(r'\w+')
_MIN_STOPWORDS = 3
_SHARED_NAMES = 2

# words common in one language and rare in the others, keyed by TMDB's original_language codes
_STOPWORDS: Dict[str, FrozenSet[str]] = {code: frozenset(words.split()) for code, words in {
    "en": "the and with his her their who they from this that when after into about are was has",
    "de": "der die das und ist mit von den dem ein eine einen sich nicht auch wird sind auf für",
    "fr": "le les des est une dans pour sur qui avec du au aux ses son leur par mais cette elle",
    "es": "el los las del por y es su sus al muy pero cuando",
    "it": "il gli della delle dei degli di che è per nel nella sono lo anche questo questa alla",
    "pt": "não uma com os das dos ao pelo pela é seu sua em mais num numa são também",
    "nl": "het een van zijn niet voor maar ook wordt worden naar deze dit wat bij uit hun zich",
    "sv": "och att är inte för också hennes honom efter sig",
    "da": "og ikke af meget nu efter hun",
    "no": "og ikke av veldig nå etter hun",
    "fi": "ja on ei että se hän joka kun mutta ovat oli myös kanssa sen",
    "pl": "się nie że jest oraz przez dla jego jej który która które jak",
    "cs": "je že jsou který která které ale jako jeho její pro také aby",
    "hu": "és az egy hogy nem van meg már csak mint után között",
    "ro": "și în pe cu este care pentru din să mai sau fost",
    "tr": "ve bir bu ile için çok olan gibi daha ama sonra kadar",
    "el": "και το της του να με σε τα για από που στην στο είναι",
}.items()}
_ALL_STOPWORDS = frozenset().union(*_STOPWORDS.values())

_RADIO_WINDOWS = " | ".join(
    f"Window.IsActive({w})"
    for w in ("radiochannels", "radioguide", "radiorecordings", "radiotimers", "radiosearch"))
# Kodi's titles for a guide slot with no programme behind it
_NO_PROGRAMME_IDS = (19055, 19266)

_genre_labels: Optional[Tuple[FrozenSet[str], FrozenSet[str]]] = None
_no_programme: Optional[FrozenSet[str]] = None


class Programme(NamedTuple):
    """What the EPG gives for one programme; empty, a 0 year or a number below 0 is unknown."""
    title: str
    original_title: str = ""
    year: int = 0
    season: int = -1
    episode: int = -1
    episode_name: str = ""
    genre: str = ""
    imdb_id: str = ""
    plot: str = ""


class PvrTitle(NamedTuple):
    """The TMDB title a programme matched."""
    media_type: str
    tmdb_id: int


class PvrLookupFailed(Exception):
    """Failed search request, as distinct from TMDB finding nothing."""


def _int_label(label: str) -> int:
    """Integer value of a numeric infolabel, -1 when it is empty or not a number."""
    return int(label) if label.lstrip("-").isdigit() else -1


def is_programme_path(path: str) -> bool:
    """True for a TV guide entry, recording, or channel or timer with EPG, never radio."""
    if path.startswith("pvr://guide/"):
        return not xbmc.getCondVisibility(_RADIO_WINDOWS)
    if path.startswith("pvr://channels/tv/"):
        return path.endswith(".pvr") and xbmc.getCondVisibility("ListItem.HasEpg")
    if path.startswith("pvr://recordings/tv/"):
        return not xbmc.getCondVisibility("ListItem.IsFolder")
    if path.startswith("pvr://timers/tv/timers/"):
        return xbmc.getCondVisibility("ListItem.HasEpg")
    return False


def programme_labels(source: str) -> List[str]:
    """Infolabels a programme read takes from the focused item or the player."""
    return [f"{source}.{field}" for field in _PROGRAMME_FIELDS]


def read_programme(title: str, source: str = "ListItem",
                   read: Callable[[str], str] = xbmc.getInfoLabel) -> Optional[Programme]:
    """Read a programme's EPG fields from the focused item or the player; None for no programme."""
    global _no_programme
    if not title:
        return None
    if _no_programme is None:
        _no_programme = frozenset(xbmc.getLocalizedString(i) for i in _NO_PROGRAMME_IDS)
    if title in _no_programme:
        return None
    return Programme(
        title=title,
        original_title=read(f"{source}.OriginalTitle"),
        year=max(_int_label(read(f"{source}.Year")), 0),
        season=_int_label(read(f"{source}.Season")),
        episode=_int_label(read(f"{source}.Episode")),
        episode_name=read(f"{source}.EpisodeName"),
        genre=read(f"{source}.Genre"),
        imdb_id=read(f"{source}.IMDBNumber"),
        plot=read(f"{source}.Plot"),
    )


def focused_programme() -> Optional[Programme]:
    """Read the focused programme, None when the focused item is not one."""
    labels = LabelSnapshot(("ListItem.FileNameAndPath", "ListItem.Title",
                            *programme_labels("ListItem")))
    if not is_programme_path(labels.get("ListItem.FileNameAndPath")):
        return None
    return read_programme(labels.get("ListItem.Title"), "ListItem", labels.get)


def _genres() -> Tuple[FrozenSet[str], FrozenSet[str]]:
    """Kodi's skipped and movie genre labels in the current language, read once."""
    global _genre_labels
    if _genre_labels is None:
        _genre_labels = (
            frozenset(xbmc.getLocalizedString(i) for i in _SKIP_GENRE_IDS),
            frozenset(xbmc.getLocalizedString(i) for i in _MOVIE_GENRE_IDS),
        )
    return _genre_labels


def is_skipped(programme: Programme) -> bool:
    """True for a news or sports programme, which never has a TMDB title."""
    return bool(programme.genre) and programme.genre in _genres()[0]


def programme_kind(programme: Programme) -> str:
    """Hint from the EPG: `tv` for any episode detail, `movie` for a dated film genre, else ''."""
    if programme.season >= 0 or programme.episode >= 0 or programme.episode_name:
        return "tv"
    # Kodi's Movie/Drama genre covers TV drama too
    if programme.year and programme.genre and programme.genre in _genres()[1]:
        return "movie"
    return ""


def clean_title(title: str) -> Tuple[str, int]:
    """Clean markers such as `New:` and `(HD)` off a title; returns it and any year it carried."""
    title = _LEADING.sub("", title.strip())
    year = 0
    found = _TRAILING_YEAR.search(title)
    if found:
        year = int(found.group(1))
        title = title[:found.start()]
    previous = None
    while previous != title:
        previous = title
        title = _TRAILING.sub("", title).strip()
    return title, year


def normalize(text: str) -> str:
    """Normalize a title for comparison: no accents, case or punctuation, `&` read as `and`."""
    decomposed = unicodedata.normalize("NFKD", text.replace("&", " and "))
    plain = "".join(c for c in decomposed if not unicodedata.combining(c))
    return " ".join(_NOT_WORD.sub(" ", plain.casefold()).split())


def match_key(programme: Programme) -> Optional[PvrMatchKey]:
    """Key a programme's match on its cleaned title, year and hint; None without a title."""
    title, title_year = clean_title(programme.title)
    folded = normalize(title)
    if not folded:
        return None
    return PvrMatchKey(folded, programme.year or title_year, programme_kind(programme))


def _result_year(result: dict) -> int:
    """Year a search result was released or first aired, 0 when unknown."""
    date = result.get("release_date") or result.get("first_air_date") or ""
    return int(date[:4]) if date[:4].isdigit() else 0


def _candidates(results: List[dict], folded: str, kind: str, year: int) -> List[dict]:
    """Search results whose title matches exactly and whose year and type fit the EPG."""
    found = []
    for result in results:
        media_type = result.get("media_type")
        if media_type not in ("movie", "tv") or (kind == "tv" and media_type != "tv"):
            continue
        names = (result.get("title") or result.get("name"),
                 result.get("original_title") or result.get("original_name"))
        if folded not in {normalize(n) for n in names if n}:
            continue
        if year:
            released = _result_year(result)
            if media_type == "movie" and (not released or abs(released - year) > 1):
                continue
            # a show's EPG year can be its episode's air year
            if media_type == "tv" and released > year + 1:
                continue
        found.append(result)
    if kind == "movie" and any(r["media_type"] == "movie" for r in found):
        found = [r for r in found if r["media_type"] == "movie"]
    return found


def detect_language(text: str) -> str:
    """Detect a plot's language code from its common words, empty when none clearly leads."""
    words = _WORD.findall(text.casefold())
    scores = sorted(((sum(w in stop for w in words), code) for code, stop in _STOPWORDS.items()),
                    reverse=True)
    (top, code), (second, _) = scores[0], scores[1]
    return code if top >= _MIN_STOPWORDS and top >= 2 * second else ""


def _name_pairs(text: str, exclude: FrozenSet[str] = frozenset()) -> FrozenSet[str]:
    """Folded pairs of adjacent capitalized words, the parts of full names, without title words."""
    pairs = set()
    words = _WORD.findall(text)
    for first, second in zip(words, words[1:]):
        if all(len(w) > 1 and w[0].isupper() and w.casefold() not in _ALL_STOPWORDS
               for w in (first, second)):
            folded = (normalize(first), normalize(second))
            if not exclude.intersection(folded):
                pairs.add(" ".join(folded))
    return frozenset(pairs)


def _by_language(candidates: List[dict], language: str) -> List[dict]:
    """Candidates first made in the plot's language; all of them when none was."""
    same = [c for c in candidates if language and c.get("original_language") == language]
    return same or candidates


def _by_names(candidates: List[dict], plot: str, title: str, language: str) -> List[dict]:
    """Candidates in the plot's language sharing full names with it; all of them when none does."""
    exclude = frozenset(title.split())
    plot_pairs = _name_pairs(plot, exclude)
    if len(plot_pairs) < _SHARED_NAMES:
        return candidates
    sharing = [c for c in candidates
               if (not language or c.get("original_language") == language)
               and len(plot_pairs & _name_pairs(c.get("overview") or "", exclude)) >= _SHARED_NAMES]
    return sharing or candidates


def _pick(candidates: List[dict], plot: str = "", title: str = "") -> Optional[dict]:
    """Pick the one candidate the plot or a vote lead singles out; None while still ambiguous."""
    if len(candidates) > 1 and plot:
        language = detect_language(plot)
        candidates = _by_language(candidates, language)
        if len(candidates) > 1:
            candidates = _by_names(candidates, plot, title, language)
    if len(candidates) == 1:
        return candidates[0]
    ranked = sorted(candidates, key=lambda r: r.get("vote_count") or 0, reverse=True)
    if len(ranked) > 1:
        top, runner_up = (r.get("vote_count") or 0 for r in ranked[:2])
        if top >= _DOMINANT_VOTES and top >= _DOMINANT_RATIO * runner_up:
            return ranked[0]
    return None


def _queries(programme: Programme, key: PvrMatchKey) -> List[str]:
    """Titles to search: the cleaned title, then an original title that differs from it."""
    queries = [clean_title(programme.title)[0]]
    original = clean_title(programme.original_title)[0] if programme.original_title else ""
    if original and normalize(original) != key.title_key:
        queries.append(original)
    return queries


def match_programme(programme: Programme, abort_flag=None) -> Optional[PvrTitle]:
    """Match a programme to a TMDB title, None when TMDB answers with nothing that fits."""
    from lib.data.api.tmdb import ApiTmdb

    key = match_key(programme)
    if not key:
        return None
    api = ApiTmdb()
    if programme.imdb_id.startswith("tt"):
        types = ("tvshow",) if key.kind == "tv" else ("movie", "tvshow")
        for media_type in types:
            tmdb_id = api.find_by_imdb(programme.imdb_id, media_type, abort_flag)
            if tmdb_id:
                return PvrTitle(media_type, int(tmdb_id))

    for query in _queries(programme, key):
        results = api.search(query, "multi", abort_flag=abort_flag)
        if results is None:
            raise PvrLookupFailed(query)
        folded = normalize(query)
        picked = _pick(_candidates(results, folded, key.kind, key.year), programme.plot, folded)
        if picked:
            media_type = "movie" if picked["media_type"] == "movie" else "tvshow"
            return PvrTitle(media_type, int(picked["id"]))
    return None


def match_title(title: str, year: int, media_type: str, abort_flag=None) -> Optional[int]:
    """Match a movie or TV show title to a TMDB id; None when nothing fits clearly."""
    from lib.data.api.tmdb import ApiTmdb

    folded = normalize(title)
    if not folded:
        return None
    results = ApiTmdb().search(title, "multi", abort_flag=abort_flag)
    if results is None:
        raise PvrLookupFailed(title)
    wanted = "movie" if media_type == "movie" else "tv"
    candidates = [r for r in _candidates(results, folded, "tv" if wanted == "tv" else "", year)
                  if r.get("media_type") == wanted]
    picked = _pick(candidates)
    return int(picked["id"]) if picked else None


def programme_candidates(programme: Programme, abort_flag=None) -> List[dict]:
    """Search results to pick from: exact title matches, else every movie and show found."""
    from lib.data.api.tmdb import ApiTmdb

    key = match_key(programme)
    if not key:
        return []
    api = ApiTmdb()
    exact: List[dict] = []
    loose: List[dict] = []
    for query in _queries(programme, key):
        results = api.search(query, "multi", abort_flag=abort_flag)
        if results is None:
            raise PvrLookupFailed(query)
        exact += _candidates(results, normalize(query), "", 0)
        loose += [r for r in results if r.get("media_type") in ("movie", "tv")]
    picked: List[dict] = []
    for result in exact or loose:
        if not any(p["id"] == result["id"] and p["media_type"] == result["media_type"]
                   for p in picked):
            picked.append(result)
    return picked


def fetch_programme_props(title: PvrTitle, abort_flag=None) -> Dict[str, str]:
    """Fetch a matched title's TMDB properties, empty when the fetch gets nothing."""
    from lib.data.online import apply_derived_props, fetch_tmdb_online_data

    tmdb_id = str(title.tmdb_id)
    props = fetch_tmdb_online_data(title.media_type, "", tmdb_id, abort_flag)
    if not props:
        return {}
    props["MediaType"] = title.media_type
    return apply_derived_props(props, title.media_type, props.get("IMDBNumber") or "", tmdb_id)
