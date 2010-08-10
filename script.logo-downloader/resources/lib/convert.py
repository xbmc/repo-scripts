
import re
from string import maketrans


def translate_string( strtrans, del_char="" ):
    # frm = Representation of " Non-ASCII character "
    if "\xc3\xa9" in strtrans:
        strtrans = strtrans.replace( "\xc3\xa9", "\xe9" )
    frm = '\xe1\xc1\xe0\xc0\xe2\xc2\xe4\xc4\xe3\xc3\xe5\xc5\xe6\xc6\xe7\xc7\xd0\xe9\xc9\xe8\xc8\xea\xca\xeb\xcb\xed\xcd\xec\xcc\xee\xce\xef\xcf\xf1\xd1\xf3\xd3\xf2\xd2\xf4\xd4\xf6\xd6\xf5\xd5\xf8\xd8\xdf\xfa\xda\xf9\xd9\xfb\xdb\xfc\xdc\xfd\xdd'
    #print " Non-ASCII character =", frm
    to = "aAaAaAaAaAaAaAcCDeEeEeEeEiIiIiIiInNoOoOoOoOoOoOsuUuUuUuUyY"
    # Construct a translation string
    table = maketrans( frm, to )
    is_unicode = 0
    if isinstance( strtrans, unicode ):
        is_unicode = 1
        # remove unicode
        strtrans = "".join( [ chr( ord( char ) ) for char in strtrans ] )
    if not del_char:
        # set win32 and xbox default invalid characters
        del_char = """,*=|<>?;:"+""" #+ "\xc3\xa9"
    # translation string
    s = strtrans.translate( table, del_char )
    # now remove others invalid characters
    s = "".join( [ char for char in s if ord( char ) < 127 ] )
    if is_unicode:
        #replace unicode
        s = unicode( s )#, "utf-8" )
    return s


class ENTITY_OR_CHARREF:
    def __init__( self, strvalue="" ):
        # Internal -- convert entity or character reference
        # http://www.toutimages.com/codes_caracteres.htm
        # http://openweb.eu.org/articles/caracteres_illegaux/
        strvalue = self._replace_html_to_iso( strvalue )

        self.entitydefs = { 'lt': '<', 'gt': '>', 'amp': '&', 'quot': '"', 'apos': '\'' }

        self.entity_or_charref = re.compile( '&(?:'
            '([a-zA-Z][-.a-zA-Z0-9]*)|#([0-9]+)'
            ')(;?)' ).sub( self._convert_ref, strvalue )

    def _replace_html_to_iso( self, strvalue ):
        # NO CONFORM
        html_to_iso = {
            '&#8211;':  "-",
            '&#8217;':  "'",
            '&euro;':   "&#128;",
            '&rsquo;':  "&#146;",
            '&ldquo;':  "&#147;",
            '&rdquo;':  "&#148;",
            '&ndash;':  "&#150;",
            '&nbsp;':   "&#32;", #'&nbsp;':   "&#160;",
            '&hellip;': "&#133;", '&Hellip;': "&#133;",
            '&agrave;': "&#224;", '&Agrave;': "&#192;",
            '&acirc;':  "&#226;", '&Acirc;':  "&#194;",
            '&ccedil;': "&#231;", '&Ccedil;': "&#199;",
            '&egrave;': "&#232;", '&Egrave;': "&#200;",
            '&eacute;': "&#233;", '&Eacute;': "&#201;",
            '&ecirc;':  "&#234;", '&Ecirc;':  "&#202;",
            '&euml;':   "&#235;", '&Euml;':   "&#203;",
            '&icirc;':  "&#238;", '&Icirc;':  "&#206;",
            '&iuml;':   "&#239;", '&Iuml;':   "&#207;",
            '&ocirc;':  "&#244;", '&Ocirc;':  "&#212;",
            '&ugrave;': "&#249;", '&Ugrave;': "&#217;",
            '&ucirc;':  "&#251;", '&Ucirc;':  "&#219;"
            }
        for key, value in html_to_iso.items():
            strvalue = strvalue.replace( key, value )
        return strvalue

    def _convert_ref( self, match ):
        if match.group( 2 ):
            return self.convert_charref( match.group( 2 ) ) or ( '&#%s%s' % match.groups( )[ 1: ] )
        elif match.group( 3 ):
            return self.convert_entityref( match.group( 1 ) ) or ( '&%s;' % match.group( 1 ) )
        else:
            return '&%s' % match.group( 1 )

    def convert_charref( self, name ):
        """Convert character reference, may be overridden."""
        try:
            n = int( name )
        except ValueError:
            return
        if not 0 <= n <= 255:
            return
        return self.convert_codepoint( n )

    def convert_codepoint( self, codepoint ):
        return chr( codepoint )

    def convert_entityref( self, name ):
        """Convert entity references.

        As an alternative to overriding this method; one can tailor the
        results by setting up the self.entitydefs mapping appropriately.
        """
        table = self.entitydefs
        if name in table:
            return table[ name ]
        else:
            return


def set_pretty_formatting( text ):
    text = text.replace( "<br />", "\n" )
    text = text.replace( "<i>", "[I]" ).replace( "</i>", "[/I]" )
    text = text.replace( "<b>", "[B]" ).replace( "</b>", "[/B]" )
    text = text.replace( "<strong>", "[B]" ).replace( "</strong>", "[/B]" )
    text = text.replace( "<em>", "[I]" ).replace( "</em>", "[/I]" )
    text = text.replace( "<p>", "" ).replace( "</p>", "" )
    return text


def set_entity_or_charref( text ):
    try: text = ENTITY_OR_CHARREF( text ).entity_or_charref
    except: pass
    return set_pretty_formatting( text )



if ( __name__ == "__main__" ):
    cvt = set_entity_or_charref( "test ENTITY_OR_CHARREF: &ccedil;&#45;&amp;&#45;?&#45&Ucirc;" )
    print cvt
    print repr( cvt )

