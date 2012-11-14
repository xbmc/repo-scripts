"""
thetvdb.com Python API
(c) 2009 James Smith (http://loopj.com)

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import urllib
import datetime
import re
import copy

import elementtree.ElementTree as ET
#from elementtree.ElementTree import ElementTree as ET

class TheTVDB(object):
    def __init__(self, api_key='2B8557E0CBF7D720'):
        #http://www.thetvdb.com/api/GetEpisodeByAirDate.php?apikey=1D62F2F90030C444&seriesid=71256&airdate=2010-03-29
        self.api_key = api_key
        self.mirror_url = "http://www.thetvdb.com"
        self.base_url =  self.mirror_url + "/api"
        self.base_key_url = "%s/%s" % (self.base_url, self.api_key)
        
    class Show(object):
        """A python object representing a thetvdb.com show record."""
        def __init__(self, node, mirror_url):
            # Main show details
            #print node
            self.id = node.findtext("id")
            self.name = node.findtext("SeriesName")
            self.overview = node.findtext("Overview")
            self.genre = node.findtext("Genre") #[g for g in node.findtext("Genre").split("|") if g]
            self.actors = [a for a in node.findtext("Actors").split("|") if a]
            self.network = node.findtext("Network")
            self.content_rating = node.findtext("ContentRating")
            self.rating = node.findtext("Rating")
            self.runtime = node.findtext("Runtime")
            self.status = node.findtext("Status")
            self.language = node.findtext("Language")
        
            # Air details
            self.first_aired = TheTVDB.convert_date(node.findtext("FirstAired"))
            self.airs_day = node.findtext("Airs_DayOfWeek")
            self.airs_time = node.findtext("Airs_Time")#TheTVDB.convert_time(node.findtext("Airs_Time"))
        
            # Main show artwork
            temp = node.findtext("banner")
            if temp != '' and temp is not None:
                self.banner_url = "%s/banners/%s" % (mirror_url, temp)
            else:
                self.banner_url = ''
            temp = node.findtext("poster")
            if temp != '' and temp is not None:
                self.poster_url = "%s/banners/%s" % (mirror_url, temp)
            else:
                self.poster_url = ''
            temp = node.findtext("fanart")
            if temp != '' and temp is not None:
                self.fanart_url = "%s/banners/%s" % (mirror_url, temp)
            else:
                self.fanart_url = ''

            # External references
            self.imdb_id = node.findtext("IMDB_ID")
            self.tvcom_id = node.findtext("SeriesID")
            self.zap2it_id = node.findtext("zap2it_id")

            # When this show was last updated
            self.last_updated = datetime.datetime.fromtimestamp(int(node.findtext("lastupdated")))
        
        def __str__(self):
            import pprint
            return pprint.saferepr(self)

    class Episode(object):
        """A python object representing a thetvdb.com episode record."""
        def __init__(self, node, mirror_url):
            self.id = node.findtext("id")
            self.show_id = node.findtext("seriesid")
            self.name = node.findtext("EpisodeName")
            self.overview = node.findtext("Overview")
            self.season_number = node.findtext("SeasonNumber")
            self.episode_number = node.findtext("EpisodeNumber")
            self.director = node.findtext("Director")
            self.guest_stars = node.findtext("GuestStars")
            self.language = node.findtext("Language")
            self.production_code = node.findtext("ProductionCode")
            self.rating = node.findtext("Rating")
            self.writer = node.findtext("Writer")

            # Air date
            self.first_aired = node.findtext("FirstAired")#TheTVDB.convert_date(node.findtext("FirstAired"))
            
            # DVD Information
            self.dvd_chapter = node.findtext("DVD_chapter")
            self.dvd_disc_id = node.findtext("DVD_discid")
            self.dvd_episode_number = node.findtext("DVD_episodenumber")
            self.dvd_season = node.findtext("DVD_season")

            # Artwork/screenshot
            temp = node.findtext("filename")
            if temp != '' and temp is not None:
                self.image = "%s/banners/%s" % (mirror_url, temp)
            else:
                self.image = ''
            #self.image = 'http://thetvdb.com/banners/' + node.findtext("filename")

            # Episode ordering information (normally for specials)
            self.airs_after_season = node.findtext("airsafter_season")
            self.airs_before_season = node.findtext("airsbefore_season")
            self.airs_before_episode = node.findtext("airsbefore_episode")

            # Unknown
            self.combined_episode_number = node.findtext("combined_episode_number")
            self.combined_season = node.findtext("combined_season")
            self.absolute_number = node.findtext("absolute_number")
            self.season_id = node.findtext("seasonid")
            self.ep_img_flag = node.findtext("EpImgFlag")

            # External references
            self.imdb_id = node.findtext("IMDB_ID")

            # When this episode was last updated
            self.last_updated = datetime.datetime.fromtimestamp(int(self.check(node.findtext("lastupdated"), '0')))

        def __str__(self):
            return repr(self)

        def check(self, value, ret=None):
            if value is None or value == '':
                if ret == None:
                    return ''
                else:
                    return ret
            else:
                return value

    @staticmethod
    def convert_time(time_string):
        """Convert a thetvdb time string into a datetime.time object."""
        time_res = [re.compile(r"\D*(?P<hour>\d{1,2})(?::(?P<minute>\d{2}))?.*(?P<ampm>a|p)m.*", re.IGNORECASE), # 12 hour
                    re.compile(r"\D*(?P<hour>\d{1,2}):?(?P<minute>\d{2}).*")]                                     # 24 hour

        for r in time_res:
            m = r.match(time_string)
            if m:
                gd = m.groupdict()

                if "hour" in gd and "minute" in gd and gd["minute"] and "ampm" in gd:
                    hour = int(gd["hour"])
                    if gd["ampm"].lower() == "p":
                        hour += 12

                    return datetime.time(hour, int(gd["minute"]))
                elif "hour" in gd and "ampm" in gd:
                    hour = int(gd["hour"])
                    if gd["ampm"].lower() == "p":
                        hour += 12

                    return datetime.time(hour, 0)
                elif "hour" in gd and "minute" in gd:
                    return datetime.time(int(gd["hour"]), int(gd["minute"]))

        return None

    @staticmethod
    def convert_date(date_string):
        """Convert a thetvdb date string into a datetime.date object."""
        first_aired = None
        try:
            first_aired = datetime.date(*map(int, date_string.split("-")))
        except ValueError:
            pass

        return first_aired

    def get_matching_shows(self, show_name):
        """Get a list of shows matching show_name."""
        get_args = urllib.urlencode({"seriesname": show_name}, doseq=True)
        url = "%s/GetSeries.php?%s" % (self.base_url, get_args)
        print url
        data = urllib.urlopen(url)
        show_list = []
        print url
        if data:
            try:
                tree = ET.parse(data)
                show_list = [(show.findtext("seriesid"), show.findtext("SeriesName"),show.findtext("IMDB_ID")) for show in tree.getiterator("Series")]
            except SyntaxError:
                pass

        return show_list

    def get_show(self, show_id):
        """Get the show object matching this show_id."""
        #url = "%s/series/%s/%s.xml" % (self.base_key_url, show_id, "el")
        url = "%s/series/%s/" % (self.base_key_url, show_id)
        data = urllib.urlopen(url)
        temp = urllib.urlopen(url)
        temp_data = str(temp.read())
        print 'data returned from TheTVDB ' + temp_data
        show = None
        if temp_data.startswith('<?xml') == False:
            return show
        try:
            tree = ET.parse(data)
            show_node = tree.find("Series")
        
            show = TheTVDB.Show(show_node, self.mirror_url)
        except SyntaxError:
            pass
        
        return show


    def get_show_by_imdb(self, imdb_id):
        """Get the show object matching this show_id."""
        #url = "%s/series/%s/%s.xml" % (self.base_key_url, show_id, "el")
        url = "%s/GetSeriesByRemoteID.php?imdbid=%s" % (self.base_url, imdb_id)
        data = urllib.urlopen(url)
        temp = urllib.urlopen(url)
        temp_data = str(temp.read())
        print 'data returned from TheTVDB ' + temp_data
        tvdb_id = ''
        if temp_data.startswith('<?xml') == False:
            return tvdb_id
        try:
            tree = ET.parse(data)
            for show in tree.getiterator("Series"):
                tvdb_id = show.findtext("seriesid")
                
        except SyntaxError:
            pass
        
        return tvdb_id

    def get_episode(self, episode_id):
        """Get the episode object matching this episode_id."""
        url = "%s/episodes/%s" % (self.base_key_url, episode_id)
        data = urllib.urlopen(url)
        print url
        episode = None
        try:
            tree = ET.parse(data)
            episode_node = tree.find("Episode")

            episode = TheTVDB.Episode(episode_node, self.mirror_url)
        except SyntaxError:
            pass
        
        return episode


    def get_episode_by_airdate(self, show_id, aired):
        """Get the episode object matching this episode_id."""
        #url = "%s/series/%s/default/%s/%s" % (self.base_key_url, show_id, season_num, ep_num)
        '''http://www.thetvdb.com/api/GetEpisodeByAirDate.php?apikey=1D62F2F90030C444&seriesid=71256&airdate=2010-03-29'''
        
        url = "%s/GetEpisodeByAirDate.php?apikey=1D62F2F90030C444&seriesid=%s&airdate=%s" % (self.base_url, show_id, aired)
        data = urllib.urlopen(url)
        
        print url
        episode = None
        
        #code to check if data has been returned
        temp_data = str(data.read())
        print 'data returned from TheTVDB ' + temp_data
        if temp_data.startswith('<?xml') == False:
            print 'No data returned ', temp_data
            return episode
        
        data = urllib.urlopen(url)
        try:
            tree = ET.parse(data)
            episode_node = tree.find("Episode")

            episode = TheTVDB.Episode(episode_node, self.mirror_url)
            
        except SyntaxError:
            pass
        
        return episode
  

    def get_episode_by_season_ep(self, show_id, season_num, ep_num):
        """Get the episode object matching this episode_id."""
        url = "%s/series/%s/default/%s/%s" % (self.base_key_url, show_id, season_num, ep_num)
        data = urllib.urlopen(url)
        
        episode = None
        print url
        
        #code to check if data has been returned
        temp_data = str(data.read())
        if temp_data.startswith('<?xml') == False :
            print 'No data returned ', temp_data
            return episode
        
        data = urllib.urlopen(url)
        try:
            tree = ET.parse(data)
            episode_node = tree.find("Episode")

            episode = TheTVDB.Episode(episode_node, self.mirror_url)
        except SyntaxError:
            pass
        
        return episode
   
    def get_show_and_episodes(self, show_id):
        """Get the show object and all matching episode objects for this show_id."""
        url = "%s/series/%s/all/" % (self.base_key_url, show_id)
        data = urllib.urlopen(url)
        
        show_and_episodes = None
        try:
            tree = ET.parse(data)
            show_node = tree.find("Series")
        
            show = TheTVDB.Show(show_node, self.mirror_url)
            episodes = []
        
            episode_nodes = tree.getiterator("Episode")
            for episode_node in episode_nodes:
                episodes.append(TheTVDB.Episode(episode_node, self.mirror_url))
        
            show_and_episodes = (show, episodes)
        except SyntaxError:
            pass
        
        return show_and_episodes

    def get_updated_shows(self, period = "day"):
        """Get a list of show ids which have been updated within this period."""
        url = "%s/updates/updates_%s.xml" % (self.base_key_url, period)
        data = urllib.urlopen(url)
        tree = ET.parse(data)

        series_nodes = tree.getiterator("Series")

        return [x.findtext("id") for x in series_nodes]

    def get_updated_episodes(self, period = "day"):
        """Get a list of episode ids which have been updated within this period."""
        url = "%s/updates/updates_%s.xml" % (self.base_key_url, period)
        data = urllib.urlopen(url)
        tree = ET.parse(data)

        episode_nodes = tree.getiterator("Episode")

        return [(x.findtext("Series"), x.findtext("id")) for x in episode_nodes]

    def get_show_image_choices(self, show_id):
        """Get a list of image urls and types relating to this show."""
        url = "%s/series/%s/banners.xml" % (self.base_key_url, show_id)
        data = urllib.urlopen(url)
        tree = ET.parse(data)
        print url
        
        images = []

        banner_data = tree.find("Banners")
        banner_nodes = tree.getiterator("Banner")
        for banner in banner_nodes:
            banner_path = banner.findtext("BannerPath")
            banner_type = banner.findtext("BannerType")
            if banner_type == 'season':
                banner_season = banner.findtext("Season")
            else:
                banner_season = ''
            banner_url = "%s/banners/%s" % (self.mirror_url, banner_path)

            images.append((banner_url, banner_type, banner_season))

        return images