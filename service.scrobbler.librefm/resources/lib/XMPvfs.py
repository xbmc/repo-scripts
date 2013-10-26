# -*- coding: utf8 -*-

import re
import xbmcvfs
from HTMLParser import HTMLParser

tag_set = {'dc:title' : 'dc:title',
           'dc:description' : 'dc:description',
           'dc:subject' : 'dc:subject'}

class XMP_Tags(object):
    get_xmp_picfile = ''
    get_xmp_inner = ''

    def __get_xmp_metadata(self, picfile):
        xmptag = 'rdf:RDF'
        self.get_xmp_picfile = picfile
        imgfile = xbmcvfs.File(picfile)
        content = imgfile.read() 
        start = content.find("<" + xmptag)
        end   = content.rfind("</" + xmptag) + 4 + len(xmptag)
        inner = content[start:end]
        self.get_xmp_inner = inner
            
    def get_xmp(self, picfile):
        xmp = {}
        for storedtag, tagname in tag_set.iteritems():
            if self.get_xmp_picfile != picfile:
                self.__get_xmp_metadata(picfile)
            start = self.get_xmp_inner.find("<" + tagname)
            end   = self.get_xmp_inner.rfind("</" + tagname) + 4 + len(tagname)
            inner = self.get_xmp_inner[start:end]
            j = 0
            people=''
            if start != -1 and end != -1:
                end = inner.find("</" + tagname)
                while end != -1:

                    start = inner.find(">")+1
                    if start == 0:
                        break
                    tag_found = inner[start:end]
                    i = 0
                    people = ''
                    while i < len(tag_found):
                        if ord(tag_found[i])!=0:
                            people += tag_found[i]
                        i += 1
                    if len(people):
                        try:
                            value = unicode(people, encoding='utf-8', errors='strict')
                        except:
                            value = unicode(people, encoding="cp1252", errors='replace')
                        matchouter=re.compile('<rdf:Alt[^>]*?>(.*?)</rdf:Alt>',re.DOTALL).findall(value)

                        if len(matchouter) == 0:
                            matchouter=re.compile('<rdf:Seq[^>]*?>(.*?)</rdf:Seq>',re.DOTALL).findall(value)
                        if len(matchouter) == 0:
                            matchouter=re.compile('<rdf:Bag[^>]*?>(.*?)</rdf:Bag>',re.DOTALL).findall(value)
                        key = ''
                        for outer in matchouter:
                            matchinner=re.compile('<rdf:li[^>]*?>(.*?)</rdf:li>',re.DOTALL).findall(outer)
                            for inner in matchinner:
                                inner = inner.strip(' \t\n\r')
                                if len(inner) > 0:

                                    if len(key) > 0:
                                        key += '||' + inner
                                    else:
                                        key = inner
                        if len(key) > 0:
                            key = HTMLParser().unescape(key)
                            if xmp.has_key(storedtag):
                                xmp[storedtag] += '||' + key
                            else:
                                xmp[storedtag] = key
                    inner = inner[end+1:]
                    start = inner.find("<" + tagname)
                    inner = inner[start:]
                    end = inner.find("</" + tagname)
                    j = j+ 1
        return xmp
