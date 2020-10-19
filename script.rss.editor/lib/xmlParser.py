import os
import sys
import unicodedata
from xml.dom.minidom import parse, Document, _write_data, Node, Element
import xbmc
import xbmcvfs
import xbmcaddon
import xbmcgui

def log(txt):
    xbmc.log(msg=txt, level=xbmc.LOGDEBUG)

def writexml(self, writer, indent="", addindent="", newl=""):
    #credit: http://ronrothman.com/public/leftbraned/xml-dom-minidom-toprettyxml-and-silly-whitespace/
    writer.write(indent + "<" + self.tagName)
    attrs = self._get_attributes()
    a_names = list(attrs.keys())
    a_names.sort()
    for a_name in a_names:
        writer.write(" %s=\"" % a_name)
        _write_data(writer, attrs[a_name].value)
        writer.write("\"")
    if self.childNodes:
        if len(self.childNodes) == 1 \
          and self.childNodes[0].nodeType == Node.TEXT_NODE:
            writer.write(">")
            self.childNodes[0].writexml(writer, "", "", "")
            writer.write("</%s>%s" % (self.tagName, newl))
            return
        writer.write(">%s" % (newl))
        for node in self.childNodes:
            node.writexml(writer, indent + addindent, addindent, newl)
        writer.write("%s</%s>%s" % (indent, self.tagName, newl))
    else:
        writer.write("/>%s" % (newl))

# monkey patch to fix whitespace issues with toprettyxml
Element.writexml = writexml
#enable localization
getLS = xbmcaddon.Addon().getLocalizedString


class XMLParser:
    def __init__(self):
        self.RssFeedsPath = xbmcvfs.translatePath('special://userdata/RssFeeds.xml')
        sane = self.checkRssFeedPathSanity()
        if sane:
            try:
                self.feedsTree = parse(self.RssFeedsPath)
            except:
                log('RSS Editor --> Failed to parse ' + unicodedata.normalize( 'NFKD', self.RssFeedsPath ))
                regen = xbmcgui.Dialog().yesno(getLS(32040), getLS(32051) + ' ' + getLS(32052) + ' ' + getLS(32053))
                if regen:
                    log('RSS Editor --> Attempting to Regenerate RssFeeds.xml')
                    xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<rssfeeds>\n\
                    <!-- RSS feeds. To have multiple feeds, just add a feed to the set. You can also have multiple sets. 	!-->\n\
                    <!-- To use different sets in your skin, each must be called from skin with a unique id.             	!-->\n\
                    <set id="1">\n    <feed updateinterval="30">http://feeds.kodi.tv/xbmc</feed>\n    \
                    <feed updateinterval="30">http://feeds.kodi.tv/latest_xbmc_addons</feed>\n    \
                    <feed updateinterval="30">http://feeds.kodi.tv/updated_xbmc_addons</feed></set>\n</rssfeeds>'
                    f = open(self.RssFeedsPath, 'w')
                    f.write(xml)
                    f.close()
                    self.__init__()
                else:
                    log('RSS Editor --> User opted to not regenerate RssFeeds.xml.  Script Exiting')
                    self.feedsTree = False
            if self.feedsTree:
                self.feedsList = self.getCurrentRssFeeds()
        else:
            self.feedsTree = False
            self.feedsList = False
            log('RSS Editor --> Could not open ' + unicodedata.normalize( 'NFKD', self.RssFeedsPath ) + '. Either the file does not exist, or its size is zero.')

    def checkRssFeedPathSanity(self):
        if os.path.isfile(self.RssFeedsPath):
            #If the filesize is zero, the parsing will fail.  XBMC creates 
            if os.path.getsize(self.RssFeedsPath):
                return True

    def getCurrentRssFeeds(self):
        feedsList = dict()
        sets = self.feedsTree.getElementsByTagName('set')
        for s in sets:
            setName = 'set' + s.attributes["id"].value
            feedsList[setName] = {'feedslist':list(), 'attrs':dict()}
            #get attrs
            for attrib in s.attributes.keys():
                feedsList[setName]['attrs'][attrib] = s.attributes[attrib].value
            #get feedslist
            feeds = s.getElementsByTagName('feed')
            for feed in feeds:
                feedsList[setName]['feedslist'].append({'url':feed.firstChild.toxml(), 'updateinterval':feed.attributes['updateinterval'].value})
        return feedsList

    def formXml(self):
        """Form the XML to be written to RssFeeds.xml"""
        #create the document
        doc = Document()
        #create root element
        rssfeedsTag = doc.createElement('rssfeeds')
        doc.appendChild(rssfeedsTag)
        #create comments
        c1Tag = doc.createComment('RSS feeds. To have multiple feeds, just add a feed to the set. You can also have multiple sets.')
        c2Tag = doc.createComment('To use different sets in your skin, each must be called from skin with a unique id.')
        rssfeedsTag.appendChild(c1Tag)
        rssfeedsTag.appendChild(c2Tag)
        for setNum in sorted(self.feedsList.keys()):
            #create sets
            setTag = doc.createElement('set')
            #create attributes
            setTag.setAttribute('id', self.feedsList[setNum]['attrs']['id'])
            #only write rtl tags if they've been explicitly set
            if 'rtl' in self.feedsList[setNum]['attrs']:
                setTag.setAttribute('rtl', self.feedsList[setNum]['attrs']['rtl'])
            rssfeedsTag.appendChild(setTag)
            #create feed elements
            for feed in self.feedsList[setNum]['feedslist']:
                feedTag = doc.createElement('feed')
                feedTag.setAttribute('updateinterval', feed['updateinterval'])
                feedUrl = doc.createTextNode(feed['url'])
                feedTag.appendChild(feedUrl)
                setTag.appendChild(feedTag)
        return doc.toprettyxml(indent = '  ', encoding = 'UTF-8')

    def writeXmlToFile(self):
        log('RSS Editor --> writing to %s' % (unicodedata.normalize( 'NFKD', self.RssFeedsPath)))
        xml = self.formXml()
        #hack for standalone attribute, minidom doesn't support DOM3
        xmlHeaderEnd = xml.find(b'?>')
        xml = xml[:xmlHeaderEnd] + b' standalone="yes"' + xml[xmlHeaderEnd:]
        try:
            RssFeedsFile = open(self.RssFeedsPath, 'wb')
            RssFeedsFile.write(xml)
            RssFeedsFile.close()
            log('RSS Editor --> write success')
            self.refreshFeed()
        except IOError as error:
            log('RSS Editor --> write failed', error)

    def refreshFeed(self):
        """Refresh XBMC's rss feed so changes can be seen immediately"""
        xbmc.executebuiltin('refreshrss()')
