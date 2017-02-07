# -*- coding: utf-8 -*-

import re
import xbmcgui
import requests 
import bs4
import pprint

from default import log, addon_path

def readHTML(link_url, a, b):
    #from resources.lib.domains import parse_reddit_link, sitesBase
    from resources.lib.utils import markdown_to_bbcode, unescape  #, ret_info_type_icon, build_script
    from resources.lib.guis import commentsGUI

    from resources.lib.html2text import HTML2Text
    
    from urlparse import urlparse
    

    listitems=[]
    
    log('readHTML:' + link_url )


    #log( unicodetoascii("####weren\xe2\x80\x99t") )    
    #return

#    aaa=u'I\xe2\x80\x99ve just finished a marathon of watching \xe2\x80\x9cBREAKING BAD\xe2\x80\x9d \xe2\x80\x93 from episode one of the First Season \xe2\x80\x93 to the last eight episodes of the Sixth Seaso'
#    aab=unicodetoascii2( aaa )
#    #aab=str(aaa)
#    log('###1#' + str(aaa).encode('utf-8') )
#    log('###2#' + aab )
#    
#    return

    #fake the user agent. to hopefully get a mobile version of the website 
    headers = {'User-Agent': 'Opera/9.80 (J2ME/MIDP; Opera Mini/9.80 (S60; SymbOS; Opera Mobi/23.348; U; en) Presto/2.5.25 Version/10.54'}
    
    page = requests.get( link_url, headers=headers )
    #log( repr( page.text ))

    h = HTML2Text()
    h.ignore_links = True
    h.body_width   = 0    #don't wrap text at 78 chars (default)
    #log(  h.handle( page.text ) )
    
    h2t=h.handle( page.text )
    
    h2t=h2t.split('\n\n')
    #log( pprint.pformat( h2t ) )
    
    for idx, line in enumerate(h2t):
        #log(line)
        
        if len(line)<25:
            #log('*len ignored:' )
            continue
        
        if line_rejected( line ):
            #log('*line_rejected:' )
            continue
        
        if '![' in line:
            alt,uri=get_alt_and_link(link_url, line)
            if uri:
                domain = '{uri.netloc}'.format( uri=urlparse( uri ) )
                if not alt: alt='(image)'
                side="[COLOR greenyellow]%s"%(alt)  + "[/COLOR]"
                liz=listitem(side, alt,uri,uri,domain )
            else:
                liz=listitem(str(len(line)), markdown_to_bbcode(line) )
            pass
        else:
            liz=listitem( label=line[0:30].replace('\n',''), 
                          plot=line,
                          link='',
                          art_thumb='',
                          domain='', 
                          votes=len(line) )
        
        if liz:
            listitems.append(liz)
    

    
#    text = soup.get_text()
#    tl=text.split('\n')
#
#    tl=[ text for text in tl if len(text) > 5]
#    log( pprint.pformat(tl) )
#
#    for text in tl:
#
#        plot=markdown_to_bbcode(text)
#        plot=unescape(plot)  #convert html entities e.g.:(&#39;)
#
#        liz=xbmcgui.ListItem(label=text[0:50] , 
#                             label2="",
#                             iconImage="", 
#                             thumbnailImage="")
#
#        liz.setInfo( type="Video", infoLabels={ "Title": '', "plot": plot, "studio": '', "votes": 0, "director": '' } )
#        listitems.append(liz)



    ui = commentsGUI('view_461_comments.xml' , addon_path, defaultSkin='Default', defaultRes='1080i', listing=listitems, id=55)
    #ui.setProperty('comments', 'no')   #i cannot get the links button to show/hide in the gui class. I resort to setting a property and having the button xml check for this property to show/hide
    
    #ui = commentsGUI('view_463_comments.xml' , addon_path, defaultSkin='Default', defaultRes='1080i', listing=li, id=55)
    ui.title_bar_text='html2text'
    ui.include_parent_directory_entry=False

    ui.doModal()
    del ui

def line_rejected( text ):
    re_1=re.compile('(\*\s[0-9a-zA-Z _]{1,20}$)', re.MULTILINE )   # up to 20 characters
    
    asterisk_line=re_1.findall(text)  #matches  * TV
    if asterisk_line:                 #         * News
        return True                   #         * Sports


def get_alt_and_link(source_url, text):
    #log('get_alt_and_link:' + text )
    #parses the ![...](...) pattern returned by html2text
    from urlparse import urlparse
    domain = '{uri.netloc}'.format( uri=urlparse( source_url ) )
    url_path = '{uri.path}'.format( uri=urlparse( source_url ) ).split('/')
    url_path= '/'.join(  url_path[:-1] )  #url_path needs more testing

    alt,uri='',''
    
    link_re = re.compile('!\[(.*?)\]\((.*?)\)')  # catch the ![...](...) pattern used in links
    #result = prog.findall(post_text)
    link=link_re.findall(text)
    if link:
        #log('got a link [...](...)match' + repr(link))
        alt, uri=link[0]
        #3 types of uri in src:
        #  1- absolute: https://.......jpg
        #  2- relative: /....jpg   or ....jpg
        #  3- data:     data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEA.....
        #
        if uri.startswith('http'):
            pass  
        elif uri.startswith('//'):
            uri='http:'+uri
        elif uri.startswith('/'):  #relative to domain
            uri='http://'+domain+uri
        elif uri.startswith('data:image'):
            log('***cant handle this image URI')
            pass
        else:          #relative to page
            uri='http://'+domain+url_path+'/'+uri  #not tested
        
    return alt,uri
    
def listitem(label, plot, link='', art_thumb='', domain='', votes=0 ):
    #builds the listitem object used in the gui
    #from resources.lib.utils import unescape
    liz=xbmcgui.ListItem(label=label, 
                         label2="",
                         iconImage="", 
                         thumbnailImage="")

    liz.setInfo( type="Video", infoLabels={ "plot": unicodetoascii(plot), "studio": domain, "votes": votes, "director": '' } )

    if link:
        liz.setProperty('onClick_action', link)  #not really useful

    if art_thumb:
        liz.setArt({"thumb": art_thumb })
        
    liz.setProperty('link_url', link )  #just used as text at bottom of the screen

    return liz

def unicodetoascii(text):
    #http://stackoverflow.com/questions/27996448/python-encoding-decoding-problems
    uni2ascii = {
            ord('\xe2\x80\x99'.decode('utf-8')): ord("'"),
            ord('\xe2\x80\x9c'.decode('utf-8')): ord('"'),
            ord('\xe2\x80\x9d'.decode('utf-8')): ord('"'),
            ord('\xe2\x80\x9e'.decode('utf-8')): ord('"'),
            ord('\xe2\x80\x9f'.decode('utf-8')): ord('"'),
            ord('\xc3\xa9'.decode('utf-8')): ord('e'),
            ord('\xe2\x80\x9c'.decode('utf-8')): ord('"'),
            ord('\xe2\x80\x93'.decode('utf-8')): ord('-'),
            ord('\xe2\x80\x92'.decode('utf-8')): ord('-'),
            ord('\xe2\x80\x94'.decode('utf-8')): ord('-'),
            ord('\xe2\x80\x94'.decode('utf-8')): ord('-'),
            ord('\xe2\x80\x98'.decode('utf-8')): ord("'"),
            ord('\xe2\x80\x9b'.decode('utf-8')): ord("'"),

            ord('\xe2\x80\x90'.decode('utf-8')): ord('-'),
            ord('\xe2\x80\x91'.decode('utf-8')): ord('-'),

            ord('\xe2\x80\xb2'.decode('utf-8')): ord("'"),
            ord('\xe2\x80\xb3'.decode('utf-8')): ord("'"),
            ord('\xe2\x80\xb4'.decode('utf-8')): ord("'"),
            ord('\xe2\x80\xb5'.decode('utf-8')): ord("'"),
            ord('\xe2\x80\xb6'.decode('utf-8')): ord("'"),
            ord('\xe2\x80\xb7'.decode('utf-8')): ord("'"),

            ord('\xe2\x81\xba'.decode('utf-8')): ord("+"),
            ord('\xe2\x81\xbb'.decode('utf-8')): ord("-"),
            ord('\xe2\x81\xbc'.decode('utf-8')): ord("="),
            ord('\xe2\x81\xbd'.decode('utf-8')): ord("("),
            ord('\xe2\x81\xbe'.decode('utf-8')): ord(")"),
        }
    
    #return text.decode('utf-8').translate(uni2ascii).encode('ascii','ignore')  #special chars disappear    
    return text.decode('utf-8').translate(uni2ascii).encode('utf-8')
    
def soup_method_bak():
#    soup = bs4.BeautifulSoup(page.text )  #soup = bs4.BeautifulSoup(page.text.encode('utf-8')  )   won't work
#    #log( repr( soup.title ))
#    try:    title=soup.title.string
#    except: title=''
#    
#    log( repr( title ))
#
#    #p=soup.find_all('p')
#    #log( pprint.pformat(p) )
#
#    #log( repr(url_path ))
#    
#    #log( 'path: ' + url_path )
#    
#
#    for elem in soup.findAll(['script', 'style']):
#        elem.extract()  #removes a tag or string from the tree. It returns the tag or string that was extracted:
#
#    for idx, elem in enumerate( soup.findAll()) :
#        liz=None
#
#        if elem.name == 'img':
#            #3 types of uri in src:
#            #  1- absolute: https://.......jpg
#            #  2- relative: /....jpg   or ....jpg
#            #  3- data:     data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEA.....
#            #
#            src=elem.get('src') 
#            if src.startswith('http'):
#                pass  
#            elif src.startswith('//'):
#                src='http:'+src
#            elif src.startswith('/'):  #relative to domain
#                src='http://'+domain+src
#            elif src.startswith('data:image'):
#                log('cant handle this image URI')
#                pass
#            else:          #relative to page
#                src='http://'+domain+url_path+'/'+src  #not tested
#
#            #log( '****%.3d %s' %( idx, repr( elem )[0:200]  ) )
#            #log( repr(elem.get('alt')) + ' --' + repr(elem.get('src')) )
#            #log( 'src='+src )
#            liz=listitem(elem.get('alt'), elem.text, '', src )
#            
#        elif elem.name == 'a':
#            #log( '****%.3d %s' %( idx, repr( elem )[0:200]  ) )
#            pass
#        elif elem.name == 'p':
#            liz=listitem(elem.name, elem.text )
#            log( '****%.3d <%s> %s' %( idx, elem.name, repr( elem.text )[0:200]  ) )
#            pass
#        else:
#            log( '****%.3d <%s> %s' %( idx, elem.name, repr( elem.text )[0:200]  ) )
#            
#        if liz:
#            listitems.append(liz)
    
    pass

def unicodetoascii2(text):
    #http://stackoverflow.com/questions/27996448/python-encoding-decoding-problems
    uni2ascii = {
            '\xe2\x80\x99': ord("'"),
        }
    
    #return text.decode('utf-8').translate(uni2ascii).encode('ascii','ignore')  #special chars disappear    
    return text.translate(uni2ascii)


if __name__ == '__main__':
    pass
