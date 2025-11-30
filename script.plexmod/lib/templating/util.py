# coding=utf-8
import ibis.context

from ibis.context import ContextDict
from six.moves import collections_abc as collections


def register_builtin(nameorfunc):
    if callable(nameorfunc):
        ibis.context.builtins[nameorfunc.__name__] = nameorfunc
        return nameorfunc

    def register_filter_function(func):
        ibis.context.builtins[nameorfunc or func.__name__] = func
        return func

    return register_filter_function


def deep_update(source, overrides):
    """
    Update a nested dictionary or similar mapping.
    Modify ``source`` in place.
    """
    for key, value in overrides.items():
        if isinstance(value, collections.Mapping) and value:
            returned = deep_update(source.get(key, {}), ContextDict(value))
            source[key] = returned
        else:
            source[key] = overrides[key]
    return source
