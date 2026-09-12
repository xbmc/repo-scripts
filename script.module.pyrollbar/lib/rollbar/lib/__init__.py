import base64
import collections
import copy
from array import array

from collections.abc import Mapping

binary_type = bytes
integer_types = int
number_types = (float, int)
string_types = str
sequence_types = (Mapping, list, tuple, set, frozenset, array, collections.deque)


def force_lower(val):
    try:
        return val.lower()
    except:
        return str(val).lower()


def prefix_match(key, prefixes):
    if not key:
        return False

    for prefix in prefixes:
        if len(prefix) > len(key):
            continue

        if prefix == key[:len(prefix)]:
            return True

    return False


def key_in(key, canonicals):
    if not key:
        return False

    for c in canonicals:
        if key_match(key, c):
            return True

    return False


def key_depth(key, canonicals) -> int:
    if not key:
        return 0

    for c in canonicals:
        if key_match(key, c):
            return len(c)

    return 0


def key_match(key, canonical):
    if len(key) < len(canonical):
        return False

    for k, c in zip(key, canonical):
        if '*' == c:
            continue
        if c == k:
            continue
        return False

    return True


def reverse_list_of_lists(l, apply_each_fn=None):
    apply_each_fn = apply_each_fn or (lambda x: x)
    return [reversed([apply_each_fn(x) for x in inner]) for inner in l or []]


def build_key_matcher(prefixes_or_suffixes, type='prefix', case_sensitive=False):
    _prefixes = []

    if type == 'prefix':
        _iter = iter
    elif type == 'suffix':
        _iter = reversed
    else:
        raise ValueError('type must be either "prefix" or "suffix"')

    prefixes_or_suffixes = prefixes_or_suffixes or []
    for prefix in prefixes_or_suffixes:
        if case_sensitive:
            # Copy the list of lists
            _prefix = list(_iter(prefix))
        else:
            # Lowercase all of the elements
            _prefix = [force_lower(x) for x in _iter(prefix)]

        _prefixes.append(_prefix)

    def matcher(prefix_or_suffix):
        if case_sensitive:
            prefix = list(_iter(prefix_or_suffix))
        else:
            prefix = [force_lower(x) for x in _iter(prefix_or_suffix)]

        return prefix_match(prefix, _prefixes)

    return matcher


def is_builtin_type(obj):
    return obj.__class__.__module__ in ('__builtin__', 'builtins')


# http://www.xormedia.com/recursively-merge-dictionaries-in-python.html
def dict_merge(a, b, silence_errors=False):
    """
    Recursively merges dict's. not just simple a['key'] = b['key'], if
    both a and bhave a key who's value is a dict then dict_merge is called
    on both values and the result stored in the returned dictionary.
    """

    if not isinstance(b, dict):
        return b

    result = a
    for k, v in b.items():
        if k in result and isinstance(result[k], dict):
            result[k] = dict_merge(result[k], v, silence_errors=silence_errors)
        else:
            try:
                result[k] = copy.deepcopy(v)
            except Exception as e:
                if not silence_errors:
                    raise e

                result[k] = '<Uncopyable obj:(%s)>' % (v,)

    return result


def circular_reference_label(data, ref_key=None):
    ref = '.'.join([str(x) for x in ref_key])
    return '<CircularReference type:(%s) ref:(%s)>' % (type(data).__name__, ref)


def float_nan_label(data):
    return '<NaN>'


def float_infinity_label(data):
    if data > 1:
        return '<Infinity>'
    else:
        return '<NegativeInfinity>'


def unencodable_object_label(data):
    return '<Unencodable type:(%s) base64:(%s)>' % (type(data).__name__,
                                                    base64.b64encode(data).decode('ascii'))


def undecodable_object_label(data):
    return '<Undecodable type:(%s) base64:(%s)>' % (type(data).__name__,
                                                    base64.b64encode(data).decode('ascii'))

try:
    from django.utils.functional import SimpleLazyObject
except ImportError:
    SimpleLazyObject = None


def defaultJSONEncode(o):
    if SimpleLazyObject and isinstance(o, SimpleLazyObject):
        if not o._wrapped:
            o._setup()
        return o._wrapped
    return repr(o) + " is not JSON serializable"
