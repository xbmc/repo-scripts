# -*- coding: utf-8 -*-
# SubClub.eu subtiitrite hankimiseks
# Adaptsioon subdivx teenusest
# Igasugused küsimused ja uuendused GitHubist

from __future__ import print_function
import os
from os.path import join as pjoin
import re
import shutil
import sys
import time
import unicodedata
import urllib
reload(sys)
sys.setdefaultencoding("utf8")

try:
    import xbmc
except ImportError:
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        import unittest  # NOQA
        try:
            import mock  # NOQA
        except ImportError:
            print("You need to install the mock Python library to run "
                  "unit tests.\n")
            sys.exit(1)
else:
    import xbmcaddon
    import xbmcgui
    import xbmcplugin
    import xbmcvfs

__addon__ = xbmcaddon.Addon()
__author__     = __addon__.getAddonInfo('author')
__scriptid__   = __addon__.getAddonInfo('id')
__scriptname__ = __addon__.getAddonInfo('name')
__version__    = __addon__.getAddonInfo('version')
__language__   = __addon__.getLocalizedString

__cwd__        = xbmc.translatePath(__addon__.getAddonInfo('path')).decode("utf-8")
__profile__    = xbmc.translatePath(__addon__.getAddonInfo('profile')).decode("utf-8")
__resource__   = xbmc.translatePath(pjoin(__cwd__, 'resources', 'lib')).decode("utf-8")
__temp__       = xbmc.translatePath(pjoin(__profile__, 'temp')).decode("utf-8")

sys.path.append(__resource__)

MAIN_URL = "http://www.subclub.eu/"
SEARCH_PAGE_URL = MAIN_URL + "jutud.php?tp=nimi&otsing=%(query)s"
CONTENT_URL = MAIN_URL + "subtitles_archivecontent.php?id=%(query)s"

INTERNAL_LINK_URL = "plugin://%(scriptid)s/?action=download&id=%(id)s&filename=%(filename)s"
SUB_EXTS = ['srt', 'aas', 'ssa', 'sub', 'smi', 'txt']
HTTP_USER_AGENT = "User-Agent=Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.2.3) Gecko/20100401 Firefox/3.6.3 ( .NET CLR 3.5.30729)"


def is_subs_file(fn):
    """Kontrollime, kas failil on laiend, mida tunneme subtiitrina."""
    ext = fn.split('.')[-1]
    return ext.upper() in [e.upper() for e in SUB_EXTS]

SUBTITLE_RE = re.compile(r'''<a\s+class="sc_link"\s+
                         href="../down.php\?id=(?P<id>.+?)".+?">(?P<pealkiri>.*?)</a>
                         .+?<span\s+id="komment_(?P<kommid>.+?)"\s+class="komment">(?P<comment>.*?)</span>
						 .+?<span\s+title="Hindajaid:\s+(?P<hindajaid>.+?)">(?P<hinne>.+?)</span>''',
                         re.IGNORECASE | re.DOTALL | re.VERBOSE | re.UNICODE |
                         re.MULTILINE)
# 'id': SubClubi faili ID
# 'comment': Kommentaarid jutustuse all
# 'hinne': SubClubis antud subtiitri hinne
# 'pealkiri': Filmi nimetus

# Hangime .rar faili sisu
SISU_RE = re.compile(r'''<a\s+href=.+?">(?P<supakas>.*?)</a>''', re.IGNORECASE | re.DOTALL | re.VERBOSE |
						re.UNICODE | re.MULTILINE)

DOWNLOAD_LINK_RE = re.compile(r'down.php\?id=(.*?)"', re.IGNORECASE |
                              re.DOTALL | re.MULTILINE | re.UNICODE)

# ==========
# Funktsioonid
# ==========


def _log(module, msg):
    s = u"### [%s] - %s" % (module, msg)
    xbmc.log(s.encode('utf-8'), level=xbmc.LOGDEBUG)


def log(msg):
    _log(__name__, msg)


def geturl(url):
    class MyOpener(urllib.FancyURLopener):
        # version = HTTP_USER_AGENT
        version = ''
    my_urlopener = MyOpener()
    log(u"URLi hankimine: %s" % (url,))
    try:
        response = my_urlopener.open(url)
        content = response.read()
    except Exception:
        log(u"URLi hankimine ebaõnnestus:%s" % (url,))
        content = None
    return content


def getallsubs(searchstring, languageshort, languagelong, file_original_path):
    subs_list = []
    if languageshort == "et":
        log(u"Subtiitrite '%s' haaramine ..." % languageshort)
        url = SEARCH_PAGE_URL % {'query': urllib.quote_plus(searchstring)}
        content = geturl(url)
        if content is not None:
			for match in SUBTITLE_RE.finditer(content):
				synkroon = ''
				rating = match.groupdict()['hinne']
				hindajaid = match.groupdict()['hindajaid']
				if hindajaid == "0":
					hinne = 0
				else:
					hinne = int(float(rating))
				id = match.groupdict()['id']
				description = match.groupdict()['pealkiri']
				url2 = CONTENT_URL % {'query': id }
				sisu = geturl(url2)
				if sisu is not None:
					supakad = []
					for klapp in SISU_RE.finditer(sisu):
						supakas = klapp.groupdict()['supakas']
						supakad.append(supakas)
				for s in supakad:
					sisu = s.strip()
					sisu = re.sub('\n', ' ', sisu)
					sisu = re.sub('<br />', '', sisu)
					sisu = re.sub(r'<[^<]+?>', '', sisu)
					_, fn = os.path.split(file_original_path)
					name, _ = os.path.splitext(fn)
					sisu, _ = os.path.splitext(sisu)
					sync = re.search(re.escape(name), sisu, re.I) is not None
					if sync == True:
						synkroon = sync
				
				text = description.strip()
				# Eemaldame uued read
				text = re.sub('\n', ' ', text)
				# Eemaldame HTML märgid
				text = re.sub(r'<[^<]+?>', '', text)
				try:
					log(u"Subtitles found: %s (id = %s)" % (text, id))
				except Exception:
					pass
				item = {
					'rating': str(hinne),
					'filename': text.decode('latin1'),
					'sync': synkroon,
					'id': id,
					# 'language_flag': 'flags/' + languageshort + '.gif',
					'language_name': languagelong,
					# 'pealkiri': nimetus,
				}
				subs_list.append(item)

        # Pane supakad sync=True märgiga etteotsa
        subs_list = sorted(subs_list, key=lambda s: s['sync'], reverse=True)

    return subs_list


def append_subtitle(item):
    listitem = xbmcgui.ListItem(
        label=item['language_name'],
        label2=item['filename'],
        iconImage=item['rating'],
        thumbnailImage='et'
    )

    listitem.setProperty("sync", 'true' if item["sync"] else 'false')
    listitem.setProperty("hearing_imp",
                         'true' if item.get("hearing_imp", False) else 'false')


    args = dict(item)
    args['scriptid'] = __scriptid__
    url = INTERNAL_LINK_URL % args


    xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),
                                url=url,
                                listitem=listitem,
                                isFolder=False)


def Search(item):

	file_original_path = item['file_original_path']
	title = item['title']
	tvshow = item['tvshow']
	season = item['season']
	episode = item['episode']
	mansearch = item['mansearch']

	if tvshow:
		searchstring = "%s %#02dx%#02d" % (tvshow, int(season), int(episode))
	elif mansearch:
		searchstring = item['mansearchstr']
		searchstring = re.sub('%20', ' ', searchstring)
	else:
		searchstring = title
	log(u"Search string = %s" % (searchstring,))

	subs_list = getallsubs(searchstring, "et", "Estonian", file_original_path)

	for sub in subs_list:
		append_subtitle(sub)


def Download(id, filename):

    if xbmcvfs.exists(__temp__):
        shutil.rmtree(__temp__)
    xbmcvfs.mkdirs(__temp__)

    subtitles_list = []

    actual_subtitle_file_url = MAIN_URL + "down.php?id=" + id
    content = geturl(actual_subtitle_file_url)
    if content is not None:
        header = content[:4]
        if header == 'Rar!':
            local_tmp_file = pjoin(__temp__, "subclub.rar")
            packed = True
        elif header == 'PK\x03\x04':
            local_tmp_file = pjoin(__temp__, "subclub.zip")
            packed = True
        else:

            local_tmp_file = pjoin(__temp__+"/subs", "subclub.srt")
            subs_file = local_tmp_file
            packed = False
        log(u"Saving subtitles to '%s'" % local_tmp_file)
        try:
            local_file_handle = open(local_tmp_file, "wb")
            local_file_handle.write(content)
            local_file_handle.close()
        except Exception:
            log(u"Failed to save subtitles to '%s'" % local_tmp_file)
        if packed:
            files = os.listdir(__temp__)
            init_filecount = len(files)
            log(u"subclub: init_filecount = %d" % init_filecount)
            filecount = init_filecount
            max_mtime = 0

            for file in files:
                if is_subs_file(file):
                    mtime = os.stat(pjoin(__temp__, file)).st_mtime
                    if mtime > max_mtime:
                        max_mtime = mtime
            init_max_mtime = max_mtime

            time.sleep(2)
            xbmc.executebuiltin("XBMC.Extract(%s, %s)" % (
                                local_tmp_file.encode("utf-8"),
                                __temp__+"/subs".encode("utf-8")))
            waittime = 0
            while filecount == init_filecount and waittime < 20 and init_max_mtime == max_mtime:
                time.sleep(1)  # Ootame ühe sekundi, kuni funktsioon
                               # 'XBMC.Extract' lahti pakib
                files = os.listdir(__temp__+"/subs")
                filecount = len(files)
		log(u"Kataloogis on %s faili" % filecount)
                # Veendu, kas on loodud uuem fail __temp__ kataloogis (tähistab
                # lahtipakkimise lõppemist)
                for file in files:
                    if is_subs_file(file):
						file.replace(u"\xa0", u" ")
						mtime = os.stat(pjoin(__temp__+"/subs", file.decode("utf-8"))).st_mtime
						if mtime > max_mtime:
							max_mtime = mtime
                waittime = waittime + 1
            if waittime == 20:
                log(u"Failed to unpack subtitles in '%s'" % (__temp__+"/subs",))
            else:
                log(u"Unpacked files in '%s'" % (__temp__+"/subs",))
                for file in files:
					log(u"Faile: '%s'" % len(files))
                    # __temp__ kataloogis võib üle ühe supaka olla, seega
                    # laseme kasutajal valida nende seast ühe
					if len(files) > 1:
						dialog = xbmcgui.Dialog()
						subs_file = dialog.browse(1, 'XBMC', 'files', '', False, False, __temp__+"/subs/")
						log(u"Supakas: %s" % subs_file)
						subtitles_list.append(subs_file)
						break
					else:
						subs_file = pjoin(__temp__+"/subs", file.decode("utf-8"))
						subtitles_list.append(subs_file)
						
						
        else:
            subtitles_list.append(subs_file)
    return subtitles_list


def normalizeString(str):
    return unicodedata.normalize('NFKD', unicode(unicode(str, 'utf-8'))).encode('ascii', 'ignore')


def get_params():
    params = {}
    arg = sys.argv[2]
    if len(arg) >= 2:
        value = arg
        if value.endswith('/'):
            value = value[:-2]  # XXX: Peaks olema [:-1] ?
        cleaned = value.replace('?', '')
        for elem in cleaned.split('&'):
            kv = elem.split('=')
            if len(kv) == 2:
                params[kv[0]] = kv[1]

    return params


def main():
    """Main entry point of the script when it is invoked by XBMC."""

    # Saame XBMC'lt parameetrid ja jooksutame
    params = get_params()

    if params['action'] == 'search' or params['action'] == 'manualsearch':
		item = {}
		item['temp']               = False
		item['rar']                = False
		item['mansearch']			= False
		item['year']               = xbmc.getInfoLabel("VideoPlayer.Year")
		item['season']             = str(xbmc.getInfoLabel("VideoPlayer.Season"))
		item['episode']            = str(xbmc.getInfoLabel("VideoPlayer.Episode"))
		item['tvshow']             = normalizeString(xbmc.getInfoLabel("VideoPlayer.TVshowtitle"))
		# Üritame hankida originaalpealkirja
		item['title']              = normalizeString(xbmc.getInfoLabel("VideoPlayer.OriginalTitle"))
		# Esitatava faili täistee
		item['file_original_path'] = urllib.unquote(xbmc.Player().getPlayingFile().decode('utf-8'))
		item['3let_language']      = []
		item['2let_language']      = []
		
		for lang in urllib.unquote(params['languages']).decode('utf-8').split(","):
			item['3let_language'].append(xbmc.convertLanguage(lang, xbmc.ISO_639_2))
			item['2let_language'].append(xbmc.convertLanguage(lang, xbmc.ISO_639_1))
			
		if 'searchstring' in params:
			item['mansearch'] = True
			item['mansearchstr'] = params['searchstring']
		
		if not item['title']:
			# Originaalpealkiri puudub, haarab lihtsalt pealkirja
			item['title'] = normalizeString(xbmc.getInfoLabel("VideoPlayer.Title"))

		if "s" in item['episode'].lower():
			# Kontrollime, kas hooaeg on  "Special"
			item['season'] = "0"
			item['episode'] = item['episode'][-1:]

		if "http" in item['file_original_path']:
			item['temp'] = True

		elif "rar://" in item['file_original_path']:
			item['rar'] = True
			item['file_original_path'] = os.path.dirname(item['file_original_path'][6:])

		elif "stack://" in item['file_original_path']:
			stackPath = item['file_original_path'].split(" , ")
			item['file_original_path'] = stackPath[0][8:]

		Search(item)

    elif params['action'] == 'download':
        # Kõik parameetrid laadime definitsioonist Search()
        subs = Download(params["id"], params["filename"])
        for sub in subs:
            listitem = xbmcgui.ListItem(label=sub)
            xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=sub,
                                        listitem=listitem, isFolder=False)

    # Saadame XBMC'le kataloogi lõpu
    xbmcplugin.endOfDirectory(int(sys.argv[1]))


if __name__ == '__main__':
    main()