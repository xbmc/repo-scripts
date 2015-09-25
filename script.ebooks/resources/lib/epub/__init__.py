# -*- coding: utf-8 -*-
# https://bitbucket.org/exirel/epub
"""Library to open and read files in the epub version 2."""
from __future__ import unicode_literals


__author__ = 'Florian Strzelecki <florian.strzelecki@gmail.com>'
__version__ = '0.5.3'
__all__ = ['opf', 'ncx', 'utils']


import os
import shutil
import tempfile
import uuid
import warnings
import zipfile

from xml.dom import minidom

from . import ncx, opf, utils


MIMETYPE_EPUB = 'application/epub+zip'
MIMETYPE_OPF = 'application/oebps-package+xml'
MIMETYPE_NCX = 'application/x-dtbncx+xml'

DEFAULT_OPF_PATH = 'OEBPS/content.opf'
DEFAULT_NCX_PATH = 'toc.ncx'


def open(filename, mode=None):
    """Open an epub file and return an EpubFile object"""
    warnings.warn('Function `epub.open` is deprecated since 0.5.0.',
                  DeprecationWarning)
    return open_epub(filename, mode)


def open_epub(filename, mode=None):
    return EpubFile(filename, mode)


class BadEpubFile(zipfile.BadZipfile):
    pass


class EpubFile(zipfile.ZipFile):
    """Represent an epub zip file, as described in version 2.0.1 of epub spec.

    This class allow an access throught a low-level API to the epub real file.
    It extends zipfile.ZipFile class and modify only a little some of its
    behavior.

    See http://idpf.org/epub/201 for more information about Epub 2.0.1.

    """
    @property
    def content_path(self):
        """Return the content path, ie, the path relative to OPF file.

        If OPF file is located in `OEBPS/content.opf`, then `content_path` is
        equal to `OEBPS`.

        """
        return os.path.dirname(self.opf_path).replace('\\', '/')

    def __init__(self, filename, mode=None):
        """Open the Epub zip file with mode read "r", write "w" or append "a".
        """
        mode = mode or 'r'
        zipfile.ZipFile.__init__(self, filename, mode)
        self.uid = None
        self.opf_path = None
        self.opf = None
        self.toc = None

        if self.mode == 'r':
            self._init_read()
        elif self.mode == 'w':
            self._init_new()
        elif self.mode == 'a':
            if len(self.namelist()) == 0:
                self._init_new()
            else:
                self._init_read()

    def _init_new(self):
        """Build an empty epub archive."""
        # Write mimetype file: 'application/epub+zip'
        self.writestr('mimetype', MIMETYPE_EPUB)
        # Default path for opf
        self.opf_path = DEFAULT_OPF_PATH
        # Uid & Uid's id
        uid_id = 'BookId'
        self.uid = '%s' % uuid.uuid4()
        # Create metadata, manifest, and spine, as minimalist as possible
        metadata = opf.Metadata()
        metadata.add_identifier(self.uid, uid_id, 'uid')
        manifest = opf.Manifest()
        manifest.add_item('ncx', 'toc.ncx', MIMETYPE_NCX)
        spine = opf.Spine('ncx')
        # Create Opf object
        self.opf = opf.Opf(uid_id=uid_id,
                           metadata=metadata, manifest=manifest, spine=spine)
        # Create Ncx object
        self.toc = ncx.Ncx()
        self.toc.uid = self.uid

    def _init_read(self):
        """Get content from existing epub file"""
        # Read container.xml to get OPF xml file path
        xmlstring = self.read('META-INF/container.xml')
        container_xml = minidom.parseString(xmlstring).documentElement

        for element in container_xml.getElementsByTagName('rootfile'):
            if element.getAttribute('media-type') == MIMETYPE_OPF:
                # Only take the first full-path available
                self.opf_path = element.getAttribute('full-path')
                break

        # Read OPF xml file
        xml_string = self.read(self.opf_path)
        self.opf = opf.parse_opf(xml_string)
        uids = [x for x in self.opf.metadata.identifiers
                      if x[1] == self.opf.uid_id]
        if uids:
            self.uid = uids[0]
        else:
            self.uid = None
            warnings.warn('The ePub does not define any uid', SyntaxWarning)

        item_toc = self.get_item(self.opf.spine.toc)

        # Inspect NCX toc file
        self.toc = None
        if item_toc is not None:
            self.toc = ncx.parse_toc(self.read_item(item_toc))
        else:
            warnings.warn('The ePub does not define any NCX file',
                          SyntaxWarning)
            self.toc = ncx.Ncx()
            self.toc.uid = self.uid

    def close(self):
        if self.fp is None:
            return
        if self.mode in ('w', 'a'):
            self._write_close()
        zipfile.ZipFile.close(self)

    def remove_paths(self, paths):
        """Remove files from the archive

        Warning: This will be slow, it needs to recreate from scratch the
        complete archive.

        This method (well, the whole behavior of "write epub file") needs
        a rework in a future version.

        """
        with tempfile.NamedTemporaryFile('rb', delete=False) as temp:
            with zipfile.ZipFile(temp.name, 'w') as new_zip:
                for item in self.infolist():
                    if item.filename not in paths:
                        new_zip.writestr(item, self.read(item.filename))
            zipfile.ZipFile.close(self)
            shutil.move(temp.name, self.filename)
            zipfile.ZipFile.__init__(self, self.filename, self.mode)

    def _write_close(self):
        """Handle writes when closing epub.

        Both new file mode (w) and append file mode (a), some files must be
        generated: container, OPF, and NCX.

        """
        item_toc = self.get_item(self.opf.spine.toc)

        # Remove the old files
        to_remove = ['META-INF/container.xml', self.opf_path]
        if item_toc:
            to_remove.append(
                # Replace \ by /, no matter what OS's separator could be
                os.path.join(self.content_path,
                             item_toc.href).replace('\\', '/')
            )

        self.remove_paths(to_remove)

        # Write META-INF/container.xml
        self.writestr('META-INF/container.xml',
                      self._build_container().encode('utf-8'))
        # Write OPF File
        self.writestr(self.opf_path,
                      self.opf.as_xml_document().toxml().encode('utf-8'))
        # Write NCX File if exist
        if item_toc:
            toc_path = os.path.join(
                self.content_path, item_toc.href
            ).replace('\\', '/')
            toc_content = self.toc.as_xml_document().toxml().encode('utf-8')

            self.writestr(toc_path, toc_content)

    def _build_container(self):
        """Build a simple XML container as in epub 2.0.1 specification."""
        template = """<?xml version="1.0" encoding="UTF-8"?>
    <container version="1.0"
               xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
        <rootfiles>
             <rootfile full-path="%s"
                       media-type="application/oebps-package+xml"/>
        </rootfiles>
    </container>"""
        return template % self.opf_path

    def add_item(self, filename, manifest_item,
                 append_to_spine=False, is_linear=True):
        """Add a file to epub.

        A manifest item must be provide to describe it.

        This function will raise a RuntimeError if epub is already closed. It
        will raise an IOError if epub is open in read-only (`r` mode).

        Optional: you can use `append_to_spine` flag (default=False) to append
        item to spine, and use `is_linear` (default=True) to specify if it is
        linear or not.

        """
        self.check_mode_write()
        self.opf.manifest.append(manifest_item)

        write_path = os.path.join(
            self.content_path, manifest_item.href
        ).replace('\\', '/')

        self.write(filename, write_path)

        if append_to_spine:
            self.opf.spine.add_itemref(manifest_item.identifier, is_linear)

    def check_mode_write(self):
        """Raise error if epub file is not writable.

        Raise RuntimeError if file is already closed.

        Raise IOError if file is opened read-only.

        """
        if not self.fp:
            raise RuntimeError(
                  'Attempt to write to EPUB file that was already closed')

        if self.mode == 'r':
            raise IOError(
                  'Attempt to write to EPUB file that was open as read-only.')

    # extract method is  zipfile.ZipFile.extract(member[, path[, pwd]])

    def extract_item(self, item, to_path=None):
        """Extract an item from its href in epub to `to_path` location.
        """
        path = item if not hasattr(item, 'href') else item.href
        member_path = os.path.join(self.content_path, path).replace('\\', '/')
        # ROB FIX: zip does not like relative paths /../ etc
        if '../' in member_path:
            member_path = os.path.normpath(member_path)

        return self.extract(member=member_path, path=to_path)

    def get_item(self, identifier):
        """Get an item from manifest through its "id" attribute.

        Return an EpubManifestItem if found, else None.

        """
        return self.opf.manifest.get(identifier, None)

    def get_item_by_href(self, href):
        """Get an item from manifest through its "href" attribute.

        Return an EpubManifestItem if found, else None.

        """
        found = [x for x in self.opf.manifest.values() if x.href == href]
        size = len(found)
        if size == 1:
            return found[0]
        elif size > 1:
            raise LookupError('Multiple items are found with this href.')
        else:
            return None

    # read method is zipfile.ZipFile.read(path)

    def read_item(self, item):
        """Read a file from the epub zipfile container.

        "item" parameter can be the relative path to the opf file or an
        EpubManifestItem object.

        Html fragments are not acceptable : the path must be exactly the same
        as indicated in the opf file.

        """
        path = item
        if hasattr(item, 'href'):
            path = item.href

        # Replace \ by /, as ZipFile always uses / as path separator.
        fullpath = os.path.join(self.content_path, path).replace('\\', '/')

        if '../' in path:
            # ROB FIX: zip does not like relative paths /../ etc
            fullpath = os.path.normpath(fullpath)

        return self.read(fullpath)


class Book(object):
    """This class is an attempt to expose a simpler object model than EpubFile.

    WARNING: Work in progress. Use with caution.

    """

    def __init__(self, epub_file):
        self.epub_file = epub_file

    @property
    def creators(self):
        return self.epub_file.opf.metadata.creators

    @property
    def description(self):
        return self.epub_file.opf.metadata.description

    @property
    def isbn(self):
        return self.epub_file.opf.metadata.get_isbn()

    @property
    def publisher(self):
        return self.epub_file.opf.metadata.publisher

    @property
    def contributors(self):
        return self.epub_file.opf.metadata.contributors

    @property
    def dates(self):
        return self.epub_file.opf.metadata.dates

    @property
    def dc_type(self):
        return self.epub_file.opf.metadata.dc_type

    @property
    def dc_format(self):
        return self.epub_file.opf.metadata.format

    @property
    def identifiers(self):
        return self.epub_file.opf.metadata.identifiers

    @property
    def source(self):
        return self.epub_file.opf.metadata.source

    @property
    def languages(self):
        return self.epub_file.opf.metadata.languages

    @property
    def relation(self):
        return self.epub_file.opf.metadata.relation

    @property
    def coverage(self):
        return self.epub_file.opf.metadata.coverage

    @property
    def right(self):
        return self.epub_file.opf.metadata.right

    @property
    def metas(self):
        return self.epub_file.opf.metadata.metas

    @property
    def subjects(self):
        return self.epub_file.opf.metadata.subjects

    @property
    def titles(self):
        return self.epub_file.opf.metadata.titles

    @property
    def chapters(self):
        """
        Return a list of linear chapter from spine.
        """
        return [BookChapter(self, identifier)
                for identifier, linear in self.epub_file.opf.spine.itemrefs
                if linear]

    @property
    def extra_chapters(self):
        """
        Return a list of non-linear chapter from spine.
        """
        return [BookChapter(self, identifier)
                for identifier, linear in self.epub_file.opf.spine.itemrefs
                if not linear]


class BookChapter(object):

    @property
    def identifier(self):
        return self._manifest_item.identifier

    def __init__(self, book, identifier, fragment=None):
        self._book = book
        self._manifest_item = self._book.epub_file.get_item(identifier)
        self._fragment = fragment

    def read(self):
        return self._book.epub_file.read_item(self._manifest_item)
