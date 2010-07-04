import os, sys, re, xbmc, xbmcgui, string, time, urllib, urllib2
from utilities import toOpenSubtitles_two

_ = sys.modules[ "__main__" ].__language__

main_url = "http://subscene.com/"
debug_pretext = "[Subscene subtitle service]:"

# Subscene uploads possible:
# zip, rar, srt, srt.style, sub, txt, ssa, smi

# XBMC supports:
# AQT, JSS, MicroDVD, MPL, RT, SMI, SRT, SUB, TXT, VobSub (idx + sub), VPlayer and partial SSA and ASS

# Subtypes supported (unfortunately the script and python do not have a rar module):
subs_types = "zip", "srt", "sub", "txt", "ssa", "smi", "rar"

# Seasons as strings for searching
seasons = ["Specials", "First", "Second", "Third", "Fourth", "Fifth", "Sixth", "Seventh", "Eighth", "Ninth", "Tenth"]
seasons = seasons + ["Eleventh", "Twelfth", "Thirteenth", "Fourteenth", "Fifteenth", "Sixteenth", "Seventeenth", "Eighteenth", "Nineteenth", "Twentieth"]
seasons = seasons + ["Twenty-first", "Twenty-second", "Twenty-third", "Twenty-fourth", "Twenty-fifth", "Twenty-sixth", "Twenty-seventh", "Twenty-eighth", "Twenty-ninth"]

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


# movie/seasonfound pattern example:
"""
			<a href="/S-Darko-AKA-S-Darko-A-Donnie-Darko-Tale/subtitles-76635.aspx" class=popular>
				S. Darko AKA S. Darko: A Donnie Darko Tale (2009)
"""
movie_season_pattern = "...<a href=\"/([^\n\r\t]*?/subtitles-\d{1,10}.aspx)\".{1,14}>\r\n.{4}([^\n\r\t]*?) \((\d\d\d\d)\) \r\n"
# group(1) = link, group(2) = movie_season_title,  group(3) = year


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



def find_movie(content, title, year):
    url_found = None
    for matches in re.finditer(movie_season_pattern, content, re.IGNORECASE | re.DOTALL):
        xbmc.output("%s Found movie on search page: %s (%s)" % (debug_pretext, matches.group(2), matches.group(3)), level=xbmc.LOGDEBUG )
        if string.find(string.lower(matches.group(2)),string.lower(title)) > -1:
            if matches.group(3) == year:
                xbmc.output("%s Matching movie found on search page: %s (%s)" % (debug_pretext, matches.group(2), matches.group(3)), level=xbmc.LOGDEBUG )
                url_found = matches.group(1)
                break
    return url_found


def find_tv_show_season(content, tvshow, season):
    url_found = None
    for matches in re.finditer(movie_season_pattern, content, re.IGNORECASE | re.DOTALL):
        xbmc.output("%s Found tv show season on search page: %s" % (debug_pretext, matches.group(2)), level=xbmc.LOGDEBUG )
        if string.find(string.lower(matches.group(2)),string.lower(tvshow) + " ") > -1:
            if string.find(string.lower(matches.group(2)),string.lower(season)) > -1:
                xbmc.output("%s Matching tv show season found on search page: %s" % (debug_pretext, matches.group(2)), level=xbmc.LOGDEBUG )
                url_found = matches.group(1)
                break
    return url_found


def getallsubs(response_url, content, language, title, subtitles_list, search_string):
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
                    if search_string != "":
                        if string.find(string.lower(filename),string.lower(search_string)) > -1:
                            xbmc.output("%s Subtitles found: %s, %s, id=%s, %s" % (debug_pretext, languagefound, typeid, subtitleid, filename), level=xbmc.LOGDEBUG )
                            subtitles_list.append({'postparams': postparams, 'rating': '0', 'format': string.lower(typeid), 'movie':  title, 'filename': filename, 'sync': False, 'link': response_url, 'language_flag': 'flags/' + languageshort + '.gif', 'language_name': language})
                    else:
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
    if len(tvshow) == 0:
        search_string = title
    if len(tvshow) > 0:
        search_string = tvshow + " - " + seasons[int(season)] + " Season"
    xbmc.output("%s Search string = %s" % (debug_pretext, search_string), level=xbmc.LOGDEBUG )
    url = main_url + "filmsearch.aspx?q=" + urllib.quote_plus(search_string)
    content, response_url = geturl(url)
    if content is not None:
        if re.search("subtitles-\d{2,10}\.aspx", response_url, re.IGNORECASE):
            xbmc.output("%s One movie found, getting subs ..." % debug_pretext, level=xbmc.LOGDEBUG )
            getallsubs(response_url, content, lang1, title, subtitles_list,  "")
            if (lang2 != lang1): getallsubs(response_url, content, lang2, title, subtitles_list, "")
            if ((lang3 != lang2) and (lang3 != lang1)): getallsubs(response_url, content, lang3, title, subtitles_list, "")
        else:
            if len(tvshow) == 0:
                xbmc.output("%s Multiple movies found, searching for the right one ..." % debug_pretext, level=xbmc.LOGDEBUG )
                subspage_url = find_movie(content, title, year)
                if subspage_url is not None:
                    xbmc.output("%s Movie found in list, getting subs ..." % debug_pretext, level=xbmc.LOGDEBUG )
                    url = main_url + subspage_url
                    content, response_url = geturl(url)
                    if content is not None:
                        getallsubs(response_url, content, lang1, title, subtitles_list, "")
                        if (lang2 != lang1): getallsubs(response_url, content, lang2, title, subtitles_list, "")
                        if ((lang3 != lang2) and (lang3 != lang1)): getallsubs(response_url, content, lang3, title, subtitles_list, "")
                else:
                    xbmc.output("%s Movie not found in list: %s" % (debug_pretext, title), level=xbmc.LOGDEBUG )
                    if string.find(string.lower(title),"&") > -1:
                        title = string.replace(title, "&", "and")
                        xbmc.output("%s Trying searching with replacing '&' to 'and': %s" % (debug_pretext, title), level=xbmc.LOGDEBUG )
                        subspage_url = find_movie(content, title, year)
                        if subspage_url is not None:
                            xbmc.output("%s Movie found in list, getting subs ..." % debug_pretext, level=xbmc.LOGDEBUG )
                            url = main_url + subspage_url
                            content, response_url = geturl(url)
                            if content is not None:
                                getallsubs(response_url, content, lang1, title, subtitles_list, "")
                                if (lang2 != lang1): getallsubs(response_url, content, lang2, title, subtitles_list, "")
                                if ((lang3 != lang2) and (lang3 != lang1)): getallsubs(response_url, content, lang3, title, subtitles_list, "")
                        else:
                            xbmc.output("%s Movie not found in list: %s" % (debug_pretext, title), level=xbmc.LOGDEBUG )
            if len(tvshow) > 0:
                xbmc.output("%s Multiple tv show seasons found, searching for the right one ..." % debug_pretext, level=xbmc.LOGDEBUG )
                tv_show_seasonurl = find_tv_show_season(content, tvshow, seasons[int(season)])
                if tv_show_seasonurl is not None:
                    xbmc.output("%s Tv show season found in list, getting subs ..." % debug_pretext, level=xbmc.LOGDEBUG )
                    url = main_url + tv_show_seasonurl
                    content, response_url = geturl(url)
                    if content is not None:
                        search_string = "s%#02de%#02d" % (int(season), int(episode))
                        getallsubs(response_url, content, lang1, title, subtitles_list, search_string)
                        if (lang2 != lang1): getallsubs(response_url, content, lang2, title, subtitles_list, search_string)
                        if ((lang3 != lang2) and (lang3 != lang1)): getallsubs(response_url, content, lang3, title, subtitles_list, search_string)


    return subtitles_list, "", msg #standard output


def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input
    url        = subtitles_list[pos][ "link" ]
    postparams = subtitles_list[pos][ "postparams" ]
    language = subtitles_list[pos][ "language_name" ]    
    format     = subtitles_list[pos][ "format" ]
    local_tmp_file = os.path.join(tmp_sub_dir, "subscene." + format)
    if (format != "zip") and (format != "rar"):
        subs_file = local_tmp_file
        packed = False
    else:
        packed = True
    class MyOpener(urllib.FancyURLopener):
        version = 'User-Agent=Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.2.3) Gecko/20100401 Firefox/3.6.3 ( .NET CLR 3.5.30729)'
    my_urlopener = MyOpener()
    my_urlopener.addheader('Referer', url)
    xbmc.output("%s Fetching subtitles using url '%s'with referer header '%s' and post parameters '%s'" % (debug_pretext, url, url, postparams), level=xbmc.LOGDEBUG )
    response = my_urlopener.open(url,  postparams)
    try:
        xbmc.output("%s Saving subtitles to '%s'" % (debug_pretext, local_tmp_file), level=xbmc.LOGDEBUG )
        local_file_handle = open(local_tmp_file, "w" + "b")
        local_file_handle.write(response.read())
        local_file_handle.close()
    except:
        xbmc.output("%s Failed to save subtitles to '%s'" % (debug_pretext, local_tmp_file), level=xbmc.LOGDEBUG )
    if packed:
        files = os.listdir(tmp_sub_dir)
        init_filecount = len(files)
        filecount = init_filecount
        xbmc.executebuiltin("XBMC.Extract(" + local_tmp_file + "," + tmp_sub_dir +")")
        waittime  = 0
        while (filecount == init_filecount) and (waittime < 20): # nothing yet extracted
            time.sleep(1)  # wait 1 second to let the builtin function 'XBMC.extract' unpack
            files = os.listdir(tmp_sub_dir)
            filecount = len(files)
            waittime  = waittime + 1
        if waittime == 20:
            xbmc.output("%s Failed to unpack subtitles in '%s'" % (debug_pretext, tmp_sub_dir), level=xbmc.LOGDEBUG )
        else:
            xbmc.output("%s Unpacked files in '%s'" % (debug_pretext, tmp_sub_dir), level=xbmc.LOGDEBUG )        
            for file in files:
                if string.split(file, '.')[-1] in ["srt", "sub", "txt", "ssa", "smi"]: # unpacked file is a subtitle file
                    xbmc.output("%s Unpacked subtitles file '%s'" % (debug_pretext, file), level=xbmc.LOGDEBUG )        
                    subs_file = os.path.join(tmp_sub_dir, file)
    
    xbmc.output("%s Subtitles saved to '%s'" % (debug_pretext, local_tmp_file), level=xbmc.LOGDEBUG )
    return False, language, subs_file #standard output
