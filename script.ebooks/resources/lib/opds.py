# -*- coding: utf-8 -*-
import urllib2
import traceback
import xbmc

from BeautifulSoup import BeautifulSoup

# Import the common settings
from settings import Settings
from settings import log


class Opds():
    def __init__(self):
        self.rootImage = None
        self.menuContents = {}
        self.isBookList = False

    def isBookListContent(self):
        return self.isBookList

    def _getUrlContents(self, href):
        # Get the server details
        rootOpds = Settings.getOPDSLocation()

        if rootOpds in [None, ""]:
            return

        log("Opds: OPDS Location is %s%s" % (rootOpds, href))

        opdsContentsDetails = None
        try:
            fullURL = href
            if not fullURL.startswith('http'):
                fullURL = "%s%s" % (rootOpds, href)

            # Get the contents list from the library
            remoteOPDSContents = urllib2.urlopen(fullURL)
            opdsContentsDetails = remoteOPDSContents.read()
            # Closes the connection after we have read the remote list
            try:
                remoteOPDSContents.close()
            except:
                log("Opds: Failed to close connection for OPDS contents", xbmc.LOGERROR)
        except:
            log("Opds: Failed to read in OPDS contents: %s" % traceback.format_exc(), xbmc.LOGERROR)

        return opdsContentsDetails

    def _getRootContents(self):
        opdsContentsDetails = self._getUrlContents('/opds')

        if opdsContentsDetails not in [None, ""]:
            log("Opds: OPDS Root is %s" % opdsContentsDetails)

            try:
                soup = BeautifulSoup(''.join(opdsContentsDetails))

                # Check to see if there is an icon
                iconElem = soup.find('icon')
                if iconElem not in [None, ""]:
                    if iconElem.string not in [None, ""]:
                        self.rootImage = "%s%s" % (Settings.getOPDSLocation(), iconElem.string)

                # Check each entry, these will be the different view sections
                for elemItem in soup.findAll('entry'):
                    titleElem = elemItem.find('title')
                    if titleElem not in [None, ""]:
                        title = titleElem.string

                        # Not we have the title, get the link associated with the title
                        linkElem = elemItem.find('link')
                        if linkElem not in [None, ""]:
                            linkHref = linkElem['href']
                            log("EBooksPlugin: Found title %s with link %s" % (title, linkHref))
                            self.menuContents[title] = linkElem['href']
            except:
                log("Opds: %s" % traceback.format_exc(), xbmc.LOGERROR)

    def getRootImage(self):
        rootIcon = 'DefaultFolder.png'
        # Load the image details if not already there
        if self.rootImage is None:
            self._getRootContents()

        if self.rootImage not in [None, ""]:
            rootIcon = self.rootImage

        return rootIcon

    def getRoootMenuContents(self):
        if len(self.menuContents) < 1:
            self._getRootContents()
        return self.menuContents

    def getList(self, href):
        opdsContentsDetails = self._getUrlContents(href)

        booklist = []
        if opdsContentsDetails not in [None, ""]:
            log("Opds: OPDS Book list is %s" % opdsContentsDetails)

            try:
                soup = BeautifulSoup(''.join(opdsContentsDetails))

                # Check to see if there is an icon
                iconElem = soup.find('icon')
                if iconElem not in [None, ""]:
                    if iconElem.string not in [None, ""]:
                        self.rootImage = "%s%s" % (Settings.getOPDSLocation(), iconElem.string)

                # Check each entry, these will be the different view sections
                for elemItem in soup.findAll('entry'):
                    bookDetails = {'title': '', 'author': '', 'link': '', 'cover': ''}

                    # Get the title of the book
                    titleElem = elemItem.find('title')
                    if titleElem not in [None, ""]:
                        bookDetails['title'] = titleElem.string
                        bookDetails['title'] = bookDetails['title'].replace('&amp;', '&')
                        bookDetails['title'] = bookDetails['title'].replace('&quote;', '"')
                        bookDetails['title'] = bookDetails['title'].replace('&nbsp;', ' ')

                    # Get the authods of the book
                    authorElem = elemItem.find('author')
                    if authorElem not in [None, ""]:
                        authors = []
                        for authorName in authorElem.findAll('name'):
                            authors.append(authorName.string)
                        bookDetails['author'] = ', '.join(authors)
                        bookDetails['author'] = bookDetails['author'].replace('&amp;', '&')
                        bookDetails['author'] = bookDetails['author'].replace('&quote;', '"')
                        bookDetails['author'] = bookDetails['author'].replace('&nbsp;', ' ')

                    # Get all the links
                    for linkElem in elemItem.findAll('link'):
                        # Check the 'rel' attribute
                        relAttrib = linkElem.get('rel', None)

                        # If there is no rel attribute, then this page is another index page
                        if relAttrib is None:
                            log("Opds: Listing is not books")
                            bookDetails['link'] = linkElem['href']
                            self.isBookList = False
                        else:
                            log("Opds: Listing is books")
                            # Get the link to the book
                            if 'acquisition' in relAttrib:
                                bookLink = "%s%s" % (Settings.getOPDSLocation(), linkElem['href'])
                                # Check if we already have a book
                                if bookDetails.get('link', None) not in [None, '']:
                                    bookLink = Settings.getOPDSPreferredBook(bookDetails['link'], bookLink)

                                bookDetails['link'] = bookLink
                                self.isBookList = True
                            # Get the cover image for the book
                            elif 'cover' in relAttrib:
                                bookDetails['cover'] = "%s%s" % (Settings.getOPDSLocation(), linkElem['href'])

                    booklist.append(bookDetails)

                # Now check to see if there are any more books, as by default it will be paged
                # there is no way to request all books in one go
                nextElem = soup.find('link', {"rel": "next"})
                if nextElem not in [None, ""]:
                    nextPage = nextElem.get('href', None)
                    if nextPage not in [None, ""]:
                        log("Opds: Getting Next page: %s" % nextPage)
                        # Call ourselves again to process the next page
                        nextPageList = self.getList(nextPage)
                        if nextPageList not in [None, ""]:
                            booklist = booklist + nextPageList
            except:
                log("Opds: %s" % traceback.format_exc(), xbmc.LOGERROR)

        return booklist
