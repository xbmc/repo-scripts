from rollbar.lib.transform import Transform
from rollbar.lib import (
    number_types,
    type_info,
)


def do_transform(transform, type_name, val, key=None, **kw):
    fn = getattr(transform, "transform_%s" % type_name, transform.transform_custom)
    val = fn(val, key=key, **kw)

    return val


def string_handler(transform, s, key=None):
    if isinstance(s, bytes):
        return do_transform(transform, "bytes", s, key=key)
    elif isinstance(s, str):
        return do_transform(transform, "unicode", s, key=key)


def default_handler(transform, o, key=None):
    if isinstance(o, bool):
        return do_transform(transform, "boolean", o, key=key)

    # There is a quirk in the current version (1.1.6) of the enum
    # backport enum34 which causes it to not have the same
    # behavior as Python 3.4+. One way to identify IntEnums is that
    # they are instances of numbers but not number types.
    if isinstance(o, number_types):
        if type(o) not in number_types:
            return do_transform(transform, "custom", o, key=key)
        else:
            return do_transform(transform, "number", o, key=key)

    return do_transform(transform, "custom", o, key=key)


handlers = {
    type_info.STRING: string_handler,
    type_info.TUPLE: lambda transform, o, key=None: do_transform(
        transform, "tuple", o, key=key
    ),
    type_info.NAMEDTUPLE: lambda transform, o, key=None: do_transform(
        transform, "namedtuple", o, key=key
    ),
    type_info.LIST: lambda transform, o, key=None: do_transform(
        transform, "list", o, key=key
    ),
    type_info.SET: lambda transform, o, key=None: do_transform(
        transform, "set", o, key=key
    ),
    type_info.MAPPING: lambda transform, o, key=None: do_transform(
        transform, "dict", o, key=key
    ),
    type_info.CIRCULAR: lambda transform, o, key=None, ref_key=None: do_transform(
        transform, "circular_reference", o, key=key, ref_key=ref_key
    ),
    type_info.DEFAULT: default_handler,
}


class BatchedTransform(Transform):
    def __init__(self, transforms):
        super(BatchedTransform, self).__init__()
        self._transforms = transforms

    def default(self, o, key=None):
        for transform in self._transforms:
            node_type = type_info.get_type(o)
            handler = handlers.get(node_type, handlers.get(type_info.DEFAULT))
            o = handler(transform, o, key=key)

        return o


__all__ = ["BatchedTransform"]
