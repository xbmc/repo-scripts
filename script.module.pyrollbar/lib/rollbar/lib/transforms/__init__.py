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

_ALLOWED_CIRCULAR_REFERENCE_TYPES = [binary_type, bool, type(None)]

if isinstance(string_types, tuple):
    _ALLOWED_CIRCULAR_REFERENCE_TYPES.extend(string_types)
else:
    _ALLOWED_CIRCULAR_REFERENCE_TYPES.append(string_types)

if isinstance(number_types, tuple):
    _ALLOWED_CIRCULAR_REFERENCE_TYPES.extend(number_types)
else:
    _ALLOWED_CIRCULAR_REFERENCE_TYPES.append(number_types)

_ALLOWED_CIRCULAR_REFERENCE_TYPES = tuple(_ALLOWED_CIRCULAR_REFERENCE_TYPES)


def transform(obj, transforms, key=None, batch_transforms=False):
    if isinstance(transforms, Transform):
        transforms = [transforms]

    if batch_transforms:
        transforms = [BatchedTransform(transforms)]

    for transform in transforms:
        if not isinstance(transform, Transform):
            continue
        obj = _transform(obj, transform, key=key)

    return obj


def _transform(obj, transform, key=None):
    key = key or ()

    def do_transform(type_name, val, key=None, **kw):
        fn = getattr(transform, "transform_%s" % type_name, transform.transform_custom)
        val = fn(val, key=key, **kw)

        return val

    def string_handler(s, key=None):
        if isinstance(s, bytes):
            return do_transform("bytes", s, key=key)
        elif isinstance(s, str):
            return do_transform("unicode", s, key=key)

    def default_handler(o, key=None):
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

    handlers = {
        "string_handler": string_handler,
        "tuple_handler": lambda o, key=None: do_transform("tuple", o, key=key),
        "namedtuple_handler": lambda o, key=None: do_transform(
            "namedtuple", o, key=key
        ),
        "list_handler": lambda o, key=None: do_transform("list", o, key=key),
        "set_handler": lambda o, key=None: do_transform("set", o, key=key),
        "mapping_handler": lambda o, key=None: do_transform("dict", o, key=key),
        "path_handler": lambda o, key=None: do_transform("path", o, key=key),
        "circular_reference_handler": lambda o, key=None, ref_key=None: do_transform(
            "circular_reference", o, key=key, ref_key=ref_key
        ),
        "default_handler": default_handler,
        "allowed_circular_reference_types": _ALLOWED_CIRCULAR_REFERENCE_TYPES,
    }

    return traverse.traverse(obj, key=key, depth_first=transform.depth_first, **handlers)


__all__ = ["transform", "Transform"]
