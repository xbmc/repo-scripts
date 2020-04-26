import sys


def try_parse_int(string):
    '''helper to parse int from string without erroring on empty or misformed string'''
    try:
        return int(string)
    except Exception:
        return 0


def try_decode_string(string, encoding='utf-8'):
    """helper to decode strings for PY 2 """
    if sys.version_info.major == 3:
        return string
    try:
        return string.decode(encoding)
    except Exception:
        return string


def try_encode_string(string, encoding='utf-8'):
    """helper to encode strings for PY 2 """
    if sys.version_info.major == 3:
        return string
    try:
        return string.encode(encoding)
    except Exception:
        return string
