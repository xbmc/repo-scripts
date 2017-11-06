#-------------------------------------------------------------------------------
# Copyright (C) 2017 Carlos Guzman (cguZZman) carlosguzmang@protonmail.com
# 
# This file is part of Cloud Drive Common Module for Kodi
# 
# Cloud Drive Common Module for Kodi is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# Cloud Drive Common Module for Kodi is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# This file incorporates work covered by the copyright and notice described at the bottom of this file.  
#-------------------------------------------------------------------------------

# -*- encoding: utf8 -*-
#
# $Id: html.py 5409 2011-06-29 07:07:25Z rjones $
# $HeadURL: svn+ssh://svn/svn/trunk/api/eklib/html.py $
#
'''Simple, elegant HTML, XHTML and XML generation.

This code is copyright 2009-2011 eKit.com Inc (http://www.ekit.com/)
See the end of the source file for the license of use.
XHTML support was contributed by Michael Haubenwallner.
'''

import cgi

from clouddrive.common.utils import Utils


__version__ = '1.16'


class HTML(object):
    '''Easily generate HTML.

    >>> print HTML('html', 'some text')
    <html>some text</html>
    >>> print HTML('html').p('some text')
    <html><p>some text</p></html>

    If a name is not passed in then the instance becomes a container for
    other tags that itself generates no tag:

    >>> h = HTML()
    >>> h.p('text')
    >>> h.p('text')
    print h
    <p>some text</p>
    <p>some text</p>

    '''
    newline_default_on = set('table ol ul dl'.split())

    def __init__(self, name=None, text=None, stack=None, newlines=True,
            escape=True):
        self._name = name
        self._content = []
        self._attrs = {}
        # insert newlines between content?
        if stack is None:
            stack = [self]
            self._top = True
            self._newlines = newlines
        else:
            self._top = False
            self._newlines = name in self.newline_default_on
        self._stack = stack
        if text is not None:
            self.text(text, escape)

    def __getattr__(self, name):
        # adding a new tag or newline
        if name == 'newline':
            e = '\n'
        else:
            e = self.__class__(name, stack=self._stack)
        if self._top:
            self._stack[-1]._content.append(e)
        else:
            self._content.append(e)
        return e

    def __iadd__(self, other):
        if self._top:
            self._stack[-1]._content.append(other)
        else:
            self._content.append(other)
        return self

    def text(self, text, escape=True):
        '''Add text to the document. If "escape" is True any characters
        special to HTML will be escaped.
        '''
        if escape:
            text = cgi.escape(text)
        # adding text
        if self._top:
            self._stack[-1]._content.append(text)
        else:
            self._content.append(text)

    def raw_text(self, text):
        '''Add raw, unescaped text to the document. This is useful for
        explicitly adding HTML code or entities.
        '''
        return self.text(text, escape=False)

    def __call__(self, *content, **kw):
        if self._name == 'read':
            if len(content) == 1 and isinstance(content[0], int):
                raise TypeError('you appear to be calling read(%d) on '
                    'a HTML instance' % content)
            elif len(content) == 0:
                raise TypeError('you appear to be calling read() on a '
                    'HTML instance')

        # customising a tag with content or attributes
        escape = kw.pop('escape', True)
        if content:
            if escape:
                self._content = list(map(cgi.escape, content))
            else:
                self._content = content
        if 'newlines' in kw:
            # special-case to allow control over newlines
            self._newlines = kw.pop('newlines')
        for k in kw:
            if k == 'klass':
                self._attrs['class'] = cgi.escape(kw[k], True)
            else:
                self._attrs[k] = cgi.escape(kw[k], True)
        return self

    def __enter__(self):
        # we're now adding tags to me!
        self._stack.append(self)
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        # we're done adding tags to me!
        self._stack.pop()

    def __repr__(self):
        return '<HTML %s 0x%x>' % (self._name, id(self))

    def _stringify(self, str_type):
        # turn me and my content into text
        join = '\n' if self._newlines else ''
        if self._name is None:
            return join.join(map(str_type, self._content))
        a = ['%s="%s"' % i for i in self._attrs.items()]
        l = [self._name] + a
        s = '<%s>%s' % (' '.join(l), join)
        if self._content:
            m = map(str_type, self._content)
            s += join.join(m)
            s += join + '</%s>' % self._name
        return s

    def __str__(self):
        return self._stringify(Utils.str)

    def __unicode__(self):
        return self._stringify(Utils.unicode)

    def __iter__(self):
        return iter([str(self)])


class XHTML(HTML):
    '''Easily generate XHTML.
    '''
    empty_elements = set('base meta link hr br param img area input col \
        colgroup basefont isindex frame'.split())

    def _stringify(self, str_type):
        # turn me and my content into text
        # honor empty and non-empty elements
        join = '\n' if self._newlines else ''
        if self._name is None:
            return join.join(map(str_type, self._content))
        a = ['%s="%s"' % i for i in self._attrs.items()]
        l = [self._name] + a
        s = '<%s>%s' % (' '.join(l), join)
        if self._content or not(self._name.lower() in self.empty_elements):
            s += join.join(map(str_type, self._content))
            s += join + '</%s>' % self._name
        else:
            s = '<%s />%s' % (' '.join(l), join)
        return s


class XML(XHTML):
    '''Easily generate XML.

    All tags with no contents are reduced to self-terminating tags.
    '''
    newline_default_on = set()  # no tags are special

    def _stringify(self, str_type):
        # turn me and my content into text
        # honor empty and non-empty elements
        join = '\n' if self._newlines else ''
        if self._name is None:
            return join.join(map(str_type, self._content))
        a = ['%s="%s"' % i for i in self._attrs.items()]
        l = [self._name] + a
        s = '<%s>%s' % (' '.join(l), join)
        if self._content:
            s += join.join(map(str_type, self._content))
            s += join + '</%s>' % self._name
        else:
            s = '<%s />%s' % (' '.join(l), join)
        return s

# Copyright (c) 2009 eKit.com Inc (http://www.ekit.com/)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in
#  all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# vim: set filetype=python ts=4 sw=4 et si
