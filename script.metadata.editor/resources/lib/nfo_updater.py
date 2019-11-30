#!/usr/bin/python
# coding: utf-8

########################

from resources.lib.helper import *

########################

class UpdateNFO():
    def __init__(self,file,elem,value,dbtype,dbid):
        self.elems = elem
        self.values = value
        self.targetfile = file
        self.dbtype = dbtype
        self.dbid = dbid

        if not isinstance(self.elems, list):
            self.elems = [self.elems]
            self.values = [self.values]

        self.run()

    def run(self):
        with busy_dialog():
            try:
                if xbmcvfs.exists(self.targetfile):
                    self.root = self.read_file()

                    if len(self.root):
                        index = 0
                        for elem in self.elems:
                            self.elem = elem
                            self.value = self.values[index]
                            self.update_elem()
                            index += 1

                        self.write_file()

            except Exception as error:
                log('Cannot find/access .nfo file for updating: %s' % error)

    def update_elem(self):
        if self.elem == 'ratings':
            self.handle_ratings()

        elif self.elem == 'uniqueid':
            self.handle_uniqueid()

        else:
            ''' Key conversion/cleanup if nfo element has a different naming.
                If Emby is using different elements, key + value will be
                converted to a list to cover both.
            '''
            if self.elem == 'plotoutline':
                self.elem = 'outline'

            elif self.elem == 'writer':
                self.elem = ['writer', 'credits']
                self.value = [self.value, self.value]

            elif self.elem == 'premiered':
                self.elem = ['premiered', 'year']
                self.value = [self.value, self.value[:4]]

            elif self.elem == 'firstaired':
                self.elem = 'aired'

            self.handle_elem()

    def read_file(self):
        file = xbmcvfs.File(self.targetfile)
        content = file.read()
        file.close()

        if content:
            tree = ET.ElementTree(ET.fromstring(content))
            root = tree.getroot()
            return root

    def handle_elem(self):
        if not isinstance(self.elem, list):
            self.elem = [self.elem]
            self.value = [self.value]

        index = 0
        for elem_item in self.elem:
            for elem in self.root.findall(elem_item):
                self.root.remove(elem)

            if isinstance(self.value[index], list):
                for item in self.value[index]:
                    elem = ET.SubElement(self.root, elem_item)
                    if item:
                        elem.text = decode_string(item)

            else:
                elem = ET.SubElement(self.root, elem_item)
                if self.value[index]:
                    value = self.value[index]
                    elem.text = decode_string(value)

            index += 1

    def handle_ratings(self):
        for elem in self.root.findall('ratings'):
            self.root.remove(elem)

        elem = ET.SubElement(self.root, 'ratings')
        for item in self.value:
            rating = float(self.value[item].get('rating', 0.0))
            rating = str(round(rating, 1))
            votes = str(self.value[item].get('votes', 0))

            subelem = ET.SubElement(elem, 'rating')
            subelem.set('name', item)
            subelem.set('max', '10')

            if self.value[item].get('default'):
                subelem.set('default', 'true')

                # <votes>, <rating>
                for key in ['rating', 'votes']:
                    for defaultelem in self.root.findall(key):
                        self.root.remove(defaultelem)

                    defaultelem = ET.SubElement(self.root, key)
                    defaultelem.text = eval(key)

            else:
                subelem.set('default', 'false')

            rating_elem = ET.SubElement(subelem, 'value')
            rating_elem.text = rating

            votes_elem = ET.SubElement(subelem, 'votes')
            votes_elem.text = votes

            # Emby <criticrating> Rotten ratings
            if item == 'tomatometerallcritics':
                normalized_rating = int(float(rating) * 10)
                if normalized_rating > 100:
                    normalized_rating = ''

                for emby_elem in self.root.findall('criticrating'):
                    self.root.remove(emby_elem)

                emby_rotten = ET.SubElement(self.root, 'criticrating')
                emby_rotten.text = str(normalized_rating)

    def handle_uniqueid(self):
        uniqueids = self.value[0]
        episodeguide = str(self.value[1])
        default = ''

        # find default uniqueid
        if 'tvdb' in episodeguide:
            default = 'tvdb'
        elif 'tmdb' in episodeguide:
            default = 'tmdb'
        else:
            for elem in self.root.findall('uniqueid'):
                if elem.get('default'):
                    default = elem.get('type')
                    break

        # set fallback default uniqueid
        if not default:
            if self.dbtype == 'movie':
                if uniqueids.get('tmdb'):
                    default = 'tmdb'
                elif uniqueids.get('imdb'):
                    default = 'imdb'

            elif self.dbtype == 'tvshow':
                scraper_default = ADDON.getSetting('tv_scraper_base')

                if (scraper_default == 'TVDb' and uniqueids.get('tvdb')):
                    default = 'tvdb'
                elif scraper_default == 'TMDb' and uniqueids.get('tmdb'):
                    default = 'tmdb'

        # <uniqueid> fields
        for elem in self.root.findall('uniqueid'):
            self.root.remove(elem)

        for item in uniqueids:
            value = uniqueids.get(item, '')

            elem = ET.SubElement(self.root, self.elem)
            elem.set('type', item)
            elem.text = value

            if default == item:
                elem.set('default', 'true')
                self._set_episodeguide(item, value)

        # Emby <imdbid>, <tmdbid>, etc.
        for item in uniqueids:
            elem_name = item + 'id'

            for elem in self.root.findall(elem_name):
                self.root.remove(elem)

            if value:
                elem = ET.SubElement(self.root, elem_name)
                elem.text = uniqueids.get(item, '')

    def write_file(self):
        xml_prettyprint(self.root)
        content = ET.tostring(self.root, encoding='UTF-8')

        file = xbmcvfs.File(self.targetfile, 'w')
        file.write(content)
        file.close()

    def _set_episodeguide(self,type,value):
        if not self.dbtype == 'tvshow':
            return

        post = False
        cache = ''

        if type == 'tvdb':
            post = 'yes'
            cache = 'auth.json'
            url = 'https://api.thetvdb.com/login?{"apikey":"439DFEBA9D3059C6","id":%s}|Content-Type=application/json' % str(value)
            json_value = '<episodeguide><url post="%s" cache="%s"><url>%s</url></episodeguide>' % (post, cache, url)

        elif type == 'tmdb':
            language = ADDON.getSetting('tmdb_language')
            cache = 'tmdb-%s-%s.json' % (str(value), language)
            url = 'http://api.themoviedb.org/3/tv/%s?api_key=6a5be4999abf74eba1f9a8311294c267&amp;language=%s' % (str(value), language)
            json_value = '<episodeguide><url cache="%s"><url>%s</url></episodeguide>' % (cache, url)

        else:
            url = ''
            json_value = '<episodeguide><url cache=""><url></url></episodeguide>'

        for elem in self.root.findall('episodeguide'):
            self.root.remove(elem)

        episodeguide_elem = ET.SubElement(self.root, 'episodeguide')
        url_elem = ET.SubElement(episodeguide_elem, 'url')
        if post:
            url_elem.set('post', post)
        url_elem.set('cache', cache)
        url_elem.text = url

        json_call('VideoLibrary.SetTVShowDetails',
                  params={'episodeguide': json_value, 'tvshowid': int(self.dbid)},
                  debug=LOG_JSON
                  )