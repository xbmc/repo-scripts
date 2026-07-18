from __future__ import annotations

import logging
from os import PathLike
from pathlib import Path
from typing import Any, NamedTuple, Callable

from rollbar.lib import circular_reference_label

# NOTE: Don't remove this line of code as it would cause a breaking change
# to the library's API. The items imported here were originally in this file
# but were moved to a new file for easier use elsewhere.
from rollbar.lib.type_info import (
    get_type,
    CIRCULAR,
    DEFAULT,
    MAPPING,
    TUPLE,
    NAMEDTUPLE,
    LIST,
    SET,
    STRING,
    PATH,
    KeyType,
)


log = logging.getLogger(__name__)


def _noop_circular(a, **kw) -> str:
    return circular_reference_label(a, ref_key=kw.get("ref_key"))


def _noop(a: Any, **_) -> Any:
    return a


def _noop_tuple(a: tuple, **_) -> tuple:
    return tuple(a)


def _noop_namedtuple(a: NamedTuple, **_) -> NamedTuple:
    return a._make(a)


def _noop_list(a: list, **_) -> list:
    return list(a)


def _noop_set(a: set, **_) -> set:
    return set(a)


def _noop_mapping(a, **_) -> dict:
    return dict(a)


def _noop_path(a: PathLike, **_) -> PathLike:
    return Path(a)

# A generic handler: accepts arbitrary args/kwargs and returns Any.
Handler = Callable[..., Any]


_default_handlers: dict[int, Handler] = {
    CIRCULAR: _noop_circular,
    DEFAULT: _noop,
    STRING: _noop,
    TUPLE: _noop_tuple,
    NAMEDTUPLE: _noop_namedtuple,
    LIST: _noop_list,
    SET: _noop_set,
    PATH: _noop_path,
    MAPPING: _noop_mapping,
}


def traverse(
    obj: Any,
    key: tuple[KeyType, ...] = (),
    string_handler: Handler = _default_handlers[STRING],
    tuple_handler: Handler = _default_handlers[TUPLE],
    namedtuple_handler: Handler = _default_handlers[NAMEDTUPLE],
    list_handler: Handler = _default_handlers[LIST],
    set_handler: Handler = _default_handlers[SET],
    mapping_handler: Handler = _default_handlers[MAPPING],
    path_handler: Handler = _default_handlers[PATH],
    default_handler: Handler = _default_handlers[DEFAULT],
    circular_reference_handler: Handler = _default_handlers[CIRCULAR],
    allowed_circular_reference_types: type | tuple[type, ...] | None = None,
    memo: dict[int, tuple[KeyType, ...]] | None = None,
    depth_first: bool = True,
    **custom_handlers: Handler,
) -> Any:
    memo = memo or {}
    obj_id = id(obj)
    obj_type = get_type(obj)

    ref_key = memo.get(obj_id)
    if ref_key:
        if not allowed_circular_reference_types or not isinstance(
            obj, allowed_circular_reference_types
        ):
            return circular_reference_handler(obj, key=key, ref_key=ref_key)

    memo[obj_id] = key

    kw: dict[str, Any] = {
        "string_handler": string_handler,
        "tuple_handler": tuple_handler,
        "namedtuple_handler": namedtuple_handler,
        "list_handler": list_handler,
        "set_handler": set_handler,
        "mapping_handler": mapping_handler,
        "path_handler": path_handler,
        "default_handler": default_handler,
        "circular_reference_handler": circular_reference_handler,
        "allowed_circular_reference_types": allowed_circular_reference_types,
        "memo": memo,
        "depth_first": depth_first,
    }
    kw.update(custom_handlers)

    try:
        if obj_type is STRING:
            return string_handler(obj, key=key)
        elif obj_type is TUPLE:
            if depth_first:
                return tuple_handler(
                    tuple(
                        traverse(elem, key=key + (i,), **kw) for i, elem in enumerate(obj)
                    ),
                    key=key,
                )
            # Breadth first
            return tuple(traverse(elem, key=key + (i,), **kw) for i, elem in enumerate(tuple_handler(obj, key=key)))
        elif obj_type is NAMEDTUPLE:
            if depth_first:
                return namedtuple_handler(
                    obj._make(
                        traverse(v, key=key + (k,), **kw)
                        for k, v in obj._asdict().items()
                    ),
                    key=key,
                )
            # Breadth first
            return obj._make(traverse(v, key=key + (k,), **kw) for k, v in namedtuple_handler(obj, key=key)._asdict().items())
        elif obj_type is LIST:
            if depth_first:
                return list_handler(
                    [traverse(elem, key=key + (i,), **kw) for i, elem in enumerate(obj)],
                    key=key,
                )
            # Breadth first
            return [traverse(elem, key=key + (i,), **kw) for i, elem in enumerate(list_handler(obj, key=key))]
        elif obj_type is SET:
            if depth_first:
                return set_handler(
                    {traverse(elem, key=key + (i,), **kw) for i, elem in enumerate(obj)},
                    key=key,
                )
            # Breadth first
            return {traverse(elem, key=key + (i,), **kw) for i, elem in enumerate(set_handler(obj, key=key))}
        elif obj_type is MAPPING:
            if depth_first:
                return mapping_handler(
                    {k: traverse(v, key=key + (k,), **kw) for k, v in obj.items()},
                    key=key,
                )
            # Breadth first
            return {k: traverse(v, key=key + (k,), **kw) for k, v in mapping_handler(obj, key=key).items()}
        elif obj_type is PATH:
            return path_handler(obj, key=key)
        elif obj_type is DEFAULT:
            for handler_type, handler in (custom_handlers or {}).items():
                # Check the full module path first e.g. "my_module.MyClass" or "builtin.complex"
                if f"{type(obj).__module__}.{type(obj).__name__}" == handler_type:
                    return handler(obj, key=key)
                # Fallback to just the name e.g. "MyClass" or "complex".
                if type(obj).__name__ == handler_type:
                    return handler(obj, key=key)
    except:
        # use the default handler for unknown object types
        log.debug(
            "Exception while traversing object using type-specific "
            "handler. Switching to default handler.",
            exc_info=True,
        )

    return default_handler(obj, key=key)


__all__ = ["traverse"]
