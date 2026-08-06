import re
from typing import Any, List


# Characters to replace in song keys
_KEY_REPLACE_RE = re.compile(r"[^\w'`.]+")


class Song:
    """Song metadata.

    Parameters
    ----------
    duration
        Song length in seconds.
    cover
        URL for the cover image.
    slides
        URLs for slideshow images.
    """

    def __init__(
            self,
            artist: str,
            title: str,
            album: str,
            year: int,
            duration: int,
            cover: str,
            slides: List[str],
            rating: float) -> None:
        self.artist = artist
        self.title = title
        self.album = album
        self.year = year
        self.duration = duration
        self.cover = cover
        self.slides = slides
        self.rating = rating
        self.key = SongKey(artist, title)

    def __str__(self) -> str:
        return f'{self.artist} - {self.title}'


class SongKey:
    """Enables more reliable matching between stream and API metadata.

    A few songs in the RP library (mostly classical music) format artist and
    title differently in stream and API metadata, needing "fuzzy" matching.

    Notes
    -----
    The `bool()` value for empty keys is ``False``, otherwise ``True``.
    """

    def __init__(self, *args: str) -> None:
        """
        Parameters
        ----------
        *args
            Passing no strings or empty strings creates an empty key.
        """
        words = []
        for s in args:
            if not isinstance(s, str):
                raise ValueError(f'Not a string: {s}')
            words.extend(_KEY_REPLACE_RE.sub(' ', s).casefold().split())
        self._key = tuple(sorted(words))

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, SongKey):
            return self._key == other._key
        else:
            return False

    def __bool__(self) -> bool:
        return bool(self._key)

    def __hash__(self) -> int:
        return hash(self._key)

    def __repr__(self) -> str:
        return str(self._key)
