"""
thetvdb.com Python API
(c) 2009 James Smith (http://loopj.com)
(c) 2014 Wayne Davison <wayne@opencoder.net>

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
import random
import re
import copy

import xml.parsers.expat as expat
from cStringIO import StringIO
from zipfile import ZipFile

class TheTVDB(object):
    def __init__(self, api_key='2B8557E0CBF7D720', language = 'en', want_raw = False):
        #http://thetvdb.com/api/<apikey>/<request>
        self.api_key = api_key
        self.mirror_url = "http://thetvdb.com"
        self.base_url =  self.mirror_url + "/api"
        self.base_key_url = "%s/%s" % (self.base_url, self.api_key)
        self.language = language
        self.want_raw = want_raw

        # Mirror selection got deprecated a while back, so tell it to skip the actual fetch.
        self.select_mirrors(False)


    def select_mirrors(self, do_the_fetch = True):
        #http://thetvdb.com/api/<apikey>/mirrors.xml
        url = "%s/mirrors.xml" % self.base_key_url
        self.xml_mirrors = []
        self.zip_mirrors = []
        try:
            filt_func = lambda name, attrs: attrs if name == 'Mirror' else None
            xml = self._get_xml_data(url, filt_func) if do_the_fetch else {}
            for mirror in xml.get("Mirror", []):
                mirrorpath = mirror.get("mirrorpath", None)
                typemask = mirror.get("typemask", None)
                if not mirrorpath or not typemask:
                    continue
                typemask = int(typemask)
                if typemask & 1:
                    self.xml_mirrors.append(mirrorpath)
                if typemask & 4:
                    self.zip_mirrors.append(mirrorpath)
        except:
            pass

        if not self.xml_mirrors:
            self.xml_mirrors = [ self.mirror_url ]
        if not self.zip_mirrors:
            self.zip_mirrors = [ self.mirror_url ]

        self.xml_mirror_url = random.choice(self.xml_mirrors)
        self.zip_mirror_url = random.choice(self.zip_mirrors)

        self.base_xml_url = "%s/api/%s" % (self.xml_mirror_url, self.api_key)
        self.base_zip_url = "%s/api/%s" % (self.zip_mirror_url, self.api_key)


    def _2show(self, attrs):
        return attrs


    def _2episode(self, attrs):
        return attrs


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
                    if hour == 12:
                        hour = 0
                    if gd["ampm"].lower() == "p":
                        hour += 12

                    return datetime.time(hour, int(gd["minute"]))
                elif "hour" in gd and "ampm" in gd:
                    hour = int(gd["hour"])
                    if hour == 12:
                        hour = 0
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


    # language can be "all", "en", "fr", etc.
    def get_matching_shows(self, show_name, language=None, want_raw=False):
        """Get a list of shows matching show_name."""
        if type(show_name) == type(u''):
            show_name = show_name.encode('utf-8')
        get_args = {"seriesname": show_name}
        if language is not None:
            get_args['language'] = language
        get_args = urllib.urlencode(get_args, doseq=True)
        url = "%s/GetSeries.php?%s" % (self.base_url, get_args)
        if want_raw:
            filt_func = lambda name, attrs: attrs if name == "Series" else None
        else:
            filt_func = lambda name, attrs: (attrs.get("seriesid", ""), attrs.get("SeriesName", ""), attrs.get("IMDB_ID", "")) if name == "Series" else None
        xml = self._get_xml_data(url, filt_func)
        return xml.get('Series', [])


    def get_show(self, show_id):
        """Get the show object matching this show_id."""
        url = "%s/series/%s/%s.xml" % (self.base_xml_url, show_id, self.language)
        return self._get_show_by_url(url)


    def _get_show_by_url(self, url):
        filt_func = lambda name, attrs: self._2show(attrs) if name == "Series" else None
        xml = self._get_xml_data(url, filt_func)
        return xml['Series'][0] if 'Series' in xml else None


    def get_episode(self, episode_id):
        """Get the episode object matching this episode_id."""
        url = "%s/episodes/%s" % (self.base_xml_url, episode_id)
        return self._get_episode_by_url(url)


    def _get_episode_by_url(self, url):
        filt_func = lambda name, attrs: self._2episode(attrs) if name == "Episode" else None
        xml = self._get_xml_data(url, filt_func)
        return xml['Episode'][0] if 'Episode' in xml else None


    def get_show_and_episodes(self, show_id):
        """Get the show object and all matching episode objects for this show_id."""
        url = "%s/series/%s/all/%s.zip" % (self.base_zip_url, show_id, self.language)
        zip_name = '%s.xml' % self.language
        filt_func = lambda name, attrs: self._2episode(attrs) if name == "Episode" else self._2show(attrs) if name == "Series" else None
        xml = self._get_xml_data(url, filt_func, zip_name=zip_name)
        if 'Series' not in xml:
            return None
        return (xml['Series'][0], xml.get('Episode', []))


    def get_updates(self, callback, period = "day"):
        """Return all series, episode, and banner updates w/o having to have it
        all in memory at once.  Also returns the Data timestamp.  The callback
        routine should be defined as: my_callback(name, attrs) where name will
        be "Data", "Series", "Episode", or "Banner", and attrs will be a dict
        of the values (e.g. id, time, etc)."""
        self._get_update_info(period, callback=callback)


    def _get_update_info(self, period, filter_func = None, callback = None):
        url = "%s/updates/updates_%s.zip" % (self.base_zip_url, period)
        zip_name = 'updates_%s.xml' % period
        return self._get_xml_data(url, filter_func, zip_name, callback)


    def _get_xml_data(self, url, filter_func = None, zip_name = None, callback = None):
        data = urllib.urlopen(url)
        if zip_name:
            zipfile = ZipFile(StringIO(data.read()))
            data = zipfile.open(zip_name)
        if not data:
            raise Exception("Failed to get any data")

        e = ExpatParseXml(callback, filter_func)
        e.parse(data)
        return e.xml


class ExpatParseXml(object):
    def __init__(self, callback, filter_func):
        self.el_container = None
        self.el_name = None
        self.el_attr_name = None
        self.el_attrs = None
        self.el_callback = callback if callback else self.stash_xml
        self.el_filter_func = filter_func # only used by stash_xml()
        self.xml = {}

        self.parser = expat.ParserCreate()
        self.parser.StartElementHandler = self.start_element
        self.parser.EndElementHandler = self.end_element
        self.parser.CharacterDataHandler = self.char_data

    def parse(self, fh):
        # Sadly ParseFile(fh) actually mangles the data, so we parse the file line by line:
        for line in fh:
            self.parser.Parse(line)

    def start_element(self, name, attrs):
        if not self.el_name:
            if not self.el_container:
                self.el_container = name
                self.el_callback(name, attrs)
            else:
                self.el_name = name
                self.el_attrs = {}
        elif not self.el_attr_name:
            self.el_attr_name = name

    def end_element(self, name):
        if self.el_attr_name and name == self.el_attr_name:
            self.el_attr_name = None
        elif self.el_name and name == self.el_name:
            self.el_callback(self.el_name, self.el_attrs)
            self.el_name = None
            self.el_attr_name = None

    def char_data(self, data):
        if self.el_attr_name:
            if self.el_attr_name in self.el_attrs:
                self.el_attrs[self.el_attr_name] += data
            else:
                self.el_attrs[self.el_attr_name] = data

    def stash_xml(self, name, attrs):
        if self.el_filter_func:
            attrs = self.el_filter_func(name, attrs)
            if attrs is None:
                return
        if name in self.xml:
            self.xml[name].append(attrs)
        else:
            self.xml[name] = [ attrs ]

# vim: sw=4 ts=8 et
