# coding=utf-8

import re
import pprint
import random

from . import context

try:
    import pygments
    import pygments.lexers
    import pygments.formatters
except ImportError:
    pygments = None

try:
    from html import escape as html_escape
except ImportError:
    from cgi import escape as html_escape


# Dictionary of registered filter functions.
filtermap = {}


# Decorator function for registering filters.  A filter function should accept at least one
# argument - the value to be filtered - and return the filtered result. It can optionally
# accept any number of additional arguments.
#
# This decorator can be used as:
#
#     @register
#     @register()
#     @register('name')
#
# If no name is supplied the function name will be used.
def register(nameorfunc=None, with_context=False):

    if callable(nameorfunc):
        nameorfunc.with_context = with_context
        filtermap[nameorfunc.__name__] = nameorfunc
        return nameorfunc

    def register_filter_function(func):
        func.with_context = with_context
        filtermap[nameorfunc or func.__name__] = func
        return func

    return register_filter_function


@register
def argtest(*args):
    """ Test filter: returns arguments as a concatenated string. """
    return '|'.join(str(arg) for arg in args)


@register
def default(obj, fallback):
    """ Returns `obj` if `obj` is truthy, otherwise `fallback`. """
    return obj or fallback


@register
def dtformat(dt, format='%Y-%m-%d %H:%M'):
    """ Formats a datetime object using the specified format string. """
    return dt.strftime(format)


@register
def endswith(s, suffix):
    """ True if the string ends with the specified suffix. """
    return s.endswith(suffix)


@register
@register('e')
@register('esc')
def escape(s, quotes=True):
    """ Converts html syntax characters to character entities. """
    return html_escape(s, quotes)


@register
def first(seq):
    """ Returns the first element in the sequence `seq`. """
    return seq[0]


@register
def firsth(html):
    """ Returns the content of the first heading element. """
    match = re.search(r'<h(\d)+[^>]*>(.*?)</h\1>', html, flags=re.DOTALL)
    return match.group(2) if match else ''


@register
def firsth1(html):
    """ Returns the content of the first h1 element. """
    match = re.search(r'<h1[^>]*>(.*?)</h1>', html, flags=re.DOTALL)
    return match.group(1) if match else ''


@register
def firstp(html):
    """ Returns the content of the first p element. """
    match = re.search(r'<p[^>]*>(.*?)</p>', html, flags=re.DOTALL)
    return match.group(1) if match else ''


@register('reversed')
def get_reversed(seq):
    """ Returns a reverse iterator over the sequence `seq`. """
    return reversed(seq)


@register
def index(seq, i):
    """ Returns the ith element in the sequence `seq`. """
    return seq[i]


@register('divisible_by')
def is_divisible_by(n, d):
    """ True if the integer `n` is a multiple of the integer `d`. """
    return n % d == 0


@register('even')
def is_even(n):
    """ True if the integer `n` is even. """
    return n % 2 == 0


@register('odd')
def is_odd(n):
    """ True if the integer `n` is odd. """
    return n % 2 != 0


@register
def join(seq, sep=''):
    """ Joins elements of the sequence `seq` with the string `sep`. """
    return sep.join(str(item) for item in seq)


@register
def last(seq):
    """ Returns the last element in the sequence `seq`. """
    return seq[-1]


@register('len')
def length(seq):
    """ Returns the length of the sequence `seq`. """
    return len(seq)


@register
def lower(s):
    """ Returns the string `s` converted to lowercase. """
    return s.lower()


@register('pprint')
def prettyprint(obj):
    """ Returns a pretty-printed representation of `obj`. """
    return pprint.pformat(obj)


@register
def pygmentize(text, lang=None):
    """ Applies syntax highlighting using Pygments.

    If no language is specified, Pygments will attempt to guess the correct
    lexer to use. If Pygments is not available or if an appropriate lexer
    cannot be found then the filter will return the input text with any
    html special characters escaped.
    """
    if pygments:
        if lang:
            try:
                lexer = pygments.lexers.get_lexer_by_name(lang)
            except pygments.util.ClassNotFound:
                lexer = None
        else:
            try:
                lexer = pygments.lexers.guess_lexer(text)
            except pygments.util.ClassNotFound:
                lexer = None
        if lexer:
            formatter = pygments.formatters.HtmlFormatter(nowrap=True)
            text = pygments.highlight(text, lexer, formatter)
        else:
            text = html_escape(text)
    else:
        text = html_escape(text)
    return text


@register
def random(seq):
    """ Returns a random element from the sequence `seq`. """
    return random.choice(seq)


@register('repr')
def to_repr(obj):
    """ Returns the result of calling repr() on `obj`. """
    return repr(obj)


@register
def slice(seq, start, stop=None, step=None):
    """ Returns the start:stop:step slice of the sequence `seq`. """
    return seq[start:stop:step]


@register
def spaceless(html):
    """ Strips all whitespace between html/xml tags. """
    return re.sub(r'>\s+<', '><', html)


@register
def startswith(s, prefix):
    """ True if the string starts with the specified prefix. """
    return s.startswith(prefix)


@register('str')
def to_str(obj):
    """ Returns the result of calling str() on `obj`. """
    return str(obj)


@register
def striptags(html):
    """ Returns the string `html` with all html tags stripped. """
    return re.sub(r'<[^>]*>', '', html)


@register
def teaser(s, delimiter='<!-- more -->'):
    """ Returns the portion of the string `s` before `delimiter`,
    or an empty string if `delimiter` is not found. """
    index = s.find(delimiter)
    if index == -1:
        return ''
    else:
        return s[:index]


@register
@register('title')
def titlecase(s):
    """ Returns the string `s` converted to titlecase. """
    return re.sub(
        r"[A-Za-z]+('[A-Za-z]+)?",
        lambda m: m.group(0)[0].upper() + m.group(0)[1:],
        s
    )


@register
def truncatechars(s, n, ellipsis='...'):
    """ Truncates the string `s` to at most `n` characters. """
    if len(s) > n:
        return s[:n - 3].rstrip(' .,;:?!') + ellipsis
    else:
        return s


@register
def truncatewords(s, n, ellipsis=' [...]'):
    """ Truncates the string `s` to at most `n` words. """
    words = s.split()
    if len(words) > n:
        return ' '.join(words[:n]) + ellipsis
    else:
        return ' '.join(words)


@register
def upper(s):
    """ Returns the string `s` converted to uppercase. """
    return s.upper()


@register
def wrap(s, tag):
    """ Wraps a string in opening and closing tags. """
    return '<%s>%s</%s>' % (tag, str(s), tag)


@register
def if_undefined(obj, fallback):
    """ Returns `obj` if `obj` is defined, otherwise `fallback`. """
    return fallback if isinstance(obj, context.Undefined) else obj


@register
def is_defined(obj):
    """ Returns true if `obj` is defined, otherwise false. """
    return not isinstance(obj, context.Undefined)

