from __future__ import annotations
from typing import Callable, TypedDict, Any, TYPE_CHECKING
from collections.abc import Iterable

from rollbar.lib import (
    binary_type,
    string_types,
    number_types,
    traverse,
)
# NOTE: Don't remove this import, it would cause a breaking change to the library's API.
# The `Transform` class was moved out of this file to prevent a cyclical dependency issue.
from rollbar.lib.transform import Transform
from rollbar.lib.transforms.batched import BatchedTransform

if TYPE_CHECKING:
    from rollbar.lib.type_info import KeyType

_ALLOWED_CIRCULAR_REFERENCE_TYPES: tuple = (binary_type, bool, type(None))

if isinstance(string_types, tuple):
    _ALLOWED_CIRCULAR_REFERENCE_TYPES = (*_ALLOWED_CIRCULAR_REFERENCE_TYPES, *string_types)
else:
    _ALLOWED_CIRCULAR_REFERENCE_TYPES = (*_ALLOWED_CIRCULAR_REFERENCE_TYPES, string_types)

if isinstance(number_types, tuple):
    _ALLOWED_CIRCULAR_REFERENCE_TYPES = (*_ALLOWED_CIRCULAR_REFERENCE_TYPES, *number_types)
else:
    _ALLOWED_CIRCULAR_REFERENCE_TYPES = (*_ALLOWED_CIRCULAR_REFERENCE_TYPES, number_types)

_ALLOWED_CIRCULAR_REFERENCE_TYPES = tuple(_ALLOWED_CIRCULAR_REFERENCE_TYPES)


class Handlers(TypedDict, total=False):
    string_handler: Callable[[Any, Any | None], Any]
    tuple_handler: Callable[[Any, Any | None], Any]
    namedtuple_handler: Callable[[Any, Any | None], Any]
    list_handler: Callable[[Any, Any | None], Any]
    set_handler: Callable[[Any, Any | None], Any]
    mapping_handler: Callable[[Any, Any | None], Any]
    path_handler: Callable[[Any, Any | None], Any]
    circular_reference_handler: Callable[[Any, Any | None], Any]
    default_handler: Callable[[Any, Any | None], Any]
    allowed_circular_reference_types: tuple | None


def transform(obj, transforms: Transform | list[Transform], key: tuple[KeyType, ...] | None = None, batch_transforms: bool = False):
    if isinstance(transforms, Transform):
        transforms = [transforms]

    if batch_transforms:
        transforms = [BatchedTransform(transforms)]

    for transform in transforms:
        if not isinstance(transform, Transform):
            continue
        obj = _transform(obj, transform, key=key)

    return obj


def _transform(obj: Any, transform: Transform, key: tuple[KeyType, ...] | None = None) -> Any:
    key = key or ()

    def do_transform(type_name: str, val: Any, key: tuple[KeyType, ...] | None = None, **kw) -> Any:
        fn = getattr(transform, "transform_%s" % type_name, transform.transform_custom)
        val = fn(val, key=key, **kw)

        return val

    def string_handler(s: str | bytes, key: tuple[KeyType, ...] | None = None):
        if isinstance(s, bytes):
            return do_transform("bytes", s, key=key)
        # Otherwise it's a string
        return do_transform("unicode", s, key=key)

    def tuple_handler(o: Any, key: tuple[KeyType, ...] | None = None) -> Any:
        return do_transform("tuple", o, key=key)

    def namedtuple_handler(o: Any, key: tuple[KeyType, ...] | None = None) -> Any:
        return do_transform("namedtuple", o, key=key)

    def list_handler(o: Any, key: tuple[KeyType, ...] | None = None) -> Any:
        return do_transform("list", o, key=key)

    def set_handler(o: Any, key: tuple[KeyType, ...] | None = None) -> Any:
        return do_transform("set", o, key=key)

    def mapping_handler(o: Any, key: tuple[KeyType, ...] | None = None) -> Any:
        return do_transform("dict", o, key=key)

    def path_handler(o: Any, key: tuple[KeyType, ...] | None = None) -> Any:
        return do_transform("path", o, key=key)

    def circular_reference_handler(
            o: Any,
            key: tuple[KeyType, ...] | None = None,
            ref_key: Any | None = None,
    ) -> Any:
        return do_transform("circular_reference", o, key=key, ref_key=ref_key)

    def default_handler(o, key: tuple[KeyType, ...] | None = None):
        if isinstance(o, bool):
            return do_transform("boolean", o, key=key)

        # There is a quirk in the current version (1.1.6) of the enum
        # backport enum34 which causes it to not have the same
        # behavior as Python 3.4+. One way to identify IntEnums is that
        # they are instances of numbers but not number types.
        if isinstance(o, number_types):
            if type(o) not in number_types:
                return do_transform("custom", o, key=key)
            else:
                return do_transform("number", o, key=key)

        return do_transform("custom", o, key=key)

    handlers: Handlers = {
        "string_handler": string_handler,
        "tuple_handler": tuple_handler,
        "namedtuple_handler": namedtuple_handler,
        "list_handler": list_handler,
        "set_handler": set_handler,
        "mapping_handler": mapping_handler,
        "path_handler": path_handler,
        "circular_reference_handler": circular_reference_handler,
        "default_handler": default_handler,
        "allowed_circular_reference_types": _ALLOWED_CIRCULAR_REFERENCE_TYPES,
    }

    return traverse.traverse(obj, key=key, depth_first=transform.depth_first, **handlers)


__all__ = ["transform", "Transform"]
