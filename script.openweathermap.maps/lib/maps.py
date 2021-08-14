import os
import time
import requests
import threading
import socket
import hashlib
import shutil
import xbmcvfs
from PIL import Image
from lib.utils import *

ADDONVERSION = ADDON.getAddonInfo('version')
CWD = ADDON.getAddonInfo('path')
PROFILE = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))

socket.setdefaulttimeout(10)


class Main():
    def __init__(self, *args, **kwargs):
        self.params = kwargs['params']
        self.DEBUG = self.params.get('DEBUG', 'false') == 'true'
        log('script version %s started' % ADDONVERSION, self.DEBUG)
        set_property('Map.IsFetched', 'true')
        lat, lon, zoom, api = self._parse_argv(self.params)
        self._clear_props()
        self._get_maps(lat, lon, zoom, api)

    def _parse_argv(self, params):
        lat = params.get('lat', '')
        lon = params.get('lon', '')
        zoom = int(params.get('zoom', ''))
        api = params.get('api', '')
        return lat, lon, zoom, api

    def _clear_props(self):
        for count in range(1,6):
            clear_property('Map.%i.Area' % count)
            clear_property('Map.%i.Layer' % count)
            clear_property('Map.%i.Heading' % count)
            clear_property('Map.%i.Legend' % count)

    def _get_maps(self, lat, lon, zoom, api):
        md5 = hashlib.md5()
        locationdeg = [lat, lon]
        md5.update(str(locationdeg).encode('utf-8') + str(zoom).encode('utf-8'))
        tag = md5.hexdigest()
        streetthread_created = False
        stamp = int(time.time())
        street_url = 'http://tile.openstreetmap.org/{}/{}/{}.png?appid={}'
        precip_url = 'http://tile.openweathermap.org/map/precipitation/{}/{}/{}.png?appid={}'
        clouds_url = 'http://tile.openweathermap.org/map/clouds/{}/{}/{}.png?appid={}'
        temp_url = 'http://tile.openweathermap.org/map/temp/{}/{}/{}.png?appid={}'
        wind_url = 'http://tile.openweathermap.org/map/wind/{}/{}/{}.png?appid={}'
        pressure_url = 'http://tile.openweathermap.org/map/pressure/{}/{}/{}.png?appid={}'
        streetmapdir = os.path.join(PROFILE, 'maps', 'streetmap-%s' % tag, '')
        precipmapdir = os.path.join(PROFILE, 'maps', 'precipmap', '')
        cloudsmapdir = os.path.join(PROFILE, 'maps', 'cloudsmap', '')
        tempmapdir = os.path.join(PROFILE, 'maps', 'tempmap', '')
        windmapdir = os.path.join(PROFILE, 'maps', 'windmap', '')
        pressuremapdir = os.path.join(PROFILE, 'maps', 'pressuremap', '')
        lat = float(lat)
        lon = float(lon)
        x, y = GET_TILE(lat, lon, zoom)
        imgs = [[x-1,y-1], [x,y-1], [x+1,y-1], [x-1,y], [x,y], [x+1,y], [x-1,y+1], [x,y+1], [x+1,y+1]]
        # adjust for locations on the edge of the map
        tile_max = 2**zoom - 1
        if x == 0:
            imgs = [[tile_max,y-1], [x,y-1], [x+1,y-1], [tile_max,y], [x,y], [x+1,y], [tile_max,y+1], [x,y+1], [x+1,y+1]]
        elif x == tile_max:
            imgs = [[x-1,y-1], [x,y-1], [0,y-1], [x-1,y], [x,y], [0,y], [x-1,y+1], [x,y+1], [0,y+1]]
        if y == 0:
            imgs = [[x-1,tile_max], [x,tile_max], [x+1,tile_max], [x-1,y], [x,y], [x+1,y], [x-1,y+1], [x,y+1], [x+1,y+1]]
        elif y == tile_max:
            imgs = [[x-1,y-1], [x,y-1], [x+1,y-1], [x-1,y], [x,y], [x+1, y], [x-1,0], [x,0], [x+1,0]]
        # delete old maps
        if xbmcvfs.exists(precipmapdir):
            shutil.rmtree(precipmapdir)
        if xbmcvfs.exists(cloudsmapdir):
            shutil.rmtree(cloudsmapdir)
        if xbmcvfs.exists(tempmapdir):
            shutil.rmtree(tempmapdir)
        if xbmcvfs.exists(windmapdir):
            shutil.rmtree(windmapdir)
        if xbmcvfs.exists(pressuremapdir):
            shutil.rmtree(pressuremapdir)
        if xbmcvfs.exists(streetmapdir) and not xbmcvfs.exists(os.path.join(streetmapdir, 'streetmap.png')):
            # we have an incomplete streetmap
            shutil.rmtree(streetmapdir)
        if not xbmcvfs.exists(streetmapdir):
            xbmcvfs.mkdirs(streetmapdir)
        # download the streetmap once, unless location or zoom has changed
        if not xbmcvfs.exists(os.path.join(streetmapdir, 'streetmap.png')):
            thread_street = get_tiles(streetmapdir, 'streetmap.png', zoom, stamp, imgs, street_url, '')
            thread_street.start()
            streetthread_created = True
        if not xbmcvfs.exists(precipmapdir):
            xbmcvfs.mkdirs(precipmapdir)
        thread_precip = get_tiles(precipmapdir, 'precipmap-%s.png', zoom, stamp, imgs, precip_url, api)
        thread_precip.start()
        if not xbmcvfs.exists(cloudsmapdir):
            xbmcvfs.mkdirs(cloudsmapdir)
        thread_clouds = get_tiles(cloudsmapdir, 'cloudsmap-%s.png', zoom, stamp, imgs, clouds_url, api)
        thread_clouds.start()
        if not xbmcvfs.exists(tempmapdir):
            xbmcvfs.mkdirs(tempmapdir)
        thread_temp = get_tiles(tempmapdir, 'tempmap-%s.png', zoom, stamp, imgs, temp_url, api)
        thread_temp.start()
        if not xbmcvfs.exists(windmapdir):
            xbmcvfs.mkdirs(windmapdir)
        thread_wind = get_tiles(windmapdir, 'windmap-%s.png', zoom, stamp, imgs, wind_url, api)
        thread_wind.start()
        if not xbmcvfs.exists(pressuremapdir):
            xbmcvfs.mkdirs(pressuremapdir)
        thread_pressure = get_tiles(pressuremapdir, 'pressuremap-%s.png', zoom, stamp, imgs, pressure_url, api)
        thread_pressure.start()
        if streetthread_created:
            thread_street.join()
        thread_precip.join()
        thread_clouds.join()
        thread_temp.join()
        thread_wind.join()
        thread_pressure.join()
        psmap = os.path.join(PROFILE, 'maps', 'pressuremap', 'pressuremap-%s.png' % stamp)
        set_property('Map.1.Area', os.path.join(PROFILE, 'maps', 'streetmap-%s' % tag, 'streetmap.png'))
        set_property('Map.2.Area', os.path.join(PROFILE, 'maps', 'streetmap-%s' % tag, 'streetmap.png'))
        set_property('Map.3.Area', os.path.join(PROFILE, 'maps', 'streetmap-%s' % tag, 'streetmap.png'))
        set_property('Map.4.Area', os.path.join(PROFILE, 'maps', 'streetmap-%s' % tag, 'streetmap.png'))
        set_property('Map.5.Area', os.path.join(PROFILE, 'maps', 'streetmap-%s' % tag, 'streetmap.png'))
        set_property('Map.1.Layer', os.path.join(PROFILE, 'maps', 'precipmap', 'precipmap-%s.png' % stamp))
        set_property('Map.2.Layer', os.path.join(PROFILE, 'maps', 'cloudsmap', 'cloudsmap-%s.png' % stamp))
        set_property('Map.3.Layer', os.path.join(PROFILE, 'maps', 'tempmap', 'tempmap-%s.png' % stamp))
        set_property('Map.4.Layer', os.path.join(PROFILE, 'maps', 'windmap', 'windmap-%s.png' % stamp))
        set_property('Map.5.Layer', os.path.join(PROFILE, 'maps', 'pressuremap', 'pressuremap-%s.png' % stamp))
        set_property('Map.1.Heading', xbmc.getLocalizedString(1448))
        set_property('Map.2.Heading', xbmc.getLocalizedString(387))
        set_property('Map.3.Heading', xbmc.getLocalizedString(1375))
        set_property('Map.4.Heading', xbmc.getLocalizedString(383))
        set_property('Map.5.Heading', xbmc.getLocalizedString(1376))
        if 'F' in TEMPUNIT:
            set_property('Map.1.Legend' , xbmcvfs.translatePath(os.path.join(CWD, 'resources', 'graphics', 'precip-in.png')))
        else:
            set_property('Map.1.Legend' , xbmcvfs.translatePath(os.path.join(CWD, 'resources', 'graphics', 'precip-mm.png')))
        set_property('Map.2.Legend' , xbmcvfs.translatePath(os.path.join(CWD, 'resources', 'graphics', 'clouds.png')))
        if 'F' in TEMPUNIT:
            set_property('Map.3.Legend' , xbmcvfs.translatePath(os.path.join(CWD, 'resources', 'graphics', 'temp-f.png')))
        else:
            set_property('Map.3.Legend' , xbmcvfs.translatePath(os.path.join(CWD, 'resources', 'graphics', 'temp-c.png')))
        if SPEEDUNIT == 'mph':
            set_property('Map.4.Legend' , xbmcvfs.translatePath(os.path.join(CWD, 'resources', 'graphics', 'wind-mi.png')))
        elif SPEEDUNIT == 'Beaufort':
            set_property('Map.4.Legend' , xbmcvfs.translatePath(os.path.join(CWD, 'resources', 'graphics', 'wind-bft.png')))
        else:
            set_property('Map.4.Legend' , xbmcvfs.translatePath(os.path.join(CWD, 'resources', 'graphics', 'wind-kmh.png')))
        set_property('Map.5.Legend' , xbmcvfs.translatePath(os.path.join(CWD, 'resources', 'graphics', 'press.png')))


class get_tiles(threading.Thread):
    def __init__(self, mapdir, mapfile, zoom, stamp, imgs, url, api):
        self.mapdir = mapdir
        self.mapfile = mapfile
        self.zoom = zoom
        self.stamp = stamp
        self.imgs = imgs
        self.url = url
        self.api = api
        self.loop = 0
        self.useragent = '%s/%s (+https://forum.kodi.tv/showthread.php?tid=207110)' % (ADDONID, ADDONVERSION)
        self.MONITOR = MyMonitor()
        threading.Thread.__init__(self)
 
    def run(self):
        self.fetch_tiles(self.imgs, self.mapdir, self.zoom, self.api)
        self.merge_tiles()

    def fetch_tiles(self, imgs, mapdir, zoom, api):
        count = 1
        failed = []
        for img in imgs:
            self.retry = False
            data = b''
            query = self.url.format(zoom, img[0], img[1], api)
            try:
                response = requests.get(query, headers={'User-Agent': self.useragent}, timeout=5)
            except:
                self.retry = True
                response = None
            if response:
                if response.status_code == 401:
                    log('401 Unauthorized', self.DEBUG)
                    return
                data = response.content
                if len(img) == 3:
                    num = img[2]
                else:
                    num = str(count)
                tilefile = xbmcvfs.translatePath(os.path.join(mapdir, num + '.png'))
                try:
                    tmpmap = open(tilefile, 'wb')
                    tmpmap.write(data)
                    tmpmap.close()
                except:
                    log('failed to save image', self.DEBUG)
                    return
            else:
                self.retry = True
            if self.retry:
                log('failed to connect, retry', self.DEBUG)
                data = []
                if len(img) == 2:
                    img.append(str(count))
                failed.append(img)
            count += 1
            if self.MONITOR.abortRequested():
                return
        if failed and self.loop < 10:
            self.loop += 1
            if self.MONITOR.waitForAbort(10):
                return
            self.fetch_tiles(failed, mapdir, zoom, self.api)

    def merge_tiles(self):
        out = Image.new("RGBA", (756, 756), None)
        count = 1
        imy = 0
        for y in range(0,3):
            imx = 0
            for x in range(0,3):
                tile_file = os.path.join(self.mapdir,str(count)+".png")
                count += 1
                try:
                    tile = Image.open(tile_file)
                except:
                    return
                out.paste( tile, (imx, imy))
                imx += 256
            imy += 256
        if not self.mapfile == 'streetmap.png':
            out.save(os.path.join(self.mapdir,self.mapfile % str(self.stamp)))
        else:
            out.save(os.path.join(self.mapdir,self.mapfile))


class MyMonitor(xbmc.Monitor):
    def __init__(self, *args, **kwargs):
        xbmc.Monitor.__init__(self)
