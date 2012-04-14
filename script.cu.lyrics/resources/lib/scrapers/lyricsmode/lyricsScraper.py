
import sys
import os
import urllib
import re
import xbmc
from utilities import *
from song import *
import lyrics
import re


__language__ = sys.modules[ "__main__" ].__language__
__title__ = __language__(30006)
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
        self.search_results_regex = re.compile("<a href=\"[^\"]+\">([^<]+)</a></td>[^<]+<td><a href=\"([^\"]+)\" class=\"b\">[^<]+</a></td>", re.IGNORECASE)
        self.next_results_regex = re.compile("<A href=\"([^\"]+)\" class=\"pages\">next .</A>", re.IGNORECASE)        
    
    def get_lyrics_start(self, *args):
        lyricThread = threading.Thread(target=self.get_lyrics_thread, args=args)
        lyricThread.setDaemon(True)
        lyricThread.start()
      
    def get_lyrics_thread(self, song):
        print "SCRAPER-DEBUG-lyricsmode: LyricsFetcher.get_lyrics_thread %s" % (song)
        l = lyrics.Lyrics()
        l.song = song
        try: # below is borowed from XBMC Lyrics
            url = "http://www.lyricsmode.com/lyrics/%s/%s/%s.html" % (song.artist.lower()[:1],song.artist.lower().replace(" ","_"), song.title.lower().replace(" ","_"), )
            lyrics_found = False
            while True:
                print "Search url: %s" % (url)
                song_search = urllib.urlopen(url).read()
                if song_search.find("<div id='songlyrics_h' class='dn'>") >= 0:
                    break
    
                if lyrics_found:
                    # if we're here, we found the lyrics page but it didn't
                    # contains the lyrics part (licensing issue or some bug)
                    return None, "No lyrics found"
                    
                # Let's try to use the research box if we didn't yet
                if not 'search' in url:
                    url = "http://www.lyricsmode.com/search.php?what=songs&s=" + urllib.quote_plus(song.title.lower())
                else:
                    # the search gave more than on result, let's try to find our song 
                    url = ""
                    start = song_search.find('<!--output-->')
                    end = song_search.find('<!--/output-->', start)
                    results = self.search_results_regex.findall(song_search, start, end)
      
                    for result in results:
                        if result[0].lower() in song.artist.lower():
                            url = "http://www.lyricsmode.com" + result[1]
                            lyrics_found = True
                            break
      
                    if not url:
                        # Is there a next page of results ?
                        match = self.next_results_regex.search(song_search[end:])
                        if match:
                            url = "http://www.lyricsmode.com/search.php" + match.group(1)
                        else:
                            return None, "No lyrics found"            

            lyr = song_search.split("<div id='songlyrics_h' class='dn'>")[1].split('<!-- /SONG LYRICS -->')[0]
            lyr = self.clean_br_regex.sub( "\n", lyr ).strip()
            lyr = self.clean_lyrics_regex.sub( "", lyr ).strip()
            lyr = self.normalize_lyrics_regex.sub( lambda m: unichr( int( m.group( 1 ) ) ), lyr.decode("ISO-8859-1") )
            lir = []
            for line in lyr.splitlines():
                line.strip()
                if line.find("Lyrics from:") < 0:
                    lir.append(line)
            lyr = u"\n".join( lir )       
            l.lyrics = lyr
            l.source = __title__
            return l, None            
        except:
            print "%s::%s (%d) [%s]" % ( self.__class__.__name__, sys.exc_info()[ 2 ].tb_frame.f_code.co_name, sys.exc_info()[ 2 ].tb_lineno, sys.exc_info()[ 1 ])
            return None, __language__(30004) % (__title__)      

