# -*- coding: utf-8 -*-
from __future__ import unicode_literals


"""
Python lib for reading NCX formated file for epub.

There is some difference between NCX original format and one for Epub; see
officiel documention for more information.1111

NCX doc: http://www.niso.org/workrooms/daisy/Z39-86-2005.html#NCX
NCX Epub spec: http://idpf.org/epub/20/spec/OPF_2.0.1_draft.htm#Section2.4.1
"""


from xml.dom import minidom


def parse_toc(xmlstring):
    """Inspect an NCX formated xml document."""
    toc = Ncx()
    toc_xml = minidom.parseString(xmlstring).documentElement

    xmlns = toc_xml.getAttribute('xmlns')
    if xmlns:
        toc.xmlns = xmlns

    version = toc_xml.getAttribute('version')
    if version:
        toc.version = version

    lang = toc_xml.getAttribute('xml:lang')
    if lang:
        toc.lang = lang

    # Inspect head > meta; unknow meta are ignored
    head = toc_xml.getElementsByTagName('head')[0]
    metas = {'dtb:uid': '',
             'dtb:depth': '',
             'dtb:totalPageCount': '',
             'dtb:maxPageNumber': '',
             'dtb:generator': ''}

    for meta in head.getElementsByTagName('meta'):
        metas[meta.getAttribute('name')] = meta.getAttribute('content')

    toc.uid = metas['dtb:uid']
    toc.depth = metas['dtb:depth']
    toc.total_page_count = metas['dtb:totalPageCount']
    toc.max_page_number = metas['dtb:maxPageNumber']
    toc.generator = metas['dtb:generator']

    # Get title (one and only one <docTitle> tag is required)
    doc_title_node = toc_xml.getElementsByTagName('docTitle')[0]
    toc.title = _parse_for_text_tag(doc_title_node)

    # Get authors (<docAuthor> tags are optionnal)
    for author in toc_xml.getElementsByTagName('docAuthor'):
        toc.authors.append(_parse_for_text_tag(author))

    # Inspect <navMap> (one is required)
    nav_map_node = toc_xml.getElementsByTagName('navMap')[0]
    toc.nav_map = _parse_xml_nav_map(nav_map_node)

    # Inspect <pageList> (optionnal, only one)
    page_lists = toc_xml.getElementsByTagName('pageList')
    if len(page_lists) > 0:
        toc.page_list = _parse_xml_page_list(page_lists[0])

    # Inspect <navList> (optionnal, many are possible)
    for nav_list in toc_xml.getElementsByTagName('navList'):
        toc.add_nav_list(_parse_xml_nav_list(nav_list))

    return toc


def _parse_xml_nav_map(element):
    """Inspect an xml.dom.Element <navMap> and return a NcxNavMap object."""
    nav_map = NavMap()
    nav_map.identifier = element.getAttribute('id')

    children = [e for e in element.childNodes if e.nodeType == e.ELEMENT_NODE]
    for node in children:
        if node.tagName == 'navLabel':
            nav_map.add_label(_parse_for_text_tag(node),
                              node.getAttribute('xml:lang'),
                              node.getAttribute('dir'))
        elif node.tagName == 'navInfo':
            nav_map.add_info(_parse_for_text_tag(node),
                             node.getAttribute('xml:lang'),
                             node.getAttribute('dir'))
        elif node.tagName == 'navPoint':
            nav_map.add_point(_parse_xml_nav_point(node))

    return nav_map


def _parse_xml_nav_point(element):
    """Inspect an xml.dom.Element <navPoint> and return a NcxNavPoint object.
    """
    nav_point = NavPoint()
    nav_point.identifier = element.getAttribute('id')
    nav_point.class_name = element.getAttribute('class')
    nav_point.play_order = element.getAttribute('playOrder')

    children = [e for e in element.childNodes if e.nodeType == e.ELEMENT_NODE]
    for node in children:
        if node.tagName == 'navLabel':
            nav_point.add_label(_parse_for_text_tag(node),
                                node.getAttribute('xml:lang'),
                                node.getAttribute('dir'))
        elif node.tagName == 'content':
            nav_point.src = node.getAttribute('src')
        elif node.tagName == 'navPoint':
            nav_point.add_point(_parse_xml_nav_point(node))

    return nav_point


def _parse_xml_page_list(element):
    """Inspect an xml.dom.Element <pageList> and return a NcxPageList object.
    """
    page_list = PageList()
    page_list.identifier = element.getAttribute('id')
    page_list.class_name = element.getAttribute('class')

    children = [e for e in element.childNodes if e.nodeType == e.ELEMENT_NODE]
    for node in children:
        if node.tagName == 'navLabel':
            page_list.add_label(_parse_for_text_tag(node),
                                node.getAttribute('xml:lang'),
                                node.getAttribute('dir'))
        elif node.tagName == 'navInfo':
            page_list.add_info(_parse_for_text_tag(node),
                               node.getAttribute('xml:lang'),
                               node.getAttribute('dir'))
        elif node.tagName == 'pageTarget':
            page_list.add_target(_parse_xml_page_target(node))

    return page_list


def _parse_xml_page_target(element):
    """Inspect an xml.dom.Element <pageTarget> and return a NcxPageTarget
    object."""
    page_target = PageTarget()
    page_target.identifier = element.getAttribute('id')
    page_target.value = element.getAttribute('value')
    page_target.target_type = element.getAttribute('type')
    page_target.class_name = element.getAttribute('class')
    page_target.play_order = element.getAttribute('playOrder')

    children = [e for e in element.childNodes if e.nodeType == e.ELEMENT_NODE]
    for node in children:
        if node.tagName == 'navLabel':
            page_target.add_label(_parse_for_text_tag(node),
                                  node.getAttribute('xml:lang'),
                                  node.getAttribute('dir'))
        elif node.tagName == 'content':
            page_target.src = node.getAttribute('src')

    return page_target


def _parse_xml_nav_list(element):
    """Inspect an xml.dom.Element <navList> and return a NcxNavList object."""
    nav_list = NavList()
    nav_list.identifier = element.getAttribute('id')
    nav_list.class_name = element.getAttribute('class')

    children = [e for e in element.childNodes if e.nodeType == e.ELEMENT_NODE]
    for node in children:
        if node.tagName == 'navLabel':
            nav_list.add_label(_parse_for_text_tag(node),
                                node.getAttribute('xml:lang'),
                                node.getAttribute('dir'))
        elif node.tagName == 'navInfo':
            nav_list.add_info(_parse_for_text_tag(node),
                               node.getAttribute('xml:lang'),
                               node.getAttribute('dir'))
        elif node.tagName == 'navTarget':
            nav_list.add_target(_parse_xml_nav_target(node))

    return nav_list


def _parse_xml_nav_target(element):
    """Inspect an xml.dom.Element <navTarget> and return a NcxNavTarget
    object."""
    nav_target = NavTarget()
    nav_target.identifier = element.getAttribute('id')
    nav_target.value = element.getAttribute('value')
    nav_target.class_name = element.getAttribute('class')
    nav_target.play_order = element.getAttribute('playOrder')

    children = [e for e in element.childNodes if e.nodeType == e.ELEMENT_NODE]
    for node in children:
        if node.tagName == 'navLabel':
            nav_target.add_label(_parse_for_text_tag(node),
                                  node.getAttribute('xml:lang'),
                                  node.getAttribute('dir'))
        elif node.tagName == 'content':
            nav_target.src = node.getAttribute('src')

    return nav_target


def _parse_for_text_tag(xml_element, name=None):
    """Inspect an xml.dom.Element with a child 'name' to get its text value.

    NCX file has many element with a child likes
    "navLabel" > "text" > TEXT_NODE
    and this function allow to avoid some boilerplate code.

    First parameter must be an xml.dom.Element, having one child named by the
    second parameter (by default a "text" tag).

    If nothing is founded, an empty string '' is returned.

    Whitespaces and tabulations are stripped."""
    name = name or 'text'
    tags = [e for e in xml_element.childNodes
              if e.nodeType == e.ELEMENT_NODE and e.tagName == name]
    text = ''
    if len(tags) > 0:
        tag = tags[0]
        if tag.firstChild and tag.firstChild.data:
            tag.normalize()
            text = tag.firstChild.data.strip()
    return text


def _create_xml_element_text(data, name=None):
    """Create a <text> ... </text> Element node.

    You can use a different tag name with the name argument
    (default is "text").

    If data is None or empty, it will create an empty element tag, eg. :
    <emptyTag/> instead of <emptyTag></emptyTag>"""
    if name is None:
        name = 'text'
    doc = minidom.Document()
    element = doc.createElement(name)
    if data:
        element.appendChild(doc.createTextNode(data))
    return element


class Ncx(object):
    """Represent the structured content of a NCX file."""

    def __init__(self, nav_map=None, page_list=None):
        self.xmlns = 'http://www.daisy.org/z3986/2005/ncx/'
        self.version = '2005-1'
        self.lang = None
        self.uid = None
        self.depth = None
        self.total_page_count = None
        self.max_page_number = None
        self.generator = None
        self.title = None
        self.authors = []
        if nav_map is None:
            nav_map = NavMap()
        self.nav_map = nav_map
        if page_list is None:
            page_list = PageList()
        self.page_list = page_list
        self.nav_lists = []

    def add_nav_list(self, nav_list):
        self.nav_lists.append(nav_list)

    def as_xml_document(self):
        """Return an xml dom Document node."""
        doc = minidom.Document()
        ncx = doc.createElement('ncx')
        ncx.setAttribute('xmlns', self.xmlns)
        ncx.setAttribute('version', self.version)
        if self.lang:
            ncx.setAttribute('xml:lang', self.lang)

        # head
        ncx.appendChild(self._head_as_xml_element())

        # title
        title = doc.createElement('docTitle')
        title.appendChild(_create_xml_element_text(self.title))
        ncx.appendChild(title)

        # authors
        for text in self.authors:
            author = doc.createElement('docAuthor')
            author.appendChild(_create_xml_element_text(text))
            ncx.appendChild(author)

        # nav_map
        ncx.appendChild(self.nav_map.as_xml_element())

        # page_list
        if self.page_list:
            ncx.appendChild(self.page_list.as_xml_element())

        # nav_lists
        for nav_list in self.nav_lists:
            ncx.appendChild(nav_list.as_xml_element())

        doc.appendChild(ncx)
        return doc

    def _head_as_xml_element(self):
        """Create an xml Element node <head> with meta-data of Ncx item."""
        doc = minidom.Document()
        head = doc.createElement('head')
        if self.uid:
            head.appendChild(self._meta_as_xml_element('dtb:uid', self.uid))
        if self.depth:
            head.appendChild(self._meta_as_xml_element('dtb:depth',
                                                       self.depth))
        if self.total_page_count:
            head.appendChild(self._meta_as_xml_element('dtb:totalPageCount',
                                                       self.total_page_count))
        if self.max_page_number:
            head.appendChild(self._meta_as_xml_element('dtb:maxPageNumber',
                                                       self.max_page_number))
        if self.generator:
            head.appendChild(self._meta_as_xml_element('dtb:generator',
                                                       self.generator))
        return head

    def _meta_as_xml_element(self, name, content):
        """Create an xml Element node <meta> with attributes name & content."""
        doc = minidom.Document()
        meta = doc.createElement('meta')
        meta.setAttribute('name', name)
        meta.setAttribute('content', content)
        return meta


class NavMap(object):
    """Represente navMap tag of an NCX file."""

    def __init__(self):
        self.identifier = None
        self.labels = []
        self.infos = []
        self.nav_point = []

    def add_label(self, label, lang=None, direction=None):
        lang = lang or ''
        direction = direction or ''
        self.labels.append((label, lang, direction))

    def add_info(self, label, lang=None, direction=None):
        lang = lang or ''
        direction = direction or ''
        self.infos.append((label, lang, direction))

    def add_point(self, point):
        self.nav_point.append(point)

    def as_xml_element(self):
        """Return an xml dom Element node."""
        doc = minidom.Document()
        nav_map = doc.createElement('navMap')

        if self.identifier:
            nav_map.setAttribute('id', self.identifier)

        for text, lang, direction in self.labels:
            label = doc.createElement('navLabel')
            label.appendChild(_create_xml_element_text(text))
            if lang:
                label.setAttribute('xml:lang', lang)
            if direction:
                label.setAttribute('dir', direction)
            nav_map.appendChild(label)

        for text, lang, direction in self.infos:
            info = doc.createElement('navInfo')
            info.appendChild(_create_xml_element_text(text))
            if lang:
                info.setAttribute('xml:lang', lang)
            if direction:
                info.setAttribute('dir', direction)
            nav_map.appendChild(info)

        for nav_point in self.nav_point:
            nav_map.appendChild(nav_point.as_xml_element())

        return nav_map


class NavPoint(object):

    def __init__(self):
        self.identifier = None
        self.class_name = None
        self.play_order = None
        self.labels = []
        self.src = None
        self.nav_point = []

    def add_label(self, label, lang=None, direction=None):
        lang = lang or ''
        direction = direction or ''
        self.labels.append((label, lang, direction))

    def add_point(self, nav_point):
        self.nav_point.append(nav_point)

    def as_xml_element(self):
        """Return an xml dom Element node."""
        doc = minidom.Document()
        nav_point = doc.createElement('navPoint')

        # Attributes
        if self.identifier:
            nav_point.setAttribute('id', self.identifier)

        if self.class_name:
            nav_point.setAttribute('class', self.class_name)

        if self.play_order:
            nav_point.setAttribute('playOrder', self.play_order)

        # navLabel
        for text, lang, direction in self.labels:
            label = doc.createElement('navLabel')
            label.appendChild(_create_xml_element_text(text))
            if lang:
                label.setAttribute('xml:lang', lang)
            if direction:
                label.setAttribute('dir', direction)
            nav_point.appendChild(label)

        # content
        content = doc.createElement('content')
        content.setAttribute('src', self.src)
        nav_point.appendChild(content)

        # navPoint
        for child in self.nav_point:
            nav_point.appendChild(child.as_xml_element())

        return nav_point


class PageList(object):

    def __init__(self):
        self.identifier = None
        self.class_name = None
        self.page_target = []
        self.labels = []
        self.infos = []

    def add_label(self, label, lang=None, direction=None):
        lang = lang or ''
        direction = direction or ''
        self.labels.append((label, lang, direction))

    def add_info(self, label, lang=None, direction=None):
        lang = lang or ''
        direction = direction or ''
        self.infos.append((label, lang, direction))

    def add_target(self, page_target):
        self.page_target.append(page_target)

    def as_xml_element(self):
        """Return an xml dom Element node."""
        doc = minidom.Document()
        page_list = doc.createElement('pageList')

        # attributes
        if self.identifier:
            page_list.setAttribute('id', self.identifier)

        if self.class_name:
            page_list.setAttribute('class', self.class_name)

        # navLabel
        for text, lang, direction in self.labels:
            label = doc.createElement('navLabel')
            label.appendChild(_create_xml_element_text(text))
            if lang:
                label.setAttribute('xml:lang', lang)
            if direction:
                label.setAttribute('dir', direction)
            page_list.appendChild(label)

        # navInfo
        for text, lang, direction in self.infos:
            info = doc.createElement('navInfo')
            info.appendChild(_create_xml_element_text(text))
            if lang:
                info.setAttribute('xml:lang', lang)
            if direction:
                info.setAttribute('dir', direction)
            page_list.appendChild(info)

        # pageTarget
        for child in self.page_target:
            page_list.appendChild(child.as_xml_element())

        return page_list


class PageTarget(object):

    def __init__(self):
        self.identifier = None
        self.value = None
        self.target_type = None
        self.class_name = None
        self.play_order = None
        self.src = None
        self.labels = []

    def add_label(self, label, lang=None, direction=None):
        lang = lang or ''
        direction = direction or ''
        self.labels.append((label, lang, direction))

    def as_xml_element(self):
        """Return an xml dom Element node."""
        doc = minidom.Document()
        page_target = doc.createElement('pageTarget')

        # attributes
        if self.identifier:
            page_target.setAttribute('id', self.identifier)

        if self.value:
            page_target.setAttribute('value', self.value)

        if self.target_type:
            page_target.setAttribute('type', self.target_type)

        if self.class_name:
            page_target.setAttribute('class', self.class_name)

        if self.play_order:
            page_target.setAttribute('playOrder', self.play_order)

        # navLabel
        for text, lang, direction in self.labels:
            label = doc.createElement('navLabel')
            label.appendChild(_create_xml_element_text(text))
            if lang:
                label.setAttribute('xml:lang', lang)
            if direction:
                label.setAttribute('dir', direction)
            page_target.appendChild(label)

        # content
        content = doc.createElement('content')
        content.setAttribute('src', self.src)
        page_target.appendChild(content)

        return page_target


class NavList(object):

    def __init__(self):
        self.identifier = None
        self.class_name = None
        self.nav_target = []
        self.labels = []
        self.infos = []

    def add_label(self, label, lang=None, direction=None):
        lang = lang or ''
        direction = direction or ''
        self.labels.append((label, lang, direction))

    def add_info(self, label, lang=None, direction=None):
        lang = lang or ''
        direction = direction or ''
        self.infos.append((label, lang, direction))

    def add_target(self, nav_target):
        self.nav_target.append(nav_target)

    def as_xml_element(self):
        """Return an xml dom Element node."""
        doc = minidom.Document()
        nav_list = doc.createElement('navList')

        # attributes
        if self.identifier:
            nav_list.setAttribute('id', self.identifier)

        if self.class_name:
            nav_list.setAttribute('class', self.class_name)

        # navLabel
        for text, lang, direction in self.labels:
            label = doc.createElement('navLabel')
            label.appendChild(_create_xml_element_text(text))
            if lang:
                label.setAttribute('xml:lang', lang)
            if direction:
                label.setAttribute('dir', direction)
            nav_list.appendChild(label)

        # navInfo
        for text, lang, direction in self.infos:
            info = doc.createElement('navInfo')
            info.appendChild(_create_xml_element_text(text))
            if lang:
                info.setAttribute('xml:lang', lang)
            if direction:
                info.setAttribute('dir', direction)
            nav_list.appendChild(info)

        # navTarget
        for nav_target in self.nav_target:
            nav_list.appendChild(nav_target.as_xml_element())

        return nav_list


class NavTarget(object):

    def __init__(self):
        self.identifier = None
        self.class_name = None
        self.value = None
        self.play_order = None
        self.labels = []
        self.src = None

    def add_label(self, label, lang=None, direction=None):
        lang = lang or ''
        direction = direction or ''
        self.labels.append((label, lang, direction))

    def as_xml_element(self):
        """Return an xml dom Element node."""
        doc = minidom.Document()
        nav_target = doc.createElement('navTarget')

        # attributes
        if self.identifier:
            nav_target.setAttribute('id', self.identifier)

        if self.class_name:
            nav_target.setAttribute('class', self.class_name)

        if self.value:
            nav_target.setAttribute('value', self.value)

        if self.play_order:
            nav_target.setAttribute('playOrder', self.play_order)

        # navLabel
        for text, lang, direction in self.labels:
            label = doc.createElement('navLabel')
            label.appendChild(_create_xml_element_text(text))
            if lang:
                label.setAttribute('xml:lang', lang)
            if direction:
                label.setAttribute('dir', direction)
            nav_target.appendChild(label)

        # content
        content = doc.createElement('content')
        content.setAttribute('src', self.src)
        nav_target.appendChild(content)

        return nav_target
