"""Which subtitle is the right one.

The rules here are the same ones packages/core/src/match.ts applies in a browser,
and plugins/shared/match-cases.json holds the cases both sides are checked against.
Resolving which *title* a file belongs to is the server's job now (the by-* lookup
verbs), so only the client-side ranking of an already-resolved title's subtitles
lives here. Two things differ from the web bindings, both from data that did not
exist when those were written:

  * ``release`` is the video file's own release name, and it is compared against the
    subtitle's. match.ts compared the subtitle's release name against the *title*,
    which cannot agree with anything; it went unnoticed because release_name was
    empty for the whole corpus until subs.sub_meta was published. Every one of these
    plugins holds the actual filename, so this is the strongest signal available.

  * season and episode are a filter, not a score. sub_meta carries them now, and a
    subtitle for the wrong episode is not a worse match: it is the wrong file, and
    showing it is how a viewer ends up watching episode 14 with episode 15's lines.
    A row with no season at all is kept, because sub_meta has no entry for every id.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from .languages import language_name

# How close two release names have to be before we call it the same encode.
EXACT_RELEASE = 0.95

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def normalise(value: str) -> str:
    """Fold case, accents and punctuation, so two spellings of one title compare equal."""
    folded = unicodedata.normalize("NFKD", value.lower())
    stripped = "".join(c for c in folded if not unicodedata.combining(c))
    return _NON_ALNUM.sub(" ", stripped).strip()


def similarity(a: str, b: str) -> float:
    """Dice coefficient over bigrams. Forgiving of word order and punctuation."""
    x = normalise(a)
    y = normalise(b)
    if not x or not y:
        return 0.0
    if x == y:
        return 1.0

    def grams(s: str) -> dict[str, int]:
        out: dict[str, int] = {}
        for i in range(len(s) - 1):
            g = s[i : i + 2]
            out[g] = out.get(g, 0) + 1
        return out

    ga = grams(x)
    gb = grams(y)
    total = sum(ga.values()) + sum(gb.values())
    if total == 0:
        return 0.0
    overlap = sum(min(n, ga.get(g, 0)) for g, n in gb.items())
    return (2 * overlap) / total


@dataclass
class Hint:
    """What the host told us about the file being played. Every field is optional."""

    imdb_id: str | None = None
    tmdb_id: int | None = None
    series_imdb_id: str | None = None
    title: str | None = None
    episode_title: str | None = None
    year: int | None = None
    season: int | None = None
    episode: int | None = None
    #: The video file's name without its extension. The best evidence there is.
    release: str | None = None


@dataclass
class Options:
    """Everything about the request that is not the media itself."""

    #: Preference order, resolved codes. Earlier is better. Empty means no preference.
    languages: list[str] = field(default_factory=list)
    #: A hard filter. Handing a player a format it cannot parse shows an empty track.
    formats: list[str] = field(default_factory=lambda: ["srt", "ass", "ssa", "vtt", "sub"])
    #: True to prefer hearing impaired, False to avoid it, None for no preference.
    hearing_impaired: bool | None = None
    #: The most subtitles per language. ``rank`` keeps this many in all; ``find`` reads
    #: and keeps this many for each language, 100 to a request.
    limit: int = 100


@dataclass
class Candidate:
    subtitle: dict
    score: float
    reason: str

    @property
    def id(self) -> int:
        return int(self.subtitle["id"])


@dataclass
class Ranked:
    candidates: list[Candidate]
    #: Dropped because the player cannot render the format.
    unrenderable: int = 0
    #: Dropped because they belong to another episode.
    wrong_episode: int = 0


def _wrong_episode(sub: dict, hint: Hint) -> bool:
    if hint.season is None or hint.episode is None:
        return False
    season = sub.get("season")
    episode = sub.get("episode")
    # No entry in sub_meta for this id. Unknown is not wrong.
    if season is None or episode is None:
        return False
    return int(season) != hint.season or int(episode) != hint.episode


def score_subtitle(sub: dict, hint: Hint, opts: Options) -> tuple[float, str]:
    reasons: list[str] = []
    score = 0.0

    if opts.languages:
        lang = str(sub.get("language") or "")
        if lang in opts.languages:
            score += 100 - opts.languages.index(lang) * 20
            reasons.append("preferred language " + lang)
        else:
            score -= 50

    if opts.hearing_impaired is not None:
        if bool(sub.get("hearing_impaired")) == opts.hearing_impaired:
            score += 15
            reasons.append("hearing impaired" if opts.hearing_impaired else "not hearing impaired")
        else:
            score -= 15

    release = str(sub.get("release_name") or "").strip()
    if release and hint.release:
        sim = similarity(release, hint.release)
        if sim >= EXACT_RELEASE:
            score += 60
            reasons.append("same release")
        elif sim > 0.5:
            score += sim * 30
            reasons.append("release name is close")

    # An episode we could confirm rather than merely not rule out.
    if hint.season is not None and sub.get("season") is not None and not _wrong_episode(sub, hint):
        score += 20
        reasons.append("season %s episode %s" % (hint.season, hint.episode))

    # A file with no cues renders as an empty track, the most confusing failure a
    # subtitle plugin has. Known corpus defect, cheap to defend against here.
    if int(sub.get("cues") or 0) == 0:
        score -= 500
        reasons.append("no cues")

    if not reasons:
        reasons.append("%s %s" % (sub.get("language"), sub.get("format")))
    return score, ", ".join(reasons)


def rank(subtitles: list[dict], hint: Hint, opts: Options) -> Ranked:
    """Filter to what can be shown, then order it best first."""
    renderable = {f.lower() for f in opts.formats}
    out = Ranked(candidates=[])
    usable: list[dict] = []
    for sub in subtitles:
        if str(sub.get("format") or "").lower() not in renderable:
            out.unrenderable += 1
            continue
        if _wrong_episode(sub, hint):
            out.wrong_episode += 1
            continue
        usable.append(sub)

    scored = []
    for sub in usable:
        score, reason = score_subtitle(sub, hint, opts)
        scored.append(Candidate(subtitle=sub, score=score, reason=reason))
    # The id breaks ties, so two runs of one query return the same order.
    scored.sort(key=lambda c: (-c.score, c.id))
    out.candidates = scored[: opts.limit]
    return out


def candidate_label(c: Candidate) -> str:
    """What a viewer reads in the subtitle list.

    Most of the corpus carries no release name, so thirty English candidates for one
    film used to read "English" thirty times over and picking one was a lottery. The
    cue count is the only other field that differs, so it is what tells them apart.
    """
    s = c.subtitle
    bits = [language_name(str(s.get("language") or "")) or "Unknown"]
    if s.get("hearing_impaired"):
        bits.append("HI")
    release = str(s.get("release_name") or "").strip()
    if release:
        bits.append(release[:40])
    elif int(s.get("cues") or 0) > 0:
        bits.append("%d lines" % int(s["cues"]))
    return " - ".join(bits)
