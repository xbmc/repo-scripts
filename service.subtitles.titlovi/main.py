# -*- coding: utf-8 -*-

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs
import codecs
import hashlib
import io
import json
import os
import re
import unicodedata
import time
import sys
import zipfile
from datetime import datetime, timedelta
from enum import IntEnum
from sys import argv as sys_argv
from urllib.parse import parse_qs

API_BASE_URL = "https://kodi.titlovi.com/api/subtitles"

ADDON = xbmcaddon.Addon()
ADDON_AUTHOR = ADDON.getAddonInfo("author")
ADDON_ID = ADDON.getAddonInfo("id")
ADDON_NAME = ADDON.getAddonInfo("name")
ADDON_VERSION = ADDON.getAddonInfo("version")
ADDON_ICON = ADDON.getAddonInfo("icon")
PROFILE_DIR = xbmcvfs.translatePath(ADDON.getAddonInfo("profile"))
ADDON_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo("path"))
LIB_PATH = os.path.join(ADDON_PATH, "resources", "lib")
GET_STRING = ADDON.getLocalizedString
GET_BOOL_SETTING = ADDON.getSettingBool
GET_SETTING = ADDON.getSetting
SET_SETTING = ADDON.setSetting

if not xbmcvfs.exists(PROFILE_DIR):
    xbmcvfs.mkdirs(PROFILE_DIR)

if LIB_PATH not in sys.path:
    sys.path.insert(0, LIB_PATH)

def logger(message, level=xbmc.LOGINFO):
    """
    Logs a message to the Kodi log if logging is enabled in the addon settings.
    Logging levels:
    xbmc.LOGDEBUG (0)
    xbmc.LOGINFO (1)
    xbmc.LOGWARNING (2)
    xbmc.LOGERROR (3)
    xbmc.LOGFATAL (4)
    """
    try:
        enable_logging = GET_BOOL_SETTING("enable_debug_log")
    except Exception as e:
        try:
            xbmc.log(f"{ADDON_NAME} - Error reading setting 'enable_debug_log': {e}. Continuing with logging.", xbmc.LOGWARNING)
        except Exception:
            pass
        enable_logging = True

    if enable_logging:
        try:
            log_msg = f"{ADDON_NAME} - {str(message)}"
            xbmc.log(log_msg, level)
        except Exception as log_err:
            pass


def show_notification(message, duration=3000):
    try:
        xbmcgui.Dialog().notification(ADDON_NAME, message, icon=ADDON_ICON, time=duration)
    except Exception as e:
        logger(f"Error displaying notification: {e}", level=xbmc.LOGERROR)
        logger(f"Notification that failed: {message}", level=xbmc.LOGWARNING)


TEMP_DIR = os.path.join(PROFILE_DIR, "temp", "")
if not xbmcvfs.exists(TEMP_DIR):
    if not xbmcvfs.mkdirs(TEMP_DIR):
        logger(f"Failed to create directory: {TEMP_DIR}", level=xbmc.LOGERROR)


import simple_requests as requests

addon_cache = None

try:
    import simple_cache

    cache_log_tag = "[Cache]"
    cache_mem_prefix = f"{ADDON_ID}.cache."

    addon_cache = simple_cache.SimpleCache(
        db_path=PROFILE_DIR,
        log_prefix=cache_log_tag,
        mem_cache_prefix=cache_mem_prefix,
        external_logger=logger
    )
    logger("SimpleCache initialized successfully (using addon profile).")

except Exception as e:
    error_message = f"CRITICAL: Failed to create/initialize SimpleCache instance: {e}"

    try:
        logger(error_message, level=xbmc.LOGFATAL)
    except Exception:
        xbmc.log(f"{ADDON_NAME} - {error_message}", level=xbmc.LOGFATAL)

    try:
        show_notification(GET_STRING(32001))
    except Exception as notify_error:
        logger(f"Failed to show notification about cache init error: {notify_error}", xbmc.LOGWARNING)


def check_and_set_paths_in_settings():
    """
    Checks and sets the paths to the profile and Kodi log file in the settings
    only if they differ from the currently saved values.
    """
    profile_setting_id = "profile_directory_path"
    log_setting_id = "kodi_logfile_path"

    new_profile_path = PROFILE_DIR
    current_profile_path = ""
    try:
        current_profile_path = GET_SETTING(profile_setting_id)
    except Exception as e:
        logger(f"Error reading setting '{profile_setting_id}': {e}", xbmc.LOGERROR)

    if new_profile_path and current_profile_path != new_profile_path:
        try:
            SET_SETTING(profile_setting_id, new_profile_path)
        except Exception as e:
            logger(f"Error setting '{profile_setting_id}': {e}", xbmc.LOGERROR)

    new_log_path = None
    try:
        log_dir = xbmcvfs.translatePath("special://logpath/")
        if xbmcvfs.exists(log_dir):
            new_log_path = os.path.join(log_dir, "kodi.log")
        else:
             logger(f"Kodi log directory does not exist: {log_dir}", xbmc.LOGWARNING)
    except Exception as e:
        logger(f"Error getting Kodi log file path: {e}", xbmc.LOGERROR)

    current_log_path = ""
    try:
        current_log_path = GET_SETTING(log_setting_id)
    except Exception as e:
        logger(f"Error reading setting '{log_setting_id}': {e}", xbmc.LOGERROR)

    if new_log_path and current_log_path != new_log_path:
        try:
            SET_SETTING(log_setting_id, new_log_path)
        except Exception as e:
            logger(f"Error setting '{log_setting_id}': {e}", xbmc.LOGERROR)


def _get_dir_size(start_path):
    """
    Recursively calculates the size of a directory in bytes using xbmcvfs.
    """
    total_size = 0
    if not start_path.endswith(os.sep):
        start_path += os.sep

    try:
        dirs, files = xbmcvfs.listdir(start_path)

        for f in files:
            try:
                file_path = os.path.join(start_path, f)
                stat_info = xbmcvfs.Stat(file_path)
                total_size += stat_info.st_size()
            except Exception as stat_e:
                logger(f"Error stating file '{file_path}': {stat_e}", xbmc.LOGWARNING)

        for d in dirs:
            try:
                dir_path = os.path.join(start_path, d) + os.sep
                total_size += _get_dir_size(dir_path)
            except Exception as list_e:
                logger(f"Error accessing/recursing subdirectory '{dir_path}': {list_e}", xbmc.LOGWARNING)

    except Exception as e:
        logger(f"Error listing directory '{start_path}': {e}", xbmc.LOGERROR)
    return total_size


def update_cache_info_setting():
    """
    Calculates the size and number of folders in TEMP_DIR and updates the corresponding setting.
    """
    size_mb_str = "N/A"
    folder_count = 0
    display_text = GET_STRING(32030)

    try:
        if not xbmcvfs.exists(TEMP_DIR):
            logger(f"Temp cache directory does not exist: {TEMP_DIR}")
            display_text = GET_STRING(32031)
            SET_SETTING("cache_info_display", display_text)
            return

        logger(f"Checking cache info for path: {TEMP_DIR}", xbmc.LOGINFO)

        total_size_bytes = _get_dir_size(TEMP_DIR)
        size_mb = total_size_bytes / (1024.0 * 1024.0)
        size_mb_str = f"{size_mb:.2f}"

        try:
            dirs, _ = xbmcvfs.listdir(TEMP_DIR)
            folder_count = len(dirs)
        except Exception as list_e:
            logger(f"Error listing TEMP_DIR for counting: {list_e}", xbmc.LOGWARNING)
            folder_count = "N/A"

        subtitles_label = GET_STRING(32033)
        display_text = f"[B]{size_mb_str}[/B] MB ([B]{folder_count}[/B] {subtitles_label})"

    except Exception as e:
        logger(f"Error calculating cache info: {e}", xbmc.LOGERROR)
        display_text = GET_STRING(32032)

    try:
        SET_SETTING("cache_info_display", display_text)
        logger("Cache info setting updated.", xbmc.LOGINFO)
    except Exception as set_e:
        logger(f"Failed to update cache_info_display setting: {set_e}", xbmc.LOGERROR)


check_and_set_paths_in_settings()

base_plugin_url = ""
try:
    base_plugin_url = sys_argv[0]
except (IndexError, ValueError):
    pass


class ConversionMode(IntEnum):
    DONT_CONVERT_LETTERS = 0
    CONVERT_LAT_TO_CYR = 1
    CONVERT_CYR_TO_LAT = 2


LANGUAGES = {
    "English": {"site_name": "English", "display_name": "English", "icon": "en"},
    "Serbian": {"site_name": "Srpski", "display_name": "Serbian", "icon": "sr"},
    "Cyrillic": {"site_name": "Cirilica", "display_name": "Cyrillic", "icon": "sr"},
    "Croatian": {"site_name": "Hrvatski", "display_name": "Croatian", "icon": "hr"},
    "Bosnian": {"site_name": "Bosanski", "display_name": "Bosnian", "icon": "bs"},
    "Slovenian": {"site_name": "Slovenski", "display_name": "Slovenian", "icon": "sl"},
    "Macedonian": {"site_name": "Makedonski", "display_name": "Macedonian", "icon": "mk"},
}


LAT_TO_CYR = {
    # capital letters
    "A": "А", "B": "Б", "C": "Ц", "Č": "Ч", "Ć": "Ћ", "D": "Д", "Dž": "Џ", "Đ": "Ђ", "E": "Е", "F": "Ф",
    "G": "Г", "H": "Х", "I": "И", "J": "Ј", "K": "К", "L": "Л", "Lj": "Љ", "M": "М", "N": "Н", "Nj": "Њ", 
    "O": "О", "P": "П", "R": "Р", "S": "С", "Š": "Ш", "T": "Т", "U": "У", "V": "В", "Z": "З", "Ž": "Ж",
        
    # small letters
    "a": "а", "b": "б", "c": "ц", "č": "ч", "ć": "ћ", "d": "д", "dž": "џ", "đ": "ђ", "e": "е", "f": "ф",
    "g": "г", "h": "х", "i": "и", "j": "ј", "k": "к", "l": "л", "lj": "љ", "m": "м", "n": "н", "nj": "њ",
    "o": "о", "p": "п", "r": "р", "s": "с", "š": "ш", "t": "т", "u": "у", "v": "в", "z": "з", "ž": "ж",
        
    # title capitalization
    "Dža": "Џа", "Dže": "Џе", "Dži": "Џи", "Džo": "Џо", "Džu": "Џу",
    "DŽa": "Џа", "DŽe": "Џе", "DŽi": "Џи", "DŽo": "Џо", "DŽu": "Џу",
    "Lja": "Ља", "Lje": "Ље", "Lji": "Љи", "Ljo": "Љо", "Lju": "Љу",
    "LJa": "Ља", "LJe": "Ље", "LJi": "Љи", "LJo": "Љо", "LJu": "Љу",
    "Nja": "Ња", "Nje": "Ње", "Nji": "Њи", "Njo": "Њо", "Nju": "Њу",
    "NJa": "Ња", "NJe": "Ње", "NJi": "Њи", "NJo": "Њо", "NJu": "Њу"
}

CYR_TO_LAT = {v: k for k, v in LAT_TO_CYR.items()}

SPECIAL_REPLACEMENTS = {
    "Đ": "Dj", "đ": "dj",
    "ß": "ss", "ẞ": "SS", "Æ": "AE", "æ": "ae", "Œ": "OE", "œ": "oe",
    "Å": "A", "å": "aa", "Ø": "O", "ø": "oe", "ä": "ae", "ö": "oe", "ü": "ue",
    "Þ": "Th", "þ": "th", "ð": "dh",
    "Ł": "L", "ł": "l", "Ŋ": "Ng", "ŋ": "ng",
    "¿": "?", "¡": "!"
}

GENERIC_CYRILLIC_TO_LATIN_MAP = {
    "А": "A", "а": "a",
    "Б": "B", "б": "b",
    "В": "V", "в": "v",
    "Г": "G", "г": "g",
      "Ґ": "G", "ґ": "g",
      "Ѓ": "Gj", "ѓ": "gj",
    "Д": "D", "д": "d",
      "Ђ": "Dj", "ђ": "dj",
    "Е": "E", "е": "e",
      "Ё": "Yo", "ё": "yo",
      "Є": "Ye", "є": "ye",
    "Ж": "Zh", "ж": "zh",
    "З": "Z", "з": "z",
      "Ѕ": "Dz", "ѕ": "dz",
    "И": "I", "и": "i",
      "Й": "Y", "й": "y",
      "І": "I", "і": "i",
      "Ї": "Yi", "ї": "yi",
    "Ј": "J", "ј": "j",
    "К": "K", "к": "k",
      "Ќ": "Kj", "ќ": "kj",
    "Л": "L", "л": "l",
      "Љ": "Lj", "љ": "lj",
    "М": "M", "м": "m",
    "Н": "N", "н": "n",
      "Њ": "Nj", "њ": "nj",
    "О": "O", "о": "o",
    "П": "P", "п": "p",
    "Р": "R", "р": "r",
    "С": "S", "с": "s",
    "Т": "T", "т": "t",
      "Ћ": "C", "ћ": "c",
    "У": "U", "у": "u",
      "Ў": "U", "ў": "u",
    "Ф": "F", "ф": "f",
    "Х": "H", "х": "h",
    "Ц": "Ts", "ц": "ts",
    "Ч": "Ch", "ч": "ch", 
      "Џ": "Dzh", "џ": "dzh",
    "Ш": "Sh", "ш": "sh",
    "Щ": "Shch", "щ": "shch",
    "Ъ": "", "ъ": "",
    "Ы": "Y", "ы": "y",
    "Ь": "", "ь": "",
    "Э": "E", "э": "e",
    "Ю": "Yu", "ю": "yu",
    "Я": "Ya", "я": "ya"
}

RE_CONVERSION_PATTERN = re.compile(r"""(
        <[^>]+>                # HTML/XML tags
        | https?://[^\s<>]+    # HTTP/HTTPS links
        | www\.[^\s<>]+        # WWW links
        | \S+@\S+\.\S+         # E-mail addresses
        | \d+                  # Numbers (digits)
        | \#[\w-]+             # Hashtags
        | -->                  # Subtitle timing arrows
        | \{\\an\d+\}          # Positional tags
    ) | ([A-Za-zČčĆćŠšĐđŽžDžLJljNjА-Яа-яЋЏЂЉЊ]+)  # Regular text (potential conversion) (Group 2)
""", re.VERBOSE | re.DOTALL | re.IGNORECASE)


def normalize_string(input_string, transliterate_cyrillic=True):
    """
    Normalizes a string: removes accents, replaces special characters defined in
    SPECIAL_REPLACEMENTS, and optionally transliterates Cyrillic to generic Latin
    according to GENERIC_CYRILLIC_TO_LATIN_MAP.
    """
    logger(f"normalize_string input: {str(input_string)[:100]}{'...' if len(str(input_string)) > 100 else ''}", level=xbmc.LOGINFO)

    if not isinstance(input_string, str):
        try:
            input_string = str(input_string)
        except Exception:
            logger(f"normalize_string: Cannot convert input to string: {type(input_string)}. Returning empty string.", level=xbmc.LOGWARNING)
            return ""

    if not input_string:
        return ""

    temp_string = "".join(SPECIAL_REPLACEMENTS.get(char, char) for char in input_string)

    try:
        decomposed_string = unicodedata.normalize("NFKD", temp_string)
    except Exception as e:
        logger(f"normalize_string: Error during unicodedata.normalize for string part '{temp_string[:50]}...': {e}", level=xbmc.LOGERROR)
        decomposed_string = temp_string

    result_chars = []
    for char in decomposed_string:
        if unicodedata.category(char) == "Mn":
            continue

        char_to_add = GENERIC_CYRILLIC_TO_LATIN_MAP.get(char, char) if transliterate_cyrillic else char
        result_chars.append(char_to_add)

    output_string = "".join(result_chars)

    logger(f"normalize_string output: {output_string[:100]}{'...' if len(output_string) > 100 else ''}", level=xbmc.LOGINFO)

    return output_string


def detect_encoding(file_path, encodings=None):
    if encodings is None:
        encodings = [
            "utf-8-sig",
            "utf-8",
            "cp1250",
            "cp1251",
            "cp1252",
            "iso-8859-2",
            "iso-8859-1",
            "cp852",
            "cp850",
            "iso-8859-5",
            "iso-8859-15",
            "cp1253",
            "cp1254",
            "iso-8859-3",
            "iso-8859-4",
            "cp855",
            "mac_cyrillic",
            "mac_latin2"
        ]

    with open(file_path, "rb") as f:
        raw_data = f.read(8192)
    if raw_data.startswith(codecs.BOM_UTF8):
        return "utf-8-sig"

    for encoding in encodings:
        try:
            with open(file_path, "r", encoding=encoding) as f:
                f.read(8192)
            logger(f"Using encoding: {encoding}")
            return encoding
        except (UnicodeDecodeError, IOError) as e:
            logger(f"Failed with encoding: {encoding}. Error: {e}")

    logger("No suitable encoding found.")
    return None


def handle_lat_cyr_conversion(subtitle_file_path, convert_option, threshold=0.7):
    if not os.path.isfile(subtitle_file_path):
        logger(f"File not found: {subtitle_file_path}")
        return None

    file_path_part, file_extension = os.path.splitext(subtitle_file_path)

    additional_extension = ".cyr" if convert_option == ConversionMode.CONVERT_LAT_TO_CYR else ".lat"
    converted_subtitle_file_path = f"{file_path_part}.converted{additional_extension}{file_extension}"
    
    if os.path.isfile(converted_subtitle_file_path):
        logger(f"Converted file already exists: {converted_subtitle_file_path}")
        return converted_subtitle_file_path

    encoding = detect_encoding(subtitle_file_path)
    
    if encoding is None:
        logger("No valid encoding detected. Skipping conversion.")
        return None
        
    try:
        with open(subtitle_file_path, "r", encoding=encoding) as opened_file:
            logger(f"Reading lines with detected encoding: {encoding}")
            text = opened_file.read()
    except UnicodeDecodeError as e:
        logger(f"Error decoding file: {e}", xbmc.LOGERROR)
        return None
    except IOError as e:
        logger(f"Error reading file: {e}", xbmc.LOGERROR)
        return None

    if not text:
        logger("Text is empty or could not be read.")
        return None

    cyrillic_letters = sum(1 for c in text if "\u0400" <= c <= "\u04FF")
    latin_letters = sum(
        1 for c in text 
        if "A" <= c <= "Z" or "a" <= c <= "z"
        or c in "ČčĆćŠšĐđŽž"
    )
    specific_latin_letters = sum(1 for c in text if c in "ČčĆćŠšĐđŽž")
    total_letters = cyrillic_letters + latin_letters

    if total_letters == 0:
        logger("No letters found in the text. Skipping conversion.")
        return subtitle_file_path

    cyrillic_ratio = cyrillic_letters / total_letters if total_letters > 0 else 0

    logger(f"Percentage of Cyrillic letters: {cyrillic_ratio:.2%}")

    if convert_option == ConversionMode.CONVERT_LAT_TO_CYR:
        if cyrillic_ratio >= threshold:
            logger("File already contains enough Cyrillic letters - skipping conversion.")
            return subtitle_file_path
        elif specific_latin_letters < 2:
            logger("No enough specific Latin letters (ČčĆćŠšĐđŽž) found. Skipping Lat->Cyr conversion.")
            return subtitle_file_path

    elif convert_option == ConversionMode.CONVERT_CYR_TO_LAT:
        if cyrillic_ratio <= (1 - threshold):
            logger("File already contains enough Latin letters - skipping conversion.")
            return subtitle_file_path

    try:
        logger("Writing converted file")
        with open(converted_subtitle_file_path, "w", encoding="utf-8") as converted_subtitle_file:
            converted_text = _replace_lat_cyr_letters(text, convert_option, encoding)
            converted_subtitle_file.write(converted_text)
            logger(f"Written file: {converted_subtitle_file_path}")
    except IOError as e:
        logger(f"Error writing file: {e}", xbmc.LOGERROR)
        if os.path.exists(converted_subtitle_file_path):
            try: os.remove(converted_subtitle_file_path)
            except: pass
        return None
    except Exception as conv_e:
        logger(f"Error during letter replacement: {conv_e}", xbmc.LOGERROR)
        if os.path.exists(converted_subtitle_file_path):
            try: os.remove(converted_subtitle_file_path)
            except: pass
        return None

    return converted_subtitle_file_path


def _replace_lat_cyr_letters(text, convert_option, encoding):
    if not isinstance(text, str):
        logger(f"Decoding {encoding} text")
        text = text.decode(encoding)

    conversion_map = LAT_TO_CYR if convert_option == ConversionMode.CONVERT_LAT_TO_CYR else CYR_TO_LAT

    sorted_keys = sorted(conversion_map.keys(), key=len, reverse=True)

    def convert_match(match):
        tag_or_special = match.group(1)
        content_to_convert = match.group(2)

        if tag_or_special:
            return tag_or_special

        elif content_to_convert:
            if "www.titlovi.com" in content_to_convert:
                return content_to_convert

            temp_content = content_to_convert
            for letter in sorted_keys:
                temp_content = temp_content.replace(letter, conversion_map[letter])
            return temp_content
        else:
             return ""

    text = RE_CONVERSION_PATTERN.sub(convert_match, text)

    return text


def parse_season_episode(input_string):
    """
    Parses season and episode numbers from an input string.

    Supports various formats for Season and Episode.
    If found, the season and episode numbers are returned as integers,
    and the matched pattern is removed from the original string.

    Args:
        input_string (str): The string to parse (e.g., video title).

    Returns:
        tuple: A three-tuple containing:
            - str: The modified string with the pattern removed (or original if not found/error).
            - int or None: The detected season number (0-2050).
            - int or None: The detected episode number (0-999).
    """
    logger(f"parse_season_episode called with input: '{input_string}'")

    if not input_string:
        logger("Input string is empty or None.")
        return input_string, None, None

    patterns = [
        # S01E03, S01 E03, S01.E03, S1E3, s1e03
        r"[sS](\d{1,4})[\s\._x]?[eE](\d{1,3}|-[123])",
        # 1x03, 01x03, 1X3
        r"(\d{1,4})[xX](\d{1,3})",
        # Season 1 Episode 3 (case-insensitive)
        r"(?:season|sezona)\s*[\._]?\s*(\d{1,4})\s*[\._]?\s*(?:episode|epizoda|ep|ep\.)\s*[\._]?\s*(\d{1,3})",
        # S01, Season 01
        r"(?:^|[ ._])((?:[sS]\d{2,4})|(?:season|sezona)[ ._]?\d{1,4})(?=$|[ ._])",
        # E03, Ep 03, Ep.03, Episode 03, Part 2, Pt.2
        r"(?:^|[ ._])((?:[eE]\d{2,3})|(?:[eE][pP]|episode|epizoda|part|pt)[ ._]?\d{1,3})(?=$|[ ._])"

    ]

    for idx, pat in enumerate(patterns):
        pattern = re.compile(pat, flags=re.IGNORECASE)
        match = pattern.search(input_string)
        if not match:
            continue

        try:
            g = match.groups()
            season, episode = None, None

            if idx in (0, 1, 2):
                season = int(g[0]) if len(g) > 0 and g[0] is not None else None
                episode = int(g[1]) if len(g) > 1 and g[1] is not None else None
            elif idx == 3:
                digits = re.search(r"\d+", g[0]) if g[0] else None
                season = int(digits.group()) if digits else None
                episode = None
            elif idx == 4:
                digits = re.search(r"\d+", g[0]) if g[0] else None
                season = None
                episode = int(digits.group()) if digits else None
            else:
                continue

            if not (0 <= (season if season is not None else 0) <= 2050 and 0 <= (episode if episode is not None else 0) <= 999):
                logger(f"Season ({season}) or Episode ({episode}) out of range.", xbmc.LOGWARNING)
                continue

        except (ValueError, IndexError) as e:
            logger(f"Error parsing season/episode numbers from match '{match.group()}': {e}", xbmc.LOGERROR)
            continue

        start, end = match.span()
        modified_string = input_string[:start] + input_string[end:]
        modified_string = modified_string.strip()
        logger(f"Pattern found: '{match.group()}', Season: {season}, Episode: {episode}")
        return modified_string, season, episode

    logger("No season or episode pattern found in input string.")
    return input_string, None, None


def get_imdb_id():
    """
    Retrieves the IMDb ID based on the currently playing or selected item.
    Uses InfoLabels and VideoInfoTag.
    """
    player = xbmc.Player()
    imdb_id = None

    if player.isPlayingVideo():
        logger("Starting IMDb ID search for ACTIVE PLAYER...")

        try:
            imdb_id = xbmc.getInfoLabel("VideoPlayer.IMDBNumber").strip()
            if imdb_id and imdb_id.lower().startswith("tt"):
                logger(f"Method 1 (VideoPlayer.IMDBNumber): Found: {imdb_id}")
                return imdb_id
            else:
                if imdb_id:
                    logger(f"Method 1 (VideoPlayer.IMDBNumber): Found value '{imdb_id}', but it's not a valid IMDb ID.")
                else:
                    logger("Method 1 (VideoPlayer.IMDBNumber): Not found or empty.", xbmc.LOGWARNING)
                imdb_id = None
        except Exception as e:
            logger(f"Error getting VideoPlayer.IMDBNumber: {str(e)}", xbmc.LOGERROR)
            imdb_id = None

        if not imdb_id:
            try:
                video_info = player.getVideoInfoTag()
                if video_info and hasattr(video_info, "getIMDBNumber"):
                    imdb_id = video_info.getIMDBNumber().strip()
                    if imdb_id and imdb_id.lower().startswith("tt"):
                        logger(f"Method 2 (VideoInfoTag): Found: {imdb_id}")
                        return imdb_id
                    else:
                        if imdb_id:
                             logger(f"Method 2 (VideoInfoTag): Found value '{imdb_id}', but it's not a valid IMDb ID.", xbmc.LOGWARNING)
                        else:
                             logger("Method 2 (VideoInfoTag): Returned empty value.", xbmc.LOGWARNING)
                        imdb_id = None
                elif not video_info:
                     logger("Method 2 (VideoInfoTag): VideoInfoTag object not available.", xbmc.LOGERROR)
                else:
                    logger("Method 2 (VideoInfoTag): VideoInfoTag object does not have getIMDBNumber() method.", xbmc.LOGERROR)

            except Exception as e:
                logger(f"Error in Method 2 (VideoInfoTag): {str(e)}", xbmc.LOGERROR)
                imdb_id = None

    logger("Starting IMDb ID search for SELECTED ITEM")

    imdb_variants = [
        "ListItem.IMDBNumber",
        "ListItem.UniqueId(imdb)",
        "ListItem.Property(unique_ids.imdb)",
        "ListItem.Property(imdbnumber)",
        "ListItem.Property(imdb_id)",
        "ListItem.Property(imdb)",
        "ListItem.Property(imdbid)",
        "ListItem.Property(ImdbCode)",
        "ListItem.Property(imdb_no)"
    ]

    for variant in imdb_variants:
        try:
            imdb_id_candidate = xbmc.getInfoLabel(variant).strip()

            match = re.match(r"^(tt\d+)$", imdb_id_candidate, re.IGNORECASE)
            if match:
                valid_imdb_id = match.group(1)
                logger(f"Method 3 (ListItem InfoLabel: {variant}): Found and validated: {valid_imdb_id}")
                return valid_imdb_id
            else:
                logger(f"Method 3 (ListItem InfoLabel: {variant}): Found value '{imdb_id_candidate}', but it's not a valid IMDb ID format.", xbmc.LOGWARNING)

        except Exception as e:
             logger(f"Error checking ListItem variant {variant}: {str(e)}", xbmc.LOGERROR)

    logger("IMDb ID not found in any source (Player or Selected Item)!")
    return None  


def smart_clean_title(input_string):
    """
    Wrapper around xbmc.getCleanMovieTitle, providing enhanced cleaning of the title and extraction of the year.
    Uses parse_season_episode as a sub-function to detect and extract season and episode numbers.
    If a season/episode pattern is found, everything after it is removed from the title.
    Returns a tuple: (title, year, season, episode).
    """
    if not input_string or not isinstance(input_string, str):
        return "", None, None, None

    try:
        clean_title, year_str = xbmc.getCleanMovieTitle(input_string)
        title = clean_title.strip()
    except Exception:
        title = input_string.strip()
        year_str = None

    year = None
    if year_str and year_str.isdigit() and 1900 <= int(year_str) <= 2100:
        try:
            year = int(year_str) 
        except Exception as e:
            logger(f"Year string '{year_str}' could not be converted to int: {e}", xbmc.LOGWARNING)
    #else:
    #    year_search = re.search(r"(19|20)\d{2}", input_string)
    #    if year_search:
    #        year = int(year_search.group(0))

    try:
        parsed_title, season, episode = parse_season_episode(title)
        if season is not None or episode is not None:
            cut_idx = 0
            for c1, c2 in zip(title, parsed_title):
                if c1 != c2:
                    break
                cut_idx += 1
            title = title[:cut_idx].strip()
    except Exception as e:
        logger(f"Error parsing season/episode from string '{title}': {e}", xbmc.LOGWARNING)
        season, episode = None, None

    clean_regexes = [
        r"\[.*?\]|\{.*?\}",
        r"[\._]"
    ]

    for reg in clean_regexes:
        title = re.sub(reg, " ", title)

    title = re.sub(r"\s+", " ", title, flags=re.IGNORECASE).strip()

    return title, year, season, episode
    
    

class ActionHandler(object):

    def __init__(self, params):
        """
         param params:
            {
                'action': string, one of: 'search', 'manualsearch', 'download',
                'languages': comma separated list of strings,
                'preferredlanguage': string,
                'searchstring': string, exists if 'action' param is 'manualsearch'
            }
        """

        self.params = params
        self.username = GET_SETTING("titlovi-username")
        self.password = GET_SETTING("titlovi-password")
        action_list = self.params.get("action", [None])
        self.action = action_list[0]
        self.login_token = None
        self.user_id = None
        
        self.dialog_delay = float(GET_SETTING("dialog_delay") or 0.3)
        self.connect_timeout = int(GET_SETTING("request_timeout") or 10)


    def validate_params(self):
        """
        Method used for validating required parameters: 'username', 'password' and 'action'.
        """
        if not self.username or not self.password:
            show_notification(GET_STRING(32002))
            ADDON.openSettings()
            return False
        if self.action not in ("search", "manualsearch", "download"):
            show_notification(GET_STRING(32003))
            return False
        return True


    def handle_login(self):
        """
        Method used for sending user login request.

        OK return:
            {
                'ExpirationDate': datetime string (format: '%Y-%m-%dT%H:%M:%S.%f'),
                'Token': string,
                'UserId': integer,
                'UserName': string
            }

        Error return: None
        """
        logger("Starting user login")
        login_params = {
            "username": self.username,
            "password": self.password,
            "returnStatusCode": True,
            "json": True
        }

        try:
            response = requests.post(f"{API_BASE_URL}/gettoken", params=login_params, timeout=self.connect_timeout)
            logger(f"Login response - Status: {response.status_code}")

            response.raise_for_status()

            resp_json = response.json()
            logger("Login successful")

            required_keys = {"ExpirationDate", "Token", "UserId", "UserName"}
            if not all(key in resp_json for key in required_keys):
                logger("Invalid API response structure", xbmc.LOGERROR)
                show_notification(GET_STRING(32004))
                return None

            return resp_json

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == requests.codes.unauthorized: # 401
                logger("Invalid credentials", xbmc.LOGWARNING)
                show_notification(GET_STRING(32005))
                ADDON.openSettings()

            elif e.response.status_code == requests.codes.forbidden: # 403
                logger("Account not verified/API disabled", xbmc.LOGERROR)
                message = GET_STRING(32021).format(self.username)
                dialog = xbmcgui.Dialog()
                dialog.ok(GET_STRING(32022), message)
                logger("API verification dialog shown to user.", xbmc.LOGINFO)
            else:
                logger(f"HTTP error: {str(e)}", xbmc.LOGERROR)
                show_notification(GET_STRING(32006))
            return None

        except requests.exceptions.RequestException as e:
            logger(f"Network error: {str(e)}", xbmc.LOGERROR)
            show_notification(GET_STRING(32007))
            return None

        except (ValueError, KeyError) as e:
            logger(f"Invalid server response: {str(e)}", xbmc.LOGERROR)
            show_notification(GET_STRING(32004))
            return None


    def set_login_data(self, login_data):
        TOKEN_CACHE_EXPIRATION = timedelta(days=7)

        if not isinstance(login_data, dict):
            logger("Missing login data for caching", xbmc.LOGWARNING)
            return False
        try:
            try:
                credentials_string = f"{self.username}:{self.password}"
                credentials_hash = hashlib.sha256(credentials_string.encode("utf-8")).hexdigest()
                login_data["CredentialsHash"] = credentials_hash
                logger("Credentials hash calculated and added to login data", xbmc.LOGINFO)
            except Exception as hash_e:
                logger(f"Failed to calculate credentials hash: {hash_e}", xbmc.LOGWARNING)
                login_data.pop("CredentialsHash", None)

            if "ExpirationDate" in login_data and isinstance(login_data["ExpirationDate"], datetime):
                login_data["ExpirationDate"] = login_data["ExpirationDate"].isoformat()

            addon_cache.set(
                "titlovi_com_login_data",
                login_data,
                expiration=TOKEN_CACHE_EXPIRATION
            )
            self.login_token = login_data.get("Token")
            self.user_id = login_data.get("UserId")
            logger("Login data successfully set in cache and instance", xbmc.LOGINFO)
            return True
        except Exception as e:
            logger(f"Error saving login data to cache: {e}", xbmc.LOGERROR)
        return False


    def user_login(self):
        """
        Handles user login process with titlovi.com credentials.
        Checks cache first, validates credentials hash and token expiration,
        and falls back to fresh login if needed.
        After successful login data is stored in cache.

        Returns:
            bool: True if login successful and instance attributes are set, False otherwise.
        """
        TOKEN_EXPIRATION_THRESHOLD = timedelta(days=1)

        try:
            titlovi_com_login_data = addon_cache.get("titlovi_com_login_data")
        except Exception as e:
            logger(f"Error getting data from cache: {e}", xbmc.LOGWARNING)
            titlovi_com_login_data = None

        if not titlovi_com_login_data or not isinstance(titlovi_com_login_data, dict):
            logger("No valid cached login data found, attempting fresh login.")
            return self._perform_fresh_login()

        logger("Cached login data found. Validating...", xbmc.LOGINFO)

        try:
            try:
                current_credentials_string = f"{self.username}:{self.password}"
                current_hash = hashlib.sha256(current_credentials_string.encode("utf-8")).hexdigest()
            except Exception as hash_e:
                logger(f"Error calculating current credentials hash during validation: {hash_e}", xbmc.LOGERROR)
                logger("Assuming cache is invalid due to hash calculation error.", xbmc.LOGWARNING)
                return self._perform_fresh_login()

            cached_hash = titlovi_com_login_data.get("CredentialsHash")
            if not cached_hash:
                logger("Credentials hash missing in cached data. Cache invalid.", xbmc.LOGWARNING)
                return self._perform_fresh_login()

            if current_hash != cached_hash:
                logger("Credentials changed since last login. Cache invalid.", xbmc.LOGWARNING)
                return self._perform_fresh_login()

            logger("Credentials hash match. Validating structure and expiration...", xbmc.LOGINFO)

            required_keys = {"Token", "UserId", "ExpirationDate", "UserName"}
            if not all(key in titlovi_com_login_data for key in required_keys):
                logger("Invalid cache data structure (missing required keys). Cache invalid.", xbmc.LOGWARNING)
                return self._perform_fresh_login()

            expiration_date_string = titlovi_com_login_data["ExpirationDate"]

            if not expiration_date_string:
                logger("Expiration date missing in cached data. Cache invalid.", xbmc.LOGWARNING)
                return self._perform_fresh_login()

            try:
                iso_match = re.match(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d+))?$", expiration_date_string)
                if iso_match:
                    main, frac = iso_match.group(1), iso_match.group(2)
                    if frac:
                        frac = (frac + "000000")[:6]
                        expiration_date_string = f"{main}.{frac}"
                    else:
                        expiration_date_string = main

                expiration_date = datetime.fromisoformat(expiration_date_string)
                time_left = expiration_date - datetime.now()

            except Exception as e:
                logger(f"ERROR parsing expiration date: '{expiration_date_string}': {e}", xbmc.LOGERROR)
                return self._perform_fresh_login()

            if time_left <= TOKEN_EXPIRATION_THRESHOLD:
                logger(f"Cached token expires soon ({time_left}). Refreshing.")
                return self._perform_fresh_login()

            logger("Using valid cached login data.")
            self.login_token = titlovi_com_login_data.get("Token")
            self.user_id = titlovi_com_login_data.get("UserId")
            return True

        except ValueError as e:
            logger(f"Invalid date format in cached data: {str(e)}. Cache invalid.", xbmc.LOGERROR)
            return self._perform_fresh_login()
        except KeyError as e:
            logger(f"Missing key {str(e)} in cached data structure. Cache invalid.", xbmc.LOGERROR)
            return self._perform_fresh_login()
        except Exception as e:
            logger(f"Unexpected error validating cached token: {str(e)}. Cache invalid.", xbmc.LOGERROR)
            return self._perform_fresh_login()


    def _perform_fresh_login(self):
        """Helper method to handle new login attempts"""
        logger("Attempting fresh login via API.")
        login_data = self.handle_login()
        if not login_data:
            return False
        if self.set_login_data(login_data):
            logger("Fresh login successful and data cached.")
            return True
        else:
            logger("Fresh login succeeded but failed to save data to cache.", xbmc.LOGERROR)
            return False


    def get_prepared_language_param(self):
        """
        Gets subtitle languages either from addon settings (if override is enabled)
        or parses selected subtitle languages (from Kodi settings) and formats
        them into a pipe-separated string of language names accepted by the API.
        """
        site_lang_list = []

        try:
            use_custom_settings = GET_BOOL_SETTING("override_kodi_languages")

            if use_custom_settings:
                logger("Using custom language settings from addon.", xbmc.LOGINFO)
                setting_to_lang_key = {
                    "lang_eng": "English",
                    "lang_srp_lat": "Serbian",
                    "lang_srp_cyr": "Cyrillic",
                    "lang_hrv": "Croatian",
                    "lang_bos": "Bosnian",
                    "lang_slv": "Slovenian",
                    "lang_mkd": "Macedonian"
                }

                selected_custom_langs = []
                for setting_id, lang_key in setting_to_lang_key.items():
                    if GET_BOOL_SETTING(setting_id):
                        selected_custom_langs.append(lang_key)
                        logger(f"Custom language selected: {lang_key} (from setting {setting_id})", xbmc.LOGINFO)

                for lang_key in selected_custom_langs:
                    site_name = LANGUAGES.get(lang_key, {}).get("site_name")
                    if site_name and site_name not in site_lang_list:
                        site_lang_list.append(site_name)
                    elif not site_name:
                        logger(f"Could not find 'site_name' for custom language key '{lang_key}' in LANGUAGES map.", xbmc.LOGWARNING)

            else:
                logger("Using language settings provided by Kodi.", xbmc.LOGINFO)
                if not self.params.get("languages") or not self.params["languages"][0]:
                    logger("No Kodi languages found in params.", level=xbmc.LOGWARNING)
                    return ""

                kodi_languages = self.params["languages"][0].split(",")

                for lang_code in kodi_languages:
                    lang_code = lang_code.strip()

                    if lang_code == "Serbo-Croatian":
                        serbian_site_name = LANGUAGES.get("Serbian", {}).get("site_name")
                        croatian_site_name = LANGUAGES.get("Croatian", {}).get("site_name")
                        if serbian_site_name and serbian_site_name not in site_lang_list:
                            site_lang_list.append(serbian_site_name)
                        if croatian_site_name and croatian_site_name not in site_lang_list:
                            site_lang_list.append(croatian_site_name)
                    elif lang_code == "Serbian":
                        serbian_site_name = LANGUAGES.get("Serbian", {}).get("site_name")
                        cyrillic_site_name = LANGUAGES.get("Cyrillic", {}).get("site_name")
                        if serbian_site_name and serbian_site_name not in site_lang_list:
                            site_lang_list.append(serbian_site_name)
                        if cyrillic_site_name and cyrillic_site_name not in site_lang_list:
                            site_lang_list.append(cyrillic_site_name)
                    else:
                        if lang_code in LANGUAGES:
                            site_name = LANGUAGES[lang_code].get("site_name")
                            if site_name and site_name not in site_lang_list:
                                site_lang_list.append(site_name)
                        else:
                            logger(f"Language code '{lang_code}' from settings not found in LANGUAGES map.", level=xbmc.LOGWARNING)

            lang_string = "|".join(site_lang_list)
            logger(f"Prepared language string for API: '{lang_string}'")

            return lang_string if lang_string else None

        except Exception as e:
            logger(f"Error preparing language parameter: {e}", xbmc.LOGERROR)
            return None


    def handle_action(self):
        """
        Method used for calling other action methods depending on 'action' parameter.
        """
        if self.action in ("search", "manualsearch"):
            self.handle_search_action()
        elif self.action == "download":
            self.handle_download_action()
        else:
            logger("Invalid action!", xbmc.LOGWARNING)
            show_notification(GET_STRING(32003))


    def handle_search_action(self):
        """
        Method used for searching
        """
        plugin_handle = int(sys_argv[1])
        logger("Starting search action...")
        search_params = {}
        search_params["returnStatusCode"] = True
        search_params["ignoreLangAndEpisode"] = False
        
        imdb_id = None
        year = None
        season = None
        episode = None
        year_temp = None
        season_temp = None
        episode_temp = None
        title = None
        title_source = None
        filename = None
        
        if self.action == "manualsearch":
            logger("Starting manualsearch.")
            search_string_list = self.params.get("searchstring")
            
            if isinstance(search_string_list, str):
                search_string_list = [search_string_list]
                
            if not search_string_list or not search_string_list[0].strip():
                show_notification(GET_STRING(32008))
                return

            search_string = search_string_list[0].strip()

            imdb_id_match = re.search(r"(tt\d+)", search_string, re.IGNORECASE)
            
            if imdb_id_match:
                imdb_id = imdb_id_match.group(1)
                logger(f"Detected IMDb ID in manual search: {imdb_id}", xbmc.LOGINFO)
                search_params["imdbid"] = imdb_id
                search_string = search_string.replace(imdb_id, "").strip()
            
            try:
                clean_title_temp, year, season, episode = smart_clean_title(search_string)
                logger(f"Manual search string ('{search_string}') -> (title: '{clean_title_temp}', year: {year}, S: {season}, E: {episode})", xbmc.LOGINFO)
                title = clean_title_temp.strip()
            except Exception as clean_e:
                logger(f"Error cleaning title '{search_string}': {clean_e}. Using as is.", xbmc.LOGWARNING)
                title = search_string.strip()
                year = None
                season = None
                episode = None

            search_params["query"] = title
            if year:
                search_params["year"] = year
            if season is not None and season >= 0:
                season_list = ["0", str(season)]
                season_list = list(dict.fromkeys(season_list))
                search_params["season"] = season_list
            if episode is not None and episode >= 0:
                episode_list = ["-1", "0", str(episode)]
                episode_list = list(dict.fromkeys(episode_list))
                search_params["episode"] = episode_list

            logger(f"Manual search finalized with search_params: {search_params}", xbmc.LOGINFO)

        else:
            logger("Handling automatic search.")
            player = xbmc.Player()

            if not player.isPlayingVideo():
                logger("Video is not playing. Attempting to get IMDb ID and fallback title...")
                try:
                    imdb_id = get_imdb_id()
                    if imdb_id:
                        logger(f"Found IMDb ID (while player not active): {imdb_id}")
                        search_params["imdbid"] = imdb_id
                        
                    season_str = xbmc.getInfoLabel("ListItem.Season")
                    episode_str = xbmc.getInfoLabel("ListItem.Episode")
                    year_str = xbmc.getInfoLabel("ListItem.Year")

                    try:
                        season = int(season_str.strip()) if season_str else None
                    except Exception:
                        season = None

                    try:
                        episode = int(episode_str.strip()) if episode_str else None
                    except Exception:
                        episode = None

                    base_title = (
                        xbmc.getInfoLabel("ListItem.TVShowTitle") or
                        xbmc.getInfoLabel("ListItem.OriginalTitle") or
                        xbmc.getInfoLabel("ListItem.Title") or
                        xbmc.getInfoLabel("ListItem.Label")
                    )
                    if base_title:
                        logger(f"Fallback title (player not active) found in InfoLabels: '{base_title}'", xbmc.LOGINFO)
                        clean_title_temp, year_temp, season_temp, episode_temp = smart_clean_title(base_title)
                        title = normalize_string(clean_title_temp.strip())
                        search_params["query"] = title
                        
                        if season is None and season_temp is not None:
                            season = season_temp
                        if episode is None and episode_temp is not None:
                            episode = episode_temp

                        year = year_str or (str(year_temp) if year_temp else None)
                        if year:
                            try:
                                if GET_BOOL_SETTING("include_year_in_search"):
                                    year = int(year.strip())
                                    search_params["year"] = year
                                    logger(f"Including year '{year}' in search params based on setting (player not active).", xbmc.LOGINFO)
                            except Exception as setting_e:
                                logger(f"Error reading or setting year: {setting_e}", xbmc.LOGWARNING)
                    else:
                        logger("No fallback title found in ListItem InfoLabels (player not active).")
                        
                    if season is not None and season >= 0:
                        season_list = ["0", str(season)]
                        season_list = list(dict.fromkeys(season_list))
                        search_params["season"] = season_list

                    if episode is not None and episode >= 0:
                        episode_list = ["-1", "0", str(episode)]
                        episode_list = list(dict.fromkeys(episode_list))
                        search_params["episode"] = episode_list
                    
                    if (season is not None and season >= 0) or (episode is not None and episode >= 0):
                        logger(f"Found Season: {season}, Episode: {episode} (while player not active)")

                    if not imdb_id and not base_title:
                        logger("Could not find IMDb ID or Title (while player not active).", xbmc.LOGWARNING)
                        return
                except Exception as e:
                    logger(f"Error while gathering fallback info when player not active: {e}", xbmc.LOGWARNING)

            else:
                logger("Video is playing. Gathering information from player...")

                try:
                    logger("Attempting to get IMDb ID (player active)...", xbmc.LOGINFO)
                    imdb_id = get_imdb_id()
                    use_imdb = True
                    try:
                        use_imdb = GET_BOOL_SETTING("include_imdb_id_in_search")
                    except Exception as setting_e:
                        logger(f"Error reading 'include_imdb_id_in_search' setting: {setting_e}. Defaulting to True.", xbmc.LOGWARNING)
                    if imdb_id:
                        if use_imdb:
                            logger(f"Found valid IMDb ID (player active): {imdb_id} (will be used)")
                            search_params["imdbid"] = imdb_id
                        else:
                            logger(f"IMDb ID found ({imdb_id}), but setting disables its use, and prioritizing title/year/S-E.", xbmc.LOGINFO)
                    else:
                        logger("No valid IMDb ID found (player active). Proceeding with title/filename.", xbmc.LOGINFO)
                except Exception as e:
                    logger(f"Error calling get_imdb_id() (player active): {e}", xbmc.LOGWARNING)

                tv_show_title = xbmc.getInfoLabel("VideoPlayer.TVshowtitle")
                movie_title = xbmc.getInfoLabel("VideoPlayer.OriginalTitle") or xbmc.getInfoLabel("VideoPlayer.Title")
                season_str = xbmc.getInfoLabel("VideoPlayer.Season")
                episode_str = xbmc.getInfoLabel("VideoPlayer.Episode")
                year_str = xbmc.getInfoLabel("VideoPlayer.Year")
                found_season_episode = False

                try:
                    playing_file = player.getPlayingFile()
                except Exception:
                    playing_file = None
                if playing_file:
                    filename = os.path.basename(xbmcvfs.translatePath(playing_file))
                else:
                    filename = (
                        os.path.basename(xbmcvfs.translatePath(xbmc.getInfoLabel("ListItem.DecodedFileNameAndPath"))) or
                        xbmc.getInfoLabel("ListItem.FileNameNoExtension") or
                        xbmc.getInfoLabel("ListItem.Filename") or
                        xbmc.getInfoLabel("ListItem.Path")
                    )

                if tv_show_title:
                    clean_title_temp, year_temp, season_temp, episode_temp = smart_clean_title(tv_show_title)
                    title = clean_title_temp.strip()
                    title_source = "tvshowtitle"

                    if season_temp is not None or episode_temp is not None:
                        found_season_episode = True
                        logger(f"Source: TVShowTitle with S/E ('{tv_show_title}'), cleaned: '{title}'", xbmc.LOGINFO)
                    else:
                        logger(f"Source: TVShowTitle ('{tv_show_title}')", xbmc.LOGINFO)

                elif movie_title:
                    clean_title_temp, year_temp, season_temp, episode_temp = smart_clean_title(movie_title)
                    title = clean_title_temp.strip()
                    title_source = "movietitle"

                    if season_temp is not None or episode_temp is not None:
                        found_season_episode = True
                        logger(f"Source: MovieTitle with S/E ('{movie_title}'), cleaned: '{title}'", xbmc.LOGINFO)
                    else:
                        logger(f"Source: MovieTitle ('{movie_title}')", xbmc.LOGINFO)

                elif filename:
                    clean_title_temp, year_temp, season_temp, episode_temp = smart_clean_title(filename)
                    title = clean_title_temp.strip()
                    title_source = "filename"

                    if season_temp is not None or episode_temp is not None:
                        found_season_episode = True
                        logger(f"Source: Filename with S/E detected in fallback ('{filename}'), cleaned: '{title}'", xbmc.LOGINFO)
                    else:
                        logger(f"Source: Filename fallback ('{filename}')", xbmc.LOGINFO)

                else:
                    logger("Could not determine title from TVShowTitle, MovieTitle or Filename!", xbmc.LOGERROR)

                if title:
                    try:
                        title = normalize_string(title)
                    except Exception as norm_e:
                        logger(f"Error normalizing title '{title}': {norm_e}. Using unnormalized.", xbmc.LOGWARNING)
                    logger(f"Normalized query: '{title}'", xbmc.LOGINFO)
                    search_params["query"] = title
                else:
                    logger("Query could not be determined.", xbmc.LOGWARNING)

                year = year_str or (str(year_temp) if year_temp else None)
                try:
                    year = int(year.strip()) if year else None
                except Exception:
                    year = None
                
                try:
                    season = int(season_str.strip()) if season_str else None
                except Exception:
                    season = None
     
                try:
                    episode = int(episode_str.strip()) if episode_str else None
                except Exception:
                    episode = None

                if season is None and season_temp is not None:
                    season = season_temp
                if episode is None and episode_temp is not None:
                    episode = episode_temp
                    
                if title_source == "tvshowtitle" and (season is None or episode is None) and filename:
                    _, _, season_from_file, episode_from_file = smart_clean_title(filename)
                    if season is None and season_from_file is not None:
                        season = season_from_file
                        logger(f"Fallback: Season extracted from filename: {season}", xbmc.LOGINFO)
                    if episode is None and episode_from_file is not None:
                        episode = episode_from_file
                        logger(f"Fallback: Episode extracted from filename: {episode}", xbmc.LOGINFO)

                if title_source == "tvshowtitle" or (season is not None and season >= 0) or (episode is not None and episode >= 0):
                    if season is not None and season >= 0:
                        season_list = ["0", str(season)]
                        season_list = list(dict.fromkeys(season_list))
                        search_params["season"] = season_list
                        logger(f"Season found: {season} -> Adding season params: {search_params['season']}", xbmc.LOGINFO)

                    episode_list = []
                    if episode is not None and episode >= 0:
                        episode_list = ["-1", "0", str(episode)]
                        try:
                            if GET_BOOL_SETTING("include_pilot_episodes"):
                                episode_list.append("-2")
                        except Exception:
                            pass
                        try:
                            if GET_BOOL_SETTING("include_specials"):
                                episode_list.append("-3")
                        except Exception:
                            pass
                        episode_list = sorted(list(dict.fromkeys(episode_list)))
                    if episode_list:
                        search_params["episode"] = episode_list
                        logger(f"Episode found: {episode} -> Adding episode params: {search_params['episode']}", xbmc.LOGINFO)

                try:
                    use_type_switch = GET_BOOL_SETTING("include_type_in_search")
                except Exception as setting_e:
                    logger(f"Error reading 'include_type_in_search' setting: {setting_e}. Assuming default (True).", xbmc.LOGWARNING)
                    use_type_switch = True

                is_tv_show = (
                    title_source == "tvshowtitle" or
                    found_season_episode or
                    (season is not None and season >= 0) or
                    (episode is not None and episode >= 0)
                )

                if use_type_switch:
                    if is_tv_show:
                        search_params["type"] = "2"
                        logger("Setting search type to '2' (TV Show).", xbmc.LOGINFO)
                    elif title_source in ("movietitle", "filename"):
                        search_params["type"] = ["1", "3"]
                        logger("Setting search type to '['1', '3']' (Movie/Documentaries).", xbmc.LOGINFO)
                    else:
                        logger("Title source unknown, not setting search type.", xbmc.LOGINFO)
                else:
                    logger("Type setting is disabled by user settings.", xbmc.LOGINFO)

                try:
                    if GET_BOOL_SETTING("include_year_in_search") and year is not None:
                        search_params["year"] = year
                        logger(f"Including final year '{year}' in search params based on setting.", xbmc.LOGINFO)
                except Exception as setting_e:
                    logger(f"Error reading 'include_year_in_search' setting: {setting_e}", xbmc.LOGWARNING)
                             
                # search_params["special"] = "-1"
                
            if not search_params.get("imdbid") and not search_params.get("query"):
                logger("Automatic search failed: Could not determine usable search parameters (IMDb or Query needed).", xbmc.LOGERROR)
                return
                
        search_language = self.get_prepared_language_param()
        if search_language:
            search_params["lang"] = search_language
        else:
            logger("No specific language selected for search.", xbmc.LOGWARNING)     

        result_list = self._fetch_search_results(search_params)

        if result_list is None:
            logger("Search failed or was aborted (e.g., timeout, login error). No results to display.", xbmc.LOGWARNING)
            time.sleep(self.dialog_delay)
            xbmcplugin.endOfDirectory(plugin_handle)
        elif not result_list:
            logger("No subtitle results found for the current search criteria, and nothing were displayed in the Kodi dialog!.")
            time.sleep(self.dialog_delay)
            xbmcplugin.endOfDirectory(plugin_handle)
        else:
            self._display_search_results(result_list)


    def _fetch_search_results(self, search_params):
        """
        Fetches subtitle search results, first checking the cache based on
        search parameters, then querying the API if no cached results are found and caches them.
        
        Returns:
            'ResultsFound', 'PagesAvailable', 'CurrentPage', 'SubtitleResults'
        """
        SEARCH_CACHE_EXPIRATION = timedelta(hours=8)
        cache_key_params = search_params.copy()
        keys_to_remove_from_cache_key = ["ignoreLangAndEpisode", "returnStatusCode", "username", "password"]
        for key in keys_to_remove_from_cache_key:
            cache_key_params.pop(key, None)
            
        if self.user_id:
            cache_key_params["__user_id__"] = self.user_id
            logger(f"Adding user ID {self.user_id} to cache key params.", xbmc.LOGINFO)
        else:
            logger("User ID not available, cache key will not be user-specific.", xbmc.LOGWARNING)

        params_hash = None
        if cache_key_params:
            try:
                sorted_items = sorted(cache_key_params.items())
                params_hash = json.dumps(sorted_items, sort_keys=True, separators=(",", ":"))
                params_hash = hashlib.sha1(params_hash.encode("utf-8")).hexdigest()
                logger(f"Cache key generated: {params_hash}", xbmc.LOGINFO)
            except Exception as json_e:
                logger(f"Error creating cache key: {json_e}. Caching disabled for this request.", xbmc.LOGERROR)
                params_hash = None
        else:
            logger("No relevant parameters found to generate cache key. Caching disabled.", xbmc.LOGWARNING)
            params_hash = None

        result_list = None
        if addon_cache and params_hash:
            try:
                result_list = addon_cache.get(params_hash)
                if result_list is not None:
                    logger("Results loaded from cache.")
                    return result_list
                else:
                    logger("Results not found in cache (or expired).")
            except Exception as cache_get_e:
                logger(f"Error reading from cache: {cache_get_e}", xbmc.LOGWARNING)
                result_list = None

        if result_list is None:
            logger("Getting results from API...")
            if not self.login_token or not self.user_id:
                logger("Login token or User ID missing. Cannot perform API search.", xbmc.LOGERROR)
                show_notification(GET_STRING(32009))
                return None

            search_params["token"] = self.login_token
            search_params["userid"] = self.user_id
            search_params["json"] = True

            try:
                logger(f"API Search Params: {search_params}", xbmc.LOGINFO)
                response = requests.get(f"{API_BASE_URL}/search", params=search_params, timeout=self.connect_timeout)
                logger(f"API Response Status: {response.status_code}")
                logger(f"API URL Queried: {response.url}", xbmc.LOGINFO)
                
                response.raise_for_status()
                resp_json = response.json()
                
                if resp_json and "SubtitleResults" in resp_json:
                    result_list = resp_json["SubtitleResults"]
                    logger(f"API returned {len(result_list)} results.")
                else:
                    logger("API response OK but 'SubtitleResults' key missing or empty.", xbmc.LOGWARNING)
                    result_list = []

            except requests.exceptions.Timeout:
                logger("API request timed out.", xbmc.LOGWARNING)
                show_notification(GET_STRING(32020))
                result_list = None

            except requests.exceptions.HTTPError as e:
                if e.response.status_code == requests.codes.unauthorized: # 401
                    logger("API search returned 401. Attempting token refresh...", xbmc.LOGWARNING)
                    login_data_refresh = self.handle_login()
                    if login_data_refresh and self.set_login_data(login_data_refresh):
                        logger("Token refreshed. Retrying API search...")
                        search_params["token"] = self.login_token
                        search_params["userid"] = self.user_id
                        try:
                            retry_response = requests.get(f"{API_BASE_URL}/search", params=search_params, timeout=self.connect_timeout)
                            retry_response.raise_for_status()
                            resp_json_retry = retry_response.json()
                            if resp_json_retry and "SubtitleResults" in resp_json_retry:
                                result_list = resp_json_retry["SubtitleResults"]
                                logger(f"API retry successful, returned {len(result_list)} results.")
                            else:
                                logger("API retry OK but 'SubtitleResults' missing/empty.", xbmc.LOGWARNING)
                                result_list = []
                        except requests.exceptions.Timeout:
                            logger("Retry API request timed out.", xbmc.LOGWARNING)
                            show_notification(GET_STRING(32020))
                            result_list = None
                        except requests.exceptions.HTTPError as retry_http_e:
                            logger(f"HTTP error on API search retry: {retry_http_e}", xbmc.LOGERROR)
                            show_notification(GET_STRING(32006))
                            result_list = None
                        except requests.exceptions.RequestException as retry_req_e:
                            logger(f"Network error on API search retry: {retry_req_e}", xbmc.LOGERROR)
                            show_notification(GET_STRING(32007))
                            result_list = None
                        except (ValueError, KeyError) as retry_parse_e:
                            logger(f"Error parsing API retry response: {retry_parse_e}", xbmc.LOGERROR)
                            show_notification(GET_STRING(32004))
                            result_list = None
                    else:
                        logger("Token refresh failed. Aborting search.", xbmc.LOGERROR)
                        result_list = None
                elif e.response.status_code == requests.codes.forbidden: # 403
                    logger("API search returned 403 Forbidden. Account not verified/API disabled.", xbmc.LOGERROR)
                    message = GET_STRING(32021).format(self.username)
                    dialog = xbmcgui.Dialog()
                    dialog.ok(GET_STRING(32022), message)
                    result_list = None
                else:
                    logger(f"HTTP error during API search: {e}", xbmc.LOGERROR)
                    show_notification(GET_STRING(32006))
                    result_list = None

            except requests.exceptions.RequestException as e:
                logger(f"Network error during API search: {e}", xbmc.LOGERROR)
                show_notification(GET_STRING(32007))
                result_list = None

            except (ValueError, KeyError) as e:
                logger(f"Error parsing API search response: {e}", xbmc.LOGERROR)
                show_notification(GET_STRING(32004))
                result_list = None

            if result_list is not None and addon_cache and params_hash:
                try:
                    for item in result_list:
                        date_val = item.get("Date")
                        if isinstance(date_val, datetime):
                            item["Date"] = date_val.isoformat()
                        elif isinstance(date_val, str):
                            item["Date"] = date_val
                        elif date_val is not None:
                            item["Date"] = str(date_val)
                        else:
                            item["Date"] = ""
                    addon_cache.set(params_hash, result_list, expiration=SEARCH_CACHE_EXPIRATION)
                    logger(f"Stored {len(result_list)} results in cache.")
                except Exception as cache_set_e:
                    logger(f"Error saving results to cache: {cache_set_e}", xbmc.LOGWARNING)
            elif result_list is None:
                logger("API call failed or returned no valid data, not caching.", xbmc.LOGWARNING)

        return result_list


    def _display_search_results(self, result_list):
        """
        Processes the list of subtitle results, sorts them, limits them,
        and adds them to the Kodi listing.
        """
        plugin_handle = int(sys_argv[1])
        
        def type_sort_key_local(item_type_val):
            if item_type_val == 1: return 0
            if item_type_val == 3: return 1
            if item_type_val == 2: return 2
            return 3

        def parse_api_date_local(date_val):
            if isinstance(date_val, datetime):
                return date_val

            if not isinstance(date_val, str) or not date_val:
                return datetime.min

            iso_match = re.match(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d+))?$", date_val)
            if iso_match:
                main, frac = iso_match.group(1), iso_match.group(2)
                if frac:
                    frac = (frac + "000000")[:6]
                    date_val = f"{main}.{frac}"
                else:
                    date_val = main

            try:
                return datetime.fromisoformat(date_val)
            except Exception as iso_err:
                logger(f"parse_api_date_local ERROR: fromisoformat failed for '{date_val}': {iso_err}", xbmc.LOGINFO)

            try:
                if "." in date_val:
                    return datetime.strptime(date_val, "%Y-%m-%dT%H:%M:%S.%f")
                else:
                    return datetime.strptime(date_val, "%Y-%m-%dT%H:%M:%S")
            except Exception as fallback_err:
                logger(f"parse_api_date_local ERROR: Failed to parse '{date_val}': {fallback_err}", xbmc.LOGWARNING)
                return datetime.min
   
        def episode_sort_key_local(episode_num_val):
            if episode_num_val is None: return 9999
            if episode_num_val == 0: return 1000
            if episode_num_val == -2: return 2000
            if episode_num_val == -3: return 3000
            return -episode_num_val

        sort_option = 0
        try:
            sort_option = int(GET_SETTING("sort_order"))
        except (ValueError, TypeError, Exception) as e:
            logger(f"Error reading 'sort_order' setting: {e}. Using default (0 - Date).", xbmc.LOGWARNING)
            sort_option = 0

        sort_series_episodes_enabled = False
        try:
            sort_series_episodes_enabled = GET_BOOL_SETTING("sort_series_episodes")
        except Exception as e:
            logger(f"Error reading 'sort_series_episodes' setting: {e}. Assuming disabled.", xbmc.LOGWARNING)

        processed_list_for_sorting = []

        for item in result_list:
            s_type = type_sort_key_local(item.get("Type"))
            s_title = item.get("Title", "").lower()
            s_year = -item.get("Year", 0)

            s_date_obj = parse_api_date_local(item.get("Date"))
            s_date_sort_val = -s_date_obj.timestamp() if s_date_obj != datetime.min else float("inf")

            s_lang = item.get("Lang", "").lower()
            s_downloads = -item.get("DownloadCount", 0)
            s_rating = -item.get("Rating", 0.0)

            s_season = -item.get("Season", -9999) if item.get("Type") == 2 else 0
            s_episode_key = episode_sort_key_local(item.get("Episode")) if item.get("Type") == 2 else 0

            processed_list_for_sorting.append((
                s_type, s_title, s_year,
                s_date_sort_val,
                s_lang,
                s_downloads,
                s_rating,
                s_season if item.get("Type") == 2 and sort_series_episodes_enabled else 0,
                s_episode_key if item.get("Type") == 2 and sort_series_episodes_enabled else 0,
                item
            ))                

        # 0:type, 1:title, 2:year, 3:date_sort_val, 4:lang, 5:downloads, 6:rating, 7:season, 8:episode_key
        
        sort_key_lambda = None
        if sort_option == 0:
            sort_key_lambda = lambda x: (x[0], x[1], x[2], x[7], x[8], x[3])
        elif sort_option == 1:
            sort_key_lambda = lambda x: (x[0], x[1], x[2], x[4], x[7], x[8], x[3])
        elif sort_option == 2:
            sort_key_lambda = lambda x: (x[0], x[1], x[2], x[5], x[7], x[8], x[3])
        elif sort_option == 3:
            sort_key_lambda = lambda x: (x[0], x[1], x[2], x[6], x[7], x[8], x[3])
        else:
            sort_key_lambda = lambda x: (x[0], x[1], x[2], x[3], x[7], x[8])   

        processed_list_for_sorting.sort(key=sort_key_lambda)

        sorted_result_list = [item_tuple[9] for item_tuple in processed_list_for_sorting]  
                
        results_to_display_count = 50
        try:
            results_to_display_count = max(1, int(GET_SETTING("results_limit")))
        except (ValueError, TypeError, Exception) as e:
            logger(f"Error reading 'results_limit' setting: {e}. Using default of 50.", xbmc.LOGWARNING)
            results_to_display_count = 50

        final_list_to_display = sorted_result_list[:results_to_display_count]

        if not final_list_to_display:
            logger("No subtitle results were displayed in the Kodi dialog! (no results after sorting/limiting)")
            time.sleep(self.dialog_delay)
            xbmcplugin.endOfDirectory(plugin_handle)
            return

        logger(f"Displaying {len(final_list_to_display)} of {len(result_list)} results (limit: {results_to_display_count}, sort: {sort_option}).", xbmc.LOGINFO)
        displayed_count = 0

        for result_item in final_list_to_display:
            api_title = result_item.get("Title", "Unknown Title")
            api_year = result_item.get("Year")
            api_season = result_item.get("Season")
            api_episode = result_item.get("Episode")
            api_release = result_item.get("Release", "")

            logger(f"Processing result_item: {result_item}", xbmc.LOGINFO)

            label2_parts = [api_title]

            if api_year:
                try:
                    label2_parts.append(f"({int(api_year)})")
                except (ValueError, TypeError):
                    if isinstance(api_year, str) and api_year:
                        label2_parts.append(f"({api_year})")

            season_num = None
            episode_num = None

            try:
                if api_season is not None: season_num = int(api_season)
            except (ValueError, TypeError): pass
            try:
                if api_episode is not None: episode_num = int(api_episode)
            except (ValueError, TypeError): pass

            se_string = None

            if season_num is not None and episode_num is not None:
                if season_num > 0 and episode_num > 0:
                    se_string = f"S{season_num:d}E{episode_num:d}"
                elif season_num > 0 and episode_num == 0:
                    se_string = f"S{season_num:d}"
                elif season_num == 0 and episode_num > 0:
                    se_string = f"E{episode_num:d}"
                elif season_num == 0 and episode_num == 0:
                    se_string = "ALL EPISODES"
                elif episode_num == -2:
                    se_string = "PILOT"
                    if season_num >= 0:
                        se_string = f"S{season_num:d} {se_string}"
                elif episode_num == -3:
                    se_string = "SPECIAL"
                    if season_num >= 0:
                        se_string = f"S{season_num:d} {se_string}"

            elif season_num is not None and season_num >= 0:
                se_string = f"S{season_num:d}"

            elif episode_num is not None:
                if episode_num > 0:
                    se_string = f"E{episode_num:d}"
                elif episode_num == -2:
                    se_string = "PILOT"
                elif episode_num == -3:
                    se_string = "SPECIAL"

            if se_string:
                label2_parts.append(se_string)

            if api_release:
                label2_parts.append(f" {api_release}")

            label2 = " ".join(label2_parts).strip()

            api_lang_name = result_item.get("Lang", "")
            lang_key = None
            if api_lang_name:
                lang_key = next((key for key, value in LANGUAGES.items() if value.get("site_name") == api_lang_name), None)
                if not lang_key:
                    logger(f"API language name '{api_lang_name}' not found in LANGUAGES map under 'site_name'.", xbmc.LOGWARNING)

            display_name_for_list = api_lang_name if api_lang_name else "Unknown"
            icon_code = ""

            if lang_key:
                lang_entry = LANGUAGES.get(lang_key, {})
                display_name_for_list = lang_entry.get("display_name", api_lang_name)
                icon_code = lang_entry.get("icon", "")

            try:
                rating_float = float(result_item.get("Rating", 0))
                rating_str = str(int(round(rating_float)))
            except (ValueError, TypeError):
                rating_str = "0"

            listitem = xbmcgui.ListItem(
                label=display_name_for_list,
                label2=label2
            )

            #listitem.setLabel(icon_code.upper())

            listitem.setArt({
                "icon": rating_str,
                "thumb": icon_code
            })

            media_id = result_item.get("Id", "")
            media_type = result_item.get("Type", "")
            if media_id:
                url = f"plugin://{ADDON_ID}/?action=download&media_id={media_id}&type={media_type}&lang={icon_code}"
                xbmcplugin.addDirectoryItem(handle=plugin_handle, url=url, listitem=listitem, isFolder=False)
                displayed_count += 1
            else:
                logger(f"Skipping result item '{api_title}' because it has no 'Id'.", xbmc.LOGWARNING)
           
        time.sleep(self.dialog_delay)
        xbmcplugin.endOfDirectory(plugin_handle)
        
        if displayed_count == len(final_list_to_display) and displayed_count > 0:
            logger(f"All {displayed_count} subtitle results successfully displayed in the Kodi dialog.")
        elif displayed_count > 0:
            logger(f"{displayed_count} of {len(final_list_to_display)} prepared subtitle results displayed in the Kodi dialog.", xbmc.LOGWARNING)
        else:
            logger("No subtitle results were displayed in the Kodi dialog!", xbmc.LOGERROR)


    def kodi_load_subtitle(self, subtitle_file_path):
        """
        Prepares and passes the subtitle file path to the Kodi player.
        Performs Latin/Cyrillic conversion if configured and necessary.
        """
        plugin_handle = int(sys_argv[1])
        logger(f"Starting subtitle load process for: {subtitle_file_path}", xbmc.LOGINFO)

        list_item = xbmcgui.ListItem(label="subtitle")

        lat_cyr_conversion = ConversionMode.DONT_CONVERT_LETTERS
        setting_value = None
        
        try:
            setting_value = GET_SETTING("titlovi-lat-cyr-conversion")
            lat_cyr_conversion = ConversionMode(int(setting_value))
        except ValueError:
            logger(f"Invalid value for 'titlovi-lat-cyr-conversion' setting: '{setting_value}'. Using default (no conversion).", xbmc.LOGERROR)
        except Exception as e:
            logger(f"Error reading subtitle conversion setting: {e}. Using default (no conversion).", xbmc.LOGERROR)
        logger(f"Subtitle conversion mode set to: {lat_cyr_conversion.name}", xbmc.LOGINFO)

        original_path = subtitle_file_path
        base_filename = os.path.basename(subtitle_file_path)
        is_dummy_file = base_filename.lower() == "dummy_subtitle.srt"

        needs_conversion = (lat_cyr_conversion != ConversionMode.DONT_CONVERT_LETTERS)
        is_already_converted = (".converted.lat" in base_filename or
                                ".converted.cyr" in base_filename)

        if needs_conversion and not is_already_converted and not is_dummy_file:
            logger(f"Attempting {lat_cyr_conversion.name} conversion for file: {original_path}", xbmc.LOGINFO)
            try:
                converted_file = handle_lat_cyr_conversion(original_path, lat_cyr_conversion)

                if converted_file is not None and converted_file != original_path:
                    logger(f"Conversion successful. Using converted file: {converted_file}", xbmc.LOGINFO)
                    subtitle_file_path = converted_file
                elif converted_file == original_path:
                    logger(f"Conversion was not needed. Using original file: {original_path}", xbmc.LOGINFO)
                else:
                    logger(f"Subtitle conversion failed. Using original file: {original_path}", xbmc.LOGWARNING)
                    show_notification(GET_STRING(32011))

            except Exception as e:
                logger(f"Unexpected error during subtitle conversion call: {e}. Using original file: {original_path}", xbmc.LOGERROR)
                show_notification(GET_STRING(32011))

        logger(f"Passing subtitle path to Kodi player: {subtitle_file_path}", xbmc.LOGINFO)
        try:
            xbmcplugin.addDirectoryItem(handle=plugin_handle, url=subtitle_file_path, listitem=list_item, isFolder=False)
            logger("Successfully added subtitle item to Kodi.")
        except Exception as e_add:
            logger(f"Error calling xbmcplugin.addDirectoryItem: {e_add}", xbmc.LOGERROR)

 
    def show_subtitle_picker_dialog(self, subtitle_filenames):
        """
        Displays a dialog for the user to select a subtitle from the given list of full filenames.
        """
        if not subtitle_filenames or not isinstance(subtitle_filenames, list):
            logger("Subtitle list for selection is empty.")
            return -1

        display_names_without_ext = []
        try:
            for fname in subtitle_filenames:
                name_without_ext, _ = os.path.splitext(fname)
                display_names_without_ext.append(name_without_ext)
            if not display_names_without_ext:
                display_names_without_ext = subtitle_filenames
        except Exception as e:
            logger(f"Error preparing display names without extensions: {e}. Using full names.", xbmc.LOGERROR)
            display_names_without_ext = subtitle_filenames

        dialog = xbmcgui.Dialog()
        logger(f"Showing dialog with {len(display_names_without_ext)} options (displayed without extensions).", xbmc.LOGINFO)
        selected_index = dialog.select(
            heading = GET_STRING(32012),
            list = display_names_without_ext
        )

        if selected_index == -1:
            logger("User cancelled subtitle selection dialog.")
        else:
            if 0 <= selected_index < len(subtitle_filenames):
                logger(f"User selected index: {selected_index} (corresponds to filename: '{subtitle_filenames[selected_index]}')", xbmc.LOGINFO)
            else:
                logger(f"Dialog returned unexpected index: {selected_index}. Treating as cancellation.", xbmc.LOGERROR)
                selected_index = -1

        return selected_index
 

    def handle_download_action(self):
        """
        Method used for downloading subtitle zip file and extracting it.
        If subtitle file is already downloaded it is reused from disk cache.
        """
        logger("Starting download/load subtitle action...")
        VALID_SUBTITLE_EXTENSIONS = (".srt", ".sub", ".txt")
        try:
            media_id = self.params["media_id"][0]
            media_type = self.params["type"][0]
            lang_code = self.params.get("lang", [None])[0]

            if not media_id or not media_type:
                logger("Missing media_id or type parameter.", xbmc.LOGERROR)
                return

            subtitle_folder_name = f"titlovi_com_subtitle_{media_id}_{media_type}_{lang_code or 'unknown'}"
            subtitle_folder_path = os.path.join(TEMP_DIR, subtitle_folder_name)
            logger(f"Target subtitle folder: {subtitle_folder_path}", xbmc.LOGINFO)

            dummy_global_filename = "dummy_subtitle.srt"
            dummy_global_path = os.path.join(TEMP_DIR, dummy_global_filename)

            needs_download = True
            download_successful = False
            
            if os.path.isdir(subtitle_folder_path):
                try:
                    if any(f.lower().endswith(VALID_SUBTITLE_EXTENSIONS) for _, _, files in os.walk(subtitle_folder_path) for f in files):
                        logger("Subtitle folder exists and populated. Skipping download.")
                        needs_download = False
                    else:
                        logger("Cache folder exists but empty/invalid. Will attempt download.", xbmc.LOGWARNING)
                except Exception as e:
                     logger(f"Error checking existing cache folder {subtitle_folder_path}: {e}", xbmc.LOGERROR)

            if needs_download:
                logger("Attempting to download and extract subtitles.")
                download_url = f"https://titlovi.com/download/?type={media_type}&mediaid={media_id}"
                try:
                    logger(f"Attempting download from: {download_url}", xbmc.LOGINFO)
                    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.6312.106 Safari/537.36"
                    referer = "www.titlovi.com"
                    headers = {"User-Agent": user_agent, "Referer": referer}
                    response = requests.get(download_url, headers=headers, timeout=self.connect_timeout)
                    if response.status_code != requests.codes.ok:
                        logger(f"Download failed with status code: {response.status_code}", xbmc.LOGINFO)
                        show_notification(GET_STRING(32013));
                        return
                except requests.exceptions.Timeout:
                    logger("Download timed out.", xbmc.LOGWARNING)
                    show_notification(GET_STRING(32014))
                    return
                except Exception as e:
                    logger(f"Network or other error during download: {e}", xbmc.LOGERROR)
                    show_notification(GET_STRING(32013));
                    return

                extracted_final_filenames = []
                try:
                    os.makedirs(subtitle_folder_path, exist_ok=True)
                    logger(f"Ensured target directory exists: {subtitle_folder_path}", xbmc.LOGINFO)
                    zip_file = zipfile.ZipFile(io.BytesIO(response.content))
                    existing_files_in_dir = {f.lower() for f in os.listdir(subtitle_folder_path)} if os.path.isdir(subtitle_folder_path) else set()
                    used_filenames_in_zip = set()
                    valid_subs_to_extract = []
                    parent_dirs = set()
                    for member in zip_file.infolist():
                        original_path_in_zip = member.filename
                        if original_path_in_zip.startswith("__MACOSX/") or member.is_dir() or original_path_in_zip.endswith("/"):
                            continue
                        _ , ext = os.path.splitext(original_path_in_zip)
                        if ext.lower() not in VALID_SUBTITLE_EXTENSIONS:
                            continue
                        
                        parent_dirs.add(os.path.dirname(original_path_in_zip))
                        path_parts = [p for p in original_path_in_zip.split("/") if p]
                        normalized_parts = [normalize_string(part, True) for part in path_parts]
                        normalized_parts = [part for part in normalized_parts if part and part != "_"]

                        if normalized_parts:
                            valid_subs_to_extract.append((member, original_path_in_zip, normalized_parts))
                        else:
                            logger(f"Skipping file due to empty normalized parts: {original_path_in_zip}", xbmc.LOGWARNING)

                    if not valid_subs_to_extract:
                        logger("No files with valid subtitle extensions found in the ZIP archive.", xbmc.LOGWARNING)
                        show_notification(GET_STRING(32015));
                        return

                    use_folder_prefix = len(parent_dirs) > 1
                    if use_folder_prefix:
                        logger("Multiple subtitle locations found. Using 'folder - file' naming.", xbmc.LOGINFO)
                    else:
                        logger("Subtitles in single location. Using simple file naming.", xbmc.LOGINFO)

                    for member, original_path_in_zip, normalized_parts in valid_subs_to_extract:
                        filename_part, ext = os.path.splitext(normalized_parts[-1])

                        if use_folder_prefix:
                            base_name_parts = normalized_parts[:-1]
                            proposed_base_name = " - ".join(base_name_parts + [filename_part]) if base_name_parts else filename_part
                        else:
                            proposed_base_name = filename_part

                        final_base_name = proposed_base_name
                        final_filename = f"{final_base_name}{ext}"
                        counter = 2

                        while final_filename.lower() in used_filenames_in_zip or final_filename.lower() in existing_files_in_dir:
                            final_base_name = f"{proposed_base_name}_{counter}"
                            final_filename = f"{final_base_name}{ext}"
                            counter += 1
                        used_filenames_in_zip.add(final_filename.lower())
                        
                        target_path = os.path.join(subtitle_folder_path, final_filename)
                        logger(f"Preparing to extract '{original_path_in_zip}' as '{final_filename}'", xbmc.LOGINFO)
                        
                        try:
                            with zip_file.open(member) as source, open(target_path, "wb") as target: target.write(source.read())
                            extracted_final_filenames.append(final_filename)
                        except Exception as write_error:
                            logger(f"Error writing extracted file {final_filename}: {write_error}", xbmc.LOGERROR)
                            used_filenames_in_zip.discard(final_filename.lower())
                        
                    if not extracted_final_filenames:
                        logger("Extraction process completed, but no files were successfully written.", xbmc.LOGWARNING)
                        show_notification(GET_STRING(32016));
                        return
                        
                    logger(f"Successfully extracted files with final names: {extracted_final_filenames}", xbmc.LOGINFO)
                    download_successful = True

                except zipfile.BadZipFile:
                    logger("Error: Downloaded file is not a valid ZIP archive.", xbmc.LOGERROR)
                    show_notification(GET_STRING(32017));
                    return
                except Exception as e:
                    logger(f"Error processing ZIP archive or extracting files: {e}", xbmc.LOGERROR)
                    show_notification(GET_STRING(32018));
                    return

                if download_successful:
                    try:
                        logger("Download and extraction successful, updating cache info setting.")
                        update_cache_info_setting()
                    except Exception as e_cache:
                        logger(f"Failed to update cache info setting after download: {e_cache}", xbmc.LOGWARNING)

            subtitle_files_info = []
            logger(f"Reading subtitle files from disk directory: {subtitle_folder_path}")
            if os.path.isdir(subtitle_folder_path):
                try:
                    subtitle_files_info = sorted(
                        [(root, fname) for root, _, files in os.walk(subtitle_folder_path)
                        for fname in files if fname.lower().endswith(VALID_SUBTITLE_EXTENSIONS)],
                        key=lambda item: item[1]
                    )
                    if subtitle_files_info:
                        logger(f"Found {len(subtitle_files_info)} actual subtitle file(s) in specific folder.")
                    else:
                        logger("Specific folder exists, but no actual subtitle files found.", xbmc.LOGWARNING)
                except Exception as e:
                    logger(f"Error reading directory contents from {subtitle_folder_path}: {e}", xbmc.LOGERROR)
                    subtitle_files_info = []
            else:
                logger(f"Error: Target directory does not exist after download/extraction attempt: {subtitle_folder_path}", xbmc.LOGERROR)

            if not subtitle_files_info:
                logger("No actual subtitle files found in specific folder to load.")
                if not needs_download:
                    show_notification(GET_STRING(32019))
                return

            if len(subtitle_files_info) == 1:
                selected_root, selected_fname = subtitle_files_info[0]
                final_subtitle_path = os.path.join(selected_root, selected_fname)
                logger(f"Automatically selecting the only subtitle found in specific folder: {final_subtitle_path}", xbmc.LOGINFO)
                self.kodi_load_subtitle(final_subtitle_path)

            elif len(subtitle_files_info) > 1:
                logger(f"Found multiple subtitles ({len(subtitle_files_info)}) in specific folder, showing selection dialog.", xbmc.LOGINFO)
                display_filenames = [fname for _, fname in subtitle_files_info]
                index = self.show_subtitle_picker_dialog(display_filenames)

                if index == -1:
                    logger("User cancelled selection. Ensuring global dummy subtitle exists in TEMP.")
                    dummy_created_or_found = False
                    try:
                        if os.path.exists(dummy_global_path):
                            logger(f"Global dummy file already exists: {dummy_global_path}", xbmc.LOGINFO)
                            dummy_created_or_found = True
                        else:
                            logger(f"Creating global dummy file: {dummy_global_path}", xbmc.LOGINFO)
                            with open(dummy_global_path, "w", encoding="utf-8") as f: f.write("1\n00:00:00,100 --> 00:00:00,500\n\n")
                            dummy_created_or_found = True
                            logger("Global dummy file created successfully.", xbmc.LOGINFO)
                    except Exception as create_err:
                         logger(f"Error ensuring global dummy file exists: {create_err}", xbmc.LOGERROR)
                    
                    if dummy_created_or_found:
                        logger(f"Loading global dummy subtitle: {dummy_global_path}")
                        self.kodi_load_subtitle(dummy_global_path)
                    else:
                        logger("Failed to create or find global dummy file. Attempting fallback to first list item.")
                        if subtitle_files_info:
                            try:
                                fallback_root, fallback_fname = subtitle_files_info[0]
                                fallback_path = os.path.join(fallback_root, fallback_fname)
                                logger(f"Fallback: Loading first subtitle from list: {fallback_path}", xbmc.LOGINFO)
                                self.kodi_load_subtitle(fallback_path)
                            except IndexError:
                                logger("Fallback failed: Could not access first subtitle info (IndexError).", xbmc.LOGERROR)
                            except Exception as load_fallback_err:
                                logger(f"Fallback failed: Error loading first subtitle '{fallback_path}': {load_fallback_err!r}", xbmc.LOGERROR)
                        else:
                            logger("Fallback failed: Subtitle list was empty, cannot load first subtitle.", xbmc.LOGERROR)
   
                else:
                    selected_root, selected_fname = subtitle_files_info[index]
                    final_subtitle_path = os.path.join(selected_root, selected_fname)
                    logger(f"User selected subtitle from specific folder: {final_subtitle_path}")
                    self.kodi_load_subtitle(final_subtitle_path)

        except Exception as e:
            logger(f"Unexpected error in handle_download_action: {e!r}", xbmc.LOGFATAL)
            
        try:
            plugin_handle = int(sys_argv[1])
            xbmcplugin.endOfDirectory(plugin_handle)
        except Exception as e:
            logger(f"Could not call endOfDirectory: {e}", xbmc.LOGINFO)



"""
params_dict:
{'action': ['manualsearch'], 'languages': ['English,Croatian'], 'searchstring': ['test'], 'preferredlanguage': ['English']}
"""

params_dict = parse_qs(sys_argv[2][1:])
logger(params_dict)

action_handler = ActionHandler(params_dict)
if action_handler.validate_params():
    is_user_loggedin = action_handler.user_login()
    if is_user_loggedin:
        logger("User is logged in.")
        action_handler.handle_action()
    else:
        logger("User login failed.", xbmc.LOGWARNING)
else:
    logger("Invalid or missing parameters for action.", xbmc.LOGWARNING)
