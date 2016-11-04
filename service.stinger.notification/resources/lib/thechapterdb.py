import re
import requests
import xbmc
import xml.etree.ElementTree as ET
from requests import Timeout, ConnectionError, HTTPError

def log(message, level=xbmc.LOGDEBUG):
    xbmc.log('[service.stinger.notification:chapterdb] %s' % (message), level)

class TheChapterDB(object):
    apikey = 'N6FOACQ6T4GMO5CMU6VD'
    apiurl = 'http://chapterdb.org/chapters/search'

    def __init__(self):
        self.session = requests.Session()
        self.session.headers['Accept'] = 'text/xml'

    def _get_root(self, title):
        try:
            result = self.session.get(self.apiurl, params={'title': title}, headers={'apikey': self.apikey}, timeout=15)
        except (Timeout, ConnectionError):
            return None
        if result.status_code == requests.codes.not_found:
            return None
        try:
            result.raise_for_status()
        except HTTPError as ex:
            log('HTTP Error: {0}'.format(ex.message), xbmc.LOGWARNING)
            return None
        return ET.fromstring(result.content)

    def get_simplechapterfile(self, title, duration, fps):
        log('Looking up {0}'.format(title), xbmc.LOGINFO)
        title = firstcleantitle(title)
        root = self._get_root(title)
        if root is None:
            return None
        result = first_checks(root, duration, fps)
        if not result:
            ctitle = cleantitle(title)
            if ctitle is not title:
                root = self._get_root(ctitle)
                if root is None:
                    return None
                result = first_checks(root, duration, fps)
        if not result:
            result = parse_chapters(root, duration, fps, True)
        if not result:
            result = parse_chapters(root)
        return result

def first_checks(root, duration, fps):
    result = parse_chapters(root, duration, fps)
    if not result:
        result = parse_chapters(root, duration)
    return result

def parse_chapters(root, duration=None, fps=None, looseduration=False):
    seconds = 7
    if looseduration:
        seconds = 20
    for chapterinfo in root.findall('{http://jvance.com/2008/ChapterGrabber}chapterInfo'):
        source = chapterinfo.find('{http://jvance.com/2008/ChapterGrabber}source')
        if (duration or fps) and source is None:
            continue
        if duration:
            infoduration = source.find('{http://jvance.com/2008/ChapterGrabber}duration')
            if infoduration is None:
                continue
            infoduration = getseconds(infoduration.text)
            if infoduration is None:
                continue
            if abs(duration - infoduration) > seconds:
                continue
        if fps:
            if source.find('{http://jvance.com/2008/ChapterGrabber}fps') is None:
                continue
            if not source.find('{http://jvance.com/2008/ChapterGrabber}fps').text.startswith(fps):
                continue
        chaptercount = 0
        simplechapterfile = u''
        lastchapterstart = None
        for chapter in chapterinfo.find('{http://jvance.com/2008/ChapterGrabber}chapters'):
            chaptercount += 1
            time = chapter.get('time')[:12]
            if duration:
                timeseconds = getseconds(time)
                if timeseconds > duration - 30:
                    log('tossing late chapter')
                    continue

            if '.' not in time:
                time = time + '.000'
            simplechapterfile += u'CHAPTER{0:02d}={1}\n'.format(chaptercount, time)
            simplechapterfile += u'CHAPTER{0:02d}NAME={1}\n'.format(chaptercount, chapter.get('name'))
            if chapter.get('time') > lastchapterstart:
                lastchapterstart = chapter.get('time')
        if lastchapterstart:
            return simplechapterfile, lastchapterstart

def firstcleantitle(title):
    return title.rstrip('.!')[:40]

def cleantitle(title):
    result = title.replace('&', 'and')
    if result != title:
        return result
    if title.endswith(')'):
        i = title.rfind('(')
        if i > 0:
            return title[:i]
    result = title.split(':', 1)[0]
    if result != title:
        return result
    result = title.translate(None, '.!()')
    if result != title:
        return result
    result = re.sub(r'[^\w ]+', '-', title)
    if result != title:
        return result
    return title

def getseconds(duration):
    duration = duration.split('.')[0].split(':')
    try:
        return int(duration[0]) * 60 * 60 + int(duration[1]) * 60 + int(duration[2])
    except ValueError:
        return None
