"""Language codes, in every spelling the hosts hand us.

The API speaks two-letter codes with four OpenSubtitles additions (``pb``, ``ze``,
``zt``, ``pm``) that are not ISO at all. The hosts do not:

    Bazarr      babelfish alpha3, ``pob`` for Brazilian Portuguese
    Kodi        English display names, "Portuguese (Brazil)"
    Jellyfin    ISO639-2, sometimes with a region, ``pt-BR``
    Emby        the same, and occasionally the bibliographic form, ``ger``
    VLC         whatever the user typed

So every plugin needs the same resolver, and the table lives here rather than
five times over. The display names are the same ones packages/core/src/languages.ts
ships to the web players, kept in step by plugins/shared/match-cases.json.

An unrecognised two-letter code passes through untouched. The corpus carries 185
distinct codes and this table names 74 of them; resolving the rest to nothing
would hide subtitles that exist, and resolving them to English would be a lie.
"""

from __future__ import annotations

# ISO639-1 (plus the four OpenSubtitles codes) to English display name.
NAMES: dict[str, str] = {
    # OpenSubtitles conventions, not ISO639.
    "pb": "Portuguese (Brazil)",
    "ze": "Chinese (bilingual)",
    "zt": "Chinese (traditional)",
    "pm": "Portuguese (Mozambique)",
    "ar": "Arabic",
    "bg": "Bulgarian",
    "bn": "Bengali",
    "bs": "Bosnian",
    "ca": "Catalan",
    "cs": "Czech",
    "da": "Danish",
    "de": "German",
    "el": "Greek",
    "en": "English",
    "eo": "Esperanto",
    "es": "Spanish",
    "et": "Estonian",
    "eu": "Basque",
    "fa": "Persian",
    "fi": "Finnish",
    "fr": "French",
    "gl": "Galician",
    "he": "Hebrew",
    "hi": "Hindi",
    "hr": "Croatian",
    "hu": "Hungarian",
    "hy": "Armenian",
    "id": "Indonesian",
    "is": "Icelandic",
    "it": "Italian",
    "ja": "Japanese",
    "ka": "Georgian",
    "kk": "Kazakh",
    "km": "Khmer",
    "ko": "Korean",
    "ku": "Kurdish",
    "lt": "Lithuanian",
    "lv": "Latvian",
    "mk": "Macedonian",
    "ml": "Malayalam",
    "mn": "Mongolian",
    "ms": "Malay",
    "my": "Burmese",
    "nl": "Dutch",
    "no": "Norwegian",
    "oc": "Occitan",
    "pl": "Polish",
    "pt": "Portuguese",
    "ro": "Romanian",
    "ru": "Russian",
    "si": "Sinhala",
    "sk": "Slovak",
    "sl": "Slovenian",
    "sq": "Albanian",
    "sr": "Serbian",
    "sv": "Swedish",
    "sw": "Swahili",
    "ta": "Tamil",
    "te": "Telugu",
    "th": "Thai",
    "tl": "Tagalog",
    "tr": "Turkish",
    "tt": "Tatar",
    "uk": "Ukrainian",
    "ur": "Urdu",
    "uz": "Uzbek",
    "vi": "Vietnamese",
    "zh": "Chinese",
}

# Three-letter forms. Both ISO639-2/T and /B are listed where they differ, because
# which one arrives depends on the host: Jellyfin sends `deu`, Emby sends `ger`.
ALPHA3: dict[str, str] = {
    "ara": "ar",
    "bul": "bg",
    "ben": "bn",
    "bos": "bs",
    "cat": "ca",
    "ces": "cs",
    "cze": "cs",
    "dan": "da",
    "deu": "de",
    "ger": "de",
    "ell": "el",
    "gre": "el",
    "eng": "en",
    "epo": "eo",
    "spa": "es",
    "est": "et",
    "eus": "eu",
    "baq": "eu",
    "fas": "fa",
    "per": "fa",
    "fin": "fi",
    "fra": "fr",
    "fre": "fr",
    "glg": "gl",
    "heb": "he",
    "hin": "hi",
    "hrv": "hr",
    "hun": "hu",
    "hye": "hy",
    "arm": "hy",
    "ind": "id",
    "isl": "is",
    "ice": "is",
    "ita": "it",
    "jpn": "ja",
    "kat": "ka",
    "geo": "ka",
    "kaz": "kk",
    "khm": "km",
    "kor": "ko",
    "kur": "ku",
    "lit": "lt",
    "lav": "lv",
    "mkd": "mk",
    "mac": "mk",
    "mal": "ml",
    "mon": "mn",
    "msa": "ms",
    "may": "ms",
    "mya": "my",
    "bur": "my",
    "nld": "nl",
    "dut": "nl",
    "nor": "no",
    "nob": "no",
    "nno": "no",
    "oci": "oc",
    "pol": "pl",
    "por": "pt",
    "pob": "pb",
    "ron": "ro",
    "rum": "ro",
    "rus": "ru",
    "sin": "si",
    "slk": "sk",
    "slo": "sk",
    "slv": "sl",
    "sqi": "sq",
    "alb": "sq",
    "srp": "sr",
    "swe": "sv",
    "swa": "sw",
    "tam": "ta",
    "tel": "te",
    "tha": "th",
    "tgl": "tl",
    "tur": "tr",
    "tat": "tt",
    "ukr": "uk",
    "urd": "ur",
    "uzb": "uz",
    "vie": "vi",
    "zho": "zh",
    "chi": "zh",
}

# Everything else a host has been seen to send. Legacy codes, regional tags and the
# names people write by hand.
ALIASES: dict[str, str] = {
    # Superseded ISO codes. Java and some older hosts still emit these.
    "iw": "he",
    "in": "id",
    "ji": "yi",
    "nb": "no",
    "nn": "no",
    # Regional tags. Brazilian Portuguese is the one that matters: the corpus files
    # it under `pb`, and a plugin that asks for `pt` gets European Portuguese and a
    # user who thinks the plugin is broken.
    "pt-br": "pb",
    "pt-pt": "pt",
    "por-br": "pb",
    "zh-hant": "zt",
    "zh-tw": "zt",
    "zh-hk": "zt",
    "zh-hans": "zh",
    "zh-cn": "zh",
    "sr-latn": "sr",
    "sr-cyrl": "sr",
    "es-419": "es",
    "es-mx": "es",
    "en-us": "en",
    "en-gb": "en",
    # Written out, as Kodi and hand configuration give them.
    "brazilian portuguese": "pb",
    "portuguese brazilian": "pb",
    "simplified chinese": "zh",
    "traditional chinese": "zt",
    "chinese bilingual": "ze",
    "farsi": "fa",
    "castilian": "es",
    "flemish": "nl",
    "greek modern": "el",
    "serbo croatian": "sr",
}

# Display name back to code, so "Portuguese (Brazil)" resolves the way Kodi sends it.
_BY_NAME: dict[str, str] = {}
for _code, _name in NAMES.items():
    _BY_NAME[_name.lower()] = _code
    # "Portuguese (Brazil)" also answers to "portuguese brazil".
    _plain = _name.lower().replace("(", " ").replace(")", " ")
    _BY_NAME[" ".join(_plain.split())] = _code


def _normalise(value: str) -> str:
    return " ".join(value.strip().lower().replace("_", "-").split())


def to_code(value: str | None) -> str | None:
    """Resolve any spelling of a language to the code the API uses.

    Returns None for an empty value, and passes an unknown two-letter code through
    rather than guessing.
    """
    if not value:
        return None
    v = _normalise(value)
    if not v:
        return None
    if v in NAMES:
        return v
    if v in ALIASES:
        return ALIASES[v]
    if v in ALPHA3:
        return ALPHA3[v]
    if v in _BY_NAME:
        return _BY_NAME[v]
    # A region we do not have a rule for: keep the base language.
    if "-" in v:
        return to_code(v.split("-", 1)[0])
    # Names with punctuation, "Chinese (traditional)" arriving as "chinese traditional".
    plain = " ".join(v.replace("(", " ").replace(")", " ").split())
    if plain != v:
        return to_code(plain)
    if len(v) == 2 and v.isalpha():
        return v
    return None


def language_name(code: str | None) -> str | None:
    """Display name for a code, falling back to the uppercased code."""
    if not code:
        return None
    key = code.strip().lower()
    if not key:
        return None
    return NAMES.get(key, key.upper())


def to_codes(values: object) -> list[str]:
    """Resolve a configured preference list, dropping what cannot be resolved.

    Accepts a list, or one string holding a comma or space separated list, because
    that is what a text field in a plugin's settings page produces.
    """
    if values is None:
        return []
    if isinstance(values, str):
        parts = [p for p in values.replace(",", " ").split() if p]
    else:
        parts = [str(v) for v in values]  # type: ignore[union-attr]
    out: list[str] = []
    for part in parts:
        code = to_code(part)
        if code and code not in out:
            out.append(code)
    return out
