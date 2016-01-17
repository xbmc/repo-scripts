# -*- coding: utf-8 -*- 
# Based on contents from https://github.com/Diecke/service.subtitles.addicted
# Thanks Diecke!

import os
import sys
import xbmc
import urllib
import urllib2
import xbmcvfs
import xbmcaddon
import xbmcgui
import xbmcplugin
import shutil
import unicodedata
import re
import socket
import string

from BeautifulSoup import BeautifulSoup

__addon__ = xbmcaddon.Addon()
__scriptid__   = __addon__.getAddonInfo('id')
__scriptname__ = __addon__.getAddonInfo('name')
__version__    = __addon__.getAddonInfo('version')
__language__   = __addon__.getLocalizedString

__cwd__        = xbmc.translatePath( __addon__.getAddonInfo('path') ).decode("utf-8")
__profile__    = xbmc.translatePath( __addon__.getAddonInfo('profile') ).decode("utf-8")
__resource__   = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib' ) ).decode("utf-8")
__temp__       = xbmc.translatePath( os.path.join( __profile__, 'temp', '') ).decode("utf-8")

sys.path.append (__resource__)

from NLOndertitelsUtilities import log

self_host = "http://www.nlondertitels.com"
self_release_pattern = re.compile("Version (.+), ([0-9]+).([0-9])+ MBs")

req_headers = {
  'User-Agent': 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US) AppleWebKit/525.13 (KHTML, like Gecko) Chrome/0.A.B.C Safari/525.13',
  'Referer': 'http://www.nlondertitels.com'}

# from https://github.com/djay/service.subtitles.thaisubtitle
def rmdirRecursive(dir):
    """This is a replacement for shutil.rmtree that works better under
    windows. Thanks to Bear at the OSAF for the code."""
    if not os.path.exists(dir):
        return

    if os.path.islink(dir.encode('utf8')):
        os.remove(dir.encode('utf8'))
        return

    # Verify the directory is read/write/execute for the current user
    os.chmod(dir, 0700)

    # os.listdir below only returns a list of unicode filenames if the parameter is unicode
    # Thus, if a non-unicode-named dir contains a unicode filename, that filename will get garbled.
    # So force dir to be unicode.
    try:
        dir = dir.decode('utf8','ignore')
    except:
        log(__name__, "rmdirRecursive: decoding from UTF-8 failed: %s" % dir)
        return

    for name in os.listdir(dir):
        try:
            name = name.decode('utf8','ignore')
        except:
            log(__name__, "rmdirRecursive: decoding from UTF-8 failed: %s" % name)
            continue
        full_name = os.path.join(dir, name)
        # on Windows, if we don't have write permission we can't remove
        # the file/directory either, so turn that on
        if os.name == 'nt':
            if not os.access(full_name, os.W_OK):
                # I think this is now redundant, but I don't have an NT
                # machine to test on, so I'm going to leave it in place
                # -warner
                os.chmod(full_name, 0600)

        if os.path.islink(full_name):
            os.remove(full_name) # as suggested in bug #792
        elif os.path.isdir(full_name):
            rmdirRecursive(full_name)
        else:
            if os.path.isfile(full_name):
                os.chmod(full_name, 0700)
            os.remove(full_name)
    os.rmdir(dir)

    
def get_url(url):
  request = urllib2.Request(url, headers=req_headers)
  opener = urllib2.build_opener()
  response = opener.open(request)

  contents = response.read()
  return contents

def append_subtitle(item):
  listitem = xbmcgui.ListItem(label="Dutch",
                              label2=item['description'],
                              iconImage=item['rating'],
                              thumbnailImage=item['lang'])

  url = "plugin://%s/?action=download&link=%s&filename=%s" % (__scriptid__,
    item['link'],
    item['file_name'])
  xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url, listitem=listitem, isFolder=False)

def query_Film(name, imdb, file_original_path):
  if imdb:
    searchurl = "%s/?extra=q&id=%s&pagenr=1&x=0&y=" %(self_host,imdb)
    query(searchurl, file_original_path)
  else:
    name = urllib.quote(name.replace(" ", "_"))
    searchurl = "%s/?extra=q&id=%s&pagenr=1&x=0&y=" %(self_host,name)
    query(searchurl, file_original_path)

def query(searchurl, file_original_path):
  sublinks = []
  socket.setdefaulttimeout(10)
  log(__name__, "search='%s', addon_version=%s" % (searchurl, __version__))
  request = urllib2.Request(searchurl, headers=req_headers)
  request.add_header('Pragma', 'no-cache')
  page = urllib2.build_opener().open(request)
  content = page.read()
  soup = BeautifulSoup(content)
  soup2 = soup.find(id="search")

  file_name = str(os.path.basename(file_original_path)).split("-")[-1].lower()

  if soup2 != None: 
    for subs in soup2("a"):

      try:
        description = subs.findNext("i").string

        sub_original_link = subs['href']

        sub_download_link = sub_original_link.rsplit('/', 1)[0].replace("subtitle", "download")

        link = "%s" % (self_host + sub_download_link)

        sublinks.append({'rating': '0', 'file_name': file_name, 'description': "%s - %s" %(subs.string, description), 'link': link, 'lang': "nl"})

      except:
        log(__name__, "Error in BeautifulSoup")
        pass

  else:
    xbmc.executebuiltin((u'Notification(%s,%s %s)' % (__scriptname__ , __language__(32004), file_name)).encode('utf-8'))

  log(__name__, "sub='%s'" % (sublinks))

  for s in sublinks:
    append_subtitle(s)

def search_manual(mansearchstr, file_original_path):
  searchurl = "%s/?extra=q&id=%s&pagenr=1&x=0&y=" %(self_host, mansearchstr)
  query(searchurl, file_original_path)

def search_filename(filename, languages):
  title, year = xbmc.getCleanMovieTitle(filename)
  log(__name__, "clean title: \"%s\" (%s)" % (title, year))
  try:
    yearval = int(year)
  except ValueError:
    yearval = 0
  if title and yearval > 1900:
    query_Film(title, year, item['3let_language'], filename)


def Search(item):
  filename = os.path.splitext(os.path.basename(item['file_original_path']))[0]
  log(__name__, "Searching NLondertitels.com='%s', filename='%s', addon_version=%s" % (item, filename, __version__))

  if item['mansearch']:
    search_manual(item['mansearchstr'], filename)
  elif item['title']:
    query_Film(item['title'], item['imdb'], filename)
  else:
    search_filename(filename, item['3let_language'])

# from https://github.com/djay/service.subtitles.thaisubtitle
def download(link, search_string=""):
  exts = [".srt", ".sub", ".smi", ".ssa", ".ass"]
  subtitle_list = []
  response = urllib2.urlopen(link)

  if xbmcvfs.exists(__temp__):
      rmdirRecursive(__temp__)
  xbmcvfs.mkdirs(__temp__)

  local_tmp_file = os.path.join(__temp__, "nlondertitel.xxx")
  packed = False

  try:
      log(__name__, "Saving subtitles to '%s'" % local_tmp_file)
      local_file_handle = open(local_tmp_file, "wb")
      local_file_handle.write(response.read())
      local_file_handle.close()

      #Check archive type (rar/zip/else) through the file header (rar=Rar!, zip=PK)
      myfile = open(local_tmp_file, "rb")
      myfile.seek(0)
      if myfile.read(1) == 'R':
          typeid = "rar"
          packed = True
          log(__name__, "Discovered RAR Archive")
      else:
          myfile.seek(0)
          if myfile.read(1) == 'P':
              typeid = "zip"
              packed = True
              log(__name__, "Discovered ZIP Archive")
          else:
              typeid = "srt"
              packed = False
              log(__name__, "Discovered a non-archive file")
      myfile.close()
      local_tmp_file = os.path.join(__temp__, "nlondertitel." + typeid)
      os.rename(os.path.join(__temp__, "nlondertitel.xxx"), local_tmp_file)
      log(__name__, "Saving to %s" % local_tmp_file)
  except:
      log(__name__, "Failed to save subtitle to %s" % local_tmp_file)

  if packed:
      xbmc.executebuiltin(('XBMC.Extract("%s","%s")' % (local_tmp_file, __temp__,)).encode('utf-8'), True)

  dirs, files = xbmcvfs.listdir(__temp__)
  
  if dirs:
    path = os.path.join(__temp__, dirs[0].decode('utf-8'))
  else:
    path= __temp__

  for file in xbmcvfs.listdir(path)[1]:
      file = os.path.join(path, file)
      if os.path.splitext(file)[1] in exts:
          if search_string and string.find(string.lower(file), string.lower(search_string)) == -1:
              continue
          log(__name__, "=== returning subtitle file %s" % file)
          subtitle_list.append(file)

  if len(subtitle_list) == 0:
      if search_string:
          xbmc.executebuiltin((u'Notification(%s,%s)' % (__scriptname__ , __language__(32002))).encode('utf-8'))
      else:
          xbmc.executebuiltin((u'Notification(%s,%s)' % (__scriptname__ , __language__(32003))).encode('utf-8'))

  return subtitle_list


def normalizeString(str):
  return unicodedata.normalize(
      'NFKD', unicode(unicode(str, 'utf-8'))
  ).encode('ascii', 'ignore')

def get_params():
  param = {}
  paramstring = sys.argv[2]
  if len(paramstring) >= 2:
    params = paramstring
    cleanedparams = params.replace('?', '')
    if (params[len(params) - 1] == '/'):
      params = params[0:len(params) - 2]
    pairsofparams = cleanedparams.split('&')
    param = {}
    for i in range(len(pairsofparams)):
      splitparams = pairsofparams[i].split('=')
      if (len(splitparams)) == 2:
        param[splitparams[0]] = splitparams[1]

  return param

params = get_params()

if params['action'] == 'search' or params['action'] == 'manualsearch':
  item = {}
  item['temp'] = False
  item['rar'] = False
  item['mansearch'] = False
  item['title'] = normalizeString(xbmc.getInfoLabel("VideoPlayer.OriginalTitle"))  # try to get original title
  item['imdb'] = str(xbmc.Player().getVideoInfoTag().getIMDBNumber())[2:] # try to get IMDB number
  item['file_original_path'] = urllib.unquote(xbmc.Player().getPlayingFile().decode('utf-8'))  # Full path
  item['3let_language'] = []

  if 'searchstring' in params:
    item['mansearch'] = True
    item['mansearchstr'] = params['searchstring']

  for lang in urllib.unquote(params['languages']).decode('utf-8').split(","):
    item['3let_language'].append(xbmc.convertLanguage(lang, xbmc.ISO_639_2))

  if item['title'] == "":
    item['title'] = normalizeString(xbmc.getInfoLabel("VideoPlayer.Title"))      # no original title, get just Title

  if item['file_original_path'].find("http") > -1:
    item['temp'] = True

  elif item['file_original_path'].find("rar://") > -1:
    item['rar'] = True
    item['file_original_path'] = os.path.dirname(item['file_original_path'][6:])

  elif item['file_original_path'].find("stack://") > -1:
    stackPath = item['file_original_path'].split(" , ")
    item['file_original_path'] = stackPath[0][8:]

  Search(item)

elif params['action'] == 'download':
  subs = download(params["link"])
  for sub in subs:
    listitem = xbmcgui.ListItem(label=sub)
    xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=sub, listitem=listitem, isFolder=False)

xbmcplugin.endOfDirectory(int(sys.argv[1]))  # send end of directory to XBMC
