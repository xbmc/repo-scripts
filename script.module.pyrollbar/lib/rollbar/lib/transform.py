from __future__ import annotations
from os import PathLike
from typing import TypeVar, TYPE_CHECKING

if TYPE_CHECKING:
    from rollbar.lib.type_info import KeyType

T = TypeVar('T')

class Transform(object):
    depth_first: bool = True
    priority: int = 100

    def default(self, o: T, key: tuple[KeyType, ...]|None = None) -> T:
        return o

    def transform_circular_reference(self, o, key: tuple[KeyType, ...]|None = None, ref_key=None):
        # By default, we just perform a no-op for circular references.
        # Subclasses should implement this method to return whatever representation
        # for the circular reference they need.
        return self.default(o, key=key)

    def transform_tuple(self, o: tuple, key: tuple[KeyType, ...]|None = None) -> tuple:
        return self.default(o, key=key)

    def transform_namedtuple(self, o, key: tuple[KeyType, ...]|None = None):
        return self.default(o, key=key)

    def transform_list(self, o, key: tuple[KeyType, ...]|None = None):
        return self.default(o, key=key)

    def transform_dict(self, o: dict, key: tuple[KeyType, ...]|None = None) -> dict:
        return self.default(o, key=key)

    def transform_number(self, o: float | int, key: tuple[KeyType, ...]|None = None) -> float | int | str:
        return self.default(o, key=key)

    def transform_bytes(self, o: bytes, key: tuple[KeyType, ...]|None = None) -> bytes | str:
        return self.default(o, key=key)

    def transform_unicode(self, o: str, key: tuple[KeyType, ...]|None = None) -> str:
        return self.default(o, key=key)

    def transform_boolean(self, o: bool, key: tuple[KeyType, ...]|None = None) -> bool:
        return self.default(o, key=key)

    def transform_path(self, o: PathLike, key: tuple[KeyType, ...]|None = None) -> str:
        return self.default(str(o), key=key)

    def transform_custom(self, o: T, key: tuple[KeyType, ...]|None = None) -> T:
        return self.default(o, key=key)

    @staticmethod
    def rollbar_repr(obj: object) -> str | None:
        r = None
        if hasattr(obj, '__rollbar_repr__'):
            r = obj.__rollbar_repr__()
            if not isinstance(r, str):
                raise TypeError(f'__rollbar_repr__ returned non-string (type {type(r)})')
        return r
