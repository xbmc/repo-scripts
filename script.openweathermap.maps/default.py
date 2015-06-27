import os, time, urllib2, threading, hashlib, shutil, gzip
import xbmc, xbmcvfs, xbmcaddon
from StringIO import StringIO
from PIL import Image
from PIL import ImageEnhance

__addon__      = xbmcaddon.Addon()
__mainaddon__  = xbmcaddon.Addon('weather.openweathermap.extended')
__addonid__    = __addon__.getAddonInfo('id')
__cwd__        = __addon__.getAddonInfo('path').decode("utf-8")
__resource__   = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib' ).encode("utf-8") ).decode("utf-8")

sys.path.append(__resource__)

from utils import *

ZOOM = int(__mainaddon__.getSetting('Zoom')) + 3


class Main:
    def __init__(self):
        set_property('Map.IsFetched', 'true')
        lat, lon = self._parse_argv()
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
        pressure_url = 'http://undefined.tile.openweathermap.org/map/pressure_cntr/%i/%i/%i.png'
        streetmapdir = xbmc.translatePath('special://profile/addon_data/%s/maps/streetmap-%s/' % (__addonid__, tag))
        precipmapdir = xbmc.translatePath('special://profile/addon_data/%s/maps/precipmap/' % __addonid__)
        cloudsmapdir = xbmc.translatePath('special://profile/addon_data/%s/maps/cloudsmap/' % __addonid__)
        tempmapdir = xbmc.translatePath('special://profile/addon_data/%s/maps/tempmap/' % __addonid__)
        windmapdir = xbmc.translatePath('special://profile/addon_data/%s/maps/windmap/' % __addonid__)
        pressuremapdir = xbmc.translatePath('special://profile/addon_data/%s/maps/pressuremap/' % __addonid__)
        lat = float(lat)
        lon = float(lon)
        x, y = GET_TILE(lat, lon, ZOOM)
        imgs = [[x-1,y-1], [x,y-1], [x+1,y-1], [x-1,y], [x,y], [x+1,y], [x-1,y+1], [x,y+1], [x+1,y+1]]
        # adjust for locations on the edge of the map
        tile_max = 2**ZOOM
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
        if streetthread_created:
            thread_street.join()
        thread_precip.join()
        thread_clouds.join()
        thread_temp.join()
        thread_wind.join()
        thread_pressure.join()
        set_property('Map.1.Area', xbmc.translatePath('special://profile/addon_data/%s/maps/streetmap-%s/streetmap.png' % (__addonid__, tag)))
        set_property('Map.2.Area', xbmc.translatePath('special://profile/addon_data/%s/maps/streetmap-%s/streetmap.png' % (__addonid__, tag)))
        set_property('Map.3.Area', xbmc.translatePath('special://profile/addon_data/%s/maps/streetmap-%s/streetmap.png' % (__addonid__, tag)))
        set_property('Map.4.Area', xbmc.translatePath('special://profile/addon_data/%s/maps/streetmap-%s/streetmap.png' % (__addonid__, tag)))
        set_property('Map.5.Area', xbmc.translatePath('special://profile/addon_data/%s/maps/streetmap-%s/streetmap.png' % (__addonid__, tag)))
        set_property('Map.1.Layer', xbmc.translatePath('special://profile/addon_data/%s/maps/precipmap/precipmap-%s.png' % (__addonid__, stamp)))
        set_property('Map.2.Layer', xbmc.translatePath('special://profile/addon_data/%s/maps/cloudsmap/cloudsmap-%s.png' % (__addonid__, stamp)))
        set_property('Map.3.Layer', xbmc.translatePath('special://profile/addon_data/%s/maps/tempmap/tempmap-%s.png' % (__addonid__, stamp)))
        set_property('Map.4.Layer', xbmc.translatePath('special://profile/addon_data/%s/maps/windmap/windmap-%s.png' % (__addonid__, stamp)))
        set_property('Map.5.Layer', xbmc.translatePath('special://profile/addon_data/%s/maps/pressuremap/pressuremap-%s.png' % (__addonid__, stamp)))
        set_property('Map.1.Heading', xbmc.getLocalizedString(1448))
        set_property('Map.2.Heading', xbmc.getLocalizedString(387))
        set_property('Map.3.Heading', xbmc.getLocalizedString(1375))
        set_property('Map.4.Heading', xbmc.getLocalizedString(383))
        set_property('Map.5.Heading', xbmc.getLocalizedString(1376))
        if 'F' in TEMPUNIT:
            set_property('Map.1.Legend' , xbmc.translatePath(os.path.join(__cwd__, 'resources', 'graphics', 'precip-in.png')))
        else:
            set_property('Map.1.Legend' , xbmc.translatePath(os.path.join(__cwd__, 'resources', 'graphics', 'precip-mm.png')))
        set_property('Map.2.Legend' , xbmc.translatePath(os.path.join(__cwd__, 'resources', 'graphics', 'clouds.png')))
        if 'F' in TEMPUNIT:
            set_property('Map.3.Legend' , xbmc.translatePath(os.path.join(__cwd__, 'resources', 'graphics', 'temp-f.png')))
        else:
            set_property('Map.3.Legend' , xbmc.translatePath(os.path.join(__cwd__, 'resources', 'graphics', 'temp-c.png')))
        if SPEEDUNIT == 'mph':
            set_property('Map.4.Legend' , xbmc.translatePath(os.path.join(__cwd__, 'resources', 'graphics', 'wind-mi.png')))
        elif SPEEDUNIT == 'Beaufort':
            set_property('Map.4.Legend' , xbmc.translatePath(os.path.join(__cwd__, 'resources', 'graphics', 'wind-bft.png')))
        else:
            set_property('Map.4.Legend' , xbmc.translatePath(os.path.join(__cwd__, 'resources', 'graphics', 'wind-kmh.png')))
        set_property('Map.5.Legend' , '')


class get_tiles(threading.Thread):
    def __init__(self, mapdir, mapfile, stamp, imgs, url):
        self.mapdir = mapdir
        self.mapfile = mapfile
        self.stamp = stamp
        self.imgs = imgs
        self.url = url
        threading.Thread.__init__(self)
 
    def run(self):
        self.fetch_tiles(self.imgs, self.mapdir)
        self.merge_tiles()

    def fetch_tiles(self, imgs, mapdir):
        count = 1
        failed = []
        for img in imgs:
            try:
                query = self.url % (ZOOM, img[0], img[1])
                req = urllib2.Request(query)
                req.add_header('Accept-encoding', 'gzip')
                response = urllib2.urlopen(req)
                if response.info().get('Content-Encoding') == 'gzip':
                    buf = StringIO(response.read())
                    compr = gzip.GzipFile(fileobj=buf)
                    data = compr.read()
                else:
                    data = response.read()
                response.close()
                log('image downloaded')
            except:
                data = ''
                log('image download failed, retry')
                if len(img) == 2:
                    img.append(str(count))
                failed.append(img)
            if data != '':
                if len(img) == 3:
                    num = img[2]
                else:
                    num = str(count)
                tilefile = xbmc.translatePath(os.path.join(mapdir, num + '.png')).decode("utf-8")
                try:
                    tmpmap = open(tilefile, 'wb')
                    tmpmap.write(data)
                    tmpmap.close()
                except:
                    log('failed to save image')
                    return
            count += 1
            if MONITOR.abortRequested():
                return
        if failed:
            xbmc.sleep(10000)
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
        if self.mapfile[0:6] == 'precip' or self.mapfile[0:6] == 'clouds':
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
    Main()
