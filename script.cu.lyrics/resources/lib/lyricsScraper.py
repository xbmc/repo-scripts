
import sys
import os
import urllib
import re
from utilities import *
from song import *
import lyrics

if ( __name__ != "__main__" ):
    import xbmc

__title__ = "LyricWiki.org API"
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
    """ required: Fetcher Class for www.lyricwiki.org """
    def __init__( self ):
        self.base_url = "http://lyricwiki.org/api.php"
        self._set_exceptions()
        
        
    def get_lyrics_start(self, *args):
        lyricThread = threading.Thread(target=self.get_lyrics_thread, args=args)
        lyricThread.setDaemon(True)
        lyricThread.start()
    
    def lyricwiki_format(self, text):
        # Test cases
        #     I've
        titleCase =lambda value: re.sub("([a-zA-Z]')([A-Z])", lambda m: m.group(1) + m.group(2).lower(), value.title())
        return urllib.quote(str(unicode(titleCase(text))))
    
    def get_lyrics_thread(self, song):
        print "SCRAPER-DEBUG: LyricsFetcher.get_lyrics_thread %s" % (song)
        l = lyrics.Lyrics()
        l.song = song
        try:
            url = "http://lyricwiki.org/index.php?title=%s:%s&fmt=js" % (self.lyricwiki_format(song.artist), self.lyricwiki_format(song.title))
            print "Search url: %s" % (url)
            song_search = urllib.urlopen(url).read()
            song_title = song_search.split("<title>")[1].split("</title>")[0]
            song_clean_title = unescape(song_title.replace(" Lyrics - LyricWiki - Music lyrics from songs and albums",""))
            print "Title:[" + song_clean_title+"]"
            lyricpage = urllib.urlopen("http://lyricwiki.org/index.php?title=%s&action=edit" % (urllib.quote(song_clean_title),)).read()
            print ("http://lyricwiki.org/index.php?title=%s&action=edit" % (urllib.quote(song_clean_title),))
            content = re.split("<textarea[^>]*>", lyricpage)[1].split("</textarea>")[0]
            
            if ( content.find("{{Disambig}}") >= 0 ):
                return None, "'%s' by '%s' matches multiple lyric pages" % (song.title, song.artist)
            
            if content.startswith("#REDIRECT [["):
                addr = "http://lyricwiki.org/index.php?title=%s&action=edit" % urllib.quote(content.split("[[")[1].split("]]")[0])
                content = urllib.urlopen(addr).read()
                
            try:
                lyricText = content.split("&lt;lyrics&gt;")[1].split("&lt;/lyrics&gt;")[0]
            except:
                lyricText = content.split("&lt;lyric&gt;")[1].split("&lt;/lyric&gt;")[0]
            lyricText = unicode(lyricText, 'utf8')
            lyricText = WikiaFormat.to_xbmc_format(unescape(lyricText.strip()))
            lyricText = lyricText.replace("{{gracenote_takedown}}", "[Lyrics removed by GraceNote]")
            lyricText = lyricText.replace("{{Instrumental}}", u"\u266B" + " Instrumental " + u"\u266B")
            
            lyricText = XmlUtils.removeComments(lyricText)
            if ( not lyricText ):
                return None, "Lyrics not found for song '%s' by '%s'" % (song.title, song.artist) 
            
            l.lyrics = lyricText
            l.source = __title__
            return l, None            
        except:
            print "%s::%s (%d) [%s]" % ( self.__class__.__name__, sys.exc_info()[ 2 ].tb_frame.f_code.co_name, sys.exc_info()[ 2 ].tb_lineno, sys.exc_info()[ 1 ])
            return None, "Fetching lyrics from %s failed" % (__title__)      

    def get_lyrics( self, artist, song ):
        """ *required: Returns song lyrics or a list of choices from artist & song """
        # format artist and song, check for exceptions
        artist = self._format_param( artist )
        song = self._format_param( song, False )
        # fetch lyrics
        lyrics = self._fetch_lyrics( artist, song )
        # if no lyrics found try just artist for a list of songs
        if ( not lyrics ):
            # fetch song list
            song_list = self._get_song_list( artist )
            return song_list
        else: return lyrics
    
    def get_lyrics_from_list( self, item ):
        """ *required: Returns song lyrics from user selection - item[1]"""
        lyrics = self.get_lyrics( item[ 0 ], item[ 1 ] )
        return lyrics
        
    def _set_exceptions( self, exception=None ):
        """ Sets exceptions for formatting artist """
        try:
            if ( __name__ == "__main__" ):
                ex_path = os.path.join( os.getcwd(), "exceptions.txt" )
            else:
                name = __name__.replace( "resources.scrapers.", "" ).replace( ".lyricsScraper", "" )
                ex_path = os.path.join( xbmc.translatePath( "P:\\script_data" ), os.getcwd(), "scrapers", name, "exceptions.txt" )
            ex_file = open( ex_path, "r" )
            self.exceptions = eval( ex_file.read() )
            ex_file.close()
        except:
            self.exceptions = {}
        if ( exception is not None ):
            self.exceptions[ exception[ 0 ] ] = exception[ 1 ]
            self._save_exception_file( ex_path, self.exceptions )
    
    def _save_exception_file( self, ex_path, exceptions ):
        """ Saves the exception file as a repr(dict) """
        try:
            if ( not os.path.isdir( os.path.split( ex_path )[ 0 ] ) ):
                os.makedirs( os.path.split( ex_path )[ 0 ] )
            ex_file = open( ex_path, "w" )
            ex_file.write( repr( exceptions ) )
            ex_file.close()
        except: pass
        
    def _fetch_lyrics( self, artist, song ):
        """ Fetch lyrics if available """
        try:
            url = self.base_url + "?action=lyrics&artist=%s&song=%s&fmt=xml&func=getSong"
            # Open url or local file (if debug)
            
            if ( not debug ):
                usock = urllib.urlopen( url % ( artist, song, ) )
                
            else:
                usock = open( os.path.join( os.getcwd(), "lyrics_source.txt" ), "r" )
            # read source
            jsonSource = usock.read()
            print str(jsonSource)
            import xml.dom.minidom
            resultDoc = xml.dom.minidom.parseString(jsonSource)
            xmlUtils  = XmlUtils() 
            result    = xmlUtils.getText(resultDoc, "url")
            print result
            
            # close socket
            usock.close()
            
            weblyr = urllib.urlopen(result)
            lyr = weblyr.read()
            weblyr.close()
            print str(lyr)
            resultDoc = lyr.split()
            print str(resultDoc)
#           xmlUtils  = XmlUtils() 
#            result1    = xmlUtils.getText(resultDoc, "div class='lyricbox'")
            
            # Save htmlSource to a file for testing scraper (if debugWrite)
            if ( debugWrite ):
                file_object = open( os.path.join( os.getcwd(), "lyrics_source.txt" ), "w" )
                file_object.write( jsonSource )
                file_object.close()
            # exec jsonSource to a native python dictionary
            exec jsonSource
            if ( song[ "lyrics" ] == "Not found" or song[ "lyrics" ].startswith( "{{Wikipedia}}" ) ):
                raise
            lyrics = song[ "lyrics" ]
            return lyrics
        except:
            return None
        
    def _get_song_list( self, artist ):
        """ If no lyrics found, fetch a list of choices """
        try:
            # TODO: change to json when json works
            url = self.base_url + "?func=getArtist&fmt=xml&artist=%s"
            # Open url or local file (if debug)
            if ( not debug ):
                usock = urllib.urlopen( url % ( artist, ) )
            else:
                usock = open( os.path.join( os.getcwd(), "songs_source.txt" ), "r" )
            # read source
            jsonSource = usock.read()
            # close socket
            usock.close()
            # Save htmlSource to a file for testing scraper (if debugWrite)
            if ( debugWrite ):
                file_object = open( os.path.join( os.getcwd(), "songs_source.txt" ), "w" )
                file_object.write( jsonSource )
                file_object.close()
            # exec jsonSource to a native python dictionary
            #exec jsonSource
            # Create sorted return list
            songs = re.findall( "<item>(.*)</item>", jsonSource )
            songs.sort()
            song_list = []
            for song in songs:
                song_list += [ [ song, ( artist, song, ) ] ]
            return song_list
        except:
            return None
    
    def _format_param( self, param, exception=True ):
        """ Converts param to the form expected by www.lyricwiki.org """
        # properly quote string for url
        result = urllib.quote( param )
        # replace any exceptions
        if ( exception and result in self.exceptions ):
            result = self.exceptions[ result ]
        return result
    
# used for testing only
debug = False
debugWrite = False
