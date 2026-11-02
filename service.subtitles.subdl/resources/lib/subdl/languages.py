"""Kodi languages to SubDL language codes and back.

Kodi hands a subtitle add-on English language names ("Persian", "Portuguese (Brazil)")
that its own ``xbmc.convertLanguage`` turns into ISO 639-1 codes ("fa", "pb"). SubDL
uses its own frozen codes ("FA", "BR_PT", "ZH_BG"). This module only speaks codes, so
it runs without Kodi; the Kodi side does the name <-> code step.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Tuple

#: SubDL code -> (ISO 639 code Kodi knows, English name Kodi uses for that code).
#: The ISO code picks Kodi's flag and names the saved file ("film.pb.srt"); the name
#: is only a fallback for when Kodi cannot convert the code itself.
SUBDL_LANGUAGES: Dict[str, Tuple[str, str]] = {
    "AR": ("ar", "Arabic"),
    "AZ": ("az", "Azerbaijani"),
    "BE": ("be", "Belarusian"),
    "BG": ("bg", "Bulgarian"),
    "BN": ("bn", "Bengali"),
    "BR_PT": ("pb", "Portuguese (Brazil)"),
    "BS": ("bs", "Bosnian"),
    "CA": ("ca", "Catalan"),
    "CS": ("cs", "Czech"),
    "DA": ("da", "Danish"),
    "DE": ("de", "German"),
    "EL": ("el", "Greek"),
    "EN": ("en", "English"),
    "EO": ("eo", "Esperanto"),
    "ES": ("es", "Spanish"),
    "ET": ("et", "Estonian"),
    "EU": ("eu", "Basque"),
    "FA": ("fa", "Persian"),
    "FI": ("fi", "Finnish"),
    "FR": ("fr", "French"),
    "FR_CA": ("fr", "French"),
    "GA": ("ga", "Irish"),
    "GL": ("gl", "Galician"),
    "HE": ("he", "Hebrew"),
    "HI": ("hi", "Hindi"),
    "HR": ("hr", "Croatian"),
    "HU": ("hu", "Hungarian"),
    "HY": ("hy", "Armenian"),
    "ID": ("id", "Indonesian"),
    "IS": ("is", "Icelandic"),
    "IT": ("it", "Italian"),
    "JA": ("ja", "Japanese"),
    "JV": ("jv", "Javanese"),
    "JW": ("jv", "Javanese"),
    "KA": ("ka", "Georgian"),
    "KK": ("kk", "Kazakh"),
    "KL": ("kl", "Greenlandic"),
    "KM": ("km", "Khmer"),
    "KN": ("kn", "Kannada"),
    "KO": ("ko", "Korean"),
    "KU": ("ku", "Kurdish"),
    "KY": ("ky", "Kyrgyz"),
    "LT": ("lt", "Lithuanian"),
    "LV": ("lv", "Latvian"),
    "MK": ("mk", "Macedonian"),
    "ML": ("ml", "Malayalam"),
    "MN": ("mn", "Mongolian"),
    "MNI": ("mni", "Manipuri"),
    "MS": ("ms", "Malay"),
    "MY": ("my", "Burmese"),
    "NL": ("nl", "Dutch"),
    "NO": ("no", "Norwegian"),
    "PL": ("pl", "Polish"),
    "PT": ("pt", "Portuguese"),
    "RO": ("ro", "Romanian"),
    "RU": ("ru", "Russian"),
    "SI": ("si", "Sinhala"),
    "SK": ("sk", "Slovak"),
    "SL": ("sl", "Slovenian"),
    "SQ": ("sq", "Albanian"),
    "SR": ("sr", "Serbian"),
    "SR_CYRL": ("sr", "Serbian"),
    "SU": ("su", "Sundanese"),
    "SV": ("sv", "Swedish"),
    "TA": ("ta", "Tamil"),
    "TE": ("te", "Telugu"),
    "TH": ("th", "Thai"),
    "TL": ("tl", "Tagalog"),
    "TR": ("tr", "Turkish"),
    "UK": ("uk", "Ukrainian"),
    "UR": ("ur", "Urdu"),
    "VI": ("vi", "Vietnamese"),
    "ZH": ("zh", "Chinese"),
    "ZH_BG": ("zh", "Chinese"),
}

#: Codes that share a Kodi language with another code. Kodi has one "Chinese" and one
#: "Serbian", so the script or region is shown beside the release name instead.
VARIANTS: Dict[str, str] = {
    "ZH": "simplified",
    "ZH_BG": "traditional",
    "SR_CYRL": "cyrillic",
    "FR_CA": "canada",
}

#: ISO 639 code from Kodi -> SubDL codes to ask for, most likely first. Kodi cannot
#: tell Simplified from Traditional Chinese or Latin from Cyrillic Serbian, so both are
#: asked for. Old and alternative codes Kodi still accepts are listed too.
_ISO_ALIASES: Dict[str, List[str]] = {
    "fil": ["TL"],
    "fr": ["FR", "FR_CA"],
    "in": ["ID"],
    "iw": ["HE"],
    "jw": ["JV"],
    "nb": ["NO"],
    "nn": ["NO"],
    "pob": ["BR_PT"],
    "sr": ["SR", "SR_CYRL"],
    "zh": ["ZH", "ZH_BG"],
    "chi": ["ZH", "ZH_BG"],
    "zho": ["ZH", "ZH_BG"],
}


def _iso_table() -> Dict[str, List[str]]:
    # Every shared ISO code is an alias above, so the first code seen wins the rest.
    table = dict(_ISO_ALIASES)
    for code, (iso, _name) in SUBDL_LANGUAGES.items():
        table.setdefault(iso, [code])
    return table


_FROM_ISO = _iso_table()


#: Kodi's own spellings that differ from the names above, for iso_for_name().
_KODI_NAMES = {
    "bengali; bangla": "bn",
    "kalaallisut": "kl",
    "kirghiz": "ky",
    "latvian, lettish": "lv",
    "norwegian bokmål": "nb",
    "norwegian nynorsk": "nn",
    "sinhalese": "si",
}


def iso_for_name(name: str) -> str:
    """ISO 639 code for an English language name, when Kodi cannot convert it."""
    key = (name or "").strip().lower()
    for _code, (iso, english) in SUBDL_LANGUAGES.items():
        if english.lower() == key:
            return iso
    return _KODI_NAMES.get(key, "")


def subdl_codes(iso_codes: Iterable[str]) -> List[str]:
    """SubDL codes for Kodi's ISO 639 codes, in order, without repeats.

    Unknown codes are dropped. That matters: SubDL ignores a code it does not know,
    and a request whose every code was ignored comes back in all languages.
    """
    codes: List[str] = []
    for iso in iso_codes:
        for code in _FROM_ISO.get((iso or "").strip().lower(), []):
            if code not in codes:
                codes.append(code)
    return codes


def normalise(code: Optional[str]) -> str:
    """A SubDL code as the API spells it ("br-pt" -> "BR_PT"), or "" if not a code."""
    return (code or "").strip().upper().replace("-", "_")


def iso_for(code: str) -> str:
    """The ISO 639 code Kodi uses for a SubDL code ("BR_PT" -> "pb"), or "".

    A two-language code such as "HU_EN" falls back to its first language.
    """
    code = normalise(code)
    if code in SUBDL_LANGUAGES:
        return SUBDL_LANGUAGES[code][0]
    first = code.split("_")[0]
    return SUBDL_LANGUAGES[first][0] if first in SUBDL_LANGUAGES else ""


def english_name(code: str) -> str:
    """Fallback English name for a SubDL code, used when Kodi cannot name it."""
    code = normalise(code)
    if code in SUBDL_LANGUAGES:
        return SUBDL_LANGUAGES[code][1]
    first = code.split("_")[0]
    return SUBDL_LANGUAGES[first][1] if first in SUBDL_LANGUAGES else code


def same_language(a: str, b: str) -> bool:
    """True when two SubDL codes are the same Kodi language ("ZH" and "ZH_BG")."""
    iso_a, iso_b = iso_for(a), iso_for(b)
    return bool(iso_a) and iso_a == iso_b
