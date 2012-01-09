#-*- coding: UTF-8 -*-
import sys
import os
import urllib
import re
import xbmc
from utilities import *
from song import *
import lyrics

__language__ = sys.modules[ "__main__" ].__language__
__title__ = __language__(30007)
__allow_exceptions__ = True

class WikiaFormat:
    @staticmethod
    def __condense_strings(parseList):
        while(True):
            if ( len(parseList) < 2 
                 or not isinstance(parseList[-1], basestring)
                 or not isinstance(parseList[-2], basestring) ):
                return parseList
            lastStr = parseList[-1]
            parseList.pop()
            for i in range(len(parseList)-1, -1, -1):
                if ( isinstance(parseList[i], basestring) ):
                    lastStr = parseList[i] + lastStr
                    parseList.pop()
                else:
                    parseList.append(lastStr)
                    return parseList
            parseList.append(lastStr)
    
    @staticmethod
    def __parse_stack(parseList):
        while(True):
            if ( len(parseList) < 3 
                 or isinstance(parseList[-1], basestring)
                 or not isinstance(parseList[-2], basestring)
                 or isinstance(parseList[-3], basestring) ):
                return parseList
            
            beginTags = {2:'[I]', 3:'[B]', 5:'[I][B]'}
            endTags = {2:'[/I]', 3:'[/B]', 5:'[/I][/B]'}
            
            begin = parseList[-3]
            str = parseList[-2]
            end = parseList[-1]
            if ( begin == end ):
                parseList = parseList[:-3]
                if ( str ):
                    parseList.append(beginTags[begin] + str + endTags[end])
            elif ( begin == 5 ):
                parseList = parseList[:-3]
                begin = 5-end
                parseList.append(begin)
                if ( str ):
                    parseList.append(beginTags[end] + str + endTags[end])
            elif ( end == 5 ):
                parseList = parseList[:-3]
                end = 5-begin
                if ( str ):
                    parseList.append(beginTags[begin] + str + endTags[begin])
                parseList.append(end)
            else:
                return parseList
    
    @staticmethod
    def __push_stack(q, str, stack):
        if ( q >= 5 ):
            stack.append(5)
            q -= 5
        elif ( q >= 3 ):
            stack.append(3)
            q -= 3
        elif ( q >= 2 ):
            stack.append(2)
            q -= 2
        stack = WikiaFormat.__parse_stack(stack)
        str = "'"*q + str
        q = 0
        if ( str ):
           stack.append(str)
        WikiaFormat.__condense_strings(stack)
        return stack
    
    @staticmethod
    def to_xbmc_format(s):
        t = s.split("'")
        numQuotes = 0
        stack = []
        for line in t:
            if (line):
                stack = WikiaFormat.__push_stack(numQuotes, line, stack)
                numQuotes = 1
            else:
                numQuotes += 1
        if ( numQuotes > 1 ):
            stack = WikiaFormat.__push_stack(numQuotes, "", stack)
        
        #Take care of any unclosed tags
        if ( not isinstance(stack[-1], basestring) ):
            stack.append("")
        stack = WikiaFormat.__push_stack(5, "", stack)
        if ( not isinstance(stack[-1], basestring) ):
            stack.pop()
        return str.join("", stack)

class XmlUtils :
    def getText (self, nodeParent, childName ):
        # Get child node...
        node = nodeParent.getElementsByTagName( childName )[0]
        
        if node == None :
            return None
        
        # Get child text...
        text = ""
        for child in node.childNodes:
            if child.nodeType == child.TEXT_NODE :
                text = text + child.data
        return text
    
    @staticmethod
    def removeComments(text):
        begin = text.split("<!--")
        if ( len(begin) > 1 ):
            end = str.join("", begin[1:]).split("-->")
            if ( len(end) > 1 ):
                return XmlUtils.removeComments(begin[0] + str.join("", end[1:]))
        return text


class LyricsFetcher:
    def __init__( self ):
        self.clean_lyrics_regex = re.compile( "<.+?>" )
        self.normalize_lyrics_regex = re.compile( "&#[x]*(?P<name>[0-9]+);*" )
        self.clean_br_regex = re.compile( "<br[ /]*>[\s]*", re.IGNORECASE )
        self.clean_info_regex = re.compile( "\[[a-z]+?:.*\]\s" )
        
    def get_lyrics_start(self, *args):
        lyricThread = threading.Thread(target=self.get_lyrics_thread, args=args)
        lyricThread.setDaemon(True)
        lyricThread.start()
    
    
    def get_lyrics_thread(self, song):
        print "SCRAPER-DEBUG-lyricstime: LyricsFetcher.get_lyrics_thread %s" % (song)
        l = lyrics.Lyrics()
        l.song = song
        try: # ***** parser - changing this changes search string
            url = "http://www.lyricstime.com/%s-%s-lyrics.html" % (song.artist.lower().replace(" ","-").replace(",","-").replace("'","-").replace("&","-").replace("and","-"), song.title.lower().replace(" ","-").replace(",","-").replace("'","-").replace("&","-"), )
            song_search = urllib.urlopen(url.replace("---","-").replace("--","-")).read()
            print "Search url: %s" % (url)
            lyr = song_search.split('<div id="songlyrics" >')[1].split('</div>')[0]     
            lyr = self.clean_br_regex.sub( "\n", lyr ).strip()
            lyr = self.clean_lyrics_regex.sub( "", lyr ).strip()
            lyr = self.normalize_lyrics_regex.sub( lambda m: unichr( int( m.group( 1 ) ) ), lyr.decode("ISO-8859-1") )
            lyr = u"\n".join( [ lyric.strip() for lyric in lyr.splitlines() ] )
            lyr = self.clean_info_regex.sub( "", lyr )     
            l.lyrics = lyr
            l.source = __title__
            return l, None            
        except:
            print "%s::%s (%d) [%s]" % ( self.__class__.__name__, sys.exc_info()[ 2 ].tb_frame.f_code.co_name, sys.exc_info()[ 2 ].tb_lineno, sys.exc_info()[ 1 ])
            return None, __language__(30004) % (__title__)