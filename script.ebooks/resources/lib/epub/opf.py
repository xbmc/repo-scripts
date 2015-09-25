# -*- coding: utf-8 -*-
from __future__ import unicode_literals


"""
Python lib for reading OPF formated file for epub.

Since the "Tour" element is deprecated in Epub 2, it is not supported by this
library.

OPF epub : http://idpf.org/epub/20/spec/OPF_2.0.1_draft.htm
"""


from xml.dom import minidom


try:
    # Only for Python 2.7+
    from collections import OrderedDict
except ImportError:
    try:
        # For Python 2.6
        from ordereddict import OrderedDict
    except ImportError:
        raise ImportError(
            'You should use Python 2.7 or install `ordereddict` from pypi.')


from epub.utils import get_node_text


XMLNS_DC = 'http://purl.org/dc/elements/1.1/'
XMLNS_OPF = 'http://www.idpf.org/2007/opf'


def parse_opf(xml_string):
    package = minidom.parseString(xml_string).documentElement

    # Get Uid
    uid_id = package.getAttribute('unique-identifier')

    # Store each child nodes into a dict (metadata, manifest, spine, guide)
    data = {'metadata': None,
            'manifest': None,
            'spine': None,
            'guide': None}
    elements = [e for e in package.childNodes if e.nodeType == e.ELEMENT_NODE]
    for node in elements:
        tag = node.tagName.lower()
        if tag.startswith('opf:'):
            tag = tag[4:]
        data[tag] = node

    # Inspect metadata
    metadata = _parse_xml_metadata(data['metadata'])

    # Inspect manifest
    manifest = _parse_xml_manifest(data['manifest'])

    # Inspect spine
    spine = _parse_xml_spine(data['spine'])

    # Inspect guide if exist
    if data['guide'] is None:
        guide = None
    else:
        guide = _parse_xml_guide(data['guide'])

    opf = Opf(uid_id=uid_id,
              metadata=metadata,
              manifest=manifest,
              spine=spine,
              guide=guide)
    return opf


def _parse_xml_metadata(element):
    """Extract metadata from an xml.dom.Element object (ELEMENT_NODE)

    The "<metadata>" tag has a lot of metadatas about the epub this method
    inspect and store into object attributes (like "title" or "creator").
    """
    metadata = Metadata()

    for node in element.getElementsByTagName('dc:title'):
        metadata.add_title(get_node_text(node),
                           node.getAttribute('xml:lang'))

    for node in element.getElementsByTagName('dc:creator'):
        metadata.add_creator(get_node_text(node),
                             node.getAttribute('opf:role'),
                             node.getAttribute('opf:file-as'))

    for node in element.getElementsByTagName('dc:subject'):
        metadata.add_subject(get_node_text(node))

    for node in element.getElementsByTagName('dc:description'):
        metadata.description = get_node_text(node)

    for node in element.getElementsByTagName('dc:publisher'):
        metadata.publisher = get_node_text(node)

    for node in element.getElementsByTagName('dc:contributor'):
        metadata.add_contributor(get_node_text(node),
                                 node.getAttribute('opf:role'),
                                 node.getAttribute('opf:file-as'))

    for node in element.getElementsByTagName('dc:date'):
        metadata.add_date(get_node_text(node),
                          node.getAttribute('opf:event'))

    for node in element.getElementsByTagName('dc:type'):
        metadata.dc_type = get_node_text(node)

    for node in element.getElementsByTagName('dc:format'):
        metadata.format = get_node_text(node)

    for node in element.getElementsByTagName('dc:identifier'):
        metadata.add_identifier(get_node_text(node),
                            node.getAttribute('id'),
                            node.getAttribute('opf:scheme'))

    for node in element.getElementsByTagName('dc:source'):
        metadata.source = get_node_text(node)

    for node in element.getElementsByTagName('dc:language'):
        metadata.add_language(get_node_text(node))

    for node in element.getElementsByTagName('dc:relation'):
        metadata.relation = get_node_text(node)

    for node in element.getElementsByTagName('dc:coverage'):
        metadata.coverage = get_node_text(node)

    for node in element.getElementsByTagName('dc:rights'):
        metadata.right = get_node_text(node)

    for node in element.getElementsByTagName('meta'):
        metadata.add_meta(node.getAttribute('name'),
                          node.getAttribute('content'))

    return metadata


def _parse_xml_manifest(element):
    """Inspect an xml.dom.Element <manifest> and return a list of
    epub.EpubManifestItem object."""

    manifest = Manifest()
    for e in element.getElementsByTagName('item'):
        manifest.add_item(e.getAttribute('id'),
                          e.getAttribute('href'),
                          e.getAttribute('media-type'),
                          e.getAttribute('fallback'),
                          e.getAttribute('required-namespace'),
                          e.getAttribute('required-modules'),
                          e.getAttribute('fallback-style'))
    return manifest


def _parse_xml_spine(element):
    """Inspect an xml.dom.Element <spine> and return epub.opf.Spine object"""

    spine = Spine()
    spine.toc = element.getAttribute('toc')
    for e in element.getElementsByTagName('itemref'):
        spine.add_itemref(e.getAttribute('idref'),
                          e.getAttribute('linear').lower() != 'no')
    return spine


def _parse_xml_guide(element):
    """Inspect an xml.dom.Element <guide> and return a list of ref as tuple."""

    guide = Guide()
    for e in element.getElementsByTagName('reference'):
        guide.add_reference(e.getAttribute('href'),
                            e.getAttribute('type'),
                            e.getAttribute('title'))
    return guide


class Opf(object):
    """Represent an OPF formated file.

    OPF is an xml formated file, used in the epub spec."""

    def __init__(self, uid_id=None, version=None, xmlns=None,
                 metadata=None, manifest=None, spine=None, guide=None):
        self.uid_id = uid_id
        self.version = version if version else '2.0'
        self.xmlns = xmlns if xmlns else XMLNS_OPF

        if metadata is None:
            self.metadata = Metadata()
        else:
            self.metadata = metadata
        if manifest is None:
            self.manifest = Manifest()
        else:
            self.manifest = manifest
        if spine is None:
            self.spine = Spine()
        else:
            self.spine = spine
        if guide is None:
            self.guide = Guide()
        else:
            self.guide = guide

    def as_xml_document(self):
        doc = minidom.Document()
        package = doc.createElement('package')
        package.setAttribute('version', self.version)
        package.setAttribute('unique-identifier', self.uid_id)
        package.setAttribute('xmlns', self.xmlns)
        package.appendChild(self.metadata.as_xml_element())
        package.appendChild(self.manifest.as_xml_element())
        package.appendChild(self.spine.as_xml_element())
        package.appendChild(self.guide.as_xml_element())
        doc.appendChild(package)
        return doc


class Metadata(object):
    """Represent an epub's metadatas set.

    See http://idpf.org/epub/20/spec/OPF_2.0.1_draft.htm#Section2.2"""

    def __init__(self):
        self.titles = []
        self.creators = []
        self.subjects = []
        self.description = None
        self.publisher = None
        self.contributors = []
        self.dates = []
        self.dc_type = None
        self.format = None
        self.identifiers = []
        self.source = None
        self.languages = []
        self.relation = None
        self.coverage = None
        self.right = None
        self.metas = []

    def add_title(self, title, lang=None):
        lang = lang or ''
        self.titles.append((title, lang))

    def add_creator(self, name, role=None, file_as=None):
        role = role or ''
        file_as = file_as or ''
        self.creators.append((name, role, file_as))

    def add_subject(self, subject):
        self.subjects.append(subject)

    def add_contributor(self, name, role=None, file_as=None):
        role = role or ''
        file_as = file_as or ''
        self.contributors.append((name, role, file_as))

    def add_date(self, date, event=None):
        event = event or ''
        self.dates.append((date, event))

    def add_identifier(self, content, identifier=None, scheme=None):
        identifier = identifier or ''
        scheme = scheme or ''
        self.identifiers.append((content, identifier, scheme))

    def add_language(self, lang):
        self.languages.append(lang)

    def add_meta(self, name, content):
        self.metas.append((name, content))

    def get_isbn(self):
        l = [x[0] for x in self.identifiers if x[2].lower() == 'isbn']
        isbn = None
        if l:
            isbn = l[0]
        return isbn

    def as_xml_element(self):
        """Return an xml dom Element node."""
        doc = minidom.Document()
        metadata = doc.createElement('metadata')
        metadata.setAttribute('xmlns:dc', XMLNS_DC)
        metadata.setAttribute('xmlns:opf', XMLNS_OPF)

        for text, lang in self.titles:
            title = doc.createElement('dc:title')
            if lang:
                title.setAttribute('xml:lang', lang)
            title.appendChild(doc.createTextNode(text))
            metadata.appendChild(title)

        for name, role, file_as in self.creators:
            creator = doc.createElement('dc:creator')
            if role:
                creator.setAttribute('opf:role', role)
            if file_as:
                creator.setAttribute('opf:file-as', file_as)
            creator.appendChild(doc.createTextNode(name))
            metadata.appendChild(creator)

        for text in self.subjects:
            subject = doc.createElement('dc:subject')
            subject.appendChild(doc.createTextNode(text))
            metadata.appendChild(subject)

        if self.description:
            description = doc.createElement('dc:description')
            description.appendChild(doc.createTextNode(self.description))
            metadata.appendChild(description)

        if self.publisher:
            publisher = doc.createElement('dc:publisher')
            publisher.appendChild(doc.createTextNode(self.publisher))
            metadata.appendChild(publisher)

        for name, role, file_as in self.contributors:
            contributor = doc.createElement('dc:contributor')
            if role:
                contributor.setAttribute('opf:role', role)
            if file_as:
                contributor.setAttribute('opf:file-as', file_as)
            contributor.appendChild(doc.createTextNode(name))
            metadata.appendChild(contributor)

        for text, event in self.dates:
            date = doc.createElement('dc:date')
            if event:
                date.setAttribute('opf:event', event)
            date.appendChild(doc.createTextNode(text))
            metadata.appendChild(date)

        if self.dc_type:
            dc_type = doc.createElement('dc:type')
            dc_type.appendChild(doc.createTextNode(self.dc_type))
            metadata.appendChild(dc_type)

        if self.format:
            dc_format = doc.createElement('dc:format')
            dc_format.appendChild(doc.createTextNode(self.format))
            metadata.appendChild(dc_format)

        for text, identifier, scheme in self.identifiers:
            dc_identifier = doc.createElement('dc:identifier')
            if identifier:
                dc_identifier.setAttribute('id', identifier)
            if scheme:
                dc_identifier.setAttribute('opf:scheme', scheme)
            dc_identifier.appendChild(doc.createTextNode(text))
            metadata.appendChild(dc_identifier)

        if self.source:
            source = doc.createElement('dc:source')
            source.appendChild(doc.createTextNode(self.source))
            metadata.appendChild(source)

        for text in self.languages:
            language = doc.createElement('dc:language')
            language.appendChild(doc.createTextNode(text))
            metadata.appendChild(language)

        if self.relation:
            relation = doc.createElement('dc:relation')
            relation.appendChild(doc.createTextNode(self.relation))
            metadata.appendChild(relation)

        if self.coverage:
            coverage = doc.createElement('dc:coverage')
            coverage.appendChild(doc.createTextNode(self.coverage))
            metadata.appendChild(coverage)

        if self.right:
            right = doc.createElement('dc:rights')
            right.appendChild(doc.createTextNode(self.right))
            metadata.appendChild(right)

        for name, content in self.metas:
            meta = doc.createElement('meta')
            meta.setAttribute('name', name)
            meta.setAttribute('content', content)
            metadata.appendChild(meta)

        return metadata


class Manifest(OrderedDict):

    def __contains__(self, item):
        if hasattr(item, 'identifier'):
            return super(Manifest, self).__contains__(item.identifier)
        else:
            return super(Manifest, self).__contains__(item)

    def __setitem__(self, key, value):
        if hasattr(value, 'identifier') and hasattr(value, 'href'):
            if value.identifier == key:
                super(Manifest, self).__setitem__(key, value)
            else:
                raise ValueError('Value\'s id is different from insert key.')
        else:
            requierements = 'id and href attributes'
            msg = 'Value does not fit the requirement (%s).' % requierements
            raise ValueError(msg)

    def add_item(self, identifier, href, media_type=None, fallback=None,
                 required_namespace=None, required_modules=None,
                 fallback_style=None):
        item = ManifestItem(identifier, href, media_type,
                            fallback, required_namespace, required_modules,
                            fallback_style)
        self.append(item)

    def append(self, item):
        if hasattr(item, 'identifier') and \
           hasattr(item, 'href') and \
           hasattr(item, 'as_xml_element'):
            self.__setitem__(item.identifier, item)
        else:
            raise ValueError('Manifest item must have [identifier, href, ' + \
                             'as_xml_element()] attributes and method.')

    def as_xml_element(self):
        """Return an xml dom Element node."""
        doc = minidom.Document()
        manifest = doc.createElement('manifest')

        for item in self.values():
            manifest.appendChild(item.as_xml_element())

        return manifest


class ManifestItem(object):
    """
    Represent an item from the epub's manifest.

    """

    def __init__(self, identifier, href, media_type=None, fallback=None,
                 required_namespace=None, required_modules=None,
                 fallback_style=None):
        self.identifier = identifier
        self.href = href
        self.media_type = media_type
        self.fallback = fallback
        self.required_namespace = required_namespace
        self.required_modules = required_modules
        self.fallback_style = fallback_style

    def as_xml_element(self):
        """Return an xml dom Element node."""

        item = minidom.Document().createElement("item")

        item.setAttribute('id', self.identifier)
        item.setAttribute('href', self.href)
        if self.media_type:
            item.setAttribute('media-type', self.media_type)
        if self.fallback:
            item.setAttribute('fallback', self.fallback)
        if self.required_namespace:
            item.setAttribute('required-namespace', self.required_namespace)
        if self.required_modules:
            item.setAttribute('required-modules', self.required_modules)
        if self.fallback_style:
            item.setAttribute('fallback-style', self.fallback_style)

        return item


class Spine(object):

    def __init__(self, toc=None, itemrefs=None):
        self.toc = toc
        if itemrefs is None:
            self.itemrefs = []
        else:
            self.itemrefs = itemrefs

    def add_itemref(self, idref, linear=True):
        self.append((idref, linear))

    def append(self, itemref):
        self.itemrefs.append(itemref)

    def as_xml_element(self):
        doc = minidom.Document()
        spine = doc.createElement('spine')
        spine.setAttribute('toc', self.toc)

        for idref, linear in self.itemrefs:
            itemref = doc.createElement('itemref')
            itemref.setAttribute('idref', idref)
            if not linear:
                itemref.setAttribute('linear', 'no')
            spine.appendChild(itemref)

        return spine


class Guide(object):

    def __init__(self):
        self.references = []

    def add_reference(self, href, ref_type=None, title=None):
        self.append((href, ref_type, title))

    def append(self, reference):
        self.references.append(reference)

    def as_xml_element(self):
        doc = minidom.Document()
        guide = doc.createElement('guide')

        for href, ref_type, title in self.references:
            reference = doc.createElement('reference')
            if type:
                reference.setAttribute('type', ref_type)
            if title:
                reference.setAttribute('title', title)
            if href:
                reference.setAttribute('href', href)
            guide.appendChild(reference)

        return guide
