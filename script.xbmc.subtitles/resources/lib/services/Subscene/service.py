import os, sys, re, xbmc, xbmcgui, string, urllib, urllib2
from utilities import toOpenSubtitles_two

_ = sys.modules[ "__main__" ].__language__

main_url = "http://subscene.com/"
debug_pretext = "[Subscene subtitle service]:"

# Subscene uploads possible:
# zip, rar, srt, srt.style, sub, txt, ssa, smi

# XBMC supports:
# AQT, JSS, MicroDVD, MPL, RT, SMI, SRT, SUB, TXT, VobSub (idx + sub), VPlayer and partial SSA and ASS 

# Subtypes supported (unfortunately the script and python do not have a rar module):
subs_types = "zip", "srt", "srt", "sub", "txt", "ssa", "smi"


#====================================================================================================================
# Regular expression patterns
#====================================================================================================================

# subtitle pattern example:
"""
		<tr>
			<td>

				<a class="a1" id=s290610 href="javascript:Subtitle(290610, 'zip', '53', '0');">
					<span class="r100" >
						Arabic 
					</span>
					 <span id="r290610">The.Time.Travelers.Wife.2009.DVDRip.XviD-iMBT (By:  Don4EveR & Abu Essa)</span>
				</a> 
				

			<td class="a3">1
			<td>
"""
subtitle_pattern = "..<tr>.{5}<td>.{6}<a class=\"a1\" id=s\d+ href=\"javascript:Subtitle\((\d+), '(...)', '\d+', '(\d+)'\);\">\
.{7}<span class=\"r(0|100)\" >.{8}(.{3,25}) .{7}</span>.{7} <span id=\"r\d+\">(.{5,500})</span>\
.{6}</a> .{13}<td class=\"a3\">1.{5}<td>(?!<div id=imgEar)" # it think it should not match a "Hearing impaired" subtitle type
# group(1) = subtitleId, group(2) = typeId, group(3) = filmId, group(4) = qualitycode, group(5) = language, group(6) = filename


# moviefound pattern example:
"""
			<a href="/S-Darko-AKA-S-Darko-A-Donnie-Darko-Tale/subtitles-76635.aspx" class=popular>
				S. Darko AKA S. Darko: A Donnie Darko Tale (2009) 
"""
movie_pattern = "...<a href=\"/([^\n\r\t]*?/subtitles-\d{1,10}.aspx)\".{1,14}>\r\n.{4}([^\n\r\t]*?) \((\d\d\d\d)\) \r\n"
# group(1) = link, group(2) = movietitle,  group(3) = year


# viewstate pattern example:
"""
<input type="hidden" name="__VIEWSTATE" id="__VIEWSTATE" value="/wEPDwUKMTM3MDMyNDg2NmQYAQUeX19Db250cm9sc1JlcXVpcmVQb3N0QmFja0tleV9fFgEFF3MkcyRsYyRiY3Ikc29ydEJ5TGF0ZXN0DgczK1M2TFdV419Eo8mR8i4CBFY=" />
"""
viewstate_pattern = "<input type=\"hidden\" name=\"__VIEWSTATE\" id=\"__VIEWSTATE\" value=\"([^\n\r\t]*?)\" />"
# group(1) = viewstatevalue


#====================================================================================================================
# Functions
#====================================================================================================================

def to_subscene_lang(language):
    if language == "Chinese":            return "Chinese BG code"
    elif language == "PortugueseBrazil": return "Brazillian Portuguese"
    elif language == "SerbianLatin":     return "Serbian"
    elif language == "Ukrainian":        return "Ukranian"
    else:                                return language


def findmovie(content, title, year):
    url_found = None
    for matches in re.finditer(movie_pattern, content, re.IGNORECASE | re.DOTALL):
        xbmc.output("%s Found movie on search page:          %s (%s)" % (debug_pretext, matches.group(2), matches.group(3)), level=xbmc.LOGDEBUG )
        if string.find(string.lower(matches.group(2)),string.lower(title)) > -1:
            if matches.group(3) == year:
                xbmc.output("%s Matching movie found on search page: %s (%s)" % (debug_pretext, matches.group(2), matches.group(3)), level=xbmc.LOGDEBUG )
                url_found = matches.group(1)
                break
    return url_found


def getallsubs(response_url, content, language, title, subtitles_list):
    match = re.search(viewstate_pattern, content, re.IGNORECASE | re.DOTALL)
    if match:
        viewstate = match.group(1)
        xbmc.output("%s Hidden inputfield __VIEWSTATE found: %s" % (debug_pretext, viewstate), level=xbmc.LOGDEBUG )
        for matches in re.finditer(subtitle_pattern, content, re.IGNORECASE | re.DOTALL):
            typeid = matches.group(2)
            if string.lower(typeid) in subs_types:
                languagefound = matches.group(5)
                if languagefound ==  to_subscene_lang(language):
                    #link = main_url + "downloadissue.aspx?subtitleId=" + matches.group(1) + "&contentType=" + matches.group(2)
                    languageshort = toOpenSubtitles_two(language)
                    subtitleid = matches.group(1)
                    filmid     = matches.group(3)
                    filename   = matches.group(6)
                    postparams = urllib.urlencode( { '__VIEWSTATE': viewstate, 'subtitleId': subtitleid , 'filmId': filmid, 'typeId': typeid} )
                    xbmc.output("%s Subtitles found: %s, %s, id=%s, %s" % (debug_pretext, languagefound, typeid, subtitleid, filename), level=xbmc.LOGDEBUG )                    
                    subtitles_list.append({'postparams': postparams, 'rating': '0', 'format': string.lower(typeid), 'movie':  title, 'filename': filename, 'sync': False, 'link': response_url, 'language_flag': 'flags/' + languageshort + '.gif', 'language_name': language})


def geturl(url):
    xbmc.output("%s Getting url:%s" % (debug_pretext, url), level=xbmc.LOGDEBUG )
    try:
        response   = urllib2.urlopen(url)
        content    = response.read()
        return_url = response.geturl()
    except:
        xbmc.output("%s Failed to get url:%s" % (debug_pretext, url), level=xbmc.LOGDEBUG )        
        content    = None
        return_url = None
    return(content, return_url)


def search_subtitles( file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3 ): #standard input
    subtitles_list = []
    msg = ""
    xbmc.output("%s Title = %s" % (debug_pretext, title), level=xbmc.LOGDEBUG )
    if len(tvshow) == 0: # only process movies
        url = main_url + "filmsearch.aspx?q=" + urllib.quote_plus(title)
        content, response_url = geturl(url)
        if content is not None:
            if re.search("subtitles-\d{2,10}\.aspx", response_url, re.IGNORECASE):
                xbmc.output("%s One movie found, getting subs ..." % debug_pretext, level=xbmc.LOGDEBUG )
                getallsubs(response_url, content, lang1, title, subtitles_list)
                if (lang2 != lang1): getallsubs(response_url, content, lang2, title, subtitles_list)
                if ((lang3 != lang2) and (lang3 != lang1)): getallsubs(response_url, content, lang3, title, subtitles_list)
            else:
                xbmc.output("%s Multiple movies found, searching for the right one ..." % debug_pretext, level=xbmc.LOGDEBUG )
                movie_url = findmovie(content, title, year)
                if movie_url is not None:
                    xbmc.output("%s Movie found in list, getting subs ..." % debug_pretext, level=xbmc.LOGDEBUG )
                    url = main_url + movie_url
                    content, response_url = geturl(url)
                    if content is not None:
                        getallsubs(response_url, content, lang1, title, subtitles_list)
                        if (lang2 != lang1): getallsubs(response_url, content, lang2, title, subtitles_list)
                        if ((lang3 != lang2) and (lang3 != lang1)): getallsubs(response_url, content, lang3, title, subtitles_list)
                else:
                    xbmc.output("%s Movie not found in list: %s" % (debug_pretext, title), level=xbmc.LOGDEBUG )
                    if string.find(string.lower(title),"&") > -1:
                        title = string.replace(title, "&", "and")
                        xbmc.output("%s Trying searching with replacing '&' to 'and': %s" % (debug_pretext, title), level=xbmc.LOGDEBUG )
                        movie_url = findmovie(content, title, year)
                        if movie_url is not None:
                            xbmc.output("%s Movie found in list, getting subs ..." % debug_pretext, level=xbmc.LOGDEBUG )
                            url = main_url + movie_url
                            content, response_url = geturl(url)
                            if content is not None:
                                getallsubs(response_url, content, lang1, title, subtitles_list)
                                if (lang2 != lang1): getallsubs(response_url, content, lang2, title, subtitles_list)
                                if ((lang3 != lang2) and (lang3 != lang1)): getallsubs(response_url, content, lang3, title, subtitles_list)
                        else:
                            xbmc.output("%s Movie not found in list: %s" % (debug_pretext, title), level=xbmc.LOGDEBUG )
    else:
        xbmc.output("%s Tv show detected: %s" % (debug_pretext, tvshow), level=xbmc.LOGDEBUG )
        msg = "Won't work, Subscene is only for movies."
    return subtitles_list, "", msg #standard output


def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input
    url        = subtitles_list[pos][ "link" ]
    postparams = subtitles_list[pos][ "postparams" ]
    format     = subtitles_list[pos][ "format" ]
    if format != "zip":
        local_tmp_file = os.path.join(tmp_sub_dir, "subscene_subs." + format)
    else:
        local_tmp_file = zip_subs
    class MyOpener(urllib.FancyURLopener):
        version = 'User-Agent=Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.2.3) Gecko/20100401 Firefox/3.6.3 ( .NET CLR 3.5.30729)'
    my_urlopener = MyOpener()
    my_urlopener.addheader('Referer', url)
    try:
        xbmc.output("%s Fetching subtitles using url '%s'with referer header '%s' and post parameters '%s'" % (debug_pretext, url, url, postparams), level=xbmc.LOGDEBUG )
        response = my_urlopener.open(url,  postparams )
        xbmc.output("%s Saving subtitles to '%s'" % (debug_pretext, local_tmp_file), level=xbmc.LOGDEBUG )
        local_file_handle = open(local_tmp_file, "w" + "b")
        local_file_handle.write(response.read())
        local_file_handle.close()
    except:
        xbmc.output("%s Failed to save subtitles to '%s'" % (debug_pretext, local_tmp_file), level=xbmc.LOGDEBUG )
    language = subtitles_list[pos][ "language_name" ]
    xbmc.output("%s Subtitles saved to '%s'" % (debug_pretext, local_tmp_file), level=xbmc.LOGDEBUG )
    if format!= "zip":
        return False, language, local_tmp_file #standard output
    else:
        return True, language, "" #standard output
