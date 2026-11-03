"""Skin labels formatted as Kodi does, their infolabels and conditions read on the main thread."""
from __future__ import annotations

import codecs
import os
import re
import time
import xml.etree.ElementTree as ET
from typing import (
    Callable, Dict, Final, Iterable, List, NamedTuple, Optional, Set, Tuple, Union,
)

import xbmc
import xbmcaddon
import xbmcvfs

from lib.kodi.client import ADDON, log
from lib.kodi.utilities import (
    LabelSnapshot, is_kodi_piers_or_later, read_conditions, read_labels,
)

_FORMATS: Final = ("$INFO[", "$ESCINFO[", "$VAR[", "$ESCVAR[")
_MAP_FORMATS: Final = ("$MAP[", "$ESCMAP[")
_RECHECK_SECONDS: Final = 5.0
# under Python's recursion limit; Kodi has none
_MAX_DEPTH: Final = 100
_MAX_RENDER: Final = 1 << 20
_COMMENT: Final = re.compile(rb"<!--.*?-->", re.S)
_DOCTYPE: Final = re.compile(rb"<!DOCTYPE(?:[^\[>]|\[.*?\])*>", re.S | re.I)
_STRAY_AMPERSAND: Final = re.compile(rb"&(?!(?:amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)")
_DEFINITION_MARKERS: Final = (b"<variable", b"<expression", b"<map", b"file=")


class _TooLong(Exception):
    """Raised when a rendered label grows past the size cap."""


class _Portion(NamedTuple):
    """One piece of a parsed label: literal text, or an infolabel, variable or map lookup."""
    kind: str
    name: str
    prefix: str = ""
    postfix: str = ""
    escaped: bool = False
    map_name: str = ""


class _SkinIndex:
    """The active skin's include files, read in Kodi's load order only as far as a lookup needs."""

    def __init__(self, skin: str) -> None:
        self.skin = skin
        self.files: List[Tuple[str, float]] = []
        self._closest, self._default = _res_folders(skin)
        self._pending: List[Union[str, List[ET.Element]]] = [self._path("Includes.xml")]
        self._expressions: Dict[str, str] = {}
        self._variables: Dict[str, List[Tuple[str, str]]] = {}
        self._flattened: Dict[str, Optional[List[Tuple[str, str]]]] = {}
        self._maps: Dict[str, Dict[str, str]] = {}
        self._map_refs: Dict[str, str] = {}
        self._include_conditions: Dict[str, bool] = {}

    def variable(self, name: str) -> Optional[List[Tuple[str, str]]]:
        """A variable's values with `$EXP` flattened in their conditions; None when undefined."""
        if name not in self._flattened:
            values = self._find(self._variables, name)
            self._flattened[name] = None if values is None else [
                (self._flatten(condition, []) if condition else "", label)
                for condition, label in values]
        return self._flattened[name]

    def map_value(self, name: str, key: str) -> str:
        """Map a value through a skin map and its refs, all files read; unchanged on a miss."""
        while self._pending:
            self._step()
        return self._lookup(name, key, [])

    def includes_changed(self) -> bool:
        """True when a conditional include file's condition now reads differently from load time."""
        if not self._include_conditions:
            return False
        states = read_conditions(self._include_conditions)
        return any(states[condition] != loaded
                   for condition, loaded in self._include_conditions.items())

    def _find(self, table: Dict, name: str):
        """Find a name, reading further include files until it turns up or none are left."""
        while name not in table and self._pending:
            self._step()
        return table.get(name)

    def _step(self) -> None:
        """Step the queue once: load the next include file or apply a file's queued maps."""
        item = self._pending.pop(0)
        if isinstance(item, str):
            self._load(item)
        else:
            self._apply_maps(item)

    def _load(self, path: str) -> None:
        """Load a file's expressions and variables, first winning; queue its includes and maps."""
        if any(path == loaded for loaded, _ in self.files):
            return
        self.files.append((path, _mtime(path)))
        try:
            with open(path, "rb") as handle:
                data = handle.read()
            if not any(marker in data for marker in _DEFINITION_MARKERS):
                return
            root = _parse_xml(data)
        except (OSError, ET.ParseError) as e:
            log("SkinUtils", f"Skipped skin include file {path}: {e}", xbmc.LOGWARNING)
            return
        if root.tag.lower() != "includes":
            return
        for node in root.findall("expression"):
            name = node.get("name")
            if name and node.text and name not in self._expressions:
                self._expressions[name] = f"[{node.text}]"
        for node in root.findall("variable"):
            name = node.get("name")
            if not name or name in self._variables or not (len(node) or (node.text or "").strip()):
                continue
            values = []
            for value in node.findall("value"):
                condition = value.get("condition")
                values.append((condition or "", value.text or ""))
                if condition is None:
                    break
            self._variables[name] = values
        files = [(node.get("file") or "", node.get("condition")) for node in root.findall("include")
                 if node.get("file") and not node.get("name")]
        states = read_conditions(condition for _, condition in files if condition is not None)
        self._include_conditions.update(states)
        nested: List[Union[str, List[ET.Element]]] = [
            self._path(file_name) for file_name, condition in files
            if condition is None or states[condition]]
        maps = root.findall("map")
        self._pending[0:0] = nested + ([maps] if maps else [])

    def _apply_maps(self, nodes: List[ET.Element]) -> None:
        """Apply a file's skin maps, a later definition replacing an earlier one."""
        for node in nodes:
            name = node.get("name")
            if not name:
                continue
            self._maps.pop(name, None)
            self._map_refs.pop(name, None)
            ref = node.get("ref")
            if ref:
                self._map_refs[name] = ref
            entries: Dict[str, str] = {}
            for entry in node.findall("entry"):
                key = entry.get("key")
                if key and entry.text is not None and key not in entries:
                    entries[key] = entry.text
            if entries:
                self._maps[name] = entries

    def _lookup(self, name: str, key: str, visited: List[str]) -> str:
        """Look a key up in a map, then the maps it refs; the key itself on a miss or a ref loop."""
        if name in visited:
            return key
        entries = self._maps.get(name)
        if entries is not None and key in entries:
            return entries[key]
        ref = self._map_refs.get(name)
        return self._lookup(ref, key, visited + [name]) if ref else key

    def _flatten(self, text: str, resolving: List[str]) -> str:
        """Flatten each `$EXP[name]` into its expression, nested too; unknown or circular is ''."""
        def expand(name: str) -> str:
            if name in resolving or len(resolving) >= _MAX_DEPTH:
                return ""
            expression = self._find(self._expressions, name)
            return "" if expression is None else self._flatten(expression, resolving + [name])
        return _replace_keyword(text, "EXP", expand)

    def _path(self, name: str) -> str:
        """Path of a skin file in the closest resolution folder, else in the default one."""
        path = os.path.normpath(os.path.join(self.skin, self._closest, name))
        if os.path.exists(path):
            return path
        return os.path.normpath(os.path.join(self.skin, self._default, name))


_index: Optional[_SkinIndex] = None
_checked_at = 0.0
_portions: Dict[str, Optional[List[_Portion]]] = {}
_warned: Set[str] = set()


def resolve_label(text: str) -> str:
    """Resolve a skin label as Kodi formats it; '' for unreadable syntax or past the size cap."""
    portions = _parse(text)
    if portions is None:
        _warn(text, f"Label uses syntax that cannot be read: {text}")
        return ""
    names = [portion.name for portion in portions if portion.kind == "var"]
    needs_skin = names or any(portion.kind == "map" for portion in portions)
    index = _current_index() if needs_skin else None
    conditions, infos = _requirements(names, index) if index else ([], [])
    infos += [portion.name for portion in portions if portion.kind in ("info", "map")]
    try:
        return _render(portions, index, read_conditions(conditions), LabelSnapshot(infos), 0, {})
    except _TooLong:
        _warn(text, f"Label renders past the size cap: {text[:200]}")
        return ""


def variable_labels(names: Iterable[str]) -> List[str]:
    """Infolabels the named variables can read, nested variables included."""
    index = _current_index()
    return _requirements(names, index)[1] if index else []


def resolve_variables(names: Iterable[str], labels: LabelSnapshot) -> str:
    """Resolve the first named variable with a value, as Kodi would; '' when none has one."""
    index = _current_index()
    if index is None:
        return ""
    names = list(names)
    states = read_conditions(_requirements(names, index)[0])
    memo: Dict[str, str] = {}
    for name in names:
        value = _variable_value(name, index, states, labels, 0, memo)
        if value:
            return value
    return ""


def _requirements(names: Iterable[str], index: _SkinIndex) -> Tuple[List[str], List[str]]:
    """Conditions and infolabels the named variables can read, nested variables included."""
    conditions: Dict[str, None] = {}
    infos: Dict[str, None] = {}
    pending = list(names)
    seen: Set[str] = set()
    while pending:
        name = pending.pop()
        if name in seen:
            continue
        seen.add(name)
        for condition, label in index.variable(name) or ():
            if condition:
                conditions[condition] = None
            for portion in _parse(label) or ():
                if portion.kind in ("info", "map"):
                    infos[portion.name] = None
                elif portion.kind == "var":
                    pending.append(portion.name)
    return list(conditions), list(infos)


def _variable_value(name: str, index: _SkinIndex, states: Dict[str, bool],
                    labels: LabelSnapshot, depth: int, memo: Dict[str, str]) -> str:
    """Value of the variable's first entry whose condition holds, worked out once per resolve."""
    if name in memo:
        return memo[name]
    memo[name] = ""
    values = index.variable(name)
    if values is None:
        _warn(name, f"Skin variable '{name}' is not defined")
        return ""
    for condition, label in values:
        if condition and not states.get(condition, False):
            continue
        portions = _parse(label)
        if portions is None:
            _warn(name, f"Skin variable '{name}' uses label syntax that cannot be read")
            return ""
        try:
            memo[name] = _render(portions, index, states, labels, depth, memo)
        except _TooLong:
            _warn(name, f"Skin variable '{name}' renders past the size cap")
        return memo[name]
    return ""


def _render(portions: List[_Portion], index: Optional[_SkinIndex], states: Dict[str, bool],
            labels: LabelSnapshot, depth: int, memo: Dict[str, str]) -> str:
    """Render parsed portions as Kodi formats a label; raises _TooLong past the size cap."""
    out = []
    size = 0
    for portion in portions:
        if portion.kind == "text":
            piece = portion.name
        elif portion.kind == "var" and (index is None or index.variable(portion.name) is None):
            piece = portion.prefix
        else:
            if portion.kind == "info":
                value = labels.get(portion.name)
            elif portion.kind == "map":
                value = labels.get(portion.name)
                if value and index is not None:
                    value = index.map_value(portion.map_name, value)
            else:
                value = (_variable_value(portion.name, index, states, labels, depth + 1, memo)
                         if index is not None and depth < _MAX_DEPTH else "")
            piece = portion.prefix + value + portion.postfix if value else ""
            if piece and portion.escaped:
                piece = '"' + piece.replace("\\", "\\\\").replace('"', '\\"') + '"'
        size += len(piece)
        if size > _MAX_RENDER:
            raise _TooLong()
        out.append(piece)
    return "".join(out)


def _parse(label: str) -> Optional[List[_Portion]]:
    """Parse a label into portions as Kodi does, cached per skin load; None when not supported."""
    if label in _portions:
        return _portions[label]
    forms = _FORMATS + _MAP_FORMATS if is_kodi_piers_or_later() else _FORMATS
    work = _replace_keyword(label, "LOCALIZE", _localized)
    work = _replace_keyword(work, "NUMBER", lambda number: number)
    work = _replace_keyword(work, "ADDON", _addon_string)
    portions: Optional[List[_Portion]] = None if "$FEATURE[" in work else []
    while portions is not None:
        found = [(work.find(form), form) for form in forms if form in work]
        if not found:
            if work:
                portions.append(_Portion("text", _unescape(work)))
            break
        pos, form = min(found)
        if pos:
            portions.append(_Portion("text", _unescape(work[:pos])))
        start = pos + len(form)
        end = _end_bracket(work, start)
        if end < 0:
            break
        params = work[start:end].split(",")
        escaped = form.startswith("$ESC")
        if form.endswith("MAP["):
            map_name = params[0].strip()
            info = params[1].strip() if len(params) > 1 else ""
            if map_name and info:
                portions.append(_Portion(
                    "map", info, _unescape(params[2]) if len(params) > 2 else "",
                    _unescape(params[3]) if len(params) > 3 else "", escaped, map_name))
        else:
            portions.append(_Portion(
                "var" if form.endswith("VAR[") else "info", params[0],
                _unescape(params[1]) if len(params) > 1 else "",
                _unescape(params[2]) if len(params) > 2 else "", escaped))
        work = work[end + 1:]
    _portions[label] = portions
    return portions


def _replace_keyword(text: str, keyword: str, replacer: Callable[[str], str]) -> str:
    """Replace each `$X[value]` form with the callback's result, as Kodi's label parser does."""
    opener = f"${keyword}["
    out = []
    index = 0
    while True:
        start = text.find(opener, index)
        if start < 0:
            break
        end = _end_bracket(text, start + len(opener))
        if end < 0:
            break
        out.append(text[index:start])
        out.append(replacer(text[start + len(opener):end]))
        index = end + 1
    return "".join(out) + text[index:] if out else text


def _string_id(value: str) -> int:
    """A string id as Kodi reads one; 0 for anything not a short run of digits."""
    digits = value.strip()
    return int(digits) if digits.isdigit() and len(digits) < 10 else 0


def _localized(value: str) -> str:
    """Kodi's or the skin's string for a `$LOCALIZE` id; '' for one not a short run of digits."""
    string_id = _string_id(value)
    return xbmc.getLocalizedString(string_id) if string_id else ""


def _addon_string(value: str) -> str:
    """An add-on's string for a `$ADDON[addon.id number]` reference; '' when it cannot be read."""
    addon_id, _, number = value.partition(" ")
    string_id = _string_id(number)
    if not string_id:
        return ""
    try:
        addon = ADDON if addon_id == ADDON.getAddonInfo("id") else xbmcaddon.Addon(addon_id)
        return addon.getLocalizedString(string_id)
    except RuntimeError:
        return ""


def _unescape(text: str) -> str:
    """Unescape the commas and brackets a label writes as `$COMMA`, `$LBRACKET` and `$RBRACKET`."""
    return text.replace("$COMMA", ",").replace("$LBRACKET", "[").replace("$RBRACKET", "]")


def _end_bracket(text: str, start: int) -> int:
    """Index of the `]` closing an already open bracket; -1 when unclosed."""
    depth = 1
    for i in range(start, len(text)):
        if text[i] == "[":
            depth += 1
        elif text[i] == "]":
            depth -= 1
            if not depth:
                return i
    return -1


def _warn(key: str, message: str) -> None:
    """Warn about a label's or variable's problem once per skin load."""
    if key not in _warned:
        _warned.add(key)
        log("SkinUtils", message, xbmc.LOGWARNING)


def _current_index() -> Optional[_SkinIndex]:
    """The active skin's index, started over on a skin change, a file edit or an include flip."""
    global _index, _checked_at
    now = time.monotonic()
    if _index is not None and now - _checked_at < _RECHECK_SECONDS:
        return _index
    _checked_at = now
    skin = xbmcvfs.translatePath("special://skin/")
    if (_index is None or _index.skin != skin
            or any(_mtime(path) != mtime for path, mtime in _index.files)
            or _index.includes_changed()):
        _portions.clear()
        _warned.clear()
        try:
            _index = _SkinIndex(skin)
        except (OSError, ET.ParseError, ValueError) as e:
            log("SkinUtils", f"Could not read the skin's resolution folders: {e}", xbmc.LOGWARNING)
            _index = None
    return _index


def _mtime(path: str) -> float:
    """Modification time of a file, 0 when it is gone."""
    try:
        return os.path.getmtime(path)
    except OSError:
        return 0.0


def _parse_xml(data: bytes) -> ET.Element:
    """Parse skin XML as leniently as Kodi's TinyXML, which skips DTDs and keeps a stray `&`."""
    if data.startswith(codecs.BOM_UTF8):
        data = data[len(codecs.BOM_UTF8):]
    data = _DOCTYPE.sub(b"", _COMMENT.sub(b"", data))
    return ET.fromstring(_STRAY_AMPERSAND.sub(b"&amp;", data).lstrip())


def _res_folders(skin: str) -> Tuple[str, str]:
    """The skin's resolution folder closest to the screen, and its default folder."""
    folders = []
    with open(os.path.join(skin, "addon.xml"), "rb") as handle:
        root = _parse_xml(handle.read())
    for res in root.iter("res"):
        width, height = int(res.get("width") or 0), int(res.get("height") or 0)
        aspect = res.get("aspect") or ""
        num, _, den = aspect.partition(":")
        ratio = (float(num) / float(den) if num and den and float(den)
                 else width / height if height else 0.0)
        folders.append((res.get("folder") or "", ratio, height, res.get("default") == "true"))
    if not folders:
        return "", ""
    default = next((f for f in folders if f[3]), folders[0])[0]
    if len(folders) == 1:
        return default, default
    screen = read_labels(("System.ScreenWidth", "System.ScreenHeight"))
    width = int(screen["System.ScreenWidth"] or 0)
    height = int(screen["System.ScreenHeight"] or 0)
    target = width / height if height else 0.0
    closest = min(folders, key=lambda f: (abs(f[1] - target), abs(f[2] - height)))[0]
    return closest, default
