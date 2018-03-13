# -*- coding: utf-8 -*-
from __future__ import absolute_import

# Standard Library Imports
import sys
import re

# Kodi imports
import xbmc

try:
    import urllib.parse as urlparse
except ImportError:
    # noinspection PyUnresolvedReferences
    import urlparse

try:
    # noinspection PyUnresolvedReferences
    long_type = long
except NameError:
    long_type = int

PY3 = sys.version_info[0] >= 3

# Unicode Type object, unicode on python2 or str on python3
unicode_type = type(u"")

__all__ = ["keyboard", "parse_qs", "urljoin_partial", "strip_tags",
           "safe_path", "ensure_bytes", "ensure_native_str", "ensure_unicode"]


def keyboard(heading, default="", hidden=False):
    """
    Show a keyboard dialog.

    :param heading: Keyboard heading.
    :type heading: str or unicode

    :param default: [opt] Default text.
    :type default: str or unicode

    :param hidden: [opt] ``True`` for hidden text entry.
    :type hidden: bool

    :return: Returns the user input as unicode.
    :rtype: unicode
    """
    # Convert inputs to strings if required
    heading = ensure_native_str(heading)
    default = ensure_native_str(default)

    # Show the onscreen keyboard
    kb = xbmc.Keyboard(default, heading, hidden)
    kb.doModal()

    # Return user input only if 'OK' was pressed (confirmed)
    if kb.isConfirmed():
        text = kb.getText()
        return text.decode("utf8") if isinstance(text, bytes) else text
    else:
        return u""  # pragma: no cover


def parse_qs(qs, keep_blank_values=False, strict_parsing=False):
    """
    Parse a urlencoded query string, and return the data as a dictionary.

    Parse a query string given as a string or unicode argument (data of type application/x-www-form-urlencoded).
    Data is returned as a dictionary. The dictionary keys are the unique query variable names and the values
    are unicode values for each name

    The optional argument keep_blank_values is a flag indicating whether blank values in percent-encoded queries
    should be treated as blank strings. A ``True`` value indicates that blanks should be retained as blank strings.
    The default ``False`` value indicates that blank values are to be ignored and treated as if they were not included.

    The optional argument strict_parsing is a flag indicating what to do with parsing errors.
    If ``False`` (the default), errors are silently ignored. If ``True``, errors raise a ValueError exception.

    :param qs: Percent-encoded query string to be parsed, or a url with a query string.
    :type qs: str or unicode

    :param bool keep_blank_values: ``True`` to keep blank values, else discard.
    :param bool strict_parsing: ``True`` to raise ValueError if there are parsing errors, else silently ignore.

    :return: Returns a dict of key/value pairs, with all keys and values as unicode.
    :rtype: dict

    :raises ValueError: If duplicate query field names exists or if there is a parsing error.

    :example:
        >>> parse_qs("http://example.com/path?q=search&safe=no")
        {u"q": u"search", u"safe": u"no"}
        >>> parse_qs(u"q=search&safe=no")
        {u"q": u"search", u"safe": u"no"}
    """
    params = {}
    qs = ensure_native_str(qs)
    parsed = urlparse.parse_qsl(qs.split("?", 1)[-1], keep_blank_values, strict_parsing)
    if PY3:
        for key, value in parsed:
            if key not in params:
                params[key] = value
            else:
                # Only add keys that are not already added, multiple values are not supported
                raise ValueError("encountered duplicate param field name: '%s'" % key)
    else:
        for bkey, value in parsed:
            ukey = unicode_type(bkey, encoding="utf8")
            if ukey not in params:
                params[ukey] = unicode_type(value, encoding="utf8")
            else:
                # Only add keys that are not already added, multiple values are not supported
                raise ValueError("encountered duplicate param field name: '%s'" % bkey)

    # Return the params with all keys and values as unicode
    return params


def urljoin_partial(base_url):
    """
    Construct a full (absolute) URL by combining a base URL with another URL.

    This is useful when parsing html as the majority of links would be relative links.

    Informally, this uses components of the base URL, in particular the addressing scheme,
    the network location and (part of) the path, to provide missing components in the relative URL.

    Returns a new partial object which when called will pass base_url to urlparse.urljoin along with the
    supplied relative URL.

    :type base_url: str or unicode
    :param base_url: The absolute url to use as the base.
    :returns: A partial function that accepts a relative url and returns a full absolute url.
    
    :example:
        >>> url_constructor = urljoin_partial("https://google.ie/")
        >>> url_constructor("/path/to/something")
        "https://google.ie/path/to/something"
        >>> url_constructor("/gmail")
        "https://google.ie/gmail"
    """
    base_url = ensure_unicode(base_url)

    def wrapper(url):
        """
        Construct a full (absolute) using saved base url.

        :param url: The relative URL to combine with base.
        :return: Absolute url.
        :rtype: unicode
        """
        return urlparse.urljoin(base_url, ensure_unicode(url))

    return wrapper


def strip_tags(html):
    """
    Strips out html tags and return plain text.

    :param html: HTML with text to extract.
    :type html: bytes or unicode

    :example:
        >>> strip_tags('<a href="http://example.com/">I linked to <i>example.com</i></a>')
        "I linked to example.com"
    """
    # This will fail under python3 when html is of type bytes
    # This is ok sence you will have much bigger problems if you are still using bytes on python3
    return re.sub("<[^<]+?>", "", html)


def safe_path(path, encoding="utf8"):
    """
    Returns path as type ``bytes`` or ``unicode`` base on platform os.

    Unicode when on windows, bytes when on linux/bsd.

    This is needed because a path operation may fail on windows if path is of type ``bytes`` and it's contains
    non ascii characters. Same if path is of type ``unicode`` on linux and locale is set to
    'C'(ascii) instead of something like 'UTF-8'.

    :type path: str or unicode
    :param path: The path to convert.
    :param str encoding: [opt] The encoding to use if needed.
    :return: Returns the path as unicode or bytes base on platform os.
    """
    return ensure_unicode(path, encoding) if sys.platform.startswith("win") else ensure_bytes(path, encoding)


def ensure_bytes(data, encoding="utf8"):
    """
    Ensures that given string is returned as type ``bytes``.

    :param data: String to convert if needed.
    :param str encoding: [opt] The encoding to use if needed..
    :returns: The given string as type ``bytes``
    :rtype: bytes
    """
    return data if isinstance(data, bytes) else unicode_type(data).encode(encoding)


def ensure_native_str(data, encoding="utf8"):
    """
    Ensures that given string is returned as a native ``str`` type, ``bytes`` on python2, ``unicode`` on python3.

    :param data: String to convert if needed.
    :param str encoding: [opt] The encoding to use if needed..
    :returns: The given string as a native ``str`` type.
    :rtype: str
    """
    if isinstance(data, str):
        return data
    elif isinstance(data, unicode_type):
        # Only executes on python 2
        return data.encode(encoding)
    elif isinstance(data, bytes):
        # Only executes on python 3
        return data.decode(encoding)
    else:
        return str(data)


def ensure_unicode(data, encoding="utf8"):
    """
    Ensures that given string is return as type ``unicode``.

    :param data: String to convert if needed.
    :param str encoding: [opt] The encoding to use if needed..
    :returns: The given string as type ``unicode``.
    :rtype: unicode
    """
    if isinstance(data, bytes):
        return data.decode(encoding)
    else:
        return unicode_type(data)
