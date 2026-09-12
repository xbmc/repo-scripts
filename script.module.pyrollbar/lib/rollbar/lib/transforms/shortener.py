from array import array
import collections
import itertools
import reprlib

from collections.abc import Mapping
from typing import Union, Tuple

from rollbar.lib import (
    integer_types, key_in, key_depth, sequence_types,
    string_types)
from rollbar.lib.transform import Transform


_type_name_mapping = {
    'string': string_types,
    'long': integer_types,
    'mapping': Mapping,
    'list': list,
    'tuple': tuple,
    'set': set,
    'frozenset': frozenset,
    'array': array,
    'deque': collections.deque,
    'other': None
}


def _max_left_right(max_len: int, seperator_len: int) -> Tuple[int, int]:
    left = max(0, (max_len-seperator_len)//2)
    right = max(0, max_len-seperator_len-left)
    return left, right


def shorten_array(obj: array, max_len: int) -> array:
    if len(obj) <= max_len:
        return obj

    return obj[:max_len]


def shorten_bytes(obj: bytes, max_len: int) -> bytes:
    if len(obj) <= max_len:
        return obj

    return obj[:max_len]


def shorten_deque(obj: collections.deque, max_len: int) -> collections.deque:
    if len(obj) <= max_len:
        return obj

    return collections.deque(itertools.islice(obj, max_len))


def shorten_frozenset(obj: frozenset, max_len: int) -> frozenset:
    if len(obj) <= max_len:
        return obj

    return frozenset([elem for i, elem in enumerate(obj) if i < max_len] + ['...'])


def shorten_int(obj: int, max_len: int) -> Union[int, str]:
    s = repr(obj)
    if len(s) <= max_len:
        return obj

    left, right = _max_left_right(max_len, 3)
    return s[:left] + '...' + s[len(s)-right:]


def shorten_list(obj: list, max_len: int) -> list:
    if len(obj) <= max_len:
        return obj

    return obj[:max_len] + ['...']


def shorten_mapping(obj: Union[dict, Mapping], max_keys: int) -> dict:
    if len(obj) <= max_keys:
        return obj

    return {k: obj[k] for k in itertools.islice(obj.keys(), max_keys)}


def shorten_set(obj: set, max_len: int) -> set:
    if len(obj) <= max_len:
        return obj

    return set([elem for i, elem in enumerate(obj) if i < max_len] + ['...'])


def shorten_string(obj: str, max_len: int) -> str:
    if len(obj) <= max_len:
        return obj

    left, right = _max_left_right(max_len, 3)
    return obj[:left] + '...' + obj[len(obj)-right:]


def shorten_tuple(obj: tuple, max_len: int) -> tuple:
    if len(obj) <= max_len:
        return obj

    return obj[:max_len] + ('...',)


class ShortenerTransform(Transform):
    depth_first = False
    priority = 10

    def __init__(self, safe_repr=True, keys=None, **sizes):
        super(ShortenerTransform, self).__init__()
        self.safe_repr = safe_repr
        self.keys = keys
        self._repr = reprlib.Repr()

        for name, size in sizes.items():
            setattr(self._repr, name, size)

    def _get_max_size(self, obj):
        for name, _type in _type_name_mapping.items():
            # Special case for dicts since we are using collections.abc.Mapping
            # to provide better type checking for dict-like objects
            if name == 'mapping':
                name = 'dict'

            if _type and isinstance(obj, _type):
                return getattr(self._repr, 'max%s' % name)

        return self._repr.maxother

    def _shorten(self, val):
        max_size = self._get_max_size(val)

        if isinstance(val, array):
            return shorten_array(val, max_size)
        if isinstance(val, bytes):
            return shorten_bytes(val, max_size)
        if isinstance(val, collections.deque):
            return shorten_deque(val, max_size)
        if isinstance(val, (dict, Mapping)):
            return shorten_mapping(val, max_size)
        if isinstance(val, float):
            return val
        if isinstance(val, frozenset):
            return shorten_frozenset(val, max_size)
        if isinstance(val, int):
            return shorten_int(val, max_size)
        if isinstance(val, list):
            return shorten_list(val, max_size)
        if isinstance(val, set):
            return shorten_set(val, max_size)
        if isinstance(val, str):
            return shorten_string(val, max_size)
        if isinstance(val, tuple):
            return shorten_tuple(val, max_size)

        return self._shorten_other(val)

    def _shorten_other(self, obj):
        if obj is None:
            return None

        # If the object has a __rollbar_repr__() method, use it.
        custom = Transform.rollbar_repr(obj)
        if custom is not None:
            return custom

        if self.safe_repr:
            obj = str(obj)

        return self._repr.repr(obj)

    def _should_shorten(self, val, key):
        if not key:
            return False

        return key_in(key, self.keys)

    def _should_drop(self, val, key) -> bool:
        if not key:
            return False

        max_depth = key_depth(key, self.keys)
        if max_depth == 0:
            return False

        return (max_depth + self._repr.maxlevel) <= len(key)

    def default(self, o, key=None):
        if self._should_drop(o, key):
            if isinstance(o, (dict, Mapping)):
                return {'...': '...'}
            if isinstance(o, sequence_types):
                return ['...']

        if self._should_shorten(o, key):
            return self._shorten(o)

        return super(ShortenerTransform, self).default(o, key=key)


__all__ = ['ShortenerTransform']
