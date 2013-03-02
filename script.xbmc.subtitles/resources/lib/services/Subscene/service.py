# -*- coding: UTF-8 -*-

import os, sys, re, xbmc, xbmcgui, string, time, urllib, urllib2
from utilities import languageTranslate, log

main_url = "http://v2.subscene.com/"
debug_pretext = ""

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
				<a class="a1" href="/arabic/Magnolia/subtitle-311056.aspx" title="Subtitle - Magnolia  - Arabic">
					<span class="r0" >

						Arabic
					</span>
					 <span id="r311056">Magnolia.1999.720p.BluRay.x264-LEVERAGE</span>
				</a>



			</td>
			<td class="a3">1
			</td>
			<td><div id=imgEar title='Hearing Impaired'>&nbsp;</div>
			</td>

"""
subtitle_pattern = "..<tr>.{5}<td>.{6}<a class=\"a1\" href=\"/([^\n\r]{10,200}?-\d{3,10}.aspx)\" title=\"[^\n\r]{10,200}\">\
[\r\n\t ]+?<span class=\"r(0|100)\" >[\r\n\t\ ]+([^\r\n\t]+?) [\r\n\t]+</span>[\r\n\t ]+?<span id=\"r\d+\">([^\r\n\t]{5,500})</span>\
[\r\n\t]+?</a>[\r\n\t ]+?</td>[\r\n\t ]+?<td class=\"a3\">1[\r\n\t\ ]+?</td>[\r\n\t\ ]+?<td>(|.{52})\r\n\t\t\t</td>"
# group(1) = downloadlink, group(2) = qualitycode, group(3) = language, group(4) = filename, group(5) = hearing impaired


# movie/seasonfound pattern example:
"""
			<a href="/inception/subtitles-80839.aspx" class=popular>
				Inception (2010) 
				<dfn>(327)</dfn>
"""
movie_season_pattern = "...<a href=\"([^\n\r\t]*?/subtitles-\d{1,10}.aspx)\".{1,14}>\r\n{0,3}.{4}([^\n\r\t\&#]*?) \((\d\d\d\d)\) \r\n{0,3}.{1,4}<dfn>\(.{1,5}</dfn>"
# group(1) = link, group(2) = movie_season_title,  group(3) = year




# download link pattern example:
"""
		<a href="/subtitle/download?mac=LxawhQiaMYm9O2AsoNMHXbXDYN2b4yBreI8TJIBfpdw7UIo1JP5566Sbb2ei_zUC0" rel="nofollow" onclick="DownloadSubtitle(this)" id="downloadButton" class="button Positive">
"""
downloadlink_pattern = "...<a href=\"(.+?)\" rel=\"nofollow\" onclick=\"DownloadSubtitle"
# group(1) = link

# <input type="hidden" name="__VIEWSTATE" id="__VIEWSTATE" value="/wEPDwUKLTk1MDk4NjQwM2Rk5ncGq+1a601mEFQDA9lqLwfzjaY=" />
viewstate_pattern = "<input type=\"hidden\" name=\"__VIEWSTATE\" id=\"__VIEWSTATE\" value=\"([^\n\r\t]*?)\" />"

# <input type="hidden" name="__PREVIOUSPAGE" id="__PREVIOUSPAGE" value="V1Stm1vgLeLd6Kbt-zkC8w2" />
previouspage_pattern = "<input type=\"hidden\" name=\"__PREVIOUSPAGE\" id=\"__PREVIOUSPAGE\" value=\"([^\n\r\t]*?)\" />"

# <input type="hidden" name="subtitleId" id="subtitleId" value="329405" />
subtitleid_pattern = "<input type=\"hidden\" name=\"subtitleId\" id=\"subtitleId\" value=\"(\d+?)\" />"

# <input type="hidden" name="typeId" value="zip" />
typeid_pattern = "<input type=\"hidden\" name=\"typeId\" value=\"([^\n\r\t]{3,15})\" />"

# <input type="hidden" name="filmId" value="78774" />
filmid_pattern = "<input type=\"hidden\" name=\"filmId\" value=\"(\d+?)\" />"


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
        log( __name__ ,"%s Found movie on search page: %s (%s)" % (debug_pretext, matches.group(2), matches.group(3)))
        if string.find(string.lower(matches.group(2)),string.lower(title)) > -1:
            if matches.group(3) == year:
                log( __name__ ,"%s Matching movie found on search page: %s (%s)" % (debug_pretext, matches.group(2), matches.group(3)))
                url_found = matches.group(1)
                break
    return url_found


def find_tv_show_season(content, tvshow, season):
    url_found = None
    for matches in re.finditer(movie_season_pattern, content, re.IGNORECASE | re.DOTALL):
        log( __name__ ,"%s Found tv show season on search page: %s" % (debug_pretext, matches.group(2).decode("utf-8")))
        if string.find(string.lower(matches.group(2)),string.lower(tvshow) + " ") > -1:
            if string.find(string.lower(matches.group(2)),string.lower(season)) > -1:
                log( __name__ ,"%s Matching tv show season found on search page: %s" % (debug_pretext, matches.group(2).decode("utf-8")))
                url_found = matches.group(1)
                break
    return url_found


def getallsubs(response_url, content, language, title, subtitles_list, search_string):
    for matches in re.finditer(subtitle_pattern, content, re.IGNORECASE | re.DOTALL):
        languagefound = matches.group(3)
        if languagefound == to_subscene_lang(language):
            link = main_url + matches.group(1)
            languageshort = languageTranslate(language,0,2)
            filename   = matches.group(4)
            hearing_imp = len(matches.group(5)) > 0
            if search_string != "":
                log( __name__ , "string.lower(filename) = >" + string.lower(filename) + "<" )
                log( __name__ , "string.lower(search_string) = >" + string.lower(search_string) + "<" )
                if string.find(string.lower(filename),string.lower(search_string)) > -1:
                    log( __name__ ,"%s Subtitles found: %s, %s" % (debug_pretext, languagefound, filename))
                    subtitles_list.append({'rating': '0', 'movie':  title, 'filename': filename, 'sync': False, 'link': link, 'language_flag': 'flags/' + languageshort + '.gif', 'language_name': language, 'hearing_imp': hearing_imp})
            else:
                log( __name__ ,"%s Subtitles found: %s, %s" % (debug_pretext, languagefound, filename))
                subtitles_list.append({'rating': '0', 'movie':  title, 'filename': filename, 'sync': False, 'link': link, 'language_flag': 'flags/' + languageshort + '.gif', 'language_name': language, 'hearing_imp': hearing_imp})


def geturl(url):
    log( __name__ ,"%s Getting url:%s" % (debug_pretext, url))
    try:
        response   = urllib2.urlopen(url)
        content    = response.read()
        #Fix non-unicode charachters in movie titles
        strip_unicode = re.compile("([^-_a-zA-Z0-9!@#%&=,/'\";:~`\$\^\*\(\)\+\[\]\.\{\}\|\?\<\>\\]+|[^\s]+)")
        content    = strip_unicode.sub('', content)
        return_url = response.geturl()
    except:
        log( __name__ ,"%s Failed to get url:%s" % (debug_pretext, url))
        content    = None
        return_url = None
    return(content, return_url)


def search_subtitles( file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack ): #standard input
    subtitles_list = []
    msg = ""
    if len(tvshow) == 0:
        search_string = title
    if len(tvshow) > 0:
        search_string = tvshow + " - " + seasons[int(season)] + " Season"
    log( __name__ ,"%s Search string = %s" % (debug_pretext, search_string))
    url = main_url + "filmsearch.aspx?q=" + urllib.quote_plus(search_string)
    content, response_url = geturl(url)
    if content is not None:
        if re.search("subtitles-\d{2,10}\.aspx", response_url, re.IGNORECASE):
            log( __name__ ,"%s One movie found, getting subs ..." % debug_pretext)
            getallsubs(response_url, content, lang1, title, subtitles_list,  "")
            if (lang2 != lang1): getallsubs(response_url, content, lang2, title, subtitles_list, "")
            if ((lang3 != lang2) and (lang3 != lang1)): getallsubs(response_url, content, lang3, title, subtitles_list, "")
        else:
            if len(tvshow) == 0:
                log( __name__ ,"%s Multiple movies found, searching for the right one ..." % debug_pretext)
                subspage_url = find_movie(content, title, year)
                if subspage_url is not None:
                    log( __name__ ,"%s Movie found in list, getting subs ..." % debug_pretext)
                    url = main_url + subspage_url
                    content, response_url = geturl(url)
                    if content is not None:
                        getallsubs(response_url, content, lang1, title, subtitles_list, "")
                        if (lang2 != lang1): getallsubs(response_url, content, lang2, title, subtitles_list, "")
                        if ((lang3 != lang2) and (lang3 != lang1)): getallsubs(response_url, content, lang3, title, subtitles_list, "")
                else:
                    log( __name__ ,"%s Movie not found in list: %s" % (debug_pretext, title))
                    if string.find(string.lower(title),"&") > -1:
                        title = string.replace(title, "&", "and")
                        log( __name__ ,"%s Trying searching with replacing '&' to 'and': %s" % (debug_pretext, title))
                        subspage_url = find_movie(content, title, year)
                        if subspage_url is not None:
                            log( __name__ ,"%s Movie found in list, getting subs ..." % debug_pretext)
                            url = main_url + subspage_url
                            content, response_url = geturl(url)
                            if content is not None:
                                getallsubs(response_url, content, lang1, title, subtitles_list, "")
                                if (lang2 != lang1): getallsubs(response_url, content, lang2, title, subtitles_list, "")
                                if ((lang3 != lang2) and (lang3 != lang1)): getallsubs(response_url, content, lang3, title, subtitles_list, "")
                        else:
                            log( __name__ ,"%s Movie not found in list: %s" % (debug_pretext, title))
            if len(tvshow) > 0:
                log( __name__ ,"%s Multiple tv show seasons found, searching for the right one ..." % debug_pretext)
                tv_show_seasonurl = find_tv_show_season(content, tvshow, seasons[int(season)])
                if tv_show_seasonurl is not None:
                    log( __name__ ,"%s Tv show season found in list, getting subs ..." % debug_pretext)
                    url = main_url + tv_show_seasonurl
                    content, response_url = geturl(url)
                    if content is not None:
                        search_string = "s%#02de%#02d" % (int(season), int(episode))
                        getallsubs(response_url, content, lang1, title, subtitles_list, search_string)
                        if (lang2 != lang1): getallsubs(response_url, content, lang2, title, subtitles_list, search_string)
                        if ((lang3 != lang2) and (lang3 != lang1)): getallsubs(response_url, content, lang3, title, subtitles_list, search_string)


    return subtitles_list, "", msg #standard output


def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input
    url = subtitles_list[pos][ "link" ]
    language = subtitles_list[pos][ "language_name" ]
    content, response_url = geturl(url)
    match=  re.compile(downloadlink_pattern).findall(content)
    if match:
        downloadlink = "http://subscene.com"  + match[0]
        log( __name__ ,"%s Downloadlink: %s " % (debug_pretext, downloadlink))
        viewstate = 0
        previouspage = 0
        subtitleid = 0
        typeid = "zip"
        filmid = 0
        postparams = urllib.urlencode( { '__EVENTTARGET': 's$lc$bcr$downloadLink', '__EVENTARGUMENT': '' , '__VIEWSTATE': viewstate, '__PREVIOUSPAGE': previouspage, 'subtitleId': subtitleid, 'typeId': typeid, 'filmId': filmid} )
        class MyOpener(urllib.FancyURLopener):
            version = 'User-Agent=Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.2.3) Gecko/20100401 Firefox/3.6.3 ( .NET CLR 3.5.30729)'
        my_urlopener = MyOpener()
        my_urlopener.addheader('Referer', url)
        log( __name__ ,"%s Fetching subtitles using url '%s' with referer header '%s' and post parameters '%s'" % (debug_pretext, downloadlink, url, postparams))
        response = my_urlopener.open(downloadlink, postparams)
        local_tmp_file = os.path.join(tmp_sub_dir, "subscene.xxx")
        try:
            log( __name__ ,"%s Saving subtitles to '%s'" % (debug_pretext, local_tmp_file))
            if not os.path.exists(tmp_sub_dir):
                os.makedirs(tmp_sub_dir)
            local_file_handle = open(local_tmp_file, "w" + "b")
            local_file_handle.write(response.read())
            local_file_handle.close()
            #Check archive type (rar/zip/else) through the file header (rar=Rar!, zip=PK)
            myfile = open(local_tmp_file, "rb")
            myfile.seek(0)
            if (myfile.read(1) == 'R'):
                typeid = "rar"
                packed = True
                log( __name__ , "Discovered RAR Archive")
            else:
                myfile.seek(0)
                if (myfile.read(1) == 'P'):
                    typeid = "zip"
                    packed = True
                    log( __name__ , "Discovered ZIP Archive")
                else:
                    typeid = "srt"
                    packed = False
                    subs_file = local_tmp_file
                    log( __name__ , "Discovered a non-archive file")
            myfile.close()
            local_tmp_file = os.path.join(tmp_sub_dir, "subscene." + typeid)
            os.rename(os.path.join(tmp_sub_dir, "subscene.xxx"), local_tmp_file)
            log( __name__ , "%s Saving to %s" % (debug_pretext,local_tmp_file))
        except:
            log( __name__ ,"%s Failed to save subtitle to %s" % (debug_pretext, local_tmp_file))
        if packed:
            files = os.listdir(tmp_sub_dir)
            init_filecount = len(files)
            max_mtime = 0
            filecount = init_filecount
            # determine the newest file from tmp_sub_dir
            for file in files:
                if (string.split(file,'.')[-1] in ['srt','sub','txt']):
                    mtime = os.stat(os.path.join(tmp_sub_dir, file)).st_mtime
                    if mtime > max_mtime:
                        max_mtime =  mtime
            init_max_mtime = max_mtime
            time.sleep(2)  # wait 2 seconds so that the unpacked files are at least 1 second newer
            xbmc.executebuiltin("XBMC.Extract(" + local_tmp_file + "," + tmp_sub_dir +")")
            waittime  = 0
            while (filecount == init_filecount) and (waittime < 20) and (init_max_mtime == max_mtime): # nothing yet extracted
                time.sleep(1)  # wait 1 second to let the builtin function 'XBMC.extract' unpack
                files = os.listdir(tmp_sub_dir)
                filecount = len(files)
                # determine if there is a newer file created in tmp_sub_dir (marks that the extraction had completed)
                for file in files:
                    if (string.split(file,'.')[-1] in ['srt','sub','txt']):
                        mtime = os.stat(os.path.join(tmp_sub_dir, file)).st_mtime
                        if (mtime > max_mtime):
                            max_mtime =  mtime
                waittime  = waittime + 1
            if waittime == 20:
                log( __name__ ,"%s Failed to unpack subtitles in '%s'" % (debug_pretext, tmp_sub_dir))
            else:
                log( __name__ ,"%s Unpacked files in '%s'" % (debug_pretext, tmp_sub_dir))
                for file in files:
                    # there could be more subtitle files in tmp_sub_dir, so make sure we get the newly created subtitle file
                    if (string.split(file, '.')[-1] in ['srt', 'sub', 'txt']) and (os.stat(os.path.join(tmp_sub_dir, file)).st_mtime > init_max_mtime): # unpacked file is a newly created subtitle file
                        log( __name__ ,"%s Unpacked subtitles file '%s'" % (debug_pretext, file))
                        subs_file = os.path.join(tmp_sub_dir, file)
        log( __name__ ,"%s Subtitles saved to '%s'" % (debug_pretext, local_tmp_file))
        return False, language, subs_file #standard output