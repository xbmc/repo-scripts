# -*- coding: utf-8 -*-

import os, sys, re, xbmc, xbmcgui, string, time, urllib, urllib2, urlparse
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
			<a href="/S-Darko-AKA-S-Darko-A-Donnie-Darko-Tale/subtitles-76635.aspx" class=popular>
				S. Darko AKA S. Darko: A Donnie Darko Tale (2009)
                                <dfn>(38)</dfn>
"""
movie_season_pattern = "...<a href=\"/([^\n\r\t]*?/subtitles-\d{1,10}.aspx)\".{1,14}>\r\n.{4}([^\n\r\t]*?) \((\d\d\d\d)\) \r\n\s*<dfn>\(([^\)]*)\)</dfn>"
# group(1) = link, group(2) = movie_season_title,  group(3) = year


# <form action="/subtitle/download" id="dl" method="post" name="dl"><button type="submit" onclick="DownloadSubtitle(this)" id="downloadButton" class="Positive">
#downloadlink_pattern = "\(new WebForm_PostBackOptions\([^\n\r\t]+?\/([^\n\r\t]+?)&quot;, false, true\)\)"
downloadlink_pattern = '<form action="([^"]*)" id="dl" method="post" name="dl">'

# <input type="hidden" name="mac" id="mac" value="iYpZfE2uRLwuOANcMW196bXDYN2b4yBreI8TJIBfpdxYfHbaSkp83VDK3BdyW77J0" />
mac_pattern = '<input type="hidden" name="mac" id="mac" value="([^"]*)" />'

# Content-Disposition: attachment; filename=dexter-seventh-season-2012_english-661907.zip
filetype_pattern = 'attachment; filename=.*\.(.*)$'


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
    possible_matches = []
    for matches in re.finditer(movie_season_pattern, content, re.IGNORECASE | re.DOTALL):
        #log( __name__ ,"%s Found tv show season on search page: %s" % (debug_pretext, matches.group(2).decode("utf-8")))
        if string.find(string.lower(matches.group(2)),string.lower(tvshow) + " ") > -1:
            if string.find(string.lower(matches.group(2)),string.lower(season)) > -1:
                log( __name__ ,"%s Matching tv show season found on search page: %s" % (debug_pretext, matches.group(2).decode("utf-8")))
                possible_matches.append(matches.groups())

    possible_matches = sorted(possible_matches, key=lambda x: -int(x[3]))
    url_found = possible_matches[0][0]

    log( __name__ ,"%s Selecting matching tv show with most subtitles: %s (%s)" % (debug_pretext, possible_matches[0][1].decode("utf-8"), possible_matches[0][3].decode("utf-8")))
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

    try:
        match = re.search(downloadlink_pattern, content, re.IGNORECASE | re.DOTALL)
        if not match:
            raise Exception("Unable to find download link")
        response_parsed = urlparse.urlparse(response_url)
        downloadlink = response_parsed.scheme + "://" + response_parsed.netloc + match.group(1)
        log( __name__ ,"%s Downloadlink: %s " % (debug_pretext, downloadlink))

        match = re.search(mac_pattern, content, re.IGNORECASE | re.DOTALL)
        if not match:
            raise Exception("Unable to find download mac")
        mac = match.group(1)
        log( __name__ ,"%s Mac: %s " % (debug_pretext, mac))

        postparams = urllib.urlencode( { 'mac': mac} )
        class MyOpener(urllib.FancyURLopener):
            version = 'User-Agent=Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.2.3) Gecko/20100401 Firefox/3.6.3 ( .NET CLR 3.5.30729)'
        my_urlopener = MyOpener()
        my_urlopener.addheader('Referer', url)
        log( __name__ ,"%s Fetching subtitles using url '%s' with referer header '%s' and post parameters '%s'" % (debug_pretext, downloadlink, url, postparams))
        response = my_urlopener.open(downloadlink, postparams)

        print response.headers["Content-Disposition"]
        match = re.search(filetype_pattern, response.headers["Content-Disposition"], re.IGNORECASE | re.DOTALL)
        if not match:
            raise Exception("Unable to find file type")
        typeid = match.group(1)

        local_tmp_file = os.path.join(tmp_sub_dir, "subscene." + typeid)
        if (typeid != "zip") and (typeid != "rar"):
            subs_file = local_tmp_file
            packed = False
        else:
            packed = True
        try:
            log( __name__ ,"%s Saving subtitles to '%s'" % (debug_pretext, local_tmp_file))
            local_file_handle = open(local_tmp_file, "w" + "b")
            local_file_handle.write(response.read())
            local_file_handle.close()
        except:
            log( __name__ ,"%s Failed to save subtitles to '%s'" % (debug_pretext, local_tmp_file))
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

    except Exception as ex:
        log( __name__ ,"%s %s" % (debug_pretext, ex.message))
        
