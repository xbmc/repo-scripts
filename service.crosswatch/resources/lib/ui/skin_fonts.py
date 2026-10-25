# SPDX-License-Identifier: GPL-2.0-only
"""
Skin-adaptive fonts for CrossWatch windows.

Kodi resolves a control's <font> against the active skin's font set only, with a
hard fallback to font13; addons cannot ship or register their own fonts for a
WindowXMLDialog. This module adapts our dialogs to the active skin: it parses the
skin's Font.xml, maps our anchor font names to the nearest-size font the skin
actually defines, writes font-substituted copies of the dialog XML into
addon_data, and returns a scriptPath the dialogs load from. Any failure falls
back to the shipped addon path (dialogs then render as before).

DELETION GUIDE (KODI-FONT-WORKAROUND, kodi#28534):
    This entire module exists only to work around a Kodi limitation: addons
    cannot register fonts for their WindowXML/WindowXMLDialog windows. It is
    tracked upstream at https://github.com/xbmc/xbmc/issues/28534. When that
    lands (an addon can ship/register its own fonts), delete all of this:
      1. Delete this module (skin_fonts.py) and tests/test_skin_fonts.py.
      2. At every call site, drop the ensure_generated(...) indirection and
         pass the shipped addon path to the dialog scriptPath instead. Find
         them all with:  grep -rn "KODI-FONT-WORKAROUND" resources/
      3. The shipped dialog XML can then reference real registered fonts
         directly, so the font-name anchors need no substitution.

Logging (logger 'ui'):
    ui.font_generated (INFO)  adapted XML written for a skin
    ui.font_fallback (WARNING)  generation failed; the shipped path is used
    ui.font_skipped (DEBUG)  the skin's Font.xml is unreadable or oversized
    ui.font_bad_id (WARNING)  an addon id failed the allowlist
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import re
import shutil
import time
import xml.etree.ElementTree as ET
from collections.abc import Iterable

import xbmc
import xbmcaddon
import xbmcvfs

from resources.lib.log import get_logger

_log = get_logger("ui")

# Generated dialog XML embeds mapped font NAMES (from the skin Font.xml) as
# <font>NAME</font> via plain text substitution, so a name MUST be free of any
# XML metacharacter. Allowlist at parse time: a hostile or metacharacter-bearing
# name is dropped (never mapped), which both blocks markup/action injection and
# guarantees the generated XML stays well-formed (so the fallback invariant holds).
_VALID_FONT_NAME = re.compile(r"^[A-Za-z0-9_.]{1,64}\Z")  # bounded length: a
# multi-KB font name would be spliced into every <font> occurrence (font10 is
# used 48x), amplifying the generated tree to tens of MB from a sub-cap input.
# Real skin fontsets are a few KB; cap input to avoid a flat-XML resource bomb.
_MAX_FONT_XML_BYTES = 512 * 1024

# Parameterised-include support (some skins define fonts inside
# <include name="..."><param name="size_main">28</param>... and reference
# $PARAM[size_main] as a font size). Bounded by design: $VAR/$INFO/$EXP and
# skinvariable tokens are dynamic (only resolvable at Kodi render time) and are
# never evaluated here; a font using one is omitted rather than guessed.
_PARAM_RE = re.compile(r"\$PARAM\[([A-Za-z0-9_]+)\]")
_MAX_INCLUDE_DEPTH = 8
_UNRESOLVED = "\x00"  # sentinel: a $PARAM key absent from scope

# Anchor font names used in the window XML, keyed to their Estuary sizes (the sizes the
# windows were designed against).
ANCHOR_SIZES: dict[str, int] = {
    "font40_title": 40,
    "font32_title": 32,
    "font30_title": 30,
    "font25_title": 25,
    "font13": 30,
    "font12": 25,
}


def _resolve_params(text: str | None, scope: dict[str, str]) -> str | None:
    """Substitute $PARAM[key] from `scope`. Return None (unresolvable) if any
    key is absent, or if any '$' token survives substitution (a $VAR/$INFO/$EXP
    or skinvariable we deliberately do not evaluate). Literal text passes
    through unchanged."""
    if text is None:
        return None
    out = _PARAM_RE.sub(lambda m: scope.get(m.group(1), _UNRESOLVED), text)
    if _UNRESOLVED in out or "$" in out:
        return None
    return out


def build_include_table(xml_texts: Iterable[str]) -> dict[str, ET.Element]:
    """Map every <include name="X"> element across the given skin XML file
    contents. Applies the same per-file guards as parse_fontset (size cap,
    DOCTYPE/ENTITY reject, parse-error skip). First definition of a name wins.
    Invocation elements (<include content=..> / <include>text</include>) are
    not definitions and are ignored here.

    Note the size cap is also a functional ceiling: a skin that defines its font
    include inside an oversized XML file is skipped here, so its fontset
    <include> resolves to nothing and the skin degrades to identity (no
    adaptation). That is a safe no-op, never a broken dialog."""
    table: dict[str, ET.Element] = {}
    for text in xml_texts:
        if not text or len(text.encode("utf-8", "ignore")) > _MAX_FONT_XML_BYTES:
            continue
        low = text.lower()
        if "<!doctype" in low or "<!entity" in low:
            continue
        try:
            root = ET.fromstring(text)
        except ET.ParseError:
            continue
        for inc in root.iter("include"):
            name = inc.get("name")
            if name and name not in table:
                table[name] = inc
    return table


def _expand_include(name: str, includes: dict[str, ET.Element],
                    overrides: dict[str, str], depth: int) -> dict[str, int]:
    """Expand include `name` into {font_name: size}, resolving $PARAM against the
    param scope (the include's <param> defaults, overridden by `overrides`).
    Bounded and bail-safe: an unknown name, depth past _MAX_INCLUDE_DEPTH, a
    conditional include, or an unresolvable/non-integer size omits that font (or
    branch) rather than raising or guessing."""
    if depth > _MAX_INCLUDE_DEPTH:
        return {}
    defn = includes.get(name)
    if defn is None:
        return {}
    scope: dict[str, str] = {}
    for p in defn.findall("param"):
        pname = p.get("name")
        if not pname:
            continue
        if pname in overrides:
            scope[pname] = overrides[pname]
        else:
            resolved = _resolve_params(p.text or "", scope)
            scope[pname] = resolved if resolved is not None else (p.text or "")
    for k, v in overrides.items():
        scope.setdefault(k, v)

    definition = defn.find("definition")
    body = definition if definition is not None else defn
    result: dict[str, int] = {}
    for child in body:
        if child.tag == "font":
            name_el = child.find("name")
            size_el = child.find("size")
            if name_el is None or size_el is None:
                continue
            fname = _resolve_params((name_el.text or "").strip(), scope)
            fsize = _resolve_params((size_el.text or "").strip(), scope)
            if fname is None or fsize is None:
                continue
            try:
                size = int(fsize)
            except ValueError:
                continue
            if fname and size > 0 and _VALID_FONT_NAME.match(fname):
                result[fname] = size
        elif child.tag == "include":
            if child.get("condition"):
                continue
            sub = child.get("content") or (child.text or "").strip()
            if not sub:
                continue
            sub_over: dict[str, str] = {}
            for p in child.findall("param"):
                pn = p.get("name")
                if not pn:
                    continue
                rv = _resolve_params(p.text or "", scope)
                sub_over[pn] = rv if rv is not None else (p.text or "")
            for fn, sz in _expand_include(sub, includes, sub_over, depth + 1).items():
                result.setdefault(fn, sz)
    return result


def parse_fontset(font_xml_text: str, fontset_id: str = "Default",
                  includes: dict[str, ET.Element] | None = None) -> dict[str, int]:
    """Parse a skin Font.xml into {font_name: size} for the given fontset.

    Falls back to the first fontset if `fontset_id` is absent. Fonts without a
    positive integer size are skipped. Returns {} on any parse error.

    Some skins define a fontset as one or more
    <include>NAME</include> references into a separate includes file, with the
    actual <font> definitions and $PARAM[...] sizes living in that include.
    Pass the table built by `build_include_table` as `includes` to resolve
    those; the default (None or {}) keeps this to inline <font> parsing only,
    matching the original behavior. Where a font name is defined both inline
    and via an include, the inline definition wins.

    Security (input is a third-party skin's Font.xml):
    - Reject input over `_MAX_FONT_XML_BYTES` (flat-XML resource bomb).
    - Reject any DOCTYPE/ENTITY declaration (billion-laughs); stdlib ElementTree
      already does not resolve external entities (XXE) on Python 3.7.1+.
    - Allowlist font names to `_VALID_FONT_NAME`; a name carrying any XML
      metacharacter is dropped, so the downstream text substitution can neither
      be injected nor produce malformed XML (no defusedxml dependency needed).
    """
    if len(font_xml_text.encode("utf-8", "ignore")) > _MAX_FONT_XML_BYTES:
        return {}
    lowered = font_xml_text.lower()
    if "<!doctype" in lowered or "<!entity" in lowered:
        return {}
    try:
        root = ET.fromstring(font_xml_text)
    except ET.ParseError:
        return {}
    fontsets = root.findall("fontset")
    chosen = None
    for fs in fontsets:
        if fs.get("id") == fontset_id:
            chosen = fs
            break
    if chosen is None and fontsets:
        chosen = fontsets[0]
    if chosen is None:
        return {}
    result: dict[str, int] = {}
    for font in chosen.findall("font"):
        name_el = font.find("name")
        size_el = font.find("size")
        if name_el is None or size_el is None:
            continue
        name = (name_el.text or "").strip()
        try:
            size = int((size_el.text or "").strip())
        except ValueError:
            continue
        if name and size > 0 and _VALID_FONT_NAME.match(name):
            result[name] = size
    if includes:
        for inc in chosen.findall("include"):
            if inc.get("condition"):
                continue
            sub = inc.get("content") or (inc.text or "").strip()
            if not sub:
                continue
            overrides: dict[str, str] = {}
            for p in inc.findall("param"):
                pn = p.get("name")
                if not pn:
                    continue
                overrides[pn] = p.text or ""
            for fname, size in _expand_include(sub, includes, overrides, 0).items():
                result.setdefault(fname, size)   # inline fonts take precedence
    return result


# Skin fonts whose NAME signals a special-purpose glyph/symbol/decorative font
# rather than general body text. Nearest-size matching MUST skip these, or
# captions and labels render as icons/wrong glyphs (observed live: a skin's
# "SymbolList" was nearest to a caption size and rendered a caption with a clock
# glyph and names in a symbol face).
_SPECIAL_FONT_HINTS = (
    "symbol", "icon", "glyph", "flag", "weather", "clock", "lyric", "mono",
    "arrow", "timeline", "selector", "watched", "wingding", "awesome",
    "material", "dingbat", "emoji",
)


def _is_text_font(name: str) -> bool:
    """True unless the font name signals a special-purpose (non-text) face."""
    low = name.lower()
    return not any(hint in low for hint in _SPECIAL_FONT_HINTS)


def build_font_map(skin_fonts: dict[str, int],
                   anchors: dict[str, int] = ANCHOR_SIZES) -> dict[str, str]:
    """Map each anchor font name to the skin's nearest-size TEXT font.

    If the skin defines the anchor name itself, it maps to itself. Special-
    purpose fonts (symbol/icon/flag/weather/etc., by name) are excluded from the
    candidate pool so text never gets mapped onto a glyph face. If the skin
    provides no usable text font, an anchor maps to itself (identity), so the
    shipped name is kept and Kodi's own font13 fallback applies.
    """
    font_map: dict[str, str] = {}
    candidates = {n: s for n, s in skin_fonts.items() if _is_text_font(n)}
    for anchor, target in anchors.items():
        if anchor in skin_fonts:
            font_map[anchor] = anchor
            continue
        if not candidates:
            font_map[anchor] = anchor
            continue
        # Nearest by absolute size difference; ties break to the smaller size
        # then the name, for determinism.
        best = min(candidates.items(),
                   key=lambda kv: (abs(kv[1] - target), kv[1], kv[0]))
        font_map[anchor] = best[0]
    return font_map


def substitute_fonts(xml_text: str, font_map: dict[str, str]) -> str:
    """Replace <font>ANCHOR</font> with <font>MAPPED</font> for each anchor."""
    out = xml_text
    for anchor, mapped in font_map.items():
        if anchor != mapped:
            out = out.replace(f"<font>{anchor}</font>",
                              f"<font>{mapped}</font>")
    return out


def cache_key(skin_id: str, skin_version: str, fontset: str,
              addon_version: str, font_mtime: int, shipped: str = "") -> str:
    """Stable identity for a generated set (invalidates on any component change).

    Includes the skin Font.xml mtime so a hand-edited or forked skin font file
    invalidates the cache without a per-open full content hash, and a digest of
    the shipped windows so a window added or changed without a version bump is
    not left out of a set built before it.
    """
    return f"{skin_id}@{skin_version}|{fontset}|addon@{addon_version}|font@{font_mtime}|ship@{shipped}"


_RES_REL = os.path.join("resources", "skins", "Default")
_XML_DIR = os.path.join(_RES_REL, "1080i")
_MEDIA_DIR = os.path.join(_RES_REL, "media")
_MARKER = ".built-for"
# The id reaches a path join under addon_data, so it is allowlisted; "." and ".." are
# rejected separately below.
_VALID_ID = re.compile(r"^[A-Za-z0-9_.-]+\Z")
_LOCK_STALE_SECS = 30


def _shipped_digest(shipped_path: str) -> str:
    """A short digest of the shipped window XML and the names of the shipped media.

    The window files are a few KB, and this runs only on the expensive probe (a memo
    miss), so reading them is cheap next to the skin directory scan beside it.
    """
    digest = hashlib.sha256()
    xml_dir = os.path.join(shipped_path, _XML_DIR)
    for name in sorted(os.listdir(xml_dir)):
        if name.endswith(".xml"):
            digest.update(name.encode())
            with open(os.path.join(xml_dir, name), "rb") as fh:
                digest.update(fh.read())
    for root, _dirs, files in sorted(os.walk(os.path.join(shipped_path, _MEDIA_DIR))):
        for name in sorted(files):
            digest.update(os.path.relpath(os.path.join(root, name), shipped_path).encode())
    return digest.hexdigest()[:16]


def _safe_shipped(addon_id: str) -> str:
    """The shipped scriptPath, but NEVER raising: the fallback must not itself
    break a dialog. If Addon() fails (malformed/unregistered id), derive the
    conventional install path defensively."""
    try:
        return xbmcaddon.Addon(addon_id).getAddonInfo('path')
    except Exception:
        return xbmcvfs.translatePath(f"special://home/addons/{addon_id}")


def _active_skin() -> tuple[str, str]:
    """Return (skin_id, skin_version). Raises if the skin addon is unavailable."""
    skin_id = xbmc.getSkinDir()
    version = xbmcaddon.Addon(skin_id).getAddonInfo('version')
    return skin_id, version


def _active_fontset() -> str:
    request = {"jsonrpc": "2.0", "id": 1, "method": "Settings.GetSettingValue", "params": {"setting": "lookandfeel.font"}}
    try:
        body = json.loads(xbmc.executeJSONRPC(json.dumps(request)))
        value = body.get("result", {}).get("value", "")
        return value if isinstance(value, str) and value else "Default"
    except Exception:
        return "Default"


def _find_skin_font_xml() -> str | None:
    """Locate the active skin's Font.xml (varies by skin: 1080i/, xml/, etc.)."""
    base = xbmcvfs.translatePath("special://skin/")
    candidates = ["1080i", "16x9", "720p", "xml", "1080p", ""]
    for sub in candidates:
        path = os.path.join(base, sub, "Font.xml") if sub else os.path.join(base, "Font.xml")
        if os.path.isfile(path):
            return path
    # Last resort: shallow search one level down.
    try:
        for entry in os.listdir(base):
            path = os.path.join(base, entry, "Font.xml")
            if os.path.isfile(path):
                return path
    except OSError:
        pass
    return None


def _read_font_xml(path: str) -> str | None:
    """Read a skin XML file, or None if missing/unreadable/oversized. Gates on
    file size BEFORE reading so a hostile skin cannot force a full allocation."""
    try:
        if os.path.getsize(path) > _MAX_FONT_XML_BYTES:
            return None
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return None


def _font_relevant_xml(names: list[str]) -> list[str]:
    """Files in a skin resolution dir that can define fonts: Font.xml plus any
    XML whose name contains 'font' or starts with 'includes' (some skins
    keep font <include>s in Includes_Font.xml). Narrows both the mtime cache
    key and the include-table parse so unrelated dialog XML edits neither
    invalidate the cache nor get parsed."""
    out: list[str] = []
    for n in names:
        low = n.lower()
        if not low.endswith(".xml"):
            continue
        if low == "font.xml" or "font" in low or low.startswith("includes"):
            out.append(n)
    return out


def _load_skin_includes(skin_xml_dir: str, names: list[str]) -> dict[str, ET.Element]:
    """Build the include table from the font-relevant files in `names` (a
    precomputed listing of the skin's resolution dir, where such
    skins keep Includes_Font.xml). Best-effort: unreadable or oversized files
    are skipped. `names` is the caller's single os.listdir of skin_xml_dir, so
    this does not scan the directory again."""
    texts: list[str] = []
    for entry in _font_relevant_xml(names):
        text = _read_font_xml(os.path.join(skin_xml_dir, entry))
        if text is None:
            continue
        texts.append(text)
    return build_include_table(texts)


def _fsync_path(path: str) -> None:
    """Best-effort fsync of a file or directory; never raises."""
    try:
        fd = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def _try_lock(lock_path: str) -> int | None:
    """Acquire an exclusive lockfile fd, or None if another process holds it.

    A lock older than _LOCK_STALE_SECS is reclaimed once (crashed writer).
    Reclaim proceeds ONLY if THIS process's rename of the stale path succeeds
    (rename-by-name acts on whatever currently sits at lock_path): of N racers
    that all saw the same stale file, only one rename can move that inode
    away, and the losers get an OSError and back off (return None) instead of
    also proceeding. This closes the common same-stale-lock race, but not
    every interleaving: if a concurrent reclaimer already recreated a fresh
    lock by the time this rename runs, the rename can move that fresh file
    instead (rated low risk). Even then the final O_EXCL create below
    still refuses to steal a lock another racer just created, so the worst
    outcome is a redundant build (PID-unique temps, idempotent output), never
    corruption or a broken dialog."""
    try:
        return os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        try:
            if time.time() - os.path.getmtime(lock_path) <= _LOCK_STALE_SECS:
                return None
            claim = lock_path + ".reclaim." + str(os.getpid())
            os.rename(lock_path, claim)
            os.remove(claim)
        except (OSError, FileExistsError):
            return None
        try:
            return os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except OSError:
            return None  # another racer recreated it first: do not steal
    except OSError:
        return None


def _release_lock(fd: int, lock_path: str) -> None:
    try:
        os.close(fd)
    except OSError:
        pass
    try:
        os.remove(lock_path)
    except OSError:
        pass


def _generate_into(shipped_path: str, out_base: str, font_map: dict[str, str]) -> None:
    """Build a COMPLETE adapted tree (every dialog XML + a full media copy) into
    out_base, which must not already exist. Media is copied every time (no
    existence gate) so an addon update ships new assets."""
    dst_xml = os.path.join(out_base, _XML_DIR)
    os.makedirs(dst_xml)
    src_xml = os.path.join(shipped_path, _XML_DIR)
    for name in os.listdir(src_xml):
        if not name.endswith(".xml"):
            continue
        with open(os.path.join(src_xml, name), encoding="utf-8") as fh:
            text = fh.read()
        dst_path = os.path.join(dst_xml, name)
        with open(dst_path, "w", encoding="utf-8") as fh:
            fh.write(substitute_fonts(text, font_map))
        _fsync_path(dst_path)
    shutil.copytree(os.path.join(shipped_path, _MEDIA_DIR),
                    os.path.join(out_base, _MEDIA_DIR))


def _swap_into_place(tmp: str, out_base: str) -> None:
    """Replace out_base with the freshly built tmp tree via renames (near-atomic).

    There is a sub-millisecond window between the first rename (out_base ->
    .old) and the second (tmp -> out_base) where out_base does not exist. A
    dialog whose load happens to land in that window can fail to construct
    (an accepted case); it does NOT silently fall back to the
    shipped path, since a reader that already holds out_base as its
    scriptPath does not re-consult ensure_generated at load time. The
    fallback-to-shipped behavior applies to the NEXT call into
    ensure_generated, not to a dialog already mid-load against out_base. On
    Windows, a rename that targets a path with an open file handle can fail;
    this is not exercised here because _compute_generated_path returns before
    any dialog is constructed, so no reader holds a handle into out_base
    during the swap."""
    old = out_base + ".old"
    if os.path.isdir(old):
        shutil.rmtree(old, ignore_errors=True)
    if os.path.exists(out_base):
        os.rename(out_base, old)
    os.rename(tmp, out_base)
    if os.path.isdir(old):
        shutil.rmtree(old, ignore_errors=True)


def _cleanup_orphans(out_base: str, keep_tmp: str) -> None:
    """Remove leftover build dirs from crashed/killed builders: every stale
    out_base + '.new.*' except keep_tmp, plus a stale out_base + '.old'.
    Best-effort; never raises.

    A '.new.*' candidate is only removed once it is older than
    _LOCK_STALE_SECS: a fresh one may belong to a live concurrent builder
    (its lock has not gone stale yet), and rmtree-ing that out from under it
    would corrupt an in-progress build. A leftover '.old' only exists after a
    completed-or-crashed swap, so it is always safe to remove unconditionally.
    """
    for path in glob.glob(out_base + ".new.*"):
        if path == keep_tmp:
            continue
        try:
            age = time.time() - os.path.getmtime(path)
        except OSError:
            continue                        # gone or unreadable; skip, not fatal
        if age > _LOCK_STALE_SECS:
            shutil.rmtree(path, ignore_errors=True)
    shutil.rmtree(out_base + ".old", ignore_errors=True)


# Session memo: addon_id -> (skin_id, resolved scriptPath, monotonic timestamp).
# ensure_generated's cheap probe (getSkinDir only) short-circuits the expensive
# probe (JSON-RPC fontset lookup + full skin-dir mtime scan, in
# _compute_generated_path) while the memo is fresh, so a dialog re-opened
# moments after the last one skips straight to the cached path.
#
# Keyed on skin_id only, NOT (skin_id, fontset): reading the active fontset
# requires the JSON-RPC call that this cheap probe exists to avoid. A fontset
# change with no skin change is picked up once the memo entry ages out (within
# _MEMO_TTL below), not immediately; that lag is the accepted tradeoff for
# skipping the RPC on every dialog open.
_MEMO: dict[str, tuple[str, str, float]] = {}   # addon_id -> (skin_id, path, ts)
_MEMO_TTL = 30.0  # seconds; a skin change flips getSkinDir immediately so a
# stale memo self-heals within this window even without the skin-id check.


def reset_memo() -> None:
    """Test/utility hook: clear the in-process memo."""
    _MEMO.clear()


def _compute_generated_path(addon_id: str, skin_id: str) -> str:
    """The expensive probe + generate-on-miss body: freshness check (fontset RPC
    + Font.xml mtime scan + marker read), and generation when stale. Called by
    `ensure_generated` only on a memo miss/expiry; `skin_id` is already known
    (from the cheap `xbmc.getSkinDir()` probe) so it is not re-derived here.
    """
    addon = xbmcaddon.Addon(addon_id)          # inside try: a bad id -> fallback
    shipped = addon.getAddonInfo('path')
    _, skin_version = _active_skin()
    fontset = _active_fontset()
    font_xml_path = _find_skin_font_xml()
    if not font_xml_path:
        return shipped                          # cannot adapt; shipped is valid
    skin_xml_dir = os.path.dirname(font_xml_path)
    try:
        skin_dir_names = sorted(os.listdir(skin_xml_dir))
    except OSError:
        skin_dir_names = []
    relevant_names = _font_relevant_xml(skin_dir_names)
    mtimes = [os.path.getmtime(font_xml_path)]
    try:
        for entry in relevant_names:
            mtimes.append(os.path.getmtime(os.path.join(skin_xml_dir, entry)))
    except OSError:
        pass
    font_mtime = int(max(mtimes))
    key = cache_key(skin_id, skin_version, fontset,
                    addon.getAddonInfo('version'), font_mtime, _shipped_digest(shipped))

    out_base = xbmcvfs.translatePath(
        f"special://profile/addon_data/{addon_id}/skingen")
    os.makedirs(os.path.dirname(out_base), exist_ok=True)
    marker = os.path.join(out_base, _MARKER)

    def _fresh() -> bool:
        try:
            with open(marker, encoding="utf-8") as fh:
                return fh.read().strip() == key
        except OSError:
            return False

    if _fresh():
        return out_base

    includes = _load_skin_includes(skin_xml_dir, skin_dir_names)
    font_xml_text = _read_font_xml(font_xml_path)
    if font_xml_text is None:
        _log.debug("ui.font_skipped", skin=skin_id)
        return shipped                          # unreadable/oversized; shipped is valid
    font_map = build_font_map(parse_fontset(font_xml_text, fontset, includes))
    if all(anchor == mapped for anchor, mapped in font_map.items()):
        return shipped                          # identity skin: no rewrite needed

    lock_path = out_base + ".lock"
    fd = _try_lock(lock_path)
    if fd is None:
        return shipped                          # another process building; do not block
    try:
        if _fresh():                            # built while we waited for the lock
            return out_base
        # The lock above is best-effort (see _try_lock's stale-reclaim). A
        # PID-unique temp dir makes a lock race benign: each builder writes
        # its own temp, output is identical for the same skin+fonts, and the
        # atomic rename-swap means a racing loser at worst falls back to the
        # shipped path for that one open.
        _cleanup_orphans(out_base, out_base + ".new." + str(os.getpid()))
        tmp = out_base + ".new." + str(os.getpid())
        if os.path.isdir(tmp):
            shutil.rmtree(tmp, ignore_errors=True)
        try:
            _generate_into(shipped, tmp, font_map)
            marker_path = os.path.join(tmp, _MARKER)
            with open(marker_path, "w", encoding="utf-8") as fh:
                fh.write(key)
            # Marker is written into tmp before the swap, so a surviving
            # marker after a crash implies the XML it names was flushed too:
            # fsync the marker file and the tmp dir entry it lives in first.
            _fsync_path(marker_path)
            _fsync_path(tmp)
            _swap_into_place(tmp, out_base)
            _fsync_path(os.path.dirname(out_base))
        except Exception:
            shutil.rmtree(tmp, ignore_errors=True)  # no partial tmp left behind
            raise
        _log.info(
            "ui.font_generated", skin=skin_id, mapped=",".join(f"{a}={m}" for a, m in sorted(font_map.items()))
        )
    finally:
        _release_lock(fd, lock_path)
    return out_base


def ensure_generated(addon_id: str) -> str:
    """Return a scriptPath whose dialog XML is adapted to the active skin.

    EVERYTHING runs inside one try, and every fallback return uses `_safe_shipped`
    so the fallback itself cannot raise (this is what actually holds the "never
    break a dialog" invariant). A cheap probe (`xbmc.getSkinDir()` only) is
    checked against a short-lived in-process memo first; only on a memo
    miss/expiry does the expensive probe run (`_compute_generated_path`: fontset
    RPC + Font.xml mtime scan + marker read), with generation on a genuine cache
    miss. Identity skins (Estuary and any skin defining all anchor names) skip
    generation entirely and return the shipped path unchanged.

    The fallback is a RELIABILITY mechanism, not a security boundary: a
    successfully generated tree is always well-formed because parse_fontset
    allowlists font names.
    """
    try:
        if not _VALID_ID.match(addon_id or "") or addon_id in (".", ".."):
            _log.warning("ui.font_bad_id")
            return _safe_shipped(addon_id)
        skin_id = xbmc.getSkinDir()                     # cheap, no RPC
        now = time.monotonic()
        cached = _MEMO.get(addon_id)
        if cached is not None and cached[0] == skin_id and (now - cached[2]) < _MEMO_TTL:
            return cached[1]
        result = _compute_generated_path(addon_id, skin_id)
        _MEMO[addon_id] = (skin_id, result, now)
        return result
    except (OSError, ET.ParseError) as exc:
        _log.warning("ui.font_fallback", error_type=type(exc).__name__)
        return _safe_shipped(addon_id)
    except Exception as exc:
        _log.warning("ui.font_fallback", error_type=type(exc).__name__, unexpected=True)
        return _safe_shipped(addon_id)
