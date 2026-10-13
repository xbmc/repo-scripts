# -*- coding: utf-8 -*-
"""Where a game's manual is, or would go.

A manual sits beside its game, or in a "manuals" folder next to it, named like
the game with a document's extension. Collections rarely name the two exactly
alike - "Sonic The Hedgehog 2 (World) (Rev A).md" against "Sonic The Hedgehog 2
(World).pdf" - so names are also compared with their bracketed tags removed.

Paths are Kodi's, which may be URLs, so they are joined with "/" and never
handed to os.path. Nothing here touches the filesystem: listing a folder is
the caller's job, passed in, so this can be tested without Kodi.
"""

import re
import zlib

#: Preferred first: a PDF is one file with real pages, where a comic archive is
#: a bag of images ordered by name
EXTENSIONS = (".pdf", ".cbz", ".cbr")

#: Where a manual is kept if not beside the game. Both spellings, because
#: collections use the capitalised one and a case-sensitive filesystem makes it
#: a different folder.
SUBFOLDERS = ("manuals", "Manuals")

#: What opens and closes a tag in a file name; PC-8801 sets put a game's
#: start-up settings in braces, as in "177 {V1 mode}.d88"
OPENERS = "([{"
CLOSERS = ")]}"

#: Protocols that address something other than a folder of files, so a game
#: reached through one has nowhere for a manual to sit beside it
NO_FOLDER = ("http://", "https://", "zip://", "rar://", "archive://", "pdf://", "plugin://")


def folder_of(path):
    """The folder a path is in, with its trailing slash."""
    index = max(path.rfind("/"), path.rfind("\\"))
    return path[:index + 1] if index >= 0 else ""


def name_of(path):
    """A path's last part."""
    trimmed = path.rstrip("/\\")
    index = max(trimmed.rfind("/"), trimmed.rfind("\\"))
    return trimmed[index + 1:]


def stem_of(path):
    """A file's name without its extension."""
    name = name_of(path)
    dot = name.rfind(".")
    return name[:dot] if dot > 0 else name


def extension_of(path):
    name = name_of(path)
    dot = name.rfind(".")
    return name[dot:].lower() if dot > 0 else ""


def join(folder, name):
    return folder + name if folder.endswith(("/", "\\")) else folder + "/" + name


def can_have_manual(game_path):
    """Whether there is a folder a manual could sit in beside this game."""
    if not game_path or game_path.lower().startswith(NO_FOLDER):
        return False
    # Without an extension, replacing it would invent a name the player never chose
    return bool(extension_of(game_path))


def normalise(name):
    """A name reduced so that two spellings of one title compare equal.

    Lowercased, with bracketed tags and the punctuation around them dropped.
    """
    depth = 0
    kept = []
    for c in name:
        if c in OPENERS:
            depth += 1
            kept.append(" ")
        elif c in CLOSERS:
            depth = max(depth - 1, 0)
            kept.append(" ")
        elif depth == 0:
            kept.append(c)
    return " ".join(re.findall(r"[^\W_]+", "".join(kept).lower()))


def display_title(game_path):
    """A game's name as a person would write it, from its file name.

    The file's bracketed tags go, so "Super Mario Bros. (USA, Europe).nes"
    reads "Super Mario Bros.".
    """
    stem = stem_of(game_path)
    depth = 0
    kept = []
    for c in stem:
        if c in OPENERS:
            depth += 1
        elif c in CLOSERS:
            depth = max(depth - 1, 0)
        elif depth == 0:
            kept.append(c)
    title = " ".join("".join(kept).split()).strip(" -_,")
    return title or stem


def title_for(game_path, given):
    """The title to show for a game, preferring the one a caller passed.

    Kodi gives a game outside a library its file name as its title, which
    reads better with its tags taken off.
    """
    if given and given not in (name_of(game_path), stem_of(game_path)):
        return given
    return display_title(game_path)


def parse_args(args):
    """RunScript's arguments: game=, title= and manual=, or the game then the manual bare.

    Kodi's $ESCINFO[] quotes a value as name="value", which survives commas and
    brackets in a game's name, and Kodi hands it over unquoted.
    """
    named = {"game": "", "title": "", "manual": ""}
    bare = []
    for arg in args:
        key, sep, value = arg.partition("=")
        if sep and key in named:
            named[key] = value
        elif arg:
            bare.append(arg)
    for key, value in zip(("game", "manual"), bare):
        named[key] = named[key] or value
    return named


def folders_for(game_path):
    """The folders a game's manual may be in, best first."""
    folder = folder_of(game_path)
    return [folder] + [join(folder, sub) + "/" for sub in SUBFOLDERS]


def exact_candidates(game_path):
    """Every path the manual would have if named exactly like the game, best first."""
    if not can_have_manual(game_path):
        return []
    stem = stem_of(game_path)
    return [join(folder, stem + extension) for folder in folders_for(game_path) for extension in EXTENSIONS]


def find(game_path, exists, listdir):
    """The game's manual, or "".

    exists(path) says whether a file is there; listdir(folder) gives the names
    of the files in a folder, or nothing if it cannot be read.
    """
    for candidate in exact_candidates(game_path):
        if exists(candidate):
            return candidate
    if not can_have_manual(game_path):
        return ""
    # Nothing matched exactly, so the folders are read and a manual whose name
    # differs only by its region and revision tags is accepted
    wanted = normalise(stem_of(game_path))
    if not wanted:
        return ""
    for folder in folders_for(game_path):
        names = listdir(folder) or []
        for extension in EXTENSIONS:
            for name in sorted(names):
                if extension_of(name) == extension and normalise(stem_of(name)) == wanted:
                    return join(folder, name)
    return ""


def fetched_extension(url):
    """The extension a manual fetched from this address is saved with."""
    extension = extension_of(url.split("?", 1)[0].split("#", 1)[0])
    return extension if extension in EXTENSIONS else ".pdf"


def profile_name(game_path, extension=".pdf"):
    """What a game's manual is called in the profile, where games from every
    folder share one, so two games with one name don't share a manual."""
    return "%s_%08x%s" % (stem_of(game_path), zlib.crc32(game_path.encode("utf-8")), extension)


def download_target(game_path, existing_folders, extension=".pdf"):
    """Where a fetched manual for this game is written, or "" if nowhere beside it.

    The "manuals" folder beside the game, which the lookup already searches, so
    a fetched manual is found the way one put there by hand would be. The
    capitalised spelling is used if that is the one already there.
    """
    if not can_have_manual(game_path):
        return ""
    folder = folder_of(game_path)
    sub = next((s for s in SUBFOLDERS if s in existing_folders), SUBFOLDERS[0])
    return join(join(folder, sub), stem_of(game_path) + extension)
