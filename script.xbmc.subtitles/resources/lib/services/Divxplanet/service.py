import mechanize
import cookielib
import re
import os, sys, re, xbmc, xbmcgui, string, time, urllib, urllib2
import difflib
from utilities import languageTranslate, log
from BeautifulSoup import BeautifulSoup

main_url = "http://koray.al/"
debug_pretext = "Divxplanet:"

def getmediaUrl(mediaArgs):
    query = "site:divxplanet.com inurl:sub/m \"%s ekibi\" intitle:\"%s\" intitle:\"(%s)\"" % (mediaArgs[0], mediaArgs[1], mediaArgs[2])
    br = mechanize.Browser()
    log( __name__ ,"Finding media %s" % query)
    # Cookie Jar
    cj = cookielib.LWPCookieJar()
    br.set_cookiejar(cj)

    # Browser options
    br.set_handle_equiv(True)
    # br.set_handle_gzip(True)
    br.set_handle_redirect(True)
    br.set_handle_referer(True)
    br.set_handle_robots(False)

    # Follows refresh 0 but not hangs on refresh > 0
    br.set_handle_refresh(mechanize._http.HTTPRefreshProcessor(), max_time=1)

    # User-Agent (this is cheating, ok?)
    br.addheaders = [('User-agent', 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.1) Gecko/2008071615 Fedora/3.0.1-1.fc9 Firefox/3.0.1')]

    br.open("http://www.google.com")
    # Select the search box and search for 'foo'
    br.select_form( 'f' )
    br.form[ 'q' ] = query
    br.submit()
    page = br.response().read()
    soup = BeautifulSoup(page)

    linkdictionary = []
    query.replace(" ", "-")
    for li in soup.findAll('li', attrs={'class':'g'}):
        sLink = li.find('a')
        sSpan = li.find('span', attrs={'class':'st'})
        if sLink:
            linkurl = re.search(r"\/url\?q=(http:\/\/divxplanet.com\/sub\/m\/[0-9]{3,8}\/.*.\.html).*", sLink["href"])
            if linkurl:
                linkdictionary.append({"text": sSpan.getText().encode('ascii', 'ignore'), "name": mediaArgs[0], "url": linkurl.group(1)})
    log( __name__ ,"found media: %s" % (linkdictionary[0]["url"]))
    return linkdictionary[0]["url"]

def search_subtitles(file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack ): #standard input
    # Build an adequate string according to media type
    if len(tvshow) != 0:
        log( __name__ ,"searching subtitles for %s %s %s %s" % (tvshow, year, season, episode))
        tvurl = getmediaUrl(["dizi",tvshow, year])
        log( __name__ ,"got media url %s" % (tvurl))
        divpname = re.search(r"http:\/\/divxplanet.com\/sub\/m\/[0-9]{3,8}\/(.*.)\.html", tvurl).group(1)
        season = int(season)
        episode = int(episode)
        # Browser
        br = mechanize.Browser()

        # Cookie Jar
        cj = cookielib.LWPCookieJar()
        br.set_cookiejar(cj)

        # Browser options
        br.set_handle_equiv(True)
        # br.set_handle_gzip(True)
        br.set_handle_redirect(True)
        br.set_handle_referer(True)
        br.set_handle_robots(False)

        # Follows refresh 0 but not hangs on refresh > 0
        br.set_handle_refresh(mechanize._http.HTTPRefreshProcessor(), max_time=1)

        # User-Agent (this is cheating, ok?)
        br.addheaders = [('User-agent', 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.1) Gecko/2008071615 Fedora/3.0.1-1.fc9 Firefox/3.0.1')]

        url = br.open(tvurl)
        html = url.read()
        soup = BeautifulSoup(html)
        subtitles_list = []
        i = 0
        # /sub/s/281212/Hannibal.html
        for link in soup.findAll('a', href=re.compile("\/sub\/s\/.*.\/%s.html" % divpname)):
            addr = link.get('href')
            info = link.parent.parent.nextSibling.nextSibling.findAll("td", colspan="3")
            if info:
                tse = info[0].div.findAll("b", text="%d" % season)
                tep = info[0].div.findAll("b", text="%02d" % episode)
                lantext = link.parent.find("br")
                lan = link.parent.parent.findAll("img", title=re.compile("^.*. (subtitle|altyazi)"))
                if tse and tep and lan and lantext:
                    language = lan[0]["title"]
                    if language[0] == "e":
                        language = "English"
                        lan_short = "en"
                    else:
                        language = "Turkish"
                        lan_short = "tr"
                    subtitles_list.append({'link'    : addr,
                                     'movie'         : tvshow,
                                     'filename'      : "%s" % (info[1].getText()),
                                     'description'   : "%s S%02dE%02d %s.%s" % (tvshow, season, episode, title, lan_short),
                                     'language_flag' : "flags/%s.gif" % lan_short,
                                     'language_name' : language,
                                     'sync'          : False,
                                     'rating'        : "0" })
        br.close()
        log( __name__ ,"found %d subtitles" % (len(subtitles_list)))
    else:
        log( __name__ ,"searching subtitles for %s %s" % (title, year))
        tvurl = getmediaUrl(["film", title, year])
        log( __name__ ,"got media url %s" % (tvurl))
        divpname = re.search(r"http:\/\/divxplanet.com\/sub\/m\/[0-9]{3,8}\/(.*.)\.html", tvurl).group(1)
        # Browser
        br = mechanize.Browser()

        # Cookie Jar
        cj = cookielib.LWPCookieJar()
        br.set_cookiejar(cj)

        # Browser options
        br.set_handle_equiv(True)
        # br.set_handle_gzip(True)
        br.set_handle_redirect(True)
        br.set_handle_referer(True)
        br.set_handle_robots(False)

        # Follows refresh 0 but not hangs on refresh > 0
        br.set_handle_refresh(mechanize._http.HTTPRefreshProcessor(), max_time=1)

        # User-Agent (this is cheating, ok?)
        br.addheaders = [('User-agent', 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.1) Gecko/2008071615 Fedora/3.0.1-1.fc9 Firefox/3.0.1')]

        url = br.open(tvurl)
        html = url.read()
        soup = BeautifulSoup(html)
        subtitles_list = []
        i = 0
        # /sub/s/281212/Hannibal.html
        for link in soup.findAll('a', href=re.compile("\/sub\/s\/.*.\/%s.html" % divpname)):
            addr = link.get('href')
            info = link.parent.parent.nextSibling.nextSibling.findAll("td", colspan="3")
            log( __name__ ,"found a link")
            if info:
                log( __name__ ,"found info: %s" % info)
                lantext = link.parent.find("br")
                lan = link.parent.parent.findAll("img", title=re.compile("^.*. (subtitle|altyazi)"))
                log( __name__ ,"lan : %s lantext : %s" % (lan[0]["title"], lantext))
                if lan and lantext:
                    language = lan[0]["title"]
                    if language[0] == "e":
                        language = "English"
                        lan_short = "en"
                    else:
                        language = "Turkish"
                        lan_short = "tr"
                    filename = "no-description"
                    if info[0].getText() != "":
                        filename = info[0].getText()
                    log( __name__ ,"found a subtitle with description: %s" % (filename))
                    subtitles_list.append({'link'    : addr,
                                     'movie'         : title,
                                     'filename'      : "%s" % (filename),
                                     'description'   : "%s.%s" % (title, lan_short),
                                     'language_flag' : "flags/%s.gif" % lan_short,
                                     'language_name' : language,
                                     'sync'          : False,
                                     'rating'        : "0" })
                    log( __name__ ,"added subtitle to list")
        br.close()
        log( __name__ ,"found %d subtitles" % (len(subtitles_list)))
    return subtitles_list, "", ""


def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input
    packed = True
    dlurl = "http://divxplanet.com%s" % subtitles_list[pos][ "link" ]
    language = subtitles_list[pos]["language_name"]
    # Browser
    br = mechanize.Browser()

    # Cookie Jar
    cj = cookielib.LWPCookieJar()
    br.set_cookiejar(cj)

    # Browser options
    br.set_handle_equiv(True)
    # br.set_handle_gzip(True)
    br.set_handle_redirect(True)
    br.set_handle_referer(True)
    br.set_handle_robots(False)

    # Follows refresh 0 but not hangs on refresh > 0
    br.set_handle_refresh(mechanize._http.HTTPRefreshProcessor(), max_time=1)

    # User-Agent (this is cheating, ok?)
    br.addheaders = [('User-agent', 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.1) Gecko/2008071615 Fedora/3.0.1-1.fc9 Firefox/3.0.1')]

    html = br.open(dlurl).read()
    br.select_form(name="dlform")
    br.submit()

    log( __name__ ,"Fetching subtitles using url '%s" % (dlurl))
    local_tmp_file = os.path.join(tmp_sub_dir, subtitles_list[pos]["description"] + ".rar")
    try:
        log( __name__ ,"Saving subtitles to '%s'" % (local_tmp_file))
        if not os.path.exists(tmp_sub_dir):
            os.makedirs(tmp_sub_dir)
        local_file_handle = open(local_tmp_file, "wb")
        local_file_handle.write(br.response().get_data())
        local_file_handle.close()
    except:
        log( __name__ ,"%s Failed to save subtitle to %s" % (debug_pretext, local_tmp_file))
    if packed:
        files = os.listdir(tmp_sub_dir)
        init_filecount = len(files)
        max_mtime = 0
        filecount = init_filecount
        # determine the newest file from tmp_sub_dir
        for file in files:
            if (string.split(file,'.')[-1] in ['srt','sub']):
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
                if (string.split(file,'.')[-1] in ['srt','sub']):
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
                if (string.split(file, '.')[-1] in ['srt', 'sub']) and (os.stat(os.path.join(tmp_sub_dir, file)).st_mtime > init_max_mtime): # unpacked file is a newly created subtitle file
                    log( __name__ ,"%s Unpacked subtitles file '%s'" % (debug_pretext, file))
                    subs_file = os.path.join(tmp_sub_dir, file)
    log( __name__ ,"%s Subtitles saved to '%s'" % (debug_pretext, local_tmp_file))
    br.close()
    return False, language, subs_file #standard output
