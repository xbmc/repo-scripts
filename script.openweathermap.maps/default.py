import os, sys, time, urllib2, threading, socket, hashlib, shutil
import xbmc, xbmcvfs, xbmcaddon
from PIL import Image
from PIL import ImageEnhance

ADDON        = xbmcaddon.Addon()
ADDONID      = ADDON.getAddonInfo('id')
ADDONVERSION = ADDON.getAddonInfo('version')
CWD          = ADDON.getAddonInfo('path').decode("utf-8")
RESOURCE     = xbmc.translatePath( os.path.join( CWD, 'resources', 'lib' ).encode("utf-8") ).decode("utf-8")
PROFILE      = xbmc.translatePath(ADDON.getAddonInfo('profile')).decode('utf-8')
MAINADDON    = xbmcaddon.Addon('weather.openweathermap.extended')

sys.path.append(RESOURCE)

from utils import *

ZOOM = int(MAINADDON.getSetting('Zoom')) + 2

socket.setdefaulttimeout(10)

class Main:
    def __init__(self):
        set_property('Map.IsFetched', 'true')
        lat, lon = self._parse_argv()
        clear_property('Map.1.Area')
        clear_property('Map.2.Area')
        clear_property('Map.3.Area')
        clear_property('Map.4.Area')
        clear_property('Map.5.Area')
        clear_property('Map.1.Layer')
        clear_property('Map.2.Layer')
        clear_property('Map.3.Layer')
        clear_property('Map.4.Layer')
        clear_property('Map.5.Layer')
        clear_property('Map.1.Heading')
        clear_property('Map.2.Heading')
        clear_property('Map.3.Heading')
        clear_property('Map.4.Heading')
        clear_property('Map.5.Heading')
        self._get_maps(lat, lon)

    def _parse_argv(self):
        try:
            params = dict(arg.split('=') for arg in sys.argv[ 1 ].split('&'))
        except:
            params = {}
        lat = params.get('lat', '')
        lon = params.get('lon', '')
        return lat, lon

    def _get_maps(self, lat, lon):
        md5 = hashlib.md5()
        locationdeg = [lat, lon]
        md5.update(str(locationdeg) + str(ZOOM))
        tag = md5.hexdigest()
        streetthread_created = False
        stamp = int(time.time())
        street_url = 'http://c.tile.openstreetmap.org/%i/%i/%i.png'
        precip_url = 'http://undefined.tile.openweathermap.org/map/precipitation/%i/%i/%i.png'
        clouds_url = 'http://undefined.tile.openweathermap.org/map/clouds/%i/%i/%i.png'
        temp_url = 'http://undefined.tile.openweathermap.org/map/temp/%i/%i/%i.png'
        wind_url = 'http://undefined.tile.openweathermap.org/map/wind/%i/%i/%i.png'
        pressure_url = 'http://undefined.tile.openweathermap.org/map/pressure/%i/%i/%i.png'
        pressurecntr_url = 'http://undefined.tile.openweathermap.org/map/pressure_cntr/%i/%i/%i.png'
        streetmapdir = os.path.join(PROFILE, 'maps', 'streetmap-%s' % tag, '')
        precipmapdir = os.path.join(PROFILE, 'maps', 'precipmap', '')
        cloudsmapdir = os.path.join(PROFILE, 'maps', 'cloudsmap', '')
        tempmapdir = os.path.join(PROFILE, 'maps', 'tempmap', '')
        windmapdir = os.path.join(PROFILE, 'maps', 'windmap', '')
        pressuremapdir = os.path.join(PROFILE, 'maps', 'pressuremap', '')
        pressurecntrmapdir = os.path.join(PROFILE, 'maps', 'pressurecntrmap', '')
        lat = float(lat)
        lon = float(lon)
        x, y = GET_TILE(lat, lon, ZOOM)
        imgs = [[x-1,y-1], [x,y-1], [x+1,y-1], [x-1,y], [x,y], [x+1,y], [x-1,y+1], [x,y+1], [x+1,y+1]]
        # adjust for locations on the edge of the map
        tile_max = 2**ZOOM - 1
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
        if xbmcvfs.exists(pressurecntrmapdir):
            shutil.rmtree(pressurecntrmapdir)
        if xbmcvfs.exists(streetmapdir) and not xbmcvfs.exists(os.path.join(streetmapdir, 'streetmap.png')):
            # we have an incomplete streetmap
            shutil.rmtree(streetmapdir)
        if not xbmcvfs.exists(streetmapdir):
            xbmcvfs.mkdirs(streetmapdir)
        # download the streetmap once, unless location or zoom has changed
        if not xbmcvfs.exists(os.path.join(streetmapdir, 'streetmap.png')):
            thread_street = get_tiles(streetmapdir, 'streetmap.png', stamp, imgs, street_url)
            thread_street.start()
            streetthread_created = True
        if not xbmcvfs.exists(precipmapdir):
            xbmcvfs.mkdirs(precipmapdir)
        thread_precip = get_tiles(precipmapdir, 'precipmap-%s.png', stamp, imgs, precip_url)
        thread_precip.start()
        if not xbmcvfs.exists(cloudsmapdir):
            xbmcvfs.mkdirs(cloudsmapdir)
        thread_clouds = get_tiles(cloudsmapdir, 'cloudsmap-%s.png', stamp, imgs, clouds_url)
        thread_clouds.start()
        if not xbmcvfs.exists(tempmapdir):
            xbmcvfs.mkdirs(tempmapdir)
        thread_temp = get_tiles(tempmapdir, 'tempmap-%s.png', stamp, imgs, temp_url)
        thread_temp.start()
        if not xbmcvfs.exists(windmapdir):
            xbmcvfs.mkdirs(windmapdir)
        thread_wind = get_tiles(windmapdir, 'windmap-%s.png', stamp, imgs, wind_url)
        thread_wind.start()
        if not xbmcvfs.exists(pressuremapdir):
            xbmcvfs.mkdirs(pressuremapdir)
        thread_pressure = get_tiles(pressuremapdir, 'pressuremap-%s.png', stamp, imgs, pressure_url)
        thread_pressure.start()
        if not xbmcvfs.exists(pressurecntrmapdir):
            xbmcvfs.mkdirs(pressurecntrmapdir)
        thread_pressurecntr = get_tiles(pressurecntrmapdir, 'pressurecntrmap-%s.png', stamp, imgs, pressurecntr_url)
        thread_pressurecntr.start()
        if streetthread_created:
            thread_street.join()
        thread_precip.join()
        thread_clouds.join()
        thread_temp.join()
        thread_wind.join()
        thread_pressure.join()
        thread_pressurecntr.join()
        psmap = os.path.join(PROFILE, 'maps', 'pressuremap', 'pressuremap-%s.png' % stamp)
        pscntrmap = os.path.join(PROFILE, 'maps', 'pressurecntrmap', 'pressurecntrmap-%s.png' % stamp)
        if xbmcvfs.exists(psmap) and xbmcvfs.exists(pscntrmap):
            background = Image.open(psmap)
            foreground = Image.open(pscntrmap)
            background.paste(foreground, (0, 0), foreground)
            background.save(psmap)
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
            set_property('Map.1.Legend' , xbmc.translatePath(os.path.join(CWD, 'resources', 'graphics', 'precip-in.png')))
        else:
            set_property('Map.1.Legend' , xbmc.translatePath(os.path.join(CWD, 'resources', 'graphics', 'precip-mm.png')))
        set_property('Map.2.Legend' , xbmc.translatePath(os.path.join(CWD, 'resources', 'graphics', 'clouds.png')))
        if 'F' in TEMPUNIT:
            set_property('Map.3.Legend' , xbmc.translatePath(os.path.join(CWD, 'resources', 'graphics', 'temp-f.png')))
        else:
            set_property('Map.3.Legend' , xbmc.translatePath(os.path.join(CWD, 'resources', 'graphics', 'temp-c.png')))
        if SPEEDUNIT == 'mph':
            set_property('Map.4.Legend' , xbmc.translatePath(os.path.join(CWD, 'resources', 'graphics', 'wind-mi.png')))
        elif SPEEDUNIT == 'Beaufort':
            set_property('Map.4.Legend' , xbmc.translatePath(os.path.join(CWD, 'resources', 'graphics', 'wind-bft.png')))
        else:
            set_property('Map.4.Legend' , xbmc.translatePath(os.path.join(CWD, 'resources', 'graphics', 'wind-kmh.png')))
        set_property('Map.5.Legend' , xbmc.translatePath(os.path.join(CWD, 'resources', 'graphics', 'press.png')))


class get_tiles(threading.Thread):
    def __init__(self, mapdir, mapfile, stamp, imgs, url):
        self.mapdir = mapdir
        self.mapfile = mapfile
        self.stamp = stamp
        self.imgs = imgs
        self.url = url
        self.loop = 0
        threading.Thread.__init__(self)
 
    def run(self):
        self.fetch_tiles(self.imgs, self.mapdir)
        self.merge_tiles()

    def fetch_tiles(self, imgs, mapdir):
        count = 1
        success = True
        failed = []
        for img in imgs:
            data = []
            query = self.url % (ZOOM, img[0], img[1])
            req = urllib2.Request(query)
            try:
                response = urllib2.urlopen(req, timeout=10)
                try:
                    while True:
                        if MONITOR.abortRequested():
                            return
                        bytes = response.read(4096)
                        if not bytes:
                            log('image downloaded')
                            break
                        data.append(bytes)
                except:
                    log('image download failed, retry')
                    success = False
                response.close()
            except:
                log('failed to connect, retry')
                success = False
            if not success:
                data = []
                if len(img) == 2:
                    img.append(str(count))
                failed.append(img)
            if data != []:
                if len(img) == 3:
                    num = img[2]
                else:
                    num = str(count)
                tilefile = xbmc.translatePath(os.path.join(mapdir, num + '.png')).decode("utf-8")
                try:
                    tmpmap = open(tilefile, 'wb')
                    tmpmap.write(''.join(data))
                    tmpmap.close()
                except:
                    log('failed to save image')
                    return
            count += 1
            if MONITOR.abortRequested():
                return
        if failed and self.loop < 10:
            self.loop += 1
            if MONITOR.waitForAbort(10):
                return
            self.fetch_tiles(failed, mapdir)

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
                out.paste( tile, (imx, imy), tile.convert('RGBA') )
                imx += 256
            imy += 256
        if self.mapfile[0:6] == 'clouds' or self.mapfile[0:9] == 'pressurec':
            enhancer = ImageEnhance.Brightness(out)
            out = enhancer.enhance(0.3)
        if not self.mapfile == 'streetmap.png':
            out.save(os.path.join(self.mapdir,self.mapfile % str(self.stamp)))
        else:
            out.save(os.path.join(self.mapdir,self.mapfile))

class MyMonitor(xbmc.Monitor):
    def __init__(self, *args, **kwargs):
        xbmc.Monitor.__init__(self)

MONITOR = MyMonitor()

if ( __name__ == "__main__" ):
    log('script version %s started' % ADDONVERSION)
    Main()

