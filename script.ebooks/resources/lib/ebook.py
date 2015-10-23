# -*- coding: utf-8 -*-
import os
import re
import traceback
import shutil
import xml.etree.ElementTree as ET
import xbmc
import xbmcvfs
import xbmcaddon

__addon__ = xbmcaddon.Addon(id='script.ebooks')
__cwd__ = __addon__.getAddonInfo('path').decode("utf-8")
__resource__ = xbmc.translatePath(os.path.join(__cwd__, 'resources').encode("utf-8")).decode("utf-8")
__media__ = xbmc.translatePath(os.path.join(__resource__, 'media').encode("utf-8")).decode("utf-8")

# Import the common settings
from settings import Settings
from settings import log
from settings import os_path_join
from settings import os_path_split
from settings import dir_exists

import epub
from mobi import Mobi
from kiehinen.ebook import Book as KMobi
from kindleunpack import kindleunpack

from cStringIO import StringIO
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfparser import PDFParser
from pdfminer.pdftypes import resolve1
from pdfminer.pdfpage import PDFPage
from pdfminer.psparser import PSLiteral
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams


# Generic class for handling EBook details
class EBookBase():
    def __init__(self, eBookFilePath, removeFileWhenComplete=False):
        log("EBookBase: Loading book %s" % eBookFilePath)
        self.filePath = eBookFilePath
        self.fileName = os_path_split(eBookFilePath)[-1]
        self.isTempBookFile = removeFileWhenComplete

    @staticmethod
    def createEBookObject(filePath):
        localFilePath = filePath
        removeWhenComplete = False
        if filePath.startswith('smb://') or filePath.startswith('nfs://'):
            try:
                # Copy the file to the local disk
                justFileName = os_path_split(filePath)[-1]
                copiedFile = os_path_join(Settings.getTempLocation(), justFileName)
                copy = xbmcvfs.copy(filePath, copiedFile)
                if copy:
                    log("EBookBase: copy successful for %s" % copiedFile)
                    localFilePath = copiedFile
                    removeWhenComplete = True
                else:
                    log("EBookBase: copy failed from %s to %s" % (filePath, copiedFile))
            except:
                log("EBookBase: Failed to copy file %s to local directory" % filePath)

        bookType = None
        # Check which type of EBook it is
        if filePath.lower().endswith('.epub'):
            bookType = EPubEBook(localFilePath, removeWhenComplete)
        elif filePath.lower().endswith('.mobi'):
            bookType = MobiEBook(localFilePath, removeWhenComplete)
        elif filePath.lower().endswith('.pdf'):
            bookType = PdfEBook(localFilePath, removeWhenComplete)
        else:
            log("EBookBase: Unknown book type for %s" % filePath)

        return bookType

    @staticmethod
    def getCoverImage(filePath, eBookFileName):
        # Check if there is a cached version
        coverTargetName = None
        fullpathLocalImage, bookExt = os.path.splitext(filePath)
        fullpathLocalImage = "%s.jpg" % fullpathLocalImage

        if xbmcvfs.exists(fullpathLocalImage):
            log("EBookBase: Found local cached image %s" % fullpathLocalImage)
            return fullpathLocalImage

        # Check for a cached cover
        coverTargetName = EBookBase.getCachedCover(eBookFileName)

        # If we reach here, then there was no cached cover image, so we need to extract one
        if coverTargetName in [None, ""]:
            ebook = EBookBase.createEBookObject(filePath)
            coverTargetName = ebook.extractCoverImage()
            ebook.tidyUp()
            del ebook

        return coverTargetName

    def tidyUp(self):
        # If we had to copy the file locally, make sure we delete it
        if self.isTempBookFile:
            if xbmcvfs.exists(self.filePath):
                xbmcvfs.delete(self.filePath)

    def getTitle(self):
        return ""

    def getAuthor(self):
        return ""

    # Checks the cache to see if there is a cover for this ebook
    @staticmethod
    def getCachedCover(fileName):
        cachedCover = None
        # check if the directory exists before searching
        dirs, files = xbmcvfs.listdir(Settings.getCoverCacheLocation())
        for aFile in files:
            # Get the filename without extension
            coverSrc, ext = os.path.splitext(aFile)

            # Get the name that the cached cover will have been stored as
            targetSrc, bookExt = os.path.splitext(fileName)

            if targetSrc == coverSrc:
                cachedCover = os_path_join(Settings.getCoverCacheLocation(), aFile)
                log("EBookBase: Cached cover found: %s" % cachedCover)

        # There is a special case for PDF files that we have a default image
        if (cachedCover is None) and fileName.endswith('.pdf'):
            cachedCover = os.path.join(__media__, 'pdf_icon.png')

        return cachedCover

    # Extracts the cover image from the ebook to the supplied location
    def extractCoverImage(self):
        return None

    def getChapterDetails(self):
        return []

    def getChapterContents(self, chapterLink):
        return ""

    # Get the text for a given chapter
    def convertHtmlIntoKodiText(self, htmlText):
        # Remove the header section of the page
        plainText = re.sub("<head>.*?</head>", "", htmlText, flags=re.DOTALL)
        # Replace the bold tags
        plainText = plainText.replace('<br></br><br></br>', '<p></p>')
        plainText = plainText.replace('<b>', '[B]')
        plainText = plainText.replace('</b>', '[/B]')
        plainText = plainText.replace('<B>', '[B]')
        plainText = plainText.replace('</B>', '[/B]')
        # Replace italic tags
        plainText = plainText.replace('<i>', '[I]')
        plainText = plainText.replace('</i>', '[/I]')
        plainText = plainText.replace('<I>', '[I]')
        plainText = plainText.replace('</I>', '[/I]')
        # Add an extra line for paragraphs
        plainText = plainText.replace('</p>', '</p>\n')
        # The html &nbsp; is not handle s well by ElementTree, so replace
        # it with a space before we start
        plainText = plainText.replace('&nbsp;', ' ')
        # Replace headers <h2> etc
        plainText = plainText.replace('<h1', '[B]<h1')
        plainText = plainText.replace('</h1>', '</h1>[/B]')
        plainText = plainText.replace('<h2', '[B]<h2')
        plainText = plainText.replace('</h2>', '</h2>[/B]')
        plainText = plainText.replace('<h3', '[B]<h3')
        plainText = plainText.replace('</h3>', '</h3>[/B]')
        plainText = plainText.replace('<h4', '[I][B]<h4')
        plainText = plainText.replace('</h4>', '</h4>[/B][/I]')

        try:
            plainText = ''.join(ET.fromstring(plainText).itertext())
        except:
            log("EBookBase: Failed to strip html text with ElementTree, error: %s" % traceback.format_exc())
            log("EBookBase: Using regex for content handling")
            plainText = re.sub(r'<[^>]+>', '', plainText, flags=re.DOTALL)

        # Replace any quotes or other escape characters
        plainText = plainText.replace('&quote;', '"')
        plainText = plainText.replace('&nbsp;', ' ')

        # Need to remove double tags as they are not handled very well when
        # displayed, they do not get nested, so the first end will close all
        # instances of this tag
        plainText = plainText.replace('[B][B]', '[B]')
        plainText = plainText.replace('[/B][/B]', '[/B]')
        plainText = plainText.replace('[I][I]', '[I]')
        plainText = plainText.replace('[/I][/I]', '[/I]')

        # Remove empty space between tags, where there is no content
        plainText = re.sub("\[B]\s*\[/B]", "", plainText, flags=re.DOTALL)
        plainText = re.sub("\[I\]\s*\[/I\]", "", plainText, flags=re.DOTALL)

        # Remove blank lines at the start of the chapter
        plainText = plainText.lstrip('\n')

        return plainText

    def getFallbackTitle(self):
        # Remove anything after the final dot
        sections = self.fileName.split('.')
        sections.pop()
        # Replace the dots with spaces
        return ' '.join(sections)


# Class to process the mobi formatted books
class MobiEBook(EBookBase):
    def __init__(self, filePath, removeFileWhenComplete=False):
        EBookBase.__init__(self, filePath, removeFileWhenComplete)
        self.book = None
        self.bookFallback = None

        try:
            self.book = KMobi(self.filePath)
        except:
            log("MobiEBook: Failed to process eBook %s with error: %s" % (self.filePath, traceback.format_exc()), xbmc.LOGERROR)

    # A secondary Mobi reader, if the first can not handle the given file
    def _getFallbackReader(self):
        if self.bookFallback is None:
            try:
                self.bookFallback = Mobi(self.filePath)
                # Need to parse all the header data in the book
                self.bookFallback.parse()
            except:
                log("MobiEBook: Expected exception for secondary reader, book %s with error: %s" % (self.filePath, traceback.format_exc()), xbmc.LOGERROR)
        return self.bookFallback

    def getTitle(self):
        # Default the title to the filename - this should be overwritten
        title = None
        if self.book is not None:
            try:
                title = self.book.title
            except:
                log("MobiEBook: Failed to get title for mobi %s with error: %s" % (self.filePath, traceback.format_exc()), xbmc.LOGERROR)

        # If we failed to get the title, use the fallback Mobi reader
        if title in [None, ""]:
            fallback = self._getFallbackReader()
            if fallback is not None:
                try:
                    title = fallback.title()
                except:
                    log("MobiEBook: Failed to get title using fallback mobi %s with error: %s" % (self.filePath, traceback.format_exc()), xbmc.LOGERROR)

        if title in [None, ""]:
            title = self.getFallbackTitle()

        log("MobiEBook: Title is %s for book %s" % (title, self.filePath))
        return title

    def getAuthor(self):
        author = ""
        if self.book is not None:
            try:
                author = self.book.author
            except:
                log("MobiEBook: Failed to get author for mobi %s with error: %s" % (self.filePath, traceback.format_exc()), xbmc.LOGERROR)

        # If we failed to get the author, use the fallback Mobi reader
        if author in [None, ""]:
            fallback = self._getFallbackReader()
            if fallback is not None:
                try:
                    author = fallback.author()
                except:
                    log("MobiEBook: Failed to get author using fallback mobi %s with error: %s" % (self.filePath, traceback.format_exc()), xbmc.LOGERROR)

        log("MobiEBook: Author is %s for book %s" % (author, self.filePath))
        return author

    def extractCoverImage(self):
        log("MobiEBook: Extracting cover for %s" % self.filePath)
        # Get the location that the book is to be extracted to
        extractDir = os_path_join(Settings.getTempLocation(), 'mobi_extracted')

        # Check if the mobi extract directory already exists
        if dir_exists(extractDir):
            try:
                shutil.rmtree(extractDir, True)
            except:
                log("MobiEBook: Failed to delete directory %s" % extractDir)

        # Extract the contents of the book so we can get the cover image
        try:
            kindleunpack.unpackBook(self.filePath, extractDir, None, '2', True)
        except:
            log("MobiEBook: Failed to extract cover for %s with error: %s" % (self.filePath, traceback.format_exc()), xbmc.LOGERROR)

        coverTargetName = None
        if dir_exists(extractDir):
            coverImages = self._findCoverImage(extractDir)

            if len(coverImages) > 0:
                coverImageSrc = coverImages[0]
                log("MobiEBook: Found cover file %s" % coverImageSrc)
                coverFileName, oldExt = os.path.splitext(self.fileName)
                cacheCoverName = "%s.jpg" % coverFileName
                coverTargetName = os_path_join(Settings.getCoverCacheLocation(), cacheCoverName)

                # Now move the file to the covers cache directory
                copy = xbmcvfs.copy(coverImageSrc, coverTargetName)
                if copy:
                    log("MobiEBook: copy successful for %s" % coverTargetName)
                else:
                    log("MobiEBook: copy failed from %s to %s" % (coverImageSrc, coverTargetName))
            else:
                log("MobiEBook: No cover image found for %s" % self.filePath)

            # Now tidy up the extracted data
            try:
                shutil.rmtree(extractDir, True)
            except:
                log("MobiEBook: Failed to tidy up directory %s" % extractDir)
        else:
            log("MobiEBook: Failed to extract Mobi file %s" % self.filePath)

        return coverTargetName

    def _findCoverImage(self, dirPath):
        coverImages = []
        dirs, files = xbmcvfs.listdir(dirPath)

        for aFile in files:
            if aFile.startswith('cover') and (aFile.endswith('jpg') or aFile.endswith('jpeg') or aFile.endswith('png')):
                # Add this image to the list
                coverImages.append(os_path_join(dirPath, aFile))

        # Now check any of the directories
        for aDir in dirs:
            coverImages = coverImages + self._findCoverImage(os_path_join(dirPath, aDir))

        return coverImages

    def getChapterDetails(self):
        log("MobiEBook: Extracting chapter list for %s" % self.filePath)
        # Get the location that the book is to be extracted to
        extractDir = os_path_join(Settings.getTempLocation(), 'mobi_extracted')

        # Check if the mobi extract directory already exists
        if dir_exists(extractDir):
            try:
                shutil.rmtree(extractDir, True)
            except:
                log("MobiEBook: Failed to delete directory %s" % extractDir)

        # Extract the contents of the book so we can get the cover image
        try:
            kindleunpack.unpackBook(self.filePath, extractDir, None, '2', True)
        except:
            log("MobiEBook: Failed to unpack book for %s with error: %s" % (self.filePath, traceback.format_exc()), xbmc.LOGERROR)

        chapterDetails = []
        if dir_exists(extractDir):
            tocNcx = self._findTocNcx(extractDir)

            if tocNcx not in [None, ""]:
                log("MobiEBook: TOC file found: %s" % tocNcx)
                # Now we have the TOC file, we need to parse it, we already have
                # a tool for that, as it is the ePub format
                try:
                    # Read the contents of the TOC file into a string
                    tocFile = xbmcvfs.File(tocNcx, 'r')
                    tocStr = tocFile.read()
                    tocFile.close()

                    # Now load it into the parser
                    toc = epub.ncx.parse_toc(tocStr)

                    # Get all the chapters
                    for navPoint in toc.nav_map.nav_point:
                        # Get each of the chapter labels
                        for aLabelGroup in navPoint.labels:
                            if aLabelGroup not in [None, ""]:
                                for aLabel in aLabelGroup:
                                    if aLabel not in [None, ""]:
                                        log("MobiEBook: Adding chapter %s with src %s" % (aLabel, navPoint.src))
                                        detail = {'title': aLabel.encode("utf-8"), 'link': navPoint.src}
                                        chapterDetails.append(detail)
                                        # Only need the first string for this label group
                                        break
                    del toc
                except:
                    log("MobiEBook: Failed to process TOC %s with error: %s" % (tocNcx, traceback.format_exc()), xbmc.LOGERROR)

            else:
                log("MobiEBook: Failed to find TOC file")

            # Check if we have any chapters, if there are none, then we should show the whole book
            if (len(chapterDetails) < 1) or (not Settings.onlyShowWholeBookIfChapters()):
                htmlFiles = self._findHtmlFiles(extractDir)

                # Check if there are any html files
                if len(htmlFiles) > 0:
                    keyHtmlFile = None
                    for htmlFile in htmlFiles:
                        if htmlFile.endswith('book.html'):
                            keyHtmlFile
                            break
                    if keyHtmlFile is None:
                        keyHtmlFile = htmlFiles[0]

                    detail = {'title': __addon__.getLocalizedString(32016), 'link': keyHtmlFile}
                    chapterDetails.insert(0, detail)

            # Now tidy up the extracted data
            try:
                shutil.rmtree(extractDir, True)
            except:
                log("MobiEBook: Failed to tidy up directory %s" % extractDir)
        else:
            log("MobiEBook: Failed to extract Mobi file %s" % self.filePath)

        return chapterDetails

    def _findTocNcx(self, dirPath):
        tocNcx = None
        dirs, files = xbmcvfs.listdir(dirPath)

        for aFile in files:
            if aFile.lower() == 'toc.ncx':
                # Found the table of contents file
                tocNcx = os_path_join(dirPath, aFile)
                break

        # Now check any of the directories
        for aDir in dirs:
            if tocNcx is None:
                tocNcx = self._findTocNcx(os_path_join(dirPath, aDir))

        return tocNcx

    def _findHtmlFiles(self, dirPath):
        htmlFiles = []
        dirs, files = xbmcvfs.listdir(dirPath)

        for aFile in files:
            if aFile.endswith('.html'):
                # Add this page to the list
                htmlFiles.append(aFile)

        # Now check any of the directories
        for aDir in dirs:
            htmlFiles = htmlFiles + self._findHtmlFiles(os_path_join(dirPath, aDir))

        return htmlFiles

    # Get the text for a given chapter
    def getChapterContents(self, chapterLink):
        log("MobiEBook: Getting chapter contents for %s" % chapterLink)

        # Find out the name of the page that this chapter is stored in
        sections = chapterLink.split('#')

        bookFileName = None
        chapterStartFlag = None
        if len(sections) > 0:
            bookFileName = sections[0]

        if len(sections) > 1:
            chapterStartFlag = sections[1]

        # Get the content of the chapter, this will be in HTML
        chapterContent = ""

        # Get the location that the book is to be extracted to
        extractDir = os_path_join(Settings.getTempLocation(), 'mobi_extracted')

        # Check if the mobi extract directory already exists
        if dir_exists(extractDir):
            try:
                shutil.rmtree(extractDir, True)
            except:
                log("MobiEBook: Failed to delete directory %s" % extractDir)

        # Extract the contents of the book so we can get the chapter contents
        try:
            kindleunpack.unpackBook(self.filePath, extractDir, None, '2', True)
        except:
            log("MobiEBook: Failed to unpack book for %s with error: %s" % (self.filePath, traceback.format_exc()), xbmc.LOGERROR)

        # Find the file containing the book contents
        bookFileLocation = self._findBookFile(extractDir, bookFileName)

        bookContents = ""
        if bookFileLocation not in [None, ""]:
            # Read the contents of the file
            try:
                # Read the contents of the book file into a string
                bookFile = xbmcvfs.File(bookFileLocation, 'r')
                bookContents = bookFile.read()
                bookFile.close()
            except:
                log("MobiEBook: Failed to read contents of book %s with error: %s" % (bookFileName, traceback.format_exc()), xbmc.LOGERROR)
        else:
            log("MobiEBook: Failed to find book content file %s" % bookFileName)

        # Cleanup the extract directory
        if dir_exists(extractDir):
            try:
                shutil.rmtree(extractDir, True)
            except:
                log("MobiEBook: Failed to delete directory %s" % extractDir)

        chapterContent = ""
        if bookContents not in [None, ""]:
            if chapterStartFlag is not None:
                # Split out the chapter (For now just add the whole book)
                # Split based on page markers
                pageBreaks = bookContents.split('<mbp:pagebreak/>')
                anchorHtml = "<a id=\"%s\"" % chapterStartFlag
                # Find which section contains this anchor
                for page in pageBreaks:
                    if anchorHtml in page.decode("utf-8"):
                        log("MobiEBook: Found page for chapter marker %s" % chapterStartFlag)
                        chapterContent = self._mobiHtmlParsing(page)
                        break
            else:
                log("MobiEBook: Chapter start flag, showing whole book")
                chapterContent = self._mobiHtmlParsing(bookContents)

        if chapterContent not in [None, ""]:
            chapterContent = self.convertHtmlIntoKodiText(chapterContent)

        return chapterContent

    # Finds the given book file
    def _findBookFile(self, dirPath, bookFileName):
        bookFile = None
        dirs, files = xbmcvfs.listdir(dirPath)

        for aFile in files:
            if aFile.lower() == bookFileName:
                # Found a match, set the value
                bookFile = os_path_join(dirPath, aFile)
                break

        # Now check any of the directories
        for aDir in dirs:
            if bookFile is None:
                bookFile = self._findBookFile(os_path_join(dirPath, aDir), bookFileName)

        return bookFile

    def _mobiHtmlParsing(self, chapterContentIn):
        # There are no line-breaks in the mobi file, so add them for each
        # html paragraph tag
        chapterContent = chapterContentIn.replace('</p>', '</p>\n')
        # Headings are just shown in larger fornts for mobi
        chapterContent = re.sub(r'<font size="5">(.*?)</font>', r'<h1>\1</h1>', chapterContent)

        return chapterContent


# Class to process the epub formatted books
class EPubEBook(EBookBase):
    def __init__(self, filePath, removeFileWhenComplete=False):
        EBookBase.__init__(self, filePath, removeFileWhenComplete)
        self.bookFile = None
        self.book = None

        try:
            self.bookFile = epub.open_epub(self.filePath)
            self.book = epub.Book(self.bookFile)
        except:
            log("EPubEBook: Failed to process eBook %s with error: %s" % (self.filePath, traceback.format_exc()), xbmc.LOGERROR)

    def getTitle(self):
        # Default the title to the filename - this should be overwritten
        title = self.getFallbackTitle()

        if self.book is not None:
            try:
                if len(self.book.titles) > 0:
                    title = self.book.titles[0][0]
            except:
                log("EPubEBook: Failed to get title for epub %s with error: %s" % (self.filePath, traceback.format_exc()), xbmc.LOGERROR)

        log("EPubEBook: Title is %s for book %s" % (title, self.filePath))
        return title

    def getAuthor(self):
        author = ""
        if self.book is not None:
            try:
                if len(self.book.creators) > 0:
                    author = self.book.creators[0][0]
            except:
                log("EPubEBook: Failed to get author for epub %s with error: %s" % (self.filePath, traceback.format_exc()), xbmc.LOGERROR)

        log("EPubEBook: Author is %s for book %s" % (author, self.filePath))
        return author

    # Gets the cover for a given eBook
    def extractCoverImage(self):
        coverTargetName = None
        try:
            # Get the cover for the book from the eBook file
            coverItem = self.bookFile.get_item('cover')

            if coverItem is None:
                # No cover found yet, try again
                coverItem = self.bookFile.get_item('cover-image')

            if coverItem is not None:
                # Check the name of the cover file, as we want to know the extension
                oldCoverName, newExt = os.path.splitext(coverItem.href)
                coverFileName, oldExt = os.path.splitext(self.fileName)
                cacheCoverName = "%s%s" % (coverFileName, newExt)
                coverTargetName = os_path_join(Settings.getCoverCacheLocation(), cacheCoverName)

                # Extract the cover to the temp target - it will get the same name as in
                # the compressed file
                extractedFile = self.bookFile.extract_item(coverItem, Settings.getTempLocation())

                log("EPubEBook: Extracted cover to: %s" % extractedFile)

                # Now move the file to the covers cache directory
                copy = xbmcvfs.copy(extractedFile, coverTargetName)
                if copy:
                    log("EPubEBook: copy successful for %s" % coverTargetName)
                else:
                    log("EPubEBook: copy failed from %s to %s" % (extractedFile, coverTargetName))
                xbmcvfs.delete(extractedFile)
        except:
            log("EPubEBook: Failed to get cover for %s with error: %s" % (self.filePath, traceback.format_exc()), xbmc.LOGERROR)

        return coverTargetName

    # Gets a list of the chapters and a link to the contents
    def getChapterDetails(self):
        # Keeping at the moment in comments as may be useful later
        # for chapter in book.chapters:
        #    log("*** ROB ***: Chanter Identifier %s" % str(chapter.identifier))
        #    log("*** ROB ***: Content %s" % str(chapter.read()))

        # Don't really need these 2
        # log("TOC title = %s" % str(bookFile.toc.title))
        # log("TOC author = %s" % str(bookFile.toc.authors))

        chapterDetails = []
        try:
            # Get all the chapters
            for navPoint in self.bookFile.toc.nav_map.nav_point:
                # Get each of the chapter labels
                for aLabelGroup in navPoint.labels:
                    if aLabelGroup not in [None, ""]:
                        for aLabel in aLabelGroup:
                            if aLabel not in [None, ""]:
                                log("EPubEBook: Adding chapter %s with src %s" % (aLabel, navPoint.src))
                                detail = {'title': aLabel.encode("utf-8"), 'link': navPoint.src}
                                chapterDetails.append(detail)
                                # Only need the first string for this label group
                                break
        except:
            log("EPubEBook: Failed to read chapter list %s with error: %s" % (self.filePath, traceback.format_exc()), xbmc.LOGERROR)

        # There may be the case that the user wants to display the entire book in one link
        # epub stores each chapter in an independent file, so we will need to join those
        # chapters into one record, so we use a special key for that
        if len(chapterDetails) > 0:
            if not Settings.onlyShowWholeBookIfChapters():
                detail = {'title': __addon__.getLocalizedString(32016), 'link': 'ENTIRE_BOOK'}
                chapterDetails.insert(0, detail)

        return chapterDetails

    # Get the text for a given chapter
    def getChapterContents(self, chapterLink):
        log("EPubEBook: Getting chapter contents for %s" % chapterLink)

        chapterContent = ""
        try:
            # Check for the case where the user wants the entire book
            if chapterLink == 'ENTIRE_BOOK':
                allChapters = self.getChapterDetails()
                for aChapter in allChapters:
                    if aChapter['link'] != 'ENTIRE_BOOK':
                        chapterContent = "%s\n%s" % (chapterContent, self.bookFile.read_item(aChapter['link']))
            else:
                # Get the content of the chapter, this will be in XML
                chapterContent = self.bookFile.read_item(chapterLink)
        except:
            log("EPubEBook: Failed to read chapter %s with error: %s" % (chapterLink, traceback.format_exc()), xbmc.LOGERROR)

        if chapterContent not in [None, ""]:
            chapterContent = self.convertHtmlIntoKodiText(chapterContent)

        return chapterContent


# Class to process the pdf formatted books
class PdfEBook(EBookBase):
    def __init__(self, filePath, removeFileWhenComplete=False):
        EBookBase.__init__(self, filePath, removeFileWhenComplete)
        self.document = None

    def _getDocument(self):
        # Get the document if we have not already
        if self.document is None:
            try:
                bookFile = open(self.filePath, 'rb')
                parser = PDFParser(bookFile)
                self.document = PDFDocument(parser, '')
            except:
                log("PdfEBook: Failed to process pdf %s with error: %s" % (self.filePath, traceback.format_exc()), xbmc.LOGERROR)
                self.document = None
        return self.document

    def getTitle(self):
        # Default the title to the filename - this should be overwritten
        title = None
        if self._getDocument() is not None:
            try:
                info = None
                for xref in self._getDocument().xrefs:
                    info_ref = xref.trailer.get('Info')
                    if info_ref:
                        info = resolve1(info_ref)
                if info is not None:
                    title = info.get('Title', None)
            except:
                log("PdfEBook: Failed to get title for pdf %s with error: %s" % (self.filePath, traceback.format_exc()), xbmc.LOGERROR)

        if title in [None, ""]:
            title = self.getFallbackTitle()

        log("PdfEBook: Title is %s for book %s" % (title.decode('utf-8', 'ignore'), self.filePath))
        return title

    def getAuthor(self):
        author = ""
        if self._getDocument() is not None:
            try:
                info = None
                for xref in self._getDocument().xrefs:
                    info_ref = xref.trailer.get('Info')
                    if info_ref:
                        info = resolve1(info_ref)
                if info is not None:
                    author = info.get('Author', '')
            except:
                log("PdfEBook: Failed to get author for pdf %s with error: %s" % (self.filePath, traceback.format_exc()), xbmc.LOGERROR)

        log("PdfEBook: Author is %s for book %s" % (author.decode('utf-8', 'ignore'), self.filePath))
        return author

    # Gets a list of the chapters and a link to the contents
    def getChapterDetails(self):
        chapterDetails = []

        numPages = 0

        # Need to know how many pages there are in the PDF file
        if self._getDocument() is not None:
            pages = dict((page.pageid, pageno) for (pageno, page) in enumerate(PDFPage.create_pages(self._getDocument())))
            numPages = len(pages)

            log("PdfEBook: Page total of %d for %s" % (numPages, self.fileName))

            if not Settings.usePageNumbersForPdf():
                # Get the outlines of the document.
                try:
                    outlines = self._getDocument().get_outlines()
                    for (level, title, dest, a, se) in outlines:
                        # Only go 3 levels deep with the chapters
                        if level < 4:
                            pageno = None
                            if dest:
                                dest = self._resolve_dest(dest, self._getDocument())
                                pageno = pages[dest[0].objid]
                            elif a:
                                action = a.resolve()
                                if isinstance(action, dict):
                                    subtype = action.get('S')
                                    if subtype and repr(subtype) == '/GoTo' and action.get('D'):
                                        dest = self._resolve_dest(action['D'], self._getDocument())
                                        pageno = pages[dest[0].objid]
                            if pageno is not None:
                                detail = {'title': title.encode("utf-8"), 'link': str(pageno)}
                                chapterDetails.append(detail)
                except:
                    log("PdfEBook: No Contents section processed for pdf %s with error: %s" % (self.filePath, traceback.format_exc()))

        if len(chapterDetails) > 0:
            # Make the link that is currently a single page number a range of page numbers
            previousChapterIdx = None
            for idx in range(0, len(chapterDetails)):
                if previousChapterIdx is not None:
                    startPage = chapterDetails[previousChapterIdx]['link']
                    endPage = chapterDetails[idx]['link']
                    if startPage != endPage:
                        # Need to actually include the end page as the start on the next section
                        # Logic would say it should be one less, but you don't know if the next
                        # chapter starts in the middle of the page it is highlighted for
                        chapterDetails[previousChapterIdx]['link'] = "%s-%s" % (startPage, endPage)
                previousChapterIdx = idx
            # Now handle the last page
            lastChapterStartPage = chapterDetails[-1]['link']
            if lastChapterStartPage != str(numPages):
                chapterDetails[-1]['link'] = "%s-%d" % (lastChapterStartPage, numPages)
        else:
            log("PdfEBook: Using page numbers instead of chapters, %s" % self.filePath)
            # There are no chapters show display a range of pages, with the range based
            # on the number of pages in the book
            pageGroupSize = 1
            if numPages > 40:
                pageGroupSize = 5
            if numPages > 200:
                pageGroupSize = 10

            pageSection = 0
            while pageSection < numPages:
                startPage = pageSection + 1
                endPage = startPage + pageGroupSize - 1
                pageSection = endPage

                if startPage > numPages:
                    break
                if endPage > numPages:
                    endPage = numPages

                pageRange = "%d-%d" % (startPage, endPage)
                pageLang = 32020
                if startPage == endPage:
                    pageRange = "%d" % startPage
                    pageLang = 32019
                title = "%s %s" % (__addon__.getLocalizedString(pageLang), pageRange)
                detail = {'title': title, 'link': pageRange}
                chapterDetails.append(detail)

        # Log all the chapters that have been added
        for chapter in chapterDetails:
            log("PdfEBook: Adding chapter %s with src %s" % (chapter['title'], chapter['link']))

        if (not Settings.onlyShowWholeBookIfChapters()) or (numPages < 1):
            detail = {'title': __addon__.getLocalizedString(32016), 'link': 'ENTIRE_BOOK'}
            chapterDetails.insert(0, detail)

        return chapterDetails

    # Get the text for a given chapter
    def getChapterContents(self, chapterLink):
        log("PdfEBook: Getting chapter contents for %s" % chapterLink)

        # Create the set of pages that we want
        pagesRequired = set()

        # If we want the entire book, then use an empty set
        if chapterLink != 'ENTIRE_BOOK':
            # Check if there pages are a range of pages
            if '-' not in chapterLink:
                pagesRequired.add(int(chapterLink))
            else:
                pageRange = chapterLink.split('-')
                startPage = int(pageRange[0])
                endPage = int(pageRange[1])
                while startPage <= endPage:
                    pagesRequired.add(startPage)
                    startPage = startPage + 1

        chapterContent = ""

        try:
            output = StringIO()
            manager = PDFResourceManager()
            converter = TextConverter(manager, output, laparams=LAParams(), showpageno=False)
#            converter = HTMLConverter(manager, output, laparams=LAParams(), showpageno=False)
            interpreter = PDFPageInterpreter(manager, converter)

            infile = file(self.filePath, 'rb')
            for page in PDFPage.get_pages(infile, pagesRequired):
                interpreter.process_page(page)
            infile.close()
            converter.close()
            chapterContent = output.getvalue()
            output.close
        except:
            log("PdfEBook: Failed to read contents for %s in pdf %s with error: %s" % (chapterLink, self.filePath, traceback.format_exc()), xbmc.LOGERROR)

        return chapterContent

    def _resolve_dest(self, dest, doc):
        if isinstance(dest, str):
            dest = resolve1(doc.get_dest(dest))
        elif isinstance(dest, PSLiteral):
            dest = resolve1(doc.get_dest(dest.name))
        if isinstance(dest, dict):
            dest = dest['D']
        return dest
