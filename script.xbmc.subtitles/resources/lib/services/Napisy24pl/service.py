# -*- coding: UTF-8 -*-

# Attention this is a Frankenstein Monster. Patched from other pieces of code,
# ugly and may not work at all. Feel free to improve, change anything.
# I do not know how to code, especially in Python, at all. 
# Credits to amet, Guilherme Jardim, and many more.
# mrto

import urllib2, re, string, xbmc, sys, os
from utilities import log, twotofull

_ = sys.modules[ "__main__" ].__language__

main_url = "http://napisy24.pl/search.php?str="
down_url = "http://napisy.me/download/sr/"

subtitle_pattern = 'a href=\"/download/(\d+)/\"><strong>(.+?)</strong></a>'

def getallsubs(content, title, subtitles_list, file_original_path, stack):
    nr_lista = 0
    wydanie_re = '<td.+?>(.+?)<br />'
    rozmiar_re = 'Rozmiar pliku: <strong>(.+?)</strong>'
    ocena_re = 'rednia ocena: (\d\,\d\d)<br />'
    jezyk_re = '<img src="images/ico_flag_(..)_2.png" alt="'
    ilosc_plyt_re = '<td.+?style="text-align: center;">[\r\n\t ]+?(\d)[\r\n\t ]+?</td>'
    wydanie_lista = re.findall(wydanie_re, content)
    jezyk_lista = re.findall(jezyk_re, content)
    rozmiar_lista = re.findall(rozmiar_re, content)
    ocena_lista = re.findall(ocena_re, content)
    ilosc_plyt_lista = re.findall(ilosc_plyt_re, content)
    for matches in re.finditer(subtitle_pattern, content):
        numer_napisu, tytul = matches.groups()
        wydanie = wydanie_lista[nr_lista]
        ocena = ocena_lista[nr_lista]
        jezyk = jezyk_lista[nr_lista]
        ilosc_plyt = ilosc_plyt_lista[nr_lista]
        nr_lista +=1
        link = "%s%s/" % (down_url, numer_napisu)
        log( __name__ ,"Subtitles found: %s %s (link=%s)" % (tytul, wydanie, link))
        obraz_flagi = "flags/%s.gif" % (jezyk)
        lang = twotofull(jezyk)
        tytul_pelny = '%s %s' % (tytul, wydanie)
        wydanie_sclean = wydanie.replace(" ","")
        wydanie_clean = wydanie_sclean.replace(",",";")
        wydanie_srednik = '%s;' % (wydanie_clean)
        for wydania in re.finditer('(.+?);', wydanie_srednik):
            wydania = wydania.group()
            wydania_clean = wydania.replace(";","")
            wydania_upper = wydania_clean.upper()
            filepatch_upper = file_original_path.upper()
            if wydania_upper in filepatch_upper:
                sync_value = True
            else:
                sync_value = False
        ocena_dot = ocena.replace(",",".")
        if ocena_dot == '0.00':
            sub_rating = '0'
        else:
            sub_rating = int(round(float(ocena_dot) * 1.666,0))
                
        if stack == True:
            if ilosc_plyt == '1':
                log( __name__ ,"Stacked file nonstacked subs")
            else:
                subtitles_list.append({'filename': tytul_pelny, 'sync': sync_value, 'link': link, 'language_flag': obraz_flagi, 'language_name': lang,'rating': '%s' % (sub_rating)})
        else:
            if  ilosc_plyt == '1':
                subtitles_list.append({'filename': tytul_pelny, 'sync': sync_value, 'link': link, 'language_flag': obraz_flagi, 'language_name': lang,'rating':'%s' % (sub_rating)})
            else:
                log( __name__ ,"Nonstacked file stacked subs")

def search_subtitles( file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack ): #standard input
    subtitles_list = []
    msg = ""
    if len(tvshow) > 0:
      for rok in re.finditer(' \(\d\d\d\d\)', tvshow):
          rok = rok.group()
          if len(rok) > 0:
              tvshow = tvshow.replace(rok, "")
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
      log( __name__ ,"Original title: [%s]" % (original_title))
      movie_title_plus = original_title.replace(" ","+")
      url = '%s%s' % (main_url, movie_title_plus)
    log( __name__ , "Pobieram z [ %s ]" % (url))     
    response = urllib2.urlopen(url)
    content = response.read()
    getallsubs(content, title, subtitles_list, file_original_path, stack)
    return subtitles_list, "", "" #standard output

def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input
    import urllib
    f = urllib.urlopen(subtitles_list[pos][ "link" ])
    language = subtitles_list[pos][ "language_name" ]
   
    local_tmp_file = os.path.join(tmp_sub_dir, "zipsubs.zip")
    log( __name__ ,"Saving subtitles to '%s'" % (local_tmp_file))
    
    local_file = open(zip_subs, "w" + "b")
    local_file.write(f.read())
    local_file.close()
   
    return True,language, "" #standard output

