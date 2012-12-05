# -*- coding: UTF-8 -*-

# Frankenstein Monster v 2.0
# Feel free to improve, change anything.
# Credits to amet, Guilherme Jardim, and many more.
# Big thanks to gaco for adding logging to site.
# mrto

import urllib2, re, string, xbmc, sys, os
from utilities import log, languageTranslate, hashFile
from BeautifulSoup import BeautifulSoup
from cookielib import CookieJar
from urllib import urlencode

_ = sys.modules[ "__main__" ].__language__
__addon__ = sys.modules[ "__main__" ].__addon__

if __addon__.getSetting( "Napisy24_type" ) == "0":
    subtitle_type = "sr"
elif __addon__.getSetting( "Napisy24_type" ) == "1":
    subtitle_type = "tmp"
elif __addon__.getSetting( "Napisy24_type" ) == "2":
    subtitle_type = "mdvd"
elif __addon__.getSetting( "Napisy24_type" ) == "3":
    subtitle_type = "mpl2"

main_url = "http://napisy24.pl/search.php?str="
base_download_url = "http://napisy24.pl/download/"
down_url = "%s%s/" % (base_download_url, subtitle_type)

def getallsubs(content, title, subtitles_list, file_original_path, stack, lang1, lang2, lang3):
    soup = BeautifulSoup(content)
    subs = soup("tr")
    sub_str = str(subs[1:])
    first_row = True
    for row in subs[1:]:
        sub_number_re = 'a href=\"/download/(\d+)/\"><strong>'
        title_re = '<a href="/download/\d+?/"><strong>(.+?)</strong></a>'
        release_re = '<td>(.+?)<br />|<td.+?>(.+?)<br />'
        rating_re = 'rednia ocena: (\d\,\d\d)<br />'
        lang_re = '<img src="images/ico_flag_(..)_2.png" alt="'
        disc_amount_re = '<td.+?style="text-align: center;">[\r\n\t ]+?(\d)[\r\n\t ]+?</td>'
        video_file_size_re = 'Rozmiar pliku: <strong>(\d+?)</strong>'
        video_file_size_re_multi = 'Rozmiar pliku:<br />- CD1: <strong>(\d+?)</strong>'
        archive_re = '<a href="/download/archiwum/(\d+?)/">'
        row_str = str(row)
        archive = re.findall(archive_re, row_str)
        if len(archive) == 0:
            if first_row == True:
                sub_number = re.findall(sub_number_re, row_str)
                subtitle = re.findall(title_re, row_str)
                release = re.findall(release_re, row_str)
                disc_amount = re.findall(disc_amount_re, row_str)
                first_row = False
            else:
                file_size, SubHash = hashFile(file_original_path, False)
                if disc_amount[0] > '1':
                    video_file_size = re.findall(video_file_size_re_multi, row_str)
                else:
                    video_file_size = re.findall(video_file_size_re, row_str)
                
                if len(video_file_size) == 0:
                    video_file_size.append('0')
                    sync_value = False
                else:
                    video_file_size = unicode(video_file_size[0], "UTF-8")
                    video_file_size = video_file_size.replace(u"\u00A0", "")
                    if file_size == video_file_size:
                        sync_value = True
                    else:
                        sync_value = False

                rating = re.findall(rating_re, row_str)
                language = re.findall(lang_re, row_str)
                
                if len(language) > 0:
                    first_row = True
                    link = "%s%s/" % (down_url, sub_number[0])
                    log( __name__ ,"Subtitles found: %s %s (link=%s)" % (subtitle[0], release, link))

                    flag_pic = "flags/%s.gif" % (language[0])
                    lang = languageTranslate(language[0],2,0)

                    if lang == lang1 or lang == lang2 or lang == lang3:
                        
                        for rel in re.findall("\'(.*?)\'", str(release)):

                            rel = rel.replace(",",":").replace(" ","")

                            if len(rel) > 1:
                                rel_semicolon = "%s;" % (rel)
                                for rel_sync in re.findall('(.+?);', rel_semicolon):
                                    if rel_sync.upper() in file_original_path.upper():
                                        sync_value = True

                        filename_release = "%s - %s" % (subtitle[0], rel_semicolon)

                        rating_dot = rating[0].replace(",",".")
                        if rating_dot == '0.00':
                            sub_rating = '0'
                        else:
                            sub_rating = int(round(float(rating_dot) * 1.666,0))

                        if stack == False:
                            if disc_amount[0] > '1':
                                log( __name__ ,"Nonstacked video file - stacked subs")
                            else:
                                subtitles_list.append({'filename': filename_release, 'sync': sync_value, 'link': link, 'language_flag': flag_pic, 'language_name': lang,'rating': '%s' % (sub_rating)})
                        else:
                            if disc_amount[0] > '1':
                                subtitles_list.append({'filename': filename_release, 'sync': sync_value, 'link': link, 'language_flag': flag_pic, 'language_name': lang,'rating': '%s' % (sub_rating)})
                            else:
                                log( __name__ ,"Stacked video file - nonstacked subs")
                    else:
                        continue
                else:
                    continue

def search_subtitles( file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack ): #standard input
    subtitles_list = []
    msg = ""
    if len(tvshow) > 0:
      for year in re.finditer(' \(\d\d\d\d\)', tvshow):
          year = year.group()
          if len(year) > 0:
              tvshow = tvshow.replace(year, "")
          else:
              continue
      tvshow_plus = tvshow.replace(" ","+")
      if len(season) < 2:
        season_full = '0%s' % (season)
      else:
        season_full = season
      if len(episode) < 2:
        episode_full = '0%s' % (episode)
      else:
        episode_full = episode
      url = '%s%s+%sx%s' % (main_url, tvshow_plus, season_full, episode_full)
    else:
      original_title = xbmc.getInfoLabel("VideoPlayer.OriginalTitle")
      if len(original_title) == 0:
        log( __name__ ,"Original title not set")
        movie_title_plus = title.replace(" ","+")
        url = '%s%s' % (main_url, movie_title_plus)
      else:
        log( __name__ ,"Original title: [%s]" % (original_title))
        movie_title_plus = original_title.replace(" ","+")
        url = '%s%s' % (main_url, movie_title_plus)
    log( __name__ , "Fetching from [ %s ]" % (url))
    response = urllib2.urlopen(url)
    content = response.read()
    re_pages_string = 'postAction%3DszukajZaawansowane">(\d)</a>'
    page_nr = re.findall(re_pages_string, content)
    getallsubs(content, title, subtitles_list, file_original_path, stack, lang1, lang2, lang3)
    for i in page_nr:
        main_url_pages = 'http://napisy24.pl/szukaj/&stronaArch=1&strona='
        rest_url = '%26postAction%3DszukajZaawansowane'
        url_2 = '%s%s&szukajNapis=%s%s' % (main_url_pages, i, title, rest_url)
        response = urllib2.urlopen(url_2)
        content = response.read()    
        getallsubs(content, title, subtitles_list, file_original_path, stack, lang1, lang2, lang3)
    return subtitles_list, "", "" #standard output

def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input
    cj = CookieJar()
    headers = {
          'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
          'Accept-Charset': 'UTF-8,*;q=0.5',
          'Accept-Encoding': 'gzip,deflate,sdch',
          'Accept-Language': 'pl,pl-PL;q=0.8,en-US;q=0.6,en;q=0.4',
          'Connection': 'keep-alive',
          'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.1 (KHTML, like Gecko) Chrome/21.0.1180.83 Safari/537.1',
          'Referer': 'http://napisy24.pl/'
    }
    values = { 'form_logowanieMail' : __addon__.getSetting( "n24user" ), 'form_logowanieHaslo' :  __addon__.getSetting( "n24pass" ), 'postAction' : 'sendLogowanie' }
    data = urlencode(values)
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
    request = urllib2.Request("http://napisy24.pl/logowanie/", data, headers)
    response = opener.open(request)
    request = urllib2.Request(subtitles_list[pos][ "link" ], "", headers)
    f = opener.open(request)
    local_tmp_file = os.path.join(tmp_sub_dir, "zipsubs.zip")
    log( __name__ ,"Saving subtitles to '%s'" % (local_tmp_file))
    
    local_file = open(zip_subs, "w" + "b")
    local_file.write(f.read())
    local_file.close()
    opener.open("http://napisy24.pl/index.php?sendAction=Wyloguj")
    
    language = subtitles_list[pos][ "language_name" ]
    return True, language, "" #standard output
