'''
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import os
import simplejson
import xbmc
import xbmcaddon
from time import sleep
from urllib import unquote
from threading import Thread
from watchdog.events import FileSystemEventHandler

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
CLEAN = ADDON.getSetting('clean') in ['true']
POLLING = int(ADDON.getSetting('method'))
RECURSIVE = not (ADDON.getSetting('nonrecursive') in ['true']) or not POLLING
WATCH_VIDEO = ADDON.getSetting('watchvideo') in ['true']
WATCH_MUSIC = ADDON.getSetting('watchmusic') in ['true']
DELAY = 1

EXTENSIONS = "|.nsv|.m4a|.flac|.aac|.strm|.pls|.rm|.rma|.mpa|.wav|.wma|.ogg|.mp3|.mp2|.m3u|.mod|.amf|.669|.dmf|.dsm|.far|.gdm|.imf|.it|.m15|.med|.okt|.s3m|.stm|.sfx|.ult|.uni|.xm|.sid|.ac3|.dts|.cue|.aif|.aiff|.wpl|.ape|.mac|.mpc|.mp+|.mpp|.shn|.zip|.rar|.wv|.nsf|.spc|.gym|.adx|.dsp|.adp|.ymf|.ast|.afc|.hps|.xsp|.xwav|.waa|.wvs|.wam|.gcm|.idsp|.mpdsp|.mss|.spt|.rsd|.mid|.kar|.sap|.cmc|.cmr|.dmc|.mpt|.mpd|.rmt|.tmc|.tm8|.tm2|.oga|.url|.pxml|.tta|.rss|.cm3|.cms|.dlt|.brstm|.wtv|.mka|.m4v|.3g2|.3gp|.nsv|.tp|.ts|.ty|.strm|.pls|.rm|.rmvb|.m3u|.ifo|.mov|.qt|.divx|.xvid|.bivx|.vob|.nrg|.img|.iso|.pva|.wmv|.asf|.asx|.ogm|.m2v|.avi|.bin|.dat|.mpg|.mpeg|.mp4|.mkv|.avc|.vp3|.svq3|.nuv|.viv|.dv|.fli|.flv|.rar|.001|.wpl|.zip|.vdr|.dvr-ms|.xsp|.mts|.m2t|.m2ts|.evo|.ogv|.sdp|.avs|.rec|.url|.pxml|.vc1|.h264|.rcv|.rss|.mpls|.webm|.bdmv|.wtv|.m4v|.3g2|.3gp|.nsv|.tp|.ts|.ty|.strm|.pls|.rm|.rmvb|.m3u|.m3u8|.ifo|.mov|.qt|.divx|.xvid|.bivx|.vob|.nrg|.img|.iso|.pva|.wmv|.asf|.asx|.ogm|.m2v|.avi|.bin|.dat|.mpg|.mpeg|.mp4|.mkv|.avc|.vp3|.svq3|.nuv|.viv|.dv|.fli|.flv|.rar|.001|.wpl|.zip|.vdr|.dvr-ms|.xsp|.mts|.m2t|.m2ts|.evo|.ogv|.sdp|.avs|.rec|.url|.pxml|.vc1|.h264|.rcv|.rss|.mpls|.webm|.bdmv|.wtv|"


if POLLING:
  from watchdog.observers.polling import PollingObserver as Observer
else:
  from watchdog.observers import Observer


class Worker(Thread):
  def __init__(self, library):
    Thread.__init__(self)
    self.scan = False
    self.clean = False
    self.library = library
  
  def run(self):
    sleep(DELAY)
    while True:
      if self.clean:
        self.clean = False
        log("cleaning %s library" % self.library)
        xbmc.executebuiltin("CleanLibrary(%s)" % self.library)
        sleep(1) #give xbmc time to render
        while xbmc.getCondVisibility('Window.IsActive(10101)'):
          sleep(1)
      
      if self.scan:
        log("scanning %s library" % self.library)
        self.scan = False
        xbmc.executebuiltin("UpdateLibrary(%s)" % self.library)
        sleep(1)
        while xbmc.getCondVisibility('Library.IsScanning'):
          sleep(1)
      
      #done if no new requests since scan/clean was set to false
      if not(self.scan) and not(self.clean):
        return

class EventHandler(FileSystemEventHandler):
  def __init__(self, library):
    FileSystemEventHandler.__init__(self)
    self.worker = Worker(library)
    self.library = library
  
  def _scan(self):
    self._on_worker('scan')
  
  def _clean(self):
    if CLEAN: self._on_worker('clean')
  
  def _on_worker(self, attr):
    if self.worker.isAlive():
      setattr(self.worker, attr, True)
    else:
      self.worker = Worker(self.library)
      setattr(self.worker, attr, True)
      self.worker.start()
  
  def on_created(self, event):
    self._scan()
  
  def on_deleted(self, event):
    if not event.is_directory:
      _, ext = os.path.splitext(str(event.src_path))
      if EXTENSIONS.find('|%s|' % ext) == -1:
        return
    self._clean()
  
  def on_moved(self, event):
    self._clean()
    self._scan()
  
  def on_any_event(self, event):
    log("<%s> <%s>" % (str(event.event_type), str(event.src_path)))

def get_media_sources(type):
  query = '{"jsonrpc": "2.0", "method": "Files.GetSources", "params": {"media": "%s"}, "id": 1}' % type
  result = xbmc.executeJSONRPC(query)
  json = simplejson.loads(result)
  ret = []
  if json.has_key('result'):
    if json['result'].has_key('sources'):
      paths = [ e['file'] for e in json['result']['sources'] ]
      for path in paths:
        #split and decode multipaths
        if path.startswith("multipath://"):
          for e in path.split("multipath://")[1].split('/'):
            if e != "":
              ret.append(unquote(e))
        else:
          ret.append(path)
  return ret

def log(msg):
  xbmc.log("%s: %s" % (ADDON_ID, msg), xbmc.LOGDEBUG)

def watch(library):
  event_handler = EventHandler(library)
  observer = Observer()
  for dir in get_media_sources(library):
    dir = dir.encode('utf-8')
    if os.path.exists(dir):
      log("watching <%s>" % dir)
      observer.schedule(event_handler, path=dir, recursive=RECURSIVE)
    else:
      log("not watching <%s>" % dir)
  observer.start()
  return observer

if __name__ == "__main__":
  log("using <%s>, recursive: %i" % (Observer, RECURSIVE))
  observers = []
  if WATCH_VIDEO: observers.append(watch('video'))
  if WATCH_MUSIC: observers.append(watch('music'))
  
  while (not xbmc.abortRequested):
    sleep(1)
  for o in observers:
    o.stop()
    o.join()
