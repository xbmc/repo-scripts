# -*- coding: utf-8 -*-
"""Names as the viewer sees them (briefs/nfo-titles.md).

Title order, first that exists wins: Kodi's library title (callers pass it);
for files Kodi doesn't have, the <title> of the .nfo next to the file (or a
show folder's tvshow.nfo); otherwise the file name, cleaned so it reads like a
title.  On air, a trailing "(1993)" is left out (display only): the stored
data and the viewer's files never change.  No Kodi imports, so it can be
tested on its own; reading files goes through xbmcvfs when Kodi is there."""
import os
import re
import threading

try:
    import xbmcvfs
except Exception:                         # tests outside Kodi
    xbmcvfs = None

VIDEO_EXT = ("mkv", "mp4", "avi", "m4v", "mov", "wmv", "mpg", "mpeg", "ts", "m2ts", "mts", "webm", "flv",
             "vob", "iso", "strm", "divx", "ogm", "3gp")
_EXT = re.compile(r"\.(?:%s)$" % "|".join(VIDEO_EXT), re.I)
# release tags: resolution, codecs, audio, source, edition words; a "-GROUP" right after one goes too
_TAG = (r"2160p|1080p|1080i|720p|576[pi]|480[pi]|4k|uhd|hdr10\+?|hdr|sdr|x ?26[45]|h ?26[45]|hevc|avc|xvid|divx|"
        r"10 ?bit|aac(?: ?2 0)?|e?ac3|dts(?: ?hd)?(?: ?ma)?|truehd|atmos|ddp?(?: ?[257] [01])?|"
        r"blu ?ray|bdrip|brrip|bdremux|remux|web[ -]?dl|web[ -]?rip|hdtv|hdrip|dvdrip|dvdscr|"
        r"proper|repack|internal|complete")
_TAGS = re.compile(r"\b(?:%s)\b(?:-[A-Za-z0-9]{2,12}\b)?" % _TAG, re.I)
_BRACKETS = re.compile(r"\[[^\]]*\]|\{[^}]*\}")
_EPISODE = re.compile(r"\b[Ss](\d{1,2}) ?[Ee](\d{1,3})\b")
_YEAR_END = re.compile(r"^(.*?)\s*\(((?:19|20)\d\d)\)\s*$")
_BARE_YEAR_END = re.compile(r"^(.*?)\s+((?:19|20)\d\d)$")


def basename(path):
    """The last part of a path, whichever slashes it uses."""
    return re.split(r"[\\/]", (path or "").rstrip("/\\"))[-1]


def clean(name, show=""):
    """A file or folder name made readable: no extension, no dots or underscores
    between words, no release tags or bracketed ids ([zNKVcGFvfTA]); a year stays,
    as "(1993)".  show: the show it belongs to - then the result is the episode's
    name only (show name and S01E02 taken out), '' when nothing is left."""
    t = _EXT.sub("", (name or "").strip())
    t = _BRACKETS.sub(" ", t)
    t = t.replace("_", " ")
    t = re.sub(r"\.(?=\S)", " ", t)                 # scene style: The.Fugitive.1993 (but "Mr. Bean" stays)
    tagged = bool(_TAGS.search(t))
    t = _TAGS.sub(" ", t)
    t = re.sub(r"\s+", " ", t).strip(" -._")
    if show:
        m = _EPISODE.search(t)
        if m:
            t = t[m.end():]                         # the name after S01E02
        elif t.lower().startswith(show.lower()):
            t = t[len(show):]
        t = t.strip(" -._")
        return "" if _EPISODE.fullmatch(t or "x") else t
    m = _BARE_YEAR_END.match(t)
    if m and tagged:                                # The.Fugitive.1993.BluRay -> The Fugitive (1993)
        t = "%s (%s)" % (m.group(1), m.group(2))
    t = re.sub(r"\(\s*\)", "", t)
    return re.sub(r"\s+", " ", t).strip(" -._")


def split_year(title):
    """('Title', '1993') for 'Title (1993)'; (title, '') otherwise."""
    m = _YEAR_END.match(title or "")
    return (m.group(1).strip(), m.group(2)) if m else ((title or ""), "")


def on_air(title, keep=(), years=None):
    """The title as shown on air: a trailing '(1993)' left out (a year inside the
    title, 'Fantasia 2000', stays).  keep: lower-case names two shows share, which
    keep their years.  years: {show title lower: year} for a trailing bare year,
    removed only when it is the show's own year."""
    base, year = split_year(title)
    if year:
        return title if base.lower() in keep else base
    if years:
        m = _BARE_YEAR_END.match(title or "")
        if m and years.get((title or "").lower()) == m.group(2) and m.group(1).lower() not in keep:
            return m.group(1)
    return title or ""


def shared_names(titles):
    """Lower-case names that more than one title shares once its year is left out
    (two "Doctor Who"s): those keep their years on air."""
    seen = {}
    for t in titles:
        seen.setdefault(split_year(t)[0].lower(), set()).add(t)
    return set(k for k, v in seen.items() if len(v) > 1)


# ------------------------------------------------------------------ NFO titles
_NFO = {}                                 # nfo path -> (mtime, title); read once per file version
_LOCK = threading.Lock()
_LOGGED = set()


_DIRS = {}                                # folder -> (when listed, set of file names lower-case)
_DIR_TTL = 600


def _exists(path):
    """Is the file there?  From the folder's listing, read once every 10 minutes
    (a thousand commercials: one listing, not a thousand file checks)."""
    folder, name = re.split(r"[\\/](?=[^\\/]*$)", path)[0], basename(path)
    import time
    now = time.time()
    with _LOCK:
        hit = _DIRS.get(folder)
    if not hit or now - hit[0] > _DIR_TTL:
        try:
            if xbmcvfs is not None:
                files = xbmcvfs.listdir(folder + ("\\" if "\\" in folder and "/" not in folder else "/"))[1]
            else:
                files = [f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))]
        except Exception:
            files = []
        hit = (now, set(f.lower() for f in files))
        with _LOCK:
            _DIRS[folder] = hit
    return name.lower() in hit[1]


def _mtime(path):
    if not _exists(path):
        return None
    try:
        if xbmcvfs is not None:
            return xbmcvfs.Stat(path).st_mtime()
        return os.path.getmtime(path)
    except Exception:
        return None


def _read(path, limit=262144):
    try:
        if xbmcvfs is not None:
            f = xbmcvfs.File(path)
            try:
                data = f.readBytes(limit)
            finally:
                f.close()
        else:
            with open(path, "rb") as f:
                data = f.read(limit)
    except Exception:
        return ""
    if isinstance(data, (bytes, bytearray)):
        data = bytes(data).decode("utf-8", "replace")
    return (data or "").lstrip("﻿")


def _parse_title(text):
    """<title> of an NFO's XML; '' when there is none.  Raises ValueError for a
    broken file.  Kodi NFOs may have a scraper URL after the XML: ignored."""
    import xml.etree.ElementTree as ET
    m = re.search(r"<([A-Za-z]\w*)[\s>]", re.sub(r"<\?xml[^>]*\?>", "", text, count=1))
    if not m:
        raise ValueError("no XML")
    root = m.group(1)
    end = text.rfind("</%s>" % root)
    if end < 0:
        raise ValueError("no </%s>" % root)
    try:
        doc = ET.fromstring(text[text.find("<" + root):end + len(root) + 3])
    except ET.ParseError as exc:
        raise ValueError(str(exc))
    t = doc.findtext("title") or ""
    return " ".join(t.split())


def nfo_title(nfo_path, log=None):
    """<title> from an NFO file (read-only, cached by modification time); ''
    when the file isn't there, has no title or is broken (one log line)."""
    mt = _mtime(nfo_path)
    if mt is None:
        return ""
    with _LOCK:
        hit = _NFO.get(nfo_path)
        if hit and hit[0] == mt:
            return hit[1]
    try:
        title = _parse_title(_read(nfo_path))
    except ValueError as exc:
        title = ""
        if log and nfo_path not in _LOGGED:
            _LOGGED.add(nfo_path)
            log("NFO not readable, using the file name: %s (%s)" % (nfo_path, exc))
    with _LOCK:
        _NFO[nfo_path] = (mt, title)
    return title


def file_title(path, log=None):
    """A video's own NFO <title>, else its cleaned file name."""
    stem = re.sub(r"\.[^./\\]+$", "", path)
    return nfo_title(stem + ".nfo", log) or clean(basename(path))


def folder_title(folder, log=None):
    """A show folder's tvshow.nfo <title>, else its cleaned folder name."""
    sep = "\\" if "\\" in folder and "/" not in folder else "/"
    nfo = folder.rstrip("/\\") + sep + "tvshow.nfo"
    return nfo_title(nfo, log) or clean(basename(folder))


def episode_title(path, show, log=None):
    """An episode file's NFO <title>, else its name with the show and S01E02
    taken out ('' when nothing is left: the episode line is then left out)."""
    stem = re.sub(r"\.[^./\\]+$", "", path)
    return nfo_title(stem + ".nfo", log) or clean(basename(path), show=show or "x")
