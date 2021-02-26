#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# The MIT License (MIT)
#
# Copyright (c) 2016 William Forde
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
HTMLement
---------
Simple lightweight HTML parser with XPath support.

Github: https://github.com/willforde/python-htmlement
Documentation: https://python-htmlement.readthedocs.io/en/stable/?badge=stable
Testing: https://www.travis-ci.com/willforde/python-htmlement
Coverage: https://coveralls.io/github/willforde/python-htmlement?branch=master
Maintainability: https://codeclimate.com/github/willforde/python-htmlement/maintainability
"""


# Python 2 compatibility
from __future__ import unicode_literals

# Standard library imports
from codecs import open as _open
import warnings
import sys
import re

# Check python version to set the object that can detect non unicode strings
if sys.version_info >= (3, 0):
    import xml.etree.ElementTree as Etree
    # noinspection PyUnresolvedReferences,PyCompatibility
    from html.parser import HTMLParser
    # noinspection PyUnresolvedReferences, PyCompatibility
    from html.entities import name2codepoint
    # Python2 compatibility
    _chr = chr
else:
    # noinspection PyUnresolvedReferences,PyCompatibility
    from HTMLParser import HTMLParser
    # noinspection PyUnresolvedReferences, PyCompatibility
    from htmlentitydefs import name2codepoint
    # noinspection PyUnresolvedReferences
    _chr = unichr

    try:
        # This attemps to import the C version of ElementTree
        import xml.etree.cElementTree as Etree
        # This will fail if the implementation is broken
        Etree.Comment("Test for broken cElementTree")
    except (ImportError, TypeError):
        import xml.etree.ElementTree as Etree

__all__ = ["HTMLement", "fromstring", "fromstringlist", "parse"]
__version__ = "1.0.0"

# Add missing codepoints
name2codepoint["apos"] = 0x0027


def fromstring(text, tag="", attrs=None, encoding=None):
    """
    Parse's "HTML" document from a string into an element tree.

    :param text: The "HTML" document to parse.
    :type text: str or bytes

    :param str tag: (optional) Name of "tag / element" which is used to filter down "the tree" to a required section.
    :type tag: str

    :param attrs: (optional) The attributes of the element, that will be used, when searchingfor the required section.
    :type attrs: dict(str, str)

    :param encoding: (optional) Encoding used, when decoding the source data before feeding it to the parser.
    :type encoding: str

    :return: The root element of the element tree.
    :rtype: xml.etree.ElementTree.Element

    :raises UnicodeDecodeError: If decoding of *text* fails.
    """
    parser = HTMLement(tag, attrs, encoding)
    parser.feed(text)
    return parser.close()


def fromstringlist(sequence, tag="", attrs=None, encoding=None):
    """
    Parses an "HTML document" from a sequence of "HTML sections" into an element tree.

    :param sequence: A sequence of "HTML sections" to parse.
    :type sequence: list(str or bytes)

    :param str tag: (optional) Name of "tag / element" which is used to filter down "the tree" to a required section.
    :type tag: str

    :param attrs: (optional) The attributes of the element, that will be used, when searchingfor the required section.
    :type attrs: dict(str, str)

    :param encoding: (optional) Encoding used, when decoding the source data before feeding it to the parser.
    :type encoding: str

    :return: The root element of the element tree.
    :rtype: xml.etree.ElementTree.Element

    :raises UnicodeDecodeError: If decoding of a section within *sequence* fails.
    """
    parser = HTMLement(tag, attrs, encoding)
    for text in sequence:
        parser.feed(text)
    return parser.close()


def parse(source, tag="", attrs=None, encoding=None):
    """
    Load an external "HTML document" into an element tree.

    :param source: A filename or file like object containing HTML data.
    :type source: str or io.TextIOBase

    :param str tag: (optional) Name of "tag / element" which is used to filter down "the tree" to a required section.
    :type tag: str

    :param attrs: (optional) The attributes of the element, that will be used, when searchingfor the required section.
    :type attrs: dict(str, str)

    :param encoding: (optional) Encoding used, when decoding the source data before feeding it to the parser.
    :type encoding: str

    :return: The root element of the element tree.
    :rtype: xml.etree.ElementTree.Element

    :raises UnicodeDecodeError: If decoding of *source* fails.
    """
    # Assume that source is a file pointer if no read methods is found
    if not hasattr(source, "read"):
        source = _open(source, "rb", encoding=encoding)
        close_source = True
    else:
        close_source = False

    try:
        parser = HTMLement(tag, attrs, encoding)
        while True:
            # Read in 64k at a time
            data = source.read(65536)
            if not data:
                break

            # Feed the parser
            parser.feed(data)

        # Return the root element
        return parser.close()

    finally:
        if close_source:
            source.close()


class HTMLement(object):
    """
    Python HTMLParser extension with ElementTree Parser support.

    This HTML Parser extends :class:`html.parser.HTMLParser`, returning an :class:`xml.etree.ElementTree.Element`
    instance. The returned root element natively supports the ElementTree API.
    (e.g. you may use its limited support for `XPath expressions`__)

    When a "tag" and "tag attributes" are given the parser will search for a required section. Only when the required
    section is found, does the parser start parsing the "HTML document". The element that matches the search criteria
    will then become the new "root element".

    Attributes are given as a dict of {'name': 'value'}. Value can be the string to match, `True` or `False.`
    `True` will match any attribute with given name and any value.
    `False` will only give a match if given attribute does not exist in the element.

    :param str tag: (optional) Name of "tag / element" which is used to filter down "the tree" to a required section.
    :type tag: str

    :param attrs: (optional) The attributes of the element, that will be used, when searchingfor the required section.
    :type attrs: dict(str, str)

    :param encoding: (optional) Encoding used, when decoding the source data before feeding it to the parser.
    :type encoding: str

    .. _Xpath: https://docs.python.org/3.6/library/xml.etree.elementtree.html#xpath-support
    __ XPath_
    """
    def __init__(self, tag="", attrs=None, encoding=None):
        self._parser = ParseHTML(tag, attrs)
        self.encoding = encoding
        self._finished = False

    def feed(self, data):
        """
        Feeds data to the parser.

        If *data*, is of type :class:`bytes` and where no encoding was specified, then the encoding
        will be extracted from *data* using "meta tags", if available.
        Otherwise encoding will default to "ISO-8859-1"

        :param data: HTML data
        :type data: str or bytes

        :raises UnicodeDecodeError: If decoding of *data* fails.
        """
        # Skip feeding data into parser if we already have what we want
        if self._finished == 1:
            return None

        # Make sure that we have unicode before continuing
        if isinstance(data, bytes):
            if self.encoding:
                data = data.decode(self.encoding)
            else:
                data = self._make_unicode(data)

        # Parse the html document
        try:
            self._parser.feed(data)
        except EOFError:
            self._finished = True
            self._parser.reset()

    def close(self):
        """
        Close the "tree builder" and return the "root element" of the "element tree".

        :return: The "root element" of the "element tree".
        :rtype: xml.etree.ElementTree.Element

        :raises RuntimeError: If no element matching search criteria was found.
        """
        return self._parser.close()

    def _make_unicode(self, data):
        """
        Convert *data* from type :class:`bytes` to type :class:`str`.

        :param data: The html document.
        :type data: bytes

        :return: HTML data decoded.
        :rtype: str
        """
        # Atemp to find the encoding from the html source
        end_head_tag = data.find(b"</head>")
        if end_head_tag:
            # Search for the charset attribute within the meta tags
            charset_refind = b'<meta.+?charset=[\'"]*(.+?)["\'].*?>'
            charset = re.search(charset_refind, data[:end_head_tag], re.IGNORECASE)
            if charset:
                self.encoding = encoding = charset.group(1).decode()
                return data.decode(encoding)

        # Decode the string into unicode using default encoding
        warn_msg = "Unable to determine encoding, defaulting to iso-8859-1"
        warnings.warn(warn_msg, UnicodeWarning, stacklevel=2)
        self.encoding = "iso-8859-1"
        return data.decode("iso-8859-1")


# noinspection PyAbstractClass
class ParseHTML(HTMLParser):
    def __init__(self, tag="", attrs=None):
        # Initiate HTMLParser
        HTMLParser.__init__(self)
        self.convert_charrefs = True
        self._root = None  # root element
        self._data = []  # data collector
        self._factory = Etree.Element
        self.enabled = not tag
        self._unw_attrs = []
        self.tag = tag

        # Split attributes into wanted and unwanted attributes
        if attrs:
            self.attrs = attrs
            for key, value in attrs.copy().items():
                if value == 0:
                    self._unw_attrs.append(key)
                    del attrs[key]
        else:
            self.attrs = {}

        # Some tags in html do not require closing tags so thoes tags will need to be auto closed (Void elements)
        # Refer to: https://www.w3.org/TR/html/syntax.html#void-elements
        self._voids = frozenset(("area", "base", "br", "col", "hr", "img", "input", "link", "meta", "param",
                                 # Only in HTML5
                                 "embed", "keygen", "source", "track",
                                 # Not supported in HTML5
                                 "basefont", "frame", "isindex",
                                 # SVG self closing tags
                                 "rect", "circle", "ellipse", "line", "polyline", "polygon",
                                 "path", "stop", "use", "image", "animatetransform"))

        # Create temporary root element to protect from badly written sites that either
        # have no html starting tag or multiple top level elements
        elem = self._factory("html")
        self._elem = [elem]
        self._last = elem
        self._tail = 0

    def handle_starttag(self, tag, attrs):
        self._handle_starttag(tag, attrs, self_closing=tag in self._voids)

    def handle_startendtag(self, tag, attrs):
        self._handle_starttag(tag, attrs, self_closing=True)

    def _handle_starttag(self, tag, attrs, self_closing=False):
        enabled = self.enabled
        # Add tag element to tree if we have no filter or that the filter matches
        if enabled or self._search(tag, attrs):
            # Convert attrs to dictionary
            attrs = dict(attrs) if attrs else {}
            self._flush()

            # Create the new element
            elem = self._factory(tag, attrs)
            self._elem[-1].append(elem)
            self._last = elem

            # Only append the element to the list of elements if it's not a self closing element
            if self_closing:
                self._tail = 1
            else:
                self._elem.append(elem)
                self._tail = 0

            # Set this element as the root element when the filter search matches
            if not enabled:
                self._root = elem
                self.enabled = True

    def handle_endtag(self, tag):
        # Only process end tags when we have no filter or that the filter has been matched
        if self.enabled and tag not in self._voids:
            _elem = self._elem
            _root = self._root
            # Check that the closing tag is what's actualy expected
            if _elem[-1].tag == tag:
                self._flush()
                self._tail = 1
                self._last = elem = _elem.pop()
                if elem is _root:
                    raise EOFError

            # If the previous element is what we actually have then the expected element was not
            # properly closed so we must close that before closing what we have now
            elif len(_elem) >= 2 and _elem[-2].tag == tag:
                self._flush()
                self._tail = 1
                for _ in range(2):
                    self._last = elem = _elem.pop()
                    if elem is _root:
                        raise EOFError
            else:
                # Unable to match the tag to an element, ignoring it
                return None

    def handle_data(self, data):
        if data.strip() and self.enabled:
            self._data.append(data)

    def handle_entityref(self, name):
        if self.enabled:
            try:
                name = _chr(name2codepoint[name])
            except KeyError:
                pass
            self._data.append(name)

    def handle_charref(self, name):
        if self.enabled:
            try:
                if name[0].lower() == "x":
                    name = _chr(int(name[1:], 16))
                else:
                    name = _chr(int(name))
            except ValueError:
                pass
            self._data.append(name)

    def handle_comment(self, data):
        data = data.strip()
        if data and self.enabled:
            elem = Etree.Comment(data)
            self._elem[-1].append(elem)

    def close(self):
        self._flush()
        if self.enabled == 0:
            msg = "Unable to find requested section with tag of '{}' and attributes of {}"
            raise RuntimeError(msg.format(self.tag, self.attrs))
        elif self._root is not None:
            return self._root
        else:
            # Search the root element to find a proper html root element if one exists
            tmp_root = self._elem[0]
            proper_root = tmp_root.find("html")
            if proper_root is None:
                # Not proper root was found
                return tmp_root
            else:
                # Proper root found
                return proper_root

    def _flush(self):
        if self._data:
            if self._last is not None:
                text = "".join(self._data)
                if self._tail:
                    self._last.tail = text
                else:
                    self._last.text = text
            self._data = []

    def _search(self, tag, attrs):
        # Only search when the tag matches
        if tag == self.tag:
            # If we have required attrs to match then search all attrs for wanted attrs
            # And also check that we do not have any attrs that are unwanted
            if self.attrs or self._unw_attrs:
                if attrs:
                    wanted_attrs = self.attrs.copy()
                    unwanted_attrs = self._unw_attrs
                    for key, value in attrs:
                        # Check for unwanted attrs
                        if key in unwanted_attrs:
                            return False

                        # Check for wanted attrs
                        elif key in wanted_attrs:
                            c_value = wanted_attrs[key]
                            if c_value == value or c_value == 1:
                                # Remove this attribute from the wanted dict of attributes
                                # to indicate that this attribute has been found
                                del wanted_attrs[key]

                    # If wanted_attrs is now empty then all attributes must have been found
                    if not wanted_attrs:
                        return True
            else:
                # We only need to match tag
                return True

        # Unable to find required section
        return False
