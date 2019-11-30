#!/usr/bin/python
# coding: utf-8

########################

from resources.lib.helper import *
from resources.lib.json_map import *
from resources.lib.functions import *

########################

class EditDialog(object):
    def __init__(self,params):
        self.params = params
        self.dbid = params.get('dbid')
        self.dbtype = params.get('type')

        self.nfo_key = []
        self.nfo_value = []

        if self.dbtype in ['movie', 'tvshow', 'season', 'episode', 'musicvideo']:
            library = 'Video'
            self.nfo_support = True
        else:
            library = 'Audio'
            self.nfo_support = False

        self.method_details = '%sLibrary.Get%sDetails' % (library, self.dbtype)
        self.param = '%sid' % self.dbtype
        self.key_details = '%sdetails' % self.dbtype
        self.properties = eval('%s_properties' % self.dbtype)

        winprop('SelectDialogPreselect', clear=True)

        self.entry_point()

    def entry_point(self):
        self.details = self.get_details()
        self.file = self.details.get('file')

        self.modeselect = []
        self.keylist = []
        self.presetlist = []
        self.typelist = []
        self.optionlist = []

        self.generate_list()
        self.editor_dialog()

    def editor_dialog(self):
        preselect = winprop('SelectDialogPreselect')
        if not preselect:
            preselect = -1

        if self.details.get('title'):
            headline = ADDON.getLocalizedString(32040) + ' "' + self.details.get('title') + '"'
        elif self.details.get('artist'):
            headline = ADDON.getLocalizedString(32040) + ' "' + self.details.get('artist') + '"'
        else:
            headline = ADDON.getLocalizedString(32000)

        self.editdialog = DIALOG.select(headline, self.modeselect, preselect=int(preselect), useDetails=True)

        # Dialog closed -> write changes to nfo and exit
        if self.editdialog == -1:
            winprop('SelectDialogPreselect', clear=True)

            if self.file and self.nfo_support:
                update_nfo(file=self.file,
                           elem=self.nfo_key,
                           value=self.nfo_value,
                           dbtype=self.dbtype,
                           dbid=self.dbid
                           )

                reload_widgets()

                exit()

        # Edit value based on the type
        winprop('SelectDialogPreselect', str(self.editdialog))

        self._handle_dbitem(value_type=self.typelist[self.editdialog],
                            dbid=self.dbid,
                            dbtype=self.dbtype,
                            key=self.keylist[self.editdialog],
                            preset=self.presetlist[self.editdialog],
                            option=self.optionlist[self.editdialog],
                            file=self.details.get('file'),
                            nfo_support=self.nfo_support
                            )

        # Return to entry_point to populate the changes in the dialog
        self.entry_point()

    def get_details(self):
        json_query = json_call(self.method_details,
                               properties=self.properties,
                               params={self.param: int(self.dbid)}
                               )
        try:
            result = json_query['result'][self.key_details]
            return result

        except KeyError:
            return

    def generate_list(self):
        details = self.details
        uniqueid = details.get('uniqueid', {})
        ratings = details.get('ratings')
        votes = details.get('votes', 0)

        if not votes or votes == -1:
            votes = 0

        # Fallback rule. Create own ratings dict if it's missing in the database.
        if not ratings:
            ratings = {'default': {'default': True,
                                   'rating': details.get('rating', 0.0),
                                   'votes': details.get('votes', 0)}
                                   }

        ratings_default = None
        for item in ratings:
            if ratings[item].get('default'):
                ratings_value = str(get_rounded_value(ratings[item].get('rating', 0.0)))
                votes_value = str(ratings[item].get('votes', '0'))
                ratings_default = ratings_value + ' / ' + votes_value + ' (' + xbmc.getLocalizedString(21870) + ': ' + item + ')'
                break

        if not ratings_default and len(ratings) > 0:
            ratings_default = ADDON.getLocalizedString(32047)

        if self.dbtype == 'movie':
            self._create_list(xbmc.getLocalizedString(369), 'title', value=details.get('title'), type='string')
            self._create_list(xbmc.getLocalizedString(20376), 'originaltitle', value=details.get('originaltitle'), type='string')
            self._create_list(xbmc.getLocalizedString(171), 'sorttitle', value=details.get('sorttitle'), type='string')
            self._create_list(xbmc.getLocalizedString(345) + ' / ' + xbmc.getLocalizedString(172), 'premiered', value=details.get('premiered'), type='date')
            self._create_list(xbmc.getLocalizedString(515), 'genre', value=get_joined_items(details.get('genre')), type='array')
            self._create_list(xbmc.getLocalizedString(202), 'tagline', value=details.get('tagline'), type='string')
            self._create_list(xbmc.getLocalizedString(207), 'plot', value=details.get('plot'), type='string')
            self._create_list(xbmc.getLocalizedString(203), 'plotoutline', value=details.get('plotoutline'), type='string')
            self._create_list(xbmc.getLocalizedString(20457), 'set', value=details.get('set'), type='string')
            self._create_list(xbmc.getLocalizedString(563) + ' / ' + xbmc.getLocalizedString(205), 'ratings', value=ratings_default, type='ratings', option=ratings)
            self._create_list(ADDON.getLocalizedString(32001), 'userrating', value=str(details.get('userrating')), type='userrating')
            self._create_list(xbmc.getLocalizedString(20074), 'mpaa', value=details.get('mpaa'), type='string')
            self._create_list(xbmc.getLocalizedString(20339), 'director', value=get_joined_items(details.get('director')), type='array')
            self._create_list(xbmc.getLocalizedString(20417), 'writer', value=get_joined_items(details.get('writer')), type='array')
            self._create_list(xbmc.getLocalizedString(21875), 'country', value=get_joined_items(details.get('country')), type='array')
            self._create_list(xbmc.getLocalizedString(572), 'studio', value=get_joined_items(details.get('studio')), type='array')
            self._create_list(xbmc.getLocalizedString(20459), 'tag', value=get_joined_items(details.get('tag')), type='array')
            self._create_list(xbmc.getLocalizedString(20410), 'trailer', value=details.get('trailer'), type='string')
            self._create_list('IMDb ID', 'uniqueid', value=uniqueid.get('imdb'), type='uniqueid', option={'type': 'imdb', 'uniqueids': uniqueid})
            self._create_list('TMDb ID', 'uniqueid', value=uniqueid.get('tmdb'), type='uniqueid', option={'type': 'tmdb', 'uniqueids': uniqueid})
            self._create_list(xbmc.getLocalizedString(13409), 'top250', value=str(details.get('top250')), type='integer')
            self._create_list(xbmc.getLocalizedString(570), 'dateadded', value=details.get('dateadded'), type='datetime')
            self._create_list(xbmc.getLocalizedString(568), 'lastplayed', value=details.get('lastplayed'), type='datetime')
            self._create_list(xbmc.getLocalizedString(567), 'playcount', value=str(details.get('playcount', 0)), type='integer')

        elif self.dbtype == 'tvshow':
            self._create_list(xbmc.getLocalizedString(369), 'title', value=details.get('title'), type='string')
            self._create_list(xbmc.getLocalizedString(20376),'originaltitle', value=details.get('originaltitle'), type='string')
            self._create_list(xbmc.getLocalizedString(171), 'sorttitle', value=details.get('sorttitle'), type='string')
            self._create_list(xbmc.getLocalizedString(345) + ' / ' + xbmc.getLocalizedString(172), 'premiered', value=details.get('premiered'), type='date')
            self._create_list(xbmc.getLocalizedString(515), 'genre', value=get_joined_items(details.get('genre')), type='array')
            self._create_list(xbmc.getLocalizedString(207), 'plot', value=details.get('plot'), type='string')
            self._create_list(xbmc.getLocalizedString(563) + ' / ' + xbmc.getLocalizedString(205), 'ratings', value=ratings_default, type='ratings', option=ratings)
            self._create_list(ADDON.getLocalizedString(32001), 'userrating', value=str(details.get('userrating')), type='userrating')
            self._create_list(xbmc.getLocalizedString(20074), 'mpaa', value=details.get('mpaa'), type='string')
            self._create_list(xbmc.getLocalizedString(572), 'studio', value=get_joined_items(details.get('studio')), type='array')
            self._create_list(xbmc.getLocalizedString(20459), 'tag', value=get_joined_items(details.get('tag')), type='array')
            self._create_list(xbmc.getLocalizedString(126), 'status', value=ADDON.getLocalizedString(32022), type='status')
            self._create_list('IMDb ID', 'uniqueid', value=uniqueid.get('imdb'), type='uniqueid', option={'type': 'imdb', 'uniqueids': uniqueid, 'episodeguide': details.get('episodeguide')})
            self._create_list('TMDb ID', 'uniqueid', value=uniqueid.get('tmdb'), type='uniqueid', option={'type': 'tmdb', 'uniqueids': uniqueid, 'episodeguide': details.get('episodeguide')})
            self._create_list('TVDb ID', 'uniqueid', value=uniqueid.get('tvdb'), type='uniqueid', option={'type': 'tvdb', 'uniqueids': uniqueid, 'episodeguide': details.get('episodeguide')})
            self._create_list('aniDB ID', 'uniqueid', value=uniqueid.get('anidb'), type='uniqueid', option={'type': 'anidb', 'uniqueids': uniqueid, 'episodeguide': details.get('episodeguide')})
            self._create_list(xbmc.getLocalizedString(570), 'dateadded', value=details.get('dateadded'), type='datetime')
            self._create_list(xbmc.getLocalizedString(568), 'lastplayed', value=details.get('lastplayed'), type='datetime')
            self._create_list(xbmc.getLocalizedString(567), 'playcount', value=str(details.get('playcount', 0)), type='integer')

        elif self.dbtype == 'episode':
            self._create_list(xbmc.getLocalizedString(369), 'title', value=details.get('title'), type='string')
            self._create_list(xbmc.getLocalizedString(20376), 'originaltitle', value=details.get('originaltitle'), type='string')
            self._create_list(xbmc.getLocalizedString(20416), 'firstaired', value=details.get('firstaired'), type='date')
            self._create_list(xbmc.getLocalizedString(207), 'plot', value=details.get('plot'), type='string')
            self._create_list(xbmc.getLocalizedString(563) + ' / ' + xbmc.getLocalizedString(205), 'ratings', value=ratings_default, type='ratings', option=ratings)
            self._create_list(ADDON.getLocalizedString(32001), 'userrating', value=str(details.get('userrating')), type='userrating')
            self._create_list(xbmc.getLocalizedString(20339), 'director', value=get_joined_items(details.get('director')), type='array')
            self._create_list(xbmc.getLocalizedString(20417), 'writer', value=get_joined_items(details.get('writer')), type='array')
            self._create_list('IMDb ID', 'uniqueid', value=uniqueid.get('imdb'), type='uniqueid', option={'type': 'imdb', 'uniqueids': uniqueid})
            self._create_list('TMDb ID', 'uniqueid', value=uniqueid.get('tmdb'), type='uniqueid', option={'type': 'tmdb', 'uniqueids': uniqueid})
            self._create_list('TVDb ID', 'uniqueid', value=uniqueid.get('tvdb'), type='uniqueid', option={'type': 'tvdb', 'uniqueids': uniqueid})
            self._create_list('aniDB ID', 'uniqueid', value=uniqueid.get('anidb'), type='uniqueid', option={'type': 'anidb', 'uniqueids': uniqueid})
            self._create_list(xbmc.getLocalizedString(570), 'dateadded', value=details.get('dateadded'), type='datetime')
            self._create_list(xbmc.getLocalizedString(568), 'lastplayed', value=details.get('lastplayed'), type='datetime')
            self._create_list(xbmc.getLocalizedString(567), 'playcount', value=str(details.get('playcount', 0)), type='integer')

        elif self.dbtype == 'musicvideo':
            self._create_list(xbmc.getLocalizedString(369), 'title', value=details.get('title'), type='string')
            self._create_list(xbmc.getLocalizedString(557), 'artist', value=get_joined_items(details.get('artist')), type='array')
            self._create_list(xbmc.getLocalizedString(558), 'album', value=details.get('album'), type='string')
            self._create_list(xbmc.getLocalizedString(345) + ' / ' + xbmc.getLocalizedString(172), 'premiered', value=details.get('premiered'), type='date')
            self._create_list(xbmc.getLocalizedString(554), 'track', value=str(details.get('track')), type='integer')
            self._create_list(xbmc.getLocalizedString(207), 'plot', value=details.get('plot'), type='string')
            self._create_list(xbmc.getLocalizedString(515), 'genre', value=get_joined_items(details.get('genre')), type='array')
            self._create_list(xbmc.getLocalizedString(20339), 'director', value=get_joined_items(details.get('director')), type='array')
            self._create_list(xbmc.getLocalizedString(572), 'studio', value=get_joined_items(details.get('studio')), type='array')
            self._create_list(xbmc.getLocalizedString(563), 'rating', value=str(get_rounded_value(details.get('rating'))), type='float')
            self._create_list(ADDON.getLocalizedString(32001), 'userrating', value=details.get('userrating'), type='userrating')
            self._create_list(xbmc.getLocalizedString(20459), 'tag', value=get_joined_items(details.get('tag')), type='array')
            self._create_list(xbmc.getLocalizedString(570), 'dateadded', value=details.get('dateadded'), type='datetime')
            self._create_list(xbmc.getLocalizedString(568), 'lastplayed', value=details.get('lastplayed'), type='datetime')
            self._create_list(xbmc.getLocalizedString(567), 'playcount', value=str(details.get('playcount', 0)), type='integer')

        elif self.dbtype == 'artist':
            self._create_list(xbmc.getLocalizedString(515), 'genre', value=get_joined_items(details.get('genre')), type='array')
            self._create_list(xbmc.getLocalizedString(21821), 'description', value=details.get('description'), type='string')
            self._create_list(xbmc.getLocalizedString(39026), 'disambiguation', value=details.get('disambiguation'), type='string')
            self._create_list(xbmc.getLocalizedString(736), 'style', value=get_joined_items(details.get('style')), type='array')
            self._create_list(xbmc.getLocalizedString(175), 'mood', value=get_joined_items(details.get('mood')), type='array')
            self._create_list(xbmc.getLocalizedString(21892), 'instrument', value=get_joined_items(details.get('instrument')), type='array')
            self._create_list(xbmc.getLocalizedString(21893), 'born', value=details.get('born'), type='string')
            self._create_list(xbmc.getLocalizedString(21897), 'died', value=details.get('died'), type='string')
            self._create_list(xbmc.getLocalizedString(21894), 'formed', value=details.get('formed'), type='string')
            self._create_list(xbmc.getLocalizedString(21896), 'disbanded', value=details.get('disbanded'), type='string')
            self._create_list(xbmc.getLocalizedString(21898), 'yearsactive', value=get_joined_items(details.get('yearsactive')), type='array')

        elif self.dbtype == 'album':
            self._create_list(ADDON.getLocalizedString(32023), 'albumlabel', value=details.get('albumlabel'), type='string')
            self._create_list(xbmc.getLocalizedString(21821), 'description', value=details.get('description'), type='string')
            self._create_list(xbmc.getLocalizedString(345), 'year', value=str(details.get('year')), type='integer')
            self._create_list(xbmc.getLocalizedString(467), 'type', value=details.get('type'), type='string')
            self._create_list(xbmc.getLocalizedString(515), 'genre', value=get_joined_items(details.get('genre')), type='array')
            self._create_list(xbmc.getLocalizedString(15111), 'theme', value=get_joined_items(details.get('theme')), type='array')
            self._create_list(xbmc.getLocalizedString(175), 'mood', value=get_joined_items(details.get('mood')), type='array')
            self._create_list(xbmc.getLocalizedString(736), 'style', value=get_joined_items(details.get('style')), type='array')
            self._create_list(xbmc.getLocalizedString(563), 'rating', value=str(get_rounded_value(details.get('rating'))), type='float')
            self._create_list(xbmc.getLocalizedString(205), 'votes', value=str(votes), type='integer')
            self._create_list(ADDON.getLocalizedString(32001), 'userrating', value=str(details.get('userrating')), type='userrating')

        elif self.dbtype == 'song':
            self._create_list(xbmc.getLocalizedString(563), 'rating', value=str(get_rounded_value(details.get('rating'))), type='float')
            #self._create_list(xbmc.getLocalizedString(205), 'votes', value=str(details.get('votes')), type='integer') not available in methods.json? DaveBlake will fix it.
            self._create_list(ADDON.getLocalizedString(32001), 'userrating', value=str(details.get('userrating')), type='userrating')
            self._create_list(xbmc.getLocalizedString(568), 'lastplayed', value=details.get('lastplayed'), type='datetime')
            self._create_list(xbmc.getLocalizedString(567), 'playcount', value=str(details.get('playcount', 0)), type='integer')

    def _create_list(self,label,key,type,value,option=None):
        if type in ['uniqueid', 'status']:
            icon = 'string'
        elif type == ('userrating'):
            icon = 'integer'
        elif type.startswith('date'):
            icon = 'date'
        elif type.startswith('rating'):
            icon = 'float'
        else:
            icon = type

        li_item = xbmcgui.ListItem(label=label, label2='n/a' if not value else value)
        li_item.setArt({'icon': 'special://home/addons/script.metadata.editor/resources/media/icon_%s.png' % icon})

        self.modeselect.append(li_item)
        self.keylist.append(key)
        self.typelist.append(type)
        self.optionlist.append(option)
        self.presetlist.append('' if not value else value)

    def _handle_dbitem(self,value_type,dbid,dbtype,key,preset,option,file,nfo_support):
        preset = preset.replace('n/a','')
        nfo_key = None
        nfo_value = None

        if value_type == 'array':
            value = set_array(preset, dbid, dbtype, key)

        elif value_type == 'string':
            value = set_string(preset)

        elif value_type == 'integer':
            value = set_integer(preset)

        elif value_type == 'float':
            value = set_float(preset)

        elif value_type == 'date':
            value = set_date(preset)

        elif value_type == 'datetime':
            preset = preset.split(' ') if preset else ['', '']
            date = set_date(preset[0])
            time = set_time(preset[1][:-3])
            value = date + ' ' + time + ':00'

        elif value_type == 'userrating':
            value = set_integer_range(preset, 11)

        elif value_type == 'ratings':
            value = set_ratings(option)

        elif value_type == 'status':
            value = set_status(preset)

        elif value_type == ('uniqueid'):
            returned_value = set_string(preset)
            returned_value_json = returned_value if returned_value else None
            returned_value_str = returned_value if returned_value else ''

            uniqueid_key = option.get('type')
            uniqueids = option.get('uniqueids')

            value = {uniqueid_key: returned_value_json}

            # build nfo info
            updated_dict = {}
            for item in uniqueids:
                if item == uniqueid_key:
                    updated_dict[item] = returned_value_json
                else:
                    updated_dict[item] = uniqueids.get(item)

            if uniqueid_key not in updated_dict:
                updated_dict[uniqueid_key] = returned_value_str

            nfo_value = [updated_dict, option.get('episodeguide')]

        update_library(dbtype, key, value, dbid)

        if nfo_support and file:
            self.nfo_key.append(nfo_key if nfo_key else key)
            self.nfo_value.append(nfo_value if nfo_value else value)