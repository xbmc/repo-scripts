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
from BeautifulSoup import BeautifulSoup
import sys
reload(sys)  # Reload does the trick!
sys.setdefaultencoding('UTF8')

__addon__ = xbmcaddon.Addon()
__author__ = __addon__.getAddonInfo('author')
__scriptid__ = __addon__.getAddonInfo('id')
__scriptname__ = __addon__.getAddonInfo('name')
__version__ = __addon__.getAddonInfo('version')
__language__ = __addon__.getLocalizedString

__cwd__ = xbmc.translatePath(__addon__.getAddonInfo('path'))
__profile__ = xbmc.translatePath(__addon__.getAddonInfo('profile'))
__resource__ = xbmc.translatePath(os.path.join(__cwd__, 'resources', 'lib'))
__temp__ = xbmc.translatePath(os.path.join(__profile__, 'temp'))

sys.path.append(__resource__)

if os.path.exists(__temp__):
    shutil.rmtree(__temp__)
os.makedirs(__temp__)

s = requests.Session()


def normalize_filename(s):
    valid_chars = '-_.() abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    return ''.join([c for c in s if c in valid_chars])


def load_url(path):
    # there is no need to be overenthusiastic
    sleep(randint(5, 25) / 10.0)
    uri = 'http://www.altyazi.org' + path.replace(' ', '+')
    log('Getting uri: %s' % uri)
    req = s.get(uri)
    req.encoding = 'ISO-8859-9'
    res = req.text.encode('ISO-8859-9')
    page = BeautifulSoup(res)
    # local_tmp_file = os.path.join(__temp__, 'test.html')
    # with open(local_tmp_file, 'w') as outfile:
    #     outfile.write(res)
    log('Got uri [%s]: %s' % (req.status_code, req.url))
    return page


def get_media_url(media_args):
    log('getting media url')
    querytype = media_args[0]
    title = re.sub(" \(?(.*.)\)", "", media_args[1])
    year = media_args[2]
    if year == "":
        yr = re.search(r"\((\d{4})\)", media_args[1])
        if yr is not None:
            year = yr.group(1)

    year_suffix = "" if querytype == "dizi" else " (%s)" % year

    page = load_url('/index.php?page=arama&arama=%s' % title + year_suffix)

    redirect_url = [sc.getText() for sc in page.findAll('script') if 'location.href' in sc.getText()]
    if len(redirect_url) > 0:
        a = redirect_url[0]
        episode_uri = a[a.find('"')+1:a.rfind('"')]
        log('Found uri via redirect')
        return episode_uri

    for result in page.findAll('td', attrs={'width': '60%'}):
        link = result.find('a')
        link_title = link.find('b').getText().strip()
        if querytype == "film":
            if str(year) == "" or str(year) in result.getText():
                return link["href"]
        elif querytype == "dizi" and link_title.startswith('"'):
            if str(year) == "" or str(year) in result.getText():
                return link["href"]
    raise ValueError('No valid results')


def search(mitem):
    tvshow = mitem["tvshow"]
    year = mitem["year"]
    season = mitem["season"]
    episode = mitem["episode"]
    title = mitem["title"]

    # Build an adequate string according to media type
    if len(tvshow) != 0:
        log("[SEARCH TVSHOW] Divxplanet: searching subtitles for %s %s %s %s" % (tvshow, year, season, episode))
        tvurl = get_media_url(["dizi", tvshow, year])
        log("Divxplanet: got media url %s" % tvurl)
        if tvurl != "":
            divpname = re.search(r"/sub/m/[0-9]{3,8}/(.*.)\.html", tvurl).group(1)
            log('TV ID: %s' % divpname)
            season = int(season)
            episode = int(episode)
            page = load_url(tvurl)

            subtitles_list = []
            i = 0
            # /sub/s/281212/Hannibal.html
            tables = page.findAll('table', attrs={'align': 'center'})
            tb = [t for t in tables if 'FPS' in t.getText()][0]
            for link in tb.findAll('a', href=re.compile("/sub/s/.*./%s.html" % divpname)):
                addr = link['href']
                info = link.parent.parent.nextSibling.nextSibling.findAll("td", colspan="3")
                if not info:
                    continue

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
                    filename = u"%s S%02dE%02d %s.%s" % (tvshow, season, episode, title, lan_short)
                    description = info[1].getText()
                    log('description and filename:')
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

                    url = "plugin://%s/?action=download&link=%s&lang=%s&description=%s" % (
                        __scriptid__,
                        addr,
                        lan_short,
                        normalize_filename(filename)
                    )

                    xbmcplugin.addDirectoryItem(
                            handle=int(sys.argv[1]),
                            url=url,
                            listitem=l_item,
                            isFolder=False
                    )
            log("Divxplanet: found %d subtitles" % (len(subtitles_list)))
    else:
        log("[SEARCH !TVSHOW] Divxplanet: searching subtitles for %s %s" % (title, year))

        tvurl = get_media_url(["film", title, year])
        if tvurl == '':
            tvurl = get_media_url(["film", title, int(year) + 1])
            log("Divxplanet: searching subtitles for %s %s" % (title, int(year) + 1))

        log("222Divxplanet: got media url %s" % tvurl)
        divpname = re.search(r"/sub/m/[0-9]{3,8}/(.*.)\.html", tvurl).group(1)

        page = load_url(tvurl)
        subtitles_list = []
        i = 0
        # /sub/s/281212/Hannibal.html
        tables = page.findAll('table', attrs={'align': 'center'})
        tb = [t for t in tables if 'FPS' in t.getText()][0]
        for link in tb.findAll('a', href=re.compile("/sub/s/.*./%s.html" % divpname)):
            addr = link.get('href')
            info = link.parent.parent.nextSibling.nextSibling.findAll("td", colspan="3")
            if info:
                lantext = link.parent.find("br")
                lan = link.parent.parent.findAll("img", title=re.compile("^.*. (subtitle|altyazi)"))
                if lan and lantext:
                    language = lan[0]["title"]
                    if language[0] == "e":
                        language = "English"
                        lan_short = "en"
                    else:
                        language = "Turkish"
                        lan_short = "tr"
                    description = "no-description"
                    if info[0].getText() != "":
                        description = info[0].getText()
                    filename = "%s.%s" % (title, lan_short)

                    log('description and filename:')
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

                    url = "plugin://%s/?action=download&link=%s&lang=%s&description=%s" % (
                        __scriptid__,
                        addr,
                        lan_short,
                        normalize_filename(filename)
                    )

                    xbmcplugin.addDirectoryItem(
                            handle=int(sys.argv[1]),
                            url=url,
                            listitem=l_item,
                            isFolder=False
                    )
        log("[SEARCH END]Divxplanet: found %d subtitles" % (len(subtitles_list)))


def download(link):
    dpid = re.search('sub/s/(\d+)/', link).group(1)
    extract_path = __temp__ + '/' + dpid

    subtitle_list = []

    page = load_url(link)

    # find the dl button and set keys for the file request
    form = page.find('form', id='dlform')
    indir_keys = form.findAll('input', attrs={'type': 'hidden'})

    form_data = {}
    for k in indir_keys:
        form_data[k['name']] = k['value']
    form_data['x'] = randint(1,19)
    form_data['y'] = randint(1,19)

    f = s.post('http://altyazi.org/indir.php', data=form_data, stream=True)
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
        raise ValueError("Couldn't Get The File")

    xbmc.executebuiltin("XBMC.Extract(" + local_tmp_file + "," + extract_path + ")", True)
    files = os.listdir(extract_path)

    for f in files:
        if string.split(f, '.')[-1] in ['srt', 'sub']:
            subs_file = os.path.join(extract_path, f)
            subtitle_list.append(subs_file)
            log("Divxplanet: Subtitles saved to '%s'" % local_tmp_file)
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
    subs = download(params["link"])
    for sub in subs:
        listitem = xbmcgui.ListItem(label=sub)
        xbmcplugin.addDirectoryItem(
                handle=int(sys.argv[1]),
                url=sub,
                listitem=listitem,
                isFolder=False
        )

xbmcplugin.endOfDirectory(int(sys.argv[1]))
s.close()
