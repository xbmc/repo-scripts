import re
import string
import xbmcvfs
from contextlib import closing

from thechapterdb import TheChapterDB

addonid = 'service.stinger.notification'

class ChaptersFile(object):
    def __init__(self, title, duration, fps, grabexternal):
        xbmcvfs.mkdirs('special://profile/addon_data/{0}/chapters/'.format(addonid))
        self.path = 'special://profile/addon_data/{0}/chapters/{1}-{2:d}-chapters.txt'.format(addonid, cleanfilename(title), duration)
        self.lastchapterstart = None
        if not self.load():
            if grabexternal:
                self.download(title, duration, fps)

    @property
    def exists(self):
        return xbmcvfs.exists(self.path)

    def load(self):
        self.lastchapterstart = None
        if self.exists:
            with closing(xbmcvfs.File(self.path)) as chaptersfile:
                self.lastchapterstart = find_lastchapterstart(chaptersfile.read())
        return self.lastchapterstart is not None

    def download(self, title, duration, fps):
        chapterdb = TheChapterDB()
        result = chapterdb.get_simplechapterfile(title, duration, fps)
        if result:
            self.lastchapterstart = result[1]
            with closing(xbmcvfs.File(self.path, 'w')) as chaptersfile:
                chaptersfile.write(result[0].encode('UTF-8'))
        else:
            self.lastchapterstart = None

def cleanfilename(title):
    valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
    return ''.join(c for c in title if c in valid_chars)

def find_lastchapterstart(simplechapterfile):
    lastchapterstart = None
    for match in re.finditer(r'^CHAPTER[\d]+=([\d:.]+)$', simplechapterfile, re.MULTILINE):
        if match.group(1) > lastchapterstart:
            lastchapterstart = match.group(1)
    return lastchapterstart
