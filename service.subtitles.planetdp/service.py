# -*- coding: utf-8 -*-
# encoding=utf8

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
from xbmc import log

import os
import re
import shutil
import string
import urllib
import requests
from random import randint
from time import sleep
from bs4 import BeautifulSoup
import sys
reload(sys)  # Reload does the trick!
sys.setdefaultencoding('UTF8')

__addon__ = xbmcaddon.Addon()
__author__ = __addon__.getAddonInfo('author')
__scriptid__ = __addon__.getAddonInfo('id')
__scriptname__ = __addon__.getAddonInfo('name')
__version__ = __addon__.getAddonInfo('version')
__language__ = __addon__.getLocalizedString

__cwd__ = xbmc.translatePath(__addon__.getAddonInfo('path')).decode('utf8')
__profile__ = xbmc.translatePath(__addon__.getAddonInfo('profile')).decode('utf8')
__resource__ = xbmc.translatePath(os.path.join(__cwd__, 'resources', 'lib')).decode('utf8')
__temp__ = xbmc.translatePath(os.path.join(__profile__, 'temp', '')).decode('utf8')

sys.path.append(__resource__)

if os.path.exists(__temp__):
    shutil.rmtree(__temp__)
os.makedirs(__temp__)

s = requests.Session()
s.verify = False


def normalize_filename(s):
    valid_chars = '-_.() abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    return ''.join([c for c in s if c in valid_chars])


def load_url(uri):
    # there is no need to be overenthusiastic
    sleep(randint(5, 25) / 10.0)
    log('Getting uri: %s' % uri)
    req = s.get(uri)
    req.encoding = 'utf-8'
    res = req.text.encode('utf-8')
    page = BeautifulSoup(res, 'html5lib')
    log('Got uri [%s]: %s' % (req.status_code, req.url))
    return req, page


def get_media_url(media_args):
    log('getting media url')
    querytype = media_args[0]
    title = re.sub(" \(?(.*.)\)", "", media_args[1])
    year = media_args[2]
    if year == "":
        yr = re.search(r"\((\d{4})\)", media_args[1])
        if yr is not None:
            year = yr.group(1)

    q_dict = {'title': title}
    if year != "" and querytype != "dizi":
        q_dict.update({'year_date': year})

    is_serial = querytype == "dizi"

    if is_serial:
        q_dict.update({'is_serial': "1", 'title': media_args[3]})
        display = display_tvshow
    else:
        q_dict.update({'is_serial': "0"})
        display = display_movie

    (req, page) = load_url('https://www.planetdp.org/movie/search?' + urllib.urlencode(q_dict))
    req_url = req.url

    if "/title/" in req_url:
        if is_serial:
            display(media_args[3], title, media_args[4], media_args[5], req_url)
        else:
            display(title, req_url)
    else:
        select_list = []
        media_urls = []
        for result in page.findAll('div', class_="movie"):
            media_tag = result.find('a', class_='movie__title')
            media_url = "https://www.planetdp.org" + media_tag['href']
            media_name = media_tag.text
            select_list.append(media_name)
            media_urls.append(media_url)
        selected = xbmcgui.Dialog().select("Please Select The Correct Title", select_list, preselect=0)
        log("Selected: %s" % selected)
        if is_serial:
            display(media_args[3], title, media_args[4], media_args[5], media_urls[selected])
        else:
            display(title, media_urls[selected])


def display_tvshow(tvshow, title, season, episode, tvurl):
    divpname = re.search(r"/title/(.*.)", tvurl).group(1)
    log('TV ID: %s' % divpname)
    season = int(season)
    episode = int(episode)
    (req, page) = load_url(tvurl)
    subtitles_list = []

    tb = page.find(id='subtable')
    links = tb.findAll('a', class_='download-btn')
    for link in links:
        addr = link['href']
        s_tr = link.find_parent('tr')
        tr_id = re.sub('row_id', '', s_tr['id'])
        s_tr2 = page.find('tr', id="row_id_alt%s" % tr_id)
        s_tr3 = page.find('tr', id="row_id_note%s" % tr_id)
        tse = ("S:%d-B:%02d" % (season, episode)) in s_tr2.find('span').text
        tsp = ("S:%d-B:Paket" % season) in s_tr2.find('span').text
        lantext = s_tr.find('img')['src']
        if (tse or tsp) and lantext:
            if "en.png" in lantext:
                language = "English"
                lan_short = "en"
            elif "tr.png" in lantext:
                language = "Turkish"
                lan_short = "tr"
            else:
                raise ValueError("unsupported language: %s" % lantext)
            filename = u"%s S%02dE%02d %s.%s" % (tvshow, season, episode, title, lan_short)
            dtd = s_tr3.find('td').text
            description = dtd[dtd.index(' :') + 2:dtd.index(' - ')]
            log('description and filename:'),
            log(description)
            log(filename)
            l_item = xbmcgui.ListItem(
                label=language,  # language name for the found subtitle
                label2=description,  # file name for the found subtitle
                iconImage="0",  # rating for the subtitle, string 0-5
                thumbnailImage=xbmc.convertLanguage(language, xbmc.ISO_639_1)
            )

            # set to "true" if subtitle is for hearing impared
            l_item.setProperty("hearing_imp", '{0}'.format("false").lower())

            subtitles_list.append(l_item)

            url = "plugin://%s/?action=download&link=%s&lang=%s&description=%s&season=%s" % (
                __scriptid__,
                addr,
                lan_short,
                normalize_filename(filename),
                "S%02dE%02d" % (season, episode)
            )

            xbmcplugin.addDirectoryItem(
                handle=int(sys.argv[1]),
                url=url,
                listitem=l_item,
                isFolder=False
            )
    log("PlanetDP: found %d subtitles from %s" % (len(subtitles_list), len(links)))


def display_movie(title, movieurl):
    divpname = re.search(r"/title/(.*.)", movieurl).group(1)
    log('MOVIE ID: %s' % divpname)
    (req, page) = load_url(movieurl)
    subtitles_list = []

    tb = page.find(id='subtable')
    links = tb.findAll('a', class_='download-btn')
    for link in links:
        addr = link['href']
        s_tr = link.find_parent('tr')
        tr_id = re.sub('row_id', '', s_tr['id'])
        s_tr2 = page.find('tr', id="row_id_alt%s" % tr_id)
        s_tr3 = page.find('tr', id="row_id_note%s" % tr_id)
        lantext = s_tr.find('img')['src']
        if lantext:
            if "en.png" in lantext:
                language = "English"
                lan_short = "en"
            elif "tr.png" in lantext:
                language = "Turkish"
                lan_short = "tr"
            else:
                raise ValueError("unsupported language: %s" % lantext)
            filename = u"%s.%s" % (title, lan_short)
            dtd = s_tr3.find('td').text
            description = dtd[dtd.index(' :') + 2:dtd.index(' - ')]
            log('description and filename:'),
            log(description)
            log(filename)
            l_item = xbmcgui.ListItem(
                label=language,  # language name for the found subtitle
                label2=description,  # file name for the found subtitle
                iconImage="0",  # rating for the subtitle, string 0-5
                thumbnailImage=xbmc.convertLanguage(language, xbmc.ISO_639_1)
            )

            # set to "true" if subtitle is for hearing impared
            l_item.setProperty("hearing_imp", '{0}'.format("false").lower())

            subtitles_list.append(l_item)

            url = "plugin://%s/?action=download&link=%s&lang=%s&description=%s&season=%s" % (
                __scriptid__,
                addr,
                lan_short,
                normalize_filename(filename),
                ""
            )

            xbmcplugin.addDirectoryItem(
                handle=int(sys.argv[1]),
                url=url,
                listitem=l_item,
                isFolder=False
            )
    log("PlanetDP: found %d subtitles from %s" % (len(subtitles_list), len(links)))


def search(mitem):
    tvshow = mitem["tvshow"]
    year = mitem["year"]
    season = mitem["season"]
    episode = mitem["episode"]
    title = mitem["title"]

    # Build an adequate string according to media type
    if len(tvshow) != 0:
        log("[SEARCH TVSHOW] PlanetDP: searching subtitles for %s %s %s %s" % (tvshow, year, season, episode))
        get_media_url(["dizi", title, year, tvshow, season, episode])
    else:
        log("[SEARCH MOVIE] PlanetDP: searching subtitles for %s %s" % (title, year))
        get_media_url(["film", title, year])


def download(link):
    dpid = link[link.index('-sub')+4:]
    extract_path = __temp__ + '/' + dpid

    subtitle_list = {}

    (req, page) = load_url('https://www.planetdp.org' + link)

    # find the dl button and set keys for the file request
    form = page.find('form', id='dlform')
    token = form.find('input', attrs={'type': 'hidden', 'name': '_token'})['value']

    uk_tag = page.find('a', attrs={'rel-tag': True})

    form_data = {
        '_token': token,
        '_method': 'POST',
        'subtitle_id': uk_tag['rel-id'],
        'uniquekey': uk_tag['rel-tag']
    }

    f = s.post('https://www.planetdp.org/subtitle/download', data=form_data, stream=True)
    if f.status_code == 200:
        if 'Content-Disposition' in f.headers:
            # use the provided file name if possible
            local_name = f.headers['Content-Disposition'].split('filename=')[1].strip('"\'')
        else:
            # use a generic name
            local_name = 'test.zip'
        local_tmp_file = os.path.join(__temp__, local_name)
        with open(local_tmp_file, 'wb') as outfile:
            for chunk in f.iter_content(1024):
                outfile.write(chunk)
    else:
        log("[%d] %s" % (f.status_code, f.text))
        raise ValueError("Couldn't Get The File")

    xbmc.executebuiltin("XBMC.Extract(" + local_tmp_file + "," + extract_path + ")", True)
    files = os.listdir(extract_path)

    for f in files:
        if string.split(f, '.')[-1] in ['srt', 'sub']:
            subs_file = os.path.join(extract_path, f)
            subtitle_list.update({f: subs_file})
            log("PlanetDP: Subtitles saved to '%s'" % local_tmp_file)
    return subtitle_list


def get_params():
    param = []
    paramstring = sys.argv[2]

    if len(paramstring) >= 2:
        mparam = paramstring
        cleanedparams = mparam.replace('?', '')

        if mparam[len(mparam) - 1] == '/':
            mparam = mparam[0:len(mparam) - 2]

        pairsofparams = cleanedparams.split('&')
        param = {}
        for i in range(len(pairsofparams)):
            splitparams = {}
            splitparams = pairsofparams[i].split('=')
            if len(splitparams) == 2:
                param[splitparams[0]] = splitparams[1]

    return param

params = get_params()

if params['action'] == 'search':
    item = {
        'temp': False,
        'rar': False,
        'year': xbmc.getInfoLabel("VideoPlayer.Year"),
        'season': str(xbmc.getInfoLabel("VideoPlayer.Season")),
        'episode': str(xbmc.getInfoLabel("VideoPlayer.Episode")),
        'tvshow': xbmc.getInfoLabel("VideoPlayer.TVshowtitle"),
        'title': xbmc.getInfoLabel("VideoPlayer.OriginalTitle"),
        'file_original_path': urllib.unquote(xbmc.Player().getPlayingFile().decode('utf-8')), '3let_language': []
    }

    for lang in urllib.unquote(params['languages']).decode('utf-8').split(","):
        item['3let_language'].append(xbmc.convertLanguage(lang, xbmc.ISO_639_2))

    if item['title'] == "":
        item['title'] = xbmc.getInfoLabel("VideoPlayer.Title")

    if item['episode'].lower().find("s") > -1:  # Check if season is "Special"
        item['season'] = "0"
        item['episode'] = item['episode'][-1:]

    if item['file_original_path'].find("http") > -1:
        item['temp'] = True
    elif item['file_original_path'].find("rar://") > -1:
        item['rar'] = True
        item['file_original_path'] = os.path.dirname(item['file_original_path'][6:])
    elif item['file_original_path'].find("stack://") > -1:
        stackPath = item['file_original_path'].split(" , ")
        item['file_original_path'] = stackPath[0][8:]
    search(item)
elif params['action'] == 'download':
    log("Downloading: %s" % params['link'])
    subs = download(params["link"])
    subs_keys = sorted(subs.keys())
    if len(subs) > 1:
        preselect_ids = []
        if params['season'] != "":
            preselect_ids = [i for (i, k) in enumerate(subs_keys) if params['season'] in k]

        pselect = preselect_ids[0] if len(preselect_ids) > 0 else -1

        selected = xbmcgui.Dialog().select("Select Subtitle (%s) " % params['description'], subs_keys, preselect=pselect)
        selected_key = subs_keys[selected]
    else:
        selected_key = subs_keys[0]
    listitem = xbmcgui.ListItem(label=selected_key)
    xbmcplugin.addDirectoryItem(
            handle=int(sys.argv[1]),
            url=subs[selected_key],
            listitem=listitem,
            isFolder=False
    )

xbmcplugin.endOfDirectory(int(sys.argv[1]))
s.close()
