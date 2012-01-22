#import libraries
from resources.lib.script_exceptions import NoFanartError
from resources.lib.utils import _log as log
from resources.lib.utils import _get_xml as get_xml
from elementtree import ElementTree as ET

class TVDBProvider():
    """
    Setup provider for TheTVDB.com
    """
    def __init__(self):
        self.name = 'TVDB'
        self.api_key = '1A41A145E2DA0053'
        self.url = 'http://www.thetvdb.com/api/%s/series/%s/banners.xml'
        self.url_prefix = 'http://www.thetvdb.com/banners/'

    def get_image_list(self, media_id):
        xml_url = self.url % (self.api_key, media_id)
        log('API:               %s ' % xml_url)
        image_list = []
        data = get_xml(xml_url)
        tree = ET.fromstring(data)
        for image in tree.findall('Banner'):
            info = {}
            if image.findtext('BannerPath'):
                info['url'] = self.url_prefix + image.findtext('BannerPath')
                if image.findtext('ThumbnailPath'):
                    info['preview'] = self.url_prefix + image.findtext('ThumbnailPath')
                else:
                    info['preview'] = self.url_prefix + image.findtext('BannerPath')
                info['language'] = image.findtext('Language')
                info['id'] = image.findtext('id')
                # process fanarts
                if image.findtext('BannerType') == 'fanart':
                    info['type'] = ['fanart','extrafanart']
                # process posters
                elif image.findtext('BannerType') == 'poster':
                    info['type'] = ['poster']
                # process banners
                elif image.findtext('BannerType') == 'series' and image.findtext('BannerType2') == 'graphical':
                    info['type'] = ['banner']
                # process seasonposters
                elif image.findtext('BannerType') == 'season' and image.findtext('BannerType2') == 'season':
                    info['type'] = ['seasonposter']
                # process seasonbanners
                elif image.findtext('BannerType') == 'season' and image.findtext('BannerType2') == 'seasonwide':
                    info['type'] = ['seasonbanner']
                else:
                    info['type'] = ['']
                # convert image size ...x... in Bannertype2
                if image.findtext('BannerType2'):
                    try:
                        x,y = image.findtext('BannerType2').split('x')
                        info['width'] = int(x)
                        info['height'] = int(y)
                    except:
                        info['type2'] = image.findtext('BannerType2')

                # check if fanart has text
                info['series_name'] = image.findtext('SeriesName') == 'true'

                # find image ratings
                if int(image.findtext('RatingCount')) >= 1:
                    info['rating'] = float( "%.1f" % float( image.findtext('Rating')) ) #output string with one decimal
                    info['votes'] = image.findtext('RatingCount')
                else:
                    info['rating'] = 'n/a'
                    info['votes'] = 'n/a'

                # find season info
                if image.findtext('Season') != '':
                    info['season'] = image.findtext('Season')
                # Create Gui string to display
                info['generalinfo'] = 'Language: %s  |  Rating: %s  |  Votes: %s  |  ' %( info['language'], info['rating'], info['votes'] )
                if 'season'in info:
                    info['generalinfo'] += 'Season: %s  |  ' %( info['season'] )
                if 'height' in info:
                    info['generalinfo'] += 'Size: %sx%s  |  ' %( info['height'], info['width'] )

            if info:
                image_list.append(info)
        if image_list == []:
            raise NoFanartError(media_id)
        else:
            return image_list
