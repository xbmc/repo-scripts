# -*- coding: utf-8 -*-

import re
import xbmcgui
import requests
import pprint

from default import log, addon_path

def readHTML(link_url, a, b):

    from resources.lib.utils import markdown_to_bbcode, unescape  #, ret_info_type_icon, build_script
    from resources.lib.guis import commentsGUI

    from resources.lib.html2text import HTML2Text

    from urlparse import urlparse


    listitems=[]

    log('readHTML:' + link_url )

    headers = {'User-Agent': 'Opera/9.80 (J2ME/MIDP; Opera Mini/9.80 (S60; SymbOS; Opera Mobi/23.348; U; en) Presto/2.5.25 Version/10.54'}

    page = requests.get( link_url, headers=headers )


    h = HTML2Text()
    h.ignore_links = True
    h.body_width   = 0    #don't wrap text at 78 chars (default)


    h2t=h.handle( page.text )

    h2t=h2t.split('\n\n')


    for _, line in enumerate(h2t):


        if len(line)<25:

            continue

        if line_rejected( line ):

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




    ui = commentsGUI('view_461_comments.xml' , addon_path, defaultSkin='Default', defaultRes='1080i', listing=listitems, id=55)

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

    from urlparse import urlparse
    domain = '{uri.netloc}'.format( uri=urlparse( source_url ) )
    url_path = '{uri.path}'.format( uri=urlparse( source_url ) ).split('/')
    url_path= '/'.join(  url_path[:-1] )  #url_path needs more testing

    alt,uri='',''

    link_re = re.compile('!\[(.*?)\]\((.*?)\)')  # catch the ![...](...) pattern used in links

    link=link_re.findall(text)
    if link:

        alt, uri=link[0]

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

    liz=xbmcgui.ListItem(label=label)

    liz.setInfo( type="Video", infoLabels={ "plot": unicodetoascii(plot), "studio": domain, "votes": votes, "director": '' } )

    if link:
        liz.setProperty('onClick_action', link)  #not really useful

    if art_thumb:
        liz.setArt({"thumb": art_thumb })

    liz.setProperty('link_url', link )  #just used as text at bottom of the screen

    return liz

def unicodetoascii(text):

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

    return text.decode('utf-8').translate(uni2ascii).encode('utf-8')

def soup_method_bak():


    pass

def unicodetoascii2(text):

    uni2ascii = {
            '\xe2\x80\x99': ord("'"),
        }

    return text.translate(uni2ascii)


if __name__ == '__main__':
    pass
