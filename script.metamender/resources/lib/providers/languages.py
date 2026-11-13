"""Mapping of Kodi language codes to the codes TMDB and TVDB expect.

Kodi folders hold a free-form language code ("nl", "nl-NL", "NL-nl", "pt_BR").
TMDB takes "xx-YY" (or a bare "xx"); TVDB takes its own three-letter ids.
"""
from __future__ import annotations

from typing import Dict, FrozenSet, Optional, Tuple

# TMDB `GET /configuration/primary_translations`, retrieved 2026-11-09.
TMDB_PRIMARY_TRANSLATIONS: Tuple[str, ...] = (
    "af-ZA", "ar-AE", "ar-BH", "ar-EG", "ar-IQ", "ar-JO", "ar-LY", "ar-MA",
    "ar-QA", "ar-SA", "ar-TD", "ar-YE", "be-BY", "bg-BG", "bn-BD", "bn-IN",
    "br-FR", "ca-AD", "ca-ES", "ch-GU", "cs-CZ", "cy-GB", "da-DK", "de-AT",
    "de-CH", "de-DE", "el-CY", "el-GR", "en-AG", "en-AU", "en-BB", "en-BZ",
    "en-CA", "en-CM", "en-GB", "en-GG", "en-GH", "en-GI", "en-GY", "en-IE",
    "en-JM", "en-KE", "en-LC", "en-MW", "en-NZ", "en-PG", "en-TC", "en-US",
    "en-ZM", "en-ZW", "eo-EO", "es-AR", "es-CL", "es-DO", "es-EC", "es-ES",
    "es-GQ", "es-GT", "es-HN", "es-MX", "es-NI", "es-PA", "es-PE", "es-PY",
    "es-SV", "es-UY", "et-EE", "eu-ES", "fa-IR", "fi-FI", "fr-BF", "fr-CA",
    "fr-CD", "fr-CI", "fr-FR", "fr-GF", "fr-GP", "fr-MC", "fr-ML", "fr-MU",
    "fr-PF", "ga-IE", "gd-GB", "gl-ES", "he-IL", "hi-IN", "hr-HR", "hu-HU",
    "hy-AM", "id-ID", "it-IT", "it-VA", "ja-JP", "ka-GE", "kk-KZ", "kn-IN",
    "ko-KR", "ku-TR", "ky-KG", "lt-LT", "lv-LV", "ml-IN", "mr-IN", "ms-MY",
    "ms-SG", "nb-NO", "ne-NP", "nl-BE", "nl-NL", "no-NO", "oc-FR", "pa-IN",
    "pl-PL", "pt-AO", "pt-BR", "pt-MZ", "pt-PT", "ro-MD", "ro-RO", "ru-RU",
    "si-LK", "sk-SK", "sl-SI", "so-SO", "sq-AL", "sq-XK", "sr-ME", "sr-RS",
    "sv-SE", "sw-TZ", "ta-IN", "te-IN", "th-TH", "tl-PH", "tr-TR", "uk-UA",
    "ur-PK", "uz-UZ", "vi-VN", "zh-CN", "zh-HK", "zh-SG", "zh-TW", "zu-ZA",
)

# Languages in TMDB's list that have several regions: the region a bare
# language code ("pt") resolves to. A language with a single listed region
# resolves to that one without an entry here.
_DEFAULT_REGION_CODE: Dict[str, str] = {
    "ar": "ar-SA", "bn": "bn-BD", "ca": "ca-ES", "de": "de-DE",
    "el": "el-GR", "en": "en-US", "es": "es-ES", "fr": "fr-FR",
    "it": "it-IT", "ms": "ms-MY", "nl": "nl-NL", "pt": "pt-PT",
    "ro": "ro-RO", "sq": "sq-AL", "sr": "sr-RS", "zh": "zh-CN",
}

# ISO 639-1 language code to TVDB language id. Ids come from TVDB v4
# `GET /languages`, retrieved 2026-11-09. Portuguese and Chinese are handled
# separately in `tvdb_language` because TVDB splits them by region.
_TVDB_BY_LANGUAGE: Dict[str, str] = {
    "aa": "aar", "ab": "abk", "ae": "ave", "af": "afr", "ak": "aka",
    "am": "amh", "an": "arg", "ar": "ara", "as": "asm", "av": "ava",
    "ay": "aym", "az": "aze", "ba": "bak", "be": "bel", "bg": "bul",
    "bh": "bih", "bi": "bis", "bm": "bam", "bn": "ben", "bo": "bod",
    "br": "bre", "bs": "bos", "ca": "cat", "ce": "che", "ch": "cha",
    "co": "cos", "cr": "cre", "cs": "ces", "cu": "chu", "cv": "chv",
    "cy": "cym", "da": "dan", "de": "deu", "dv": "div", "dz": "dzo",
    "ee": "ewe", "el": "ell", "en": "eng", "eo": "epo", "es": "spa",
    "et": "est", "eu": "eus", "fa": "fas", "ff": "ful", "fi": "fin",
    "fj": "fij", "fo": "fao", "fr": "fra", "fy": "fry", "ga": "gle",
    "gd": "gla", "gl": "glg", "gn": "grn", "gu": "guj", "gv": "glv",
    "ha": "hau", "he": "heb", "hi": "hin", "ho": "hmo", "hr": "hrv",
    "ht": "hat", "hu": "hun", "hy": "hye", "hz": "her", "ia": "ina",
    "id": "ind", "ie": "ile", "ig": "ibo", "ii": "iii", "ik": "ipk",
    "io": "ido", "is": "isl", "it": "ita", "iu": "iku", "ja": "jpn",
    "jv": "jav", "ka": "kat", "kg": "kon", "ki": "kik", "kj": "kua",
    "kk": "kaz", "kl": "kal", "km": "khm", "kn": "kan", "ko": "kor",
    "kr": "kau", "ks": "kas", "ku": "kur", "kv": "kom", "kw": "cor",
    "ky": "kir", "la": "lat", "lb": "ltz", "lg": "lug", "li": "lim",
    "ln": "lin", "lo": "lao", "lt": "lit", "lu": "lub", "lv": "lav",
    "mg": "mlg", "mh": "mah", "mi": "mri", "mk": "mkd", "ml": "mal",
    "mn": "mon", "mr": "mar", "ms": "msa", "mt": "mlt", "my": "mya",
    "na": "nau", "nb": "nor", "nd": "nde", "ne": "nep", "ng": "ndo",
    "nl": "nld", "no": "nor", "nr": "nbl", "nv": "nav", "ny": "nya",
    "oc": "oci", "oj": "oji", "om": "orm", "or": "ori", "os": "oss",
    "pa": "pan", "pi": "pli", "pl": "pol", "ps": "pus", "qu": "que",
    "rm": "roh", "rn": "run", "ro": "ron", "ru": "rus", "rw": "kin",
    "sa": "san", "sc": "srd", "sd": "snd", "se": "sme", "sg": "sag",
    "si": "sin", "sk": "slk", "sl": "slv", "sm": "smo", "sn": "sna",
    "so": "som", "sq": "sqi", "sr": "srp", "ss": "ssw", "st": "sot",
    "su": "sun", "sv": "swe", "sw": "swa", "ta": "tam", "te": "tel",
    "tg": "tgk", "th": "tha", "ti": "tir", "tk": "tuk", "tl": "tgl",
    "tn": "tsn", "to": "ton", "tr": "tur", "ts": "tso", "tt": "tat",
    "tw": "twi", "ty": "tah", "ug": "uig", "uk": "ukr", "ur": "urd",
    "uz": "uzb", "ve": "ven", "vi": "vie", "vo": "vol", "wa": "wln",
    "wo": "wol", "xh": "xho", "yi": "yid", "yo": "yor", "za": "zha",
    "zu": "zul",
}

# TMDB translations TVDB has no language for. Every listed TMDB language has
# a TVDB counterpart today.
TVDB_UNSUPPORTED: FrozenSet[str] = frozenset()

# TVDB's Portuguese ids: "por" is Portugal, "pt" is Brazil.
_TVDB_PORTUGUESE = {"BR": "pt"}
_TVDB_PORTUGUESE_DEFAULT = "por"
# TVDB has one Taiwan id, which also serves Hong Kong (both Traditional);
# every other Chinese region uses "zho".
_TVDB_TRADITIONAL_CHINESE = {"TW": "zhtw", "HK": "zhtw"}


def _split(kodi_lang: str) -> Tuple[str, str]:
    """Return (language, REGION) from a free-form Kodi code; either may be empty."""
    parts = kodi_lang.strip().replace("_", "-").split("-")
    return parts[0].lower(), (parts[1].upper() if len(parts) > 1 else "")


def tmdb_language(kodi_lang: str) -> str:
    """Normalize to TMDB's "xx-YY" form.

    A bare language takes TMDB's primary translation for it (the single listed
    region, or the entry in _DEFAULT_REGION_CODE). A code TMDB does not list
    keeps its normalized form so TMDB decides what to do with it.
    """
    lang, region = _split(kodi_lang)
    if not lang:
        return ""
    if region:
        return "%s-%s" % (lang, region)
    default = _DEFAULT_REGION_CODE.get(lang)
    if default:
        return default
    matches = [c for c in TMDB_PRIMARY_TRANSLATIONS if c.startswith(lang + "-")]
    return matches[0] if len(matches) == 1 else lang


def tvdb_language(kodi_lang: str) -> Optional[str]:
    """Map a Kodi language code to a TVDB language id.

    Returns None when TVDB has no such language, so callers can skip TVDB for
    the folder instead of sending a request that would be rejected.
    """
    lang, region = _split(kodi_lang)
    if lang == "pt":
        return _TVDB_PORTUGUESE.get(region, _TVDB_PORTUGUESE_DEFAULT)
    if lang == "zh":
        return _TVDB_TRADITIONAL_CHINESE.get(region, "zho")
    return _TVDB_BY_LANGUAGE.get(lang)
