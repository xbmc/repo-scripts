"""Unpack a SubDL download and choose the subtitle file(s) to hand to Kodi.

Most downloads are zip archives with one subtitle inside. Season packs hold one file
per episode, some archives hold a file per CD, and the single-file endpoint returns
the subtitle itself. Archives are read in memory, never extracted wholesale: only
the chosen files are written, under names this module makes safe.
"""

from __future__ import annotations

import codecs
import io
import os
import re
import zipfile
from dataclasses import dataclass
from typing import Callable, List, Optional, Sequence, Tuple

from . import languages, releases

#: Formats Kodi plays, best first when one archive offers the same subtitle twice.
SUBTITLE_FORMATS = (".srt", ".ass", ".ssa", ".vtt", ".smi", ".sami", ".sub", ".sup", ".txt", ".mpl")
MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_TOTAL_BYTES = 64 * 1024 * 1024
MAX_ENTRIES = 2000
_TIMING = re.compile(rb"\d\d:\d\d:\d\d[,.:]\d|\{\d+\}\{\d+\}|\[\d+\]\[\d+\]")
_CD = re.compile(r"(?:cd|disc|disk|part)[ ._-]?(\d)", re.I)
_UNSAFE = re.compile(r"[^\w\-. ()\[\]]+", re.U)
#: Text formats whose bytes may be re-encoded; .sub only when it is MicroDVD text.
_TEXT_FORMATS = (".srt", ".ass", ".ssa", ".vtt", ".smi", ".sami", ".txt", ".mpl")
_BOMS = (codecs.BOM_UTF8, codecs.BOM_UTF32_LE, codecs.BOM_UTF32_BE, codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)
#: The code page a subtitle in this language most likely uses when it is not UTF-8.
#: Kodi reads a file without a BOM in its own subtitle charset (Windows-1252 unless the
#: viewer changed it), so a Persian Windows-1256 file shows as "ÈÇíÏ" instead of "باید".
_LEGACY_CODEC = {
    "ar": "cp1256", "fa": "cp1256", "ur": "cp1256",
    "he": "cp1255", "el": "cp1253", "tr": "cp1254", "az": "cp1254",
    "ru": "cp1251", "uk": "cp1251", "bg": "cp1251", "be": "cp1251", "mk": "cp1251",
    "kk": "cp1251", "ky": "cp1251", "mn": "cp1251",
    "cs": "cp1250", "sk": "cp1250", "pl": "cp1250", "hu": "cp1250", "ro": "cp1250",
    "hr": "cp1250", "sl": "cp1250", "bs": "cp1250", "sq": "cp1250", "sr": "cp1250",
    "lt": "cp1257", "lv": "cp1257", "et": "cp1257",
    "vi": "cp1258", "th": "cp874", "ja": "cp932", "ko": "cp949", "zh": "gb18030",
    "en": "cp1252", "fr": "cp1252", "de": "cp1252", "es": "cp1252", "it": "cp1252",
    "pt": "cp1252", "pb": "cp1252", "nl": "cp1252", "da": "cp1252", "sv": "cp1252",
    "no": "cp1252", "fi": "cp1252", "ca": "cp1252", "eu": "cp1252", "gl": "cp1252",
    "id": "cp1252", "ms": "cp1252", "is": "cp1252", "ga": "cp1252", "tl": "cp1252",
}
#: SubDL codes whose script differs from the rest of their Kodi language.
_LEGACY_CODEC_BY_CODE = {"SR_CYRL": "cp1251", "ZH_BG": "big5"}
#: Windows-1256 has no Persian yeh or keheh; Persian files use the Arabic letters.
_PERSIAN_LETTERS = {0x064A: 0x06CC, 0x0643: 0x06A9}


class ArchiveError(Exception):
    """The download is not something this add-on can open."""


@dataclass
class SubtitleFile:
    name: str
    data: bytes
    #: The .idx that belongs to a VobSub .sub; Kodi loads it from beside the .sub.
    idx: Optional[bytes] = None

    @property
    def extension(self) -> str:
        return os.path.splitext(self.name)[1].lower()


def kind(data: bytes) -> str:
    """The archive type from the first bytes: zip, rar, 7z, or "" for a plain file."""
    if data[:4] in (b"PK\x03\x04", b"PK\x05\x06"):
        return "zip"
    if data[:4] == b"Rar!":
        return "rar"
    if data[:6] == b"7z\xbc\xaf\x27\x1c":
        return "7z"
    return ""


def looks_like_subtitle(data: bytes) -> bool:
    """A .txt is often a release note; keep it only if it carries subtitle timings."""
    return bool(_TIMING.search(data[:65536]))


def files_in(data: bytes, name: str = "", fallback_format: str = "srt") -> List[SubtitleFile]:
    """Every subtitle file in a download, which may be an archive or the file itself."""
    detected = kind(data)
    if detected == "zip":
        return _from_zip(data, depth=0)
    if detected:
        raise ArchiveError("%s archives are not supported" % detected)
    extension = os.path.splitext(name)[1].lower()
    if extension not in SUBTITLE_FORMATS:
        name = "subtitle.%s" % (fallback_format or "srt").lstrip(".").lower()
        extension = os.path.splitext(name)[1].lower()
    if extension not in SUBTITLE_FORMATS or not data.strip():
        raise ArchiveError("not a subtitle file")
    return [SubtitleFile(safe_name(name), data)]


def _from_zip(data: bytes, depth: int) -> List[SubtitleFile]:
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except (zipfile.BadZipFile, zipfile.LargeZipFile, ValueError) as error:
        raise ArchiveError("broken zip archive") from error
    found: List[SubtitleFile] = []
    idx_files = {}
    total = 0
    with archive:
        for info in archive.infolist()[:MAX_ENTRIES]:
            if info.is_dir() or info.flag_bits & 0x1:  # folders and encrypted entries
                continue
            base = info.filename.replace("\\", "/").rsplit("/", 1)[-1]
            extension = os.path.splitext(base)[1].lower()
            wanted = extension in SUBTITLE_FORMATS or extension == ".idx" or (extension == ".zip" and depth == 0)
            if not wanted or base.startswith(".") or info.file_size > MAX_FILE_BYTES:
                continue
            content = _read_entry(archive, info)
            if content is None:
                continue
            total += len(content)
            if total > MAX_TOTAL_BYTES:
                break
            if extension == ".zip":
                try:
                    found.extend(_from_zip(content, depth + 1))
                except ArchiveError:
                    pass
            elif extension == ".idx":
                idx_files[os.path.splitext(base)[0].lower()] = content
            elif extension != ".txt" or looks_like_subtitle(content):
                found.append(SubtitleFile(safe_name(base), content))
    for subtitle in found:
        if subtitle.extension == ".sub":
            subtitle.idx = idx_files.get(os.path.splitext(subtitle.name)[0].lower())
    return found


def _read_entry(archive: zipfile.ZipFile, info: zipfile.ZipInfo) -> Optional[bytes]:
    """The entry's bytes, or None when it is unreadable or bigger than it claimed."""
    try:
        with archive.open(info) as handle:
            content = handle.read(MAX_FILE_BYTES + 1)
    except (zipfile.BadZipFile, NotImplementedError, RuntimeError, OSError, EOFError, ValueError):
        return None
    return content if len(content) <= MAX_FILE_BYTES else None


def safe_name(name: str) -> str:
    """A file name that stays inside the folder it is written to, on every system."""
    base = (name or "").replace("\\", "/").rsplit("/", 1)[-1]
    stem, extension = os.path.splitext(base)
    stem = _UNSAFE.sub("_", stem).strip(" ._")[:120] or "subtitle"
    extension = _UNSAFE.sub("", extension.lower())[:8]
    return stem + extension


def _format_rank(subtitle: SubtitleFile) -> int:
    try:
        return SUBTITLE_FORMATS.index(subtitle.extension)
    except ValueError:
        return len(SUBTITLE_FORMATS)


def for_episode(files: Sequence[SubtitleFile], season: Optional[int], episode: int) -> List[SubtitleFile]:
    """The files that belong to an episode, surest first. Files that name another
    episode are dropped; when no name says anything, every file is kept."""
    scored = [(releases.episode_match(item.name, season, episode), item) for item in files]
    best = max((strength for strength, _ in scored), default=0)
    if best > 0:
        return [item for strength, item in scored if strength == best]
    return [item for strength, item in scored if strength == 0]


def cd_parts(files: Sequence[SubtitleFile]) -> List[SubtitleFile]:
    """CD1, CD2, ... files in order when the archive is one subtitle per disc, else []."""
    numbered = []
    for item in files:
        match = _CD.search(item.name)
        if not match:
            return []
        numbered.append((int(match.group(1)), _format_rank(item), item))
    numbers = sorted({number for number, _, _ in numbered})
    if len(numbers) < 2 or numbers != list(range(numbers[0], numbers[0] + len(numbers))):
        return []
    chosen = {}
    for number, rank, item in sorted(numbered, key=lambda entry: (entry[0], entry[1])):
        chosen.setdefault(number, item)
    return [chosen[number] for number in numbers]


def choose(files: Sequence[SubtitleFile], video: str = "",
           target: Optional[Tuple[Optional[int], int]] = None, stacked: bool = False,
           ask: Optional[Callable[[List[str]], int]] = None) -> List[SubtitleFile]:
    """The file(s) to give Kodi, or [] when there is none or the viewer cancels.

    For an episode only that episode's files count. Several CD parts go to a
    stacked video in order. Otherwise the file whose name is closest to the video
    wins; when no name tells them apart, ``ask`` lets the viewer choose.
    """
    candidates = list(files)
    if target is not None:
        candidates = for_episode(candidates, target[0], target[1])
    if not candidates:
        return []
    if stacked:
        parts = cd_parts(candidates)
        if parts:
            return parts
    if len(candidates) == 1:
        return candidates
    ranked = sorted(candidates, key=lambda item: (-releases.score(video, item.name), _format_rank(item), item.name))
    top, runner_up = ranked[0], ranked[1]
    same_subtitle = os.path.splitext(top.name)[0] == os.path.splitext(runner_up.name)[0]
    if releases.score(video, top.name) > releases.score(video, runner_up.name) or same_subtitle:
        return [top]
    if ask is None:
        return [top]
    picked = ask([item.name for item in ranked])
    return [ranked[picked]] if 0 <= picked < len(ranked) else []


def is_text(subtitle: SubtitleFile) -> bool:
    """True for a text subtitle; VobSub .sub/.idx and .sup pictures are binary."""
    if subtitle.extension == ".sub":
        return subtitle.idx is None and looks_like_subtitle(subtitle.data)
    return subtitle.extension in _TEXT_FORMATS


def as_utf8(data: bytes, language: str) -> bytes:
    """UTF-8 bytes (with a BOM, so every Kodi reads them as UTF-8) for a text subtitle
    in its language's legacy code page. Files that are already UTF-8 or carry a BOM,
    and files in a language without one likely code page, are returned unchanged."""
    if data.startswith(_BOMS):
        return data
    try:
        data.decode("utf-8")
        return data
    except UnicodeDecodeError:
        pass
    code = languages.normalise(language)
    codec = _LEGACY_CODEC_BY_CODE.get(code) or _LEGACY_CODEC.get(languages.iso_for(code))
    if not codec:
        return data
    try:
        text = data.decode(codec)
    except UnicodeDecodeError:
        return data
    if languages.iso_for(code) == "fa":
        text = text.translate(_PERSIAN_LETTERS)
    return codecs.BOM_UTF8 + text.encode("utf-8")


def write(subtitle: SubtitleFile, folder: str, language: str = "") -> str:
    """Write a chosen file (and its .idx) into ``folder``; returns the subtitle's path.

    A text subtitle that is not UTF-8 is converted from ``language``'s code page.
    """
    path = os.path.join(folder, subtitle.name)
    data = as_utf8(subtitle.data, language) if is_text(subtitle) else subtitle.data
    with open(path, "wb") as handle:
        handle.write(data)
    if subtitle.idx is not None:
        with open(os.path.splitext(path)[0] + ".idx", "wb") as handle:
            handle.write(subtitle.idx)
    return path
