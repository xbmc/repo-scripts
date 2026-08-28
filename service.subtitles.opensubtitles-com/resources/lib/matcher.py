"""
OpenSubtitles.com Smart Subtitle Matcher & Ranking Engine
Ranks subtitles by release token precision matching against the playing video filename and Guessit metadata.
"""

import math
import os
import re
from difflib import SequenceMatcher

# Known high-frequency Scene / P2P release groups
KNOWN_RELEASE_GROUPS = {
    "flux", "framestor", "sparks", "yify", "yts", "rarbg", "ntb", "psa",
    "dimension", "ion10", "cmrg", "glados", "surcode", "kogi", "ctrlhd",
    "don", "playbd", "tayto", "ebp", "geek", "smurf", "rovers", "amiable",
    "evo", "galaxyrg", "megusta", "tgx", "fgt", "pahe", "bone", "deflate",
    "shortbreath", "minx", "tigole", "qxr", "vyndros", "judas", "ember",
    "bhd", "hallowed", "geckos", "strife", "chd", "wiki", "hdchina",
    "vxt", "cakes", "ggwp", "hazmat", "as88", "cinev", "acool", "glam"
}

# Quality Hierarchy & Compatibility
SOURCES_BLURAY = {"bluray", "bdrip", "brrip", "uhdbluray", "uhd", "remux"}
SOURCES_WEB = {"web-dl", "webdl", "webrip", "web", "amzn", "nf", "dsnp", "atvp", "hmax", "max", "hulu", "pcok"}
SOURCES_HDTV = {"hdtv", "pdtv", "dsr", "dvb"}
SOURCES_DVD = {"dvdrip", "dvd", "dvd5", "dvd9"}
SOURCES_CAM = {"cam", "camrip", "hdcam", "ts", "telesync", "tc", "telecine", "scr", "screener", "r5"}

STREAMING_SERVICES = {"nf", "amzn", "atvp", "dsnp", "hmax", "max", "hulu", "pcok", "pmtp", "itunes"}

EDITIONS = {
    "extended": ["extended", "extended cut", "ext"],
    "directors_cut": ["directors cut", "director's cut", "dc"],
    "unrated": ["unrated", "uncut"],
    "imax": ["imax", "imax edition"],
    "remastered": ["remastered", "restored"],
    "theatrical": ["theatrical", "theatrical cut"]
}


def _attrs(subtitle):
    """The entry's attributes as a dict - {} for any malformed shape."""
    attributes = subtitle.get("attributes") if isinstance(subtitle, dict) else None
    return attributes if isinstance(attributes, dict) else {}


def sanitize_filename(filename):
    """Strips extension, directory path, and special punctuation for comparison."""
    if not filename:
        return ""
    # Coerce: API fields are not guaranteed to be strings, and os.path.basename() raises
    # TypeError on anything else - which used to abort ranking for the entire result list.
    # (parse_release_tokens() below already does the same.)
    base = os.path.basename(str(filename))
    # Strip common container extensions
    base = re.sub(r"\.(mkv|mp4|avi|m4v|ts|mov|wmv|iso)$", "", base, flags=re.IGNORECASE)
    return base.strip()


def parse_release_tokens(text):
    """
    Extracts structured release tokens from a video filename or subtitle release string.
    Returns a dictionary of normalized tokens.
    """
    if not text:
        return {}

    raw = str(text)
    clean = re.sub(r"[\[\]\(\)\._\-+]", " ", raw)
    words = [w.lower() for w in clean.split() if w]
    words_set = set(words)
    raw_lower = raw.lower()

    tokens = {
        "raw": raw,
        "release_group": None,
        "source": None,
        "resolution": None,
        "video_codec": None,
        "audio_codec": None,
        "edition": None,
        "streaming_service": None,
        "is_cam": False,
        "is_bluray": False,
        "is_web": False,
    }

    # 1. Release Group
    # Match standard hyphenated group at end: e.g. -FLUX or [FLUX]
    end_group_match = re.search(r"[-_]([a-zA-Z0-9]{2,15})(?:\.[a-zA-Z0-9]{2,4})?$", raw)
    if end_group_match:
        cand = end_group_match.group(1).lower()
        if cand not in {"mkv", "mp4", "avi", "srt", "sub", "2160p", "1080p", "720p", "x264", "x265", "hevc"}:
            tokens["release_group"] = cand

    if not tokens["release_group"]:
        for group in KNOWN_RELEASE_GROUPS:
            if group in words_set:
                tokens["release_group"] = group
                break

    # 2. Resolution / Screen Size
    if "2160p" in words_set or "4k" in words_set or "uhd" in words_set:
        tokens["resolution"] = "2160p"
    elif "1080p" in words_set or "1080i" in words_set or "fhd" in words_set:
        tokens["resolution"] = "1080p"
    elif "720p" in words_set or "hd" in words_set:
        tokens["resolution"] = "720p"
    elif "480p" in words_set or "576p" in words_set or "sd" in words_set:
        tokens["resolution"] = "480p"

    # 3. Source
    if words_set.intersection(SOURCES_CAM) or "telesync" in raw_lower or "camrip" in raw_lower:
        tokens["source"] = "cam"
        tokens["is_cam"] = True
    elif words_set.intersection(SOURCES_BLURAY) or "bluray" in raw_lower or "bdrip" in raw_lower:
        tokens["source"] = "bluray"
        tokens["is_bluray"] = True
    elif words_set.intersection(SOURCES_WEB) or "web-dl" in raw_lower or "webdl" in raw_lower or "webrip" in raw_lower:
        tokens["source"] = "web"
        tokens["is_web"] = True
    elif words_set.intersection(SOURCES_HDTV):
        tokens["source"] = "hdtv"
    elif words_set.intersection(SOURCES_DVD):
        tokens["source"] = "dvd"

    # 4. Streaming Service
    for s in STREAMING_SERVICES:
        if s in words_set:
            tokens["streaming_service"] = s
            break

    # 5. Video Codec
    if "x265" in words_set or "hevc" in words_set or "h265" in words_set or "h 265" in raw_lower:
        tokens["video_codec"] = "x265"
    elif "x264" in words_set or "avc" in words_set or "h264" in words_set or "h 264" in raw_lower:
        tokens["video_codec"] = "x264"
    elif "av1" in words_set:
        tokens["video_codec"] = "av1"
    elif "xvid" in words_set or "divx" in words_set:
        tokens["video_codec"] = "xvid"

    # 6. Audio Codec
    if "atmos" in words_set or "truehd" in words_set:
        tokens["audio_codec"] = "atmos"
    elif "dts-hd" in raw_lower or "dtshd" in words_set or "dts" in words_set:
        tokens["audio_codec"] = "dts"
    elif "ddp" in words_set or "ddp5" in words_set or "eac3" in words_set:
        tokens["audio_codec"] = "ddp"
    elif "ac3" in words_set or "dd5" in words_set:
        tokens["audio_codec"] = "ac3"
    elif "aac" in words_set:
        tokens["audio_codec"] = "aac"

    # 7. Edition / Cut
    for ed_key, ed_patterns in EDITIONS.items():
        for pat in ed_patterns:
            if pat in raw_lower:
                tokens["edition"] = ed_key
                break
        if tokens["edition"]:
            break

    return tokens


def calculate_match_score(subtitle, video_filename, guessit_data=None, prefer_hearing_impaired=False):
    """
    Calculates a precision match score (0 - 15000+) between a subtitle item and the playing video.
    Higher score indicates higher sync confidence and release match accuracy.
    """
    score = 0.0
    attributes = _attrs(subtitle)

    # 1. Moviehash Bit-Exact Match (Ultimate Accuracy)
    if attributes.get("moviehash_match"):
        score += 10000.0

    # Extract clean release strings
    sub_release = attributes.get("release", "") or ""
    sub_clean = sanitize_filename(sub_release)
    video_clean = sanitize_filename(video_filename)

    # 2. Exact or Substring Filename Match
    if sub_clean and video_clean:
        if sub_clean.lower() == video_clean.lower():
            score += 5000.0
        elif sub_clean.lower() in video_clean.lower() or video_clean.lower() in sub_clean.lower():
            score += 3000.0

    # 3. Tokenized Match Comparison
    video_tokens = parse_release_tokens(video_filename)
    sub_tokens = parse_release_tokens(sub_release)

    # Augment video tokens with Guessit data if available
    if guessit_data and isinstance(guessit_data, dict):
        if guessit_data.get("release_group") and not video_tokens.get("release_group"):
            video_tokens["release_group"] = str(guessit_data.get("release_group")).lower()
        if guessit_data.get("source") and not video_tokens.get("source"):
            video_tokens["source"] = str(guessit_data.get("source")).lower()
        if guessit_data.get("screen_size") and not video_tokens.get("resolution"):
            video_tokens["resolution"] = str(guessit_data.get("screen_size")).lower()
        if guessit_data.get("video_codec") and not video_tokens.get("video_codec"):
            video_tokens["video_codec"] = str(guessit_data.get("video_codec")).lower()

    # (a) Release Group Matching (Highest single predictor of timing sync)
    if video_tokens.get("release_group") and sub_tokens.get("release_group"):
        if video_tokens["release_group"] == sub_tokens["release_group"]:
            score += 1500.0
        else:
            # Different release group penalty
            score -= 100.0

    # (b) Source / Quality Matching
    if video_tokens.get("source") and sub_tokens.get("source"):
        if video_tokens["source"] == sub_tokens["source"]:
            score += 800.0
        elif (video_tokens["is_bluray"] and sub_tokens["is_web"]) or (video_tokens["is_web"] and sub_tokens["is_bluray"]):
            score += 300.0  # Often compatible sync between WEB and BluRay
        elif (video_tokens["is_cam"] and not sub_tokens["is_cam"]) or (not video_tokens["is_cam"] and sub_tokens["is_cam"]):
            # Severe sync incompatibility between CAM and Digital/BluRay
            score -= 3000.0

    # (c) Edition Matching (Extended vs Theatrical timing shift)
    if video_tokens.get("edition") and sub_tokens.get("edition"):
        if video_tokens["edition"] == sub_tokens["edition"]:
            score += 1000.0
        else:
            score -= 2000.0
    elif (video_tokens.get("edition") and not sub_tokens.get("edition")) or (not video_tokens.get("edition") and sub_tokens.get("edition")):
        score -= 500.0

    # (d) Streaming Service Matching
    if video_tokens.get("streaming_service") and sub_tokens.get("streaming_service"):
        if video_tokens["streaming_service"] == sub_tokens["streaming_service"]:
            score += 500.0

    # (e) Resolution Matching
    if video_tokens.get("resolution") and sub_tokens.get("resolution"):
        if video_tokens["resolution"] == sub_tokens["resolution"]:
            score += 300.0

    # (f) Video Codec Matching
    if video_tokens.get("video_codec") and sub_tokens.get("video_codec"):
        if video_tokens["video_codec"] == sub_tokens["video_codec"]:
            score += 150.0

    # (g) Audio Codec Matching
    if video_tokens.get("audio_codec") and sub_tokens.get("audio_codec"):
        if video_tokens["audio_codec"] == sub_tokens["audio_codec"]:
            score += 100.0

    # 4. Fuzzy Sequence Similarity
    if sub_clean and video_clean:
        sim = SequenceMatcher(None, sub_clean.lower(), video_clean.lower()).ratio()
        score += sim * 500.0

    # 5. Hearing Impaired (Accessibility alignment)
    is_hi = bool(attributes.get("hearing_impaired"))
    if prefer_hearing_impaired:
        if is_hi:
            score += 350.0  # Boost hearing impaired subtitles when preferred
        else:
            score -= 150.0  # De-prioritize non-HI when user prefers HI

    # 6. Reputation & Community Quality Bonuses (Tie Breakers)
    if attributes.get("from_trusted"):
        score += 100.0

    try:
        rating = float(attributes.get("ratings") or 0.0)
    except (TypeError, ValueError):
        rating = 0.0
    score += (rating / 10.0) * 50.0

    try:
        downloads = int(attributes.get("download_count") or 0)
    except (TypeError, ValueError):
        downloads = 0
    if downloads > 0:
        score += min(math.log10(downloads + 1) * 10.0, 50.0)

    # Built-in sync flag is strictly reserved for bit-exact moviehash matches
    is_sync = bool(attributes.get("moviehash_match"))

    # Attach computed score and sync flag to subtitle dict
    subtitle["_match_score"] = score
    subtitle["_is_sync"] = is_sync

    return score


def get_match_display_tag(subtitle):
    """
    Returns a clean, colorized Kodi match badge string for display in the subtitle list (e.g. [COLOR yellow](+95)[/COLOR]).
    """
    attributes = _attrs(subtitle)
    if attributes.get("moviehash_match"):
        return "[COLOR yellow](Hash)[/COLOR]"

    score = subtitle.get("_match_score", 0.0)
    
    # Scale score into clean relative match rating (+1 to +99)
    if score >= 5000:
        val = 99
    elif score >= 2000:
        val = min(95, 80 + int((score - 2000) / 200))
    elif score >= 1000:
        val = min(79, 60 + int((score - 1000) / 50))
    elif score >= 500:
        val = min(59, 40 + int((score - 500) / 25))
    elif score >= 100:
        val = min(39, 15 + int((score - 100) / 20))
    elif score > 0:
        val = max(1, min(14, int(score / 10)))
    else:
        val = 0

    if val > 0:
        return f"[COLOR yellow](+{val})[/COLOR]"
    return ""


def rank_subtitles(subtitles, video_filename, guessit_data=None, smart_ranking=True, preferred_languages=None, prefer_hearing_impaired=False):
    """
    Ranks subtitle list according to smart release token precision, sync confidence,
    and multi-language user preference hierarchy:
      1. Top #1 best match for 1st preferred language
      2. Top #1 best match for 2nd preferred language (etc.)
      3. Remaining subtitles grouped by language in preferred order, sorted from best to worst.
    """
    if not subtitles:
        return []

    # a non-object entry cannot score, sort or render - drop it here so it
    # cannot raise inside the except handler below (assigning _match_score
    # to a string re-raised and disabled ranking for the whole page)
    subtitles = [s for s in subtitles if isinstance(s, dict)]
    if not subtitles:
        return []

    # 1. Compute match scores for all subtitles if smart ranking enabled
    if smart_ranking and video_filename:
        for sub in subtitles:
            try:
                calculate_match_score(sub, video_filename, guessit_data, prefer_hearing_impaired=prefer_hearing_impaired)
            except Exception:
                # one malformed entry (non-numeric ratings, odd attributes) must
                # not disable ranking for every valid result - it just scores 0
                sub["_match_score"] = 0.0
        sort_key = lambda s: s.get("_match_score", 0.0)
    else:
        def _num(value):
            # API fields are not guaranteed numeric ("SizeError" scalars have
            # shipped) - a str/int mix inside sorted() raises TypeError
            try:
                return float(value or 0)
            except (TypeError, ValueError):
                return 0.0

        def sort_key(s):
            attributes = s.get("attributes")
            if not isinstance(attributes, dict):
                attributes = {}
            return (bool(attributes.get("from_trusted", False)),
                    _num(attributes.get("votes")),
                    _num(attributes.get("ratings")),
                    _num(attributes.get("download_count")))

    # 2. If no preferred languages list provided, sort everything globally
    if not preferred_languages:
        return sorted(subtitles, key=sort_key, reverse=True)

    # 3. Group and sort subtitles by language
    lang_map = {}
    for sub in subtitles:
        lang = str(_attrs(sub).get("language", "")).lower()
        if lang not in lang_map:
            lang_map[lang] = []
        lang_map[lang].append(sub)

    # Sort each language group best to worst
    for lang in lang_map:
        lang_map[lang] = sorted(lang_map[lang], key=sort_key, reverse=True)

    # Determine ordered list of languages (preferred first, then any remaining)
    ordered_langs = []
    for plang in preferred_languages:
        plang_clean = str(plang).lower().strip()
        if plang_clean in lang_map and plang_clean not in ordered_langs:
            ordered_langs.append(plang_clean)

    for lang in lang_map:
        if lang not in ordered_langs:
            ordered_langs.append(lang)

    # 4. Multi-language grouping / interleaving:
    if smart_ranking:
        # Phase A: Pick #1 Top match for each preferred language
        top_picks = []
        remaining_groups = {}

        for lang in ordered_langs:
            subs_for_lang = list(lang_map.get(lang, []))
            if subs_for_lang:
                top_picks.append(subs_for_lang.pop(0))
                remaining_groups[lang] = subs_for_lang

        # Phase B: Group remaining subtitles by language in order, best to worst
        remaining_ordered = []
        for lang in ordered_langs:
            if lang in remaining_groups and remaining_groups[lang]:
                remaining_ordered.extend(remaining_groups[lang])

        return top_picks + remaining_ordered
    else:
        # When smart ranking is off, cleanly group all subtitles by language in preferred order
        result = []
        for lang in ordered_langs:
            result.extend(lang_map.get(lang, []))
        return result
