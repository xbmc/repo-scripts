'''
    common XBMC Module
    Copyright (C) 2011 t0mm0

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

import cgi
import re
import os
try:
   import cPickle as pickle
except:
   import pickle
import unicodedata
import urllib
import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
    
class Addon:
    '''
    This class provides a lot of code that is used across many XBMC addons
    in the hope that it will simplify some of the common tasks an addon needs
    to perform.
    
    Mostly this is achieved by providing a wrapper around commonly used parts
    of :mod:`xbmc`, :mod:`xbmcaddon`, :mod:`xbmcgui` and :mod:`xbmcplugin`. 
    
    You probably want to have exactly one instance of this class in your addon
    which you can call from anywhere in your code.
    
    Example::
        
        import sys
        from t0mm0.common.addon import Addon
        addon = Addon('my.plugin.id', argv=sys.argv)
    '''
    
        
    def __init__(self, addon_id, argv=None):
        '''        
        Args:
            addon_id (str): Your addon's id (eg. 'plugin.video.t0mm0.test').
            
        Kwargs:
            argv (list): List of arguments passed to your addon if applicable
            (eg. sys.argv).
        '''
        self.addon = xbmcaddon.Addon(id=addon_id)
        if argv:
            self.url = argv[0]
            self.handle = int(argv[1])
            self.queries = self.parse_query(argv[2][1:])
        

    def get_author(self):
        '''Returns the addon author as defined in ``addon.xml``.'''
        return self.addon.getAddonInfo('author')
            

    def get_changelog(self):    
        '''Returns the addon changelog.'''
        return self.addon.getAddonInfo('changelog')
            

    def get_description(self):
        '''Returns the addon description as defined in ``addon.xml``.'''
        return self.addon.getAddonInfo('description')
            

    def get_disclaimer(self):    
        '''Returns the addon disclaimer as defined in ``addon.xml``.'''
        return self.addon.getAddonInfo('disclaimer')
            

    def get_fanart(self):
        '''Returns the full path to the addon fanart.'''
        return self.addon.getAddonInfo('fanart')
            

    def get_icon(self):
        '''Returns the full path to the addon icon.'''
        return self.addon.getAddonInfo('icon')
            

    def get_id(self):
        '''Returns the addon id as defined in ``addon.xml``.'''
        return self.addon.getAddonInfo('id')
            

    def get_name(self):    
        '''Returns the addon name as defined in ``addon.xml``.'''
        return self.addon.getAddonInfo('name')
            

    def get_path(self):
        '''Returns the full path to the addon directory.'''
        return self.addon.getAddonInfo('path')
            

    def get_profile(self):    
        '''
        Returns the full path to the addon profile directory 
        (useful for storing files needed by the addon such as cookies).
        '''
        return xbmc.translatePath(self.addon.getAddonInfo('profile'))
            

    def get_stars(self):    
        '''Returns the number of stars for this addon.'''
        return self.addon.getAddonInfo('stars')
            

    def get_summary(self):    
        '''Returns the addon summary as defined in ``addon.xml``.'''
        return self.addon.getAddonInfo('summary')
            

    def get_type(self): 
        '''
        Returns the addon summary as defined in ``addon.xml`` 
        (eg. xbmc.python.pluginsource).
        '''   
        return self.addon.getAddonInfo('type')
            

    def get_version(self):    
        '''Returns the addon version as defined in ``addon.xml``.'''
        return self.addon.getAddonInfo('version')
            

    def get_setting(self, setting):
        '''
        Returns an addon setting. Settings must be defined in your addon's
        ``resources/settings.xml`` file.
        
        Args:
            setting (str): Name of the setting to be retrieved.
            
        Returns:
            str containing the requested setting.
        '''
        return self.addon.getSetting(setting)
        

    def get_string(self, string_id):
        '''
        Returns a localized string. Strings must be defined in your addon's
        ``resources/language/[lang_name]/strings.xml`` file.
        
        Args:
            string_id (int): id of the translated string to retrieve.
            
        Returns:
            str containing the localized requested string.
        '''
        return self.addon.getLocalizedString(string_id)   


    def parse_query(self, query, defaults={'mode': 'main'}):
        '''
        Parse a query string as used in a URL or passed to your addon by XBMC.
        
        Example:
         
        >>> addon.parse_query('name=test&type=basic')
        {'mode': 'main', 'name': 'test', 'type': 'basic'} 
            
        Args:
            query (str): A query string.
            
        Kwargs:
            defaults (dict): A dictionary containing key/value pairs parsed 
            from the query string. If a key is repeated in the query string
            its value will be a list containing all of that keys values.  
        '''
        queries = cgi.parse_qs(query)
        q = defaults
        for key, value in queries.items():
            if len(value) == 1:
                q[key] = value[0]
            else:
                q[key] = value
        return q


    def build_plugin_url(self, queries):
        '''
        Returns a ``plugin://`` URL which can be used to call the addon with 
        the specified queries.
        
        Example:
        
        >>> addon.build_plugin_url({'name': 'test', 'type': 'basic'})
        'plugin://your.plugin.id/?name=test&type=basic'
        
        
        Args:
            queries (dict): A dctionary of keys/values to be added to the 
            ``plugin://`` URL.
            
        Retuns:
            A string containing a fully formed ``plugin://`` URL.
        '''
        out_dict = {}
        for k, v in queries.iteritems():
            if isinstance(v, unicode):
                v = v.encode('utf8')
            elif isinstance(v, str):
                # Must be encoded in UTF-8
                v.decode('utf8')
            out_dict[k] = v
        return self.url + '?' + urllib.urlencode(out_dict)


    def log(self, msg, level=xbmc.LOGNOTICE):
        '''
        Writes a string to the XBMC log file. The addon name is inserted into 
        the beginning of the message automatically to help you find relevent 
        messages in the log file.
        
        The available log levels are defined in the :mod:`xbmc` module and are
        currently as follows::
        
            xbmc.LOGDEBUG = 0
            xbmc.LOGERROR = 4
            xbmc.LOGFATAL = 6
            xbmc.LOGINFO = 1
            xbmc.LOGNONE = 7
            xbmc.LOGNOTICE = 2
            xbmc.LOGSEVERE = 5
            xbmc.LOGWARNING = 3
        
        Args:
            msg (str or unicode): The message to be written to the log file.
        
        Kwargs:
            level (int): The XBMC log level to write at.
        '''
        #msg = unicodedata.normalize('NFKD', unicode(msg)).encode('ascii',
        #                                                         'ignore')
        xbmc.log('%s: %s' % (self.get_name(), msg), level)
        

    def log_error(self, msg):
        '''
        Convenience method to write to the XBMC log file at the 
        ``xbmc.LOGERROR`` error level. Use when something has gone wrong in
        your addon code. This will show up in the log prefixed with 'ERROR:'
        whether you have debugging switched on or not.
        '''
        self.log(msg, xbmc.LOGERROR)    
        

    def log_debug(self, msg):
        '''
        Convenience method to write to the XBMC log file at the 
        ``xbmc.LOGDEBUG`` error level. Use this when you want to print out lots 
        of detailed information that is only usefull for debugging. This will 
        show up in the log only when debugging is enabled in the XBMC settings,
        and will be prefixed with 'DEBUG:'.
        '''
        self.log(msg, xbmc.LOGDEBUG)    


    def log_notice(self, msg):
        '''
        Convenience method to write to the XBMC log file at the 
        ``xbmc.LOGNOTICE`` error level. Use for general log messages. This will
        show up in the log prefixed with 'NOTICE:' whether you have debugging 
        switched on or not.
        '''
        self.log(msg, xbmc.LOGNOTICE)    


    def show_ok_dialog(self, msg, title=None, is_error=False):
        '''
        Display an XBMC dialog with a message and a single 'OK' button. The 
        message is also written to the XBMC log file at the appropriate log
        level.
        
        .. warning::
            
            Don't forget that `msg` must be a list of strings and not just a 
            string even if you only want to display a single line!
        
        Example::
        
            addon.show_ok_dialog(['My message'], 'My Addon')
        
        Args:
            msg (list of strings): The message to be displayed in the dialog. 
            Only the first 3 list items will be displayed.
            
        Kwargs:
            title (str): String to be displayed as the title of the dialog box.
            Defaults to the addon name.
            
            is_error (bool): If ``True``, the log message will be written at 
            the ERROR log level, otherwise NOTICE will be used.
        '''
        if not title:
            title = self.get_name()
        log_msg = ' '.join(msg)
        
        while len(msg) < 3:
            msg.append('')
        
        if is_error:
            self.log_error(log_msg)
        else:
            self.log_notice(log_msg)
        
        xbmcgui.Dialog().ok(title, msg[0], msg[1], msg[2])


    def show_error_dialog(self, msg):
        '''
        Convenience method to show an XBMC dialog box with a single OK button
        and also write the message to the log file at the ERROR log level.
        
        The title of the dialog will be the addon's name with the prefix 
        'Error: '.
        
        .. warning::
            
            Don't forget that `msg` must be a list of strings and not just a 
            string even if you only want to display a single line!

        Args:
            msg (list of strings): The message to be displayed in the dialog. 
            Only the first 3 list items will be displayed.
        '''
        self.show_ok_dialog(msg, 'Error: %s' % self.get_name(), True)


    def show_small_popup(self, title='', msg='', delay=5000, image=''):
        '''
        Displays a small popup box in the lower right corner. The default delay 
        is 5 seconds.

        Code inspired by anarchintosh and daledude's Icefilms addon.

        Example::

            import os
            logo = os.path.join(addon.get_path(), 'art','logo.jpg')
            addon.show_small_popup('MyAddonName','Is now loaded enjoy', 5000, logo)

        Kwargs:
            title (str): title to be displayed at the top of the box
            
            msg (str): Main message body
            
            delay (int): delay in milliseconds until it disapears
            
            image (str): Path to the image you want to display
        '''
        xbmc.executebuiltin('XBMC.Notification("%s","%s",%d,"%s")' %
                            (title, msg, delay, image))


    def show_countdown(self, time_to_wait, title='', text=''):
        '''
        Show a countdown dialog with a progress bar for XBMC while delaying 
        execution. Necessary for some filehosters eg. megaupload
        
        The original version of this code came from Anarchintosh.
        
        Args:
            time_to_wait (int): number of seconds to pause for.
            
        Kwargs:
            title (str): Displayed in the title of the countdown dialog. Default
            is blank.
                         
            text (str): A line of text to be displayed in the dialog. Default
            is blank.
            
        Returns: 
            ``True`` if countdown is allowed to complete, ``False`` if the 
            user cancelled the countdown.
        '''
        
        dialog = xbmcgui.DialogProgress()
        ret = dialog.create(title)

        self.log_notice('waiting %d secs' % time_to_wait)
        
        secs = 0
        increment = 100 / time_to_wait

        cancelled = False
        while secs <= time_to_wait:

            if (dialog.iscanceled()):
                cancelled = True
                break

            if secs != 0: 
                xbmc.sleep(1000)

            secs_left = time_to_wait - secs
            if secs_left == 0: 
                percent = 100
            else: 
                percent = increment * secs
            
            remaining_display = ('Wait %d seconds for the ' +
                    'video stream to activate...') % secs_left
            dialog.update(percent, text, remaining_display)

            secs += 1

        if cancelled == True:     
            self.log_notice('countdown cancelled')
            return False
        else:
            self.log_debug('countdown finished waiting')
            return True        


    def show_settings(self):
        '''Shows the settings dialog for this addon.'''
        self.addon.openSettings()


    def resolve_url(self, stream_url):
        '''
        Tell XBMC that you have resolved a URL (or not!).
        
        This method should be called as follows:
        
        #. The user selects a list item that has previously had ``isPlayable``
           set (this is true for items added with :meth:`add_item`, 
           :meth:`add_music_item` or :meth:`add_music_item`)
        #. Your code resolves the item requested by the user to a media URL
        #. Your addon calls this method with the resolved URL
        
        Args:
            stream_url (str or ``False``): If a string, tell XBMC that the 
            media URL ha been successfully resolved to stream_url. If ``False`` 
            or an empty string tell XBMC the resolving failed and pop up an 
            error messsage.
        '''
        if stream_url:
            self.log_debug('resolved to: %s' % stream_url)
            xbmcplugin.setResolvedUrl(self.handle, True, 
                                      xbmcgui.ListItem(path=stream_url))
        else:
            self.show_error_dialog(['sorry, failed to resolve URL :('])
            xbmcplugin.setResolvedUrl(self.handle, False, xbmcgui.ListItem())

    
    def get_playlist(self, pl_type, new=False):
        '''
        Return a :class:`xbmc.Playlist` object of the specified type.
        
        The available playlist types are defined in the :mod:`xbmc` module and 
        are currently as follows::
        
            xbmc.PLAYLIST_MUSIC = 0
            xbmc.PLAYLIST_VIDEO = 1
            
        .. seealso::
            
            :meth:`get_music_playlist`, :meth:`get_video_playlist`
            
        Args:
            pl_type (int): The type of playlist to get.
            
            new (bool): If ``False`` (default), get the current 
            :class:`xbmc.Playlist` object of the type specified. If ``True`` 
            then return a new blank :class:`xbmc.Playlist`.

        Returns:
            A :class:`xbmc.Playlist` object.
        '''
        pl = xbmc.PlayList(pl_type)
        if new:
            pl.clear()
        return pl
    
    
    def get_music_playlist(self, new=False):
        '''
        Convenience method to return a music :class:`xbmc.Playlist` object.
        
        .. seealso::
        
            :meth:`get_playlist`
        
        Kwargs:
            new (bool): If ``False`` (default), get the current music 
            :class:`xbmc.Playlist` object. If ``True`` then return a new blank
            music :class:`xbmc.Playlist`.
        Returns:
            A :class:`xbmc.Playlist` object.
       '''
        self.get_playlist(xbmc.PLAYLIST_MUSIC, new)
    

    def get_video_playlist(self, new=False):
        '''
        Convenience method to return a video :class:`xbmc.Playlist` object.
        
        .. seealso::
        
            :meth:`get_playlist`
        
        Kwargs:
            new (bool): If ``False`` (default), get the current video 
            :class:`xbmc.Playlist` object. If ``True`` then return a new blank
            video :class:`xbmc.Playlist`.
            
        Returns:
            A :class:`xbmc.Playlist` object.
        '''
        self.get_playlist(xbmc.PLAYLIST_VIDEO, new)


    def add_item(self, queries, infolabels, contextmenu_items='', context_replace=False, img='',
                 fanart='', resolved=False, total_items=0, playlist=False, item_type='video', 
                 is_folder=False):
        '''
        Adds an item to the list of entries to be displayed in XBMC or to a 
        playlist.
        
        Use this method when you want users to be able to select this item to
        start playback of a media file. ``queries`` is a dict that will be sent 
        back to the addon when this item is selected::
        
            add_item({'host': 'youtube.com', 'media_id': 'ABC123XYZ'}, 
                     {'title': 'A youtube vid'})
                     
        will add a link to::
        
            plugin://your.plugin.id/?host=youtube.com&media_id=ABC123XYZ
        
        .. seealso::
        
            :meth:`add_music_item`, :meth:`add_video_item`, 
            :meth:`add_directory`
            
        Args:
            queries (dict): A set of keys/values to be sent to the addon when 
            the user selects this item.
            
            infolabels (dict): A dictionary of information about this media 
            (see the `XBMC Wiki InfoLabels entry 
            <http://wiki.xbmc.org/?title=InfoLabels>`_).
            
        Kwargs:
            
            contextmenu_items (list): A list of contextmenu items
            
            context_replace (bool): To replace the xbmc default contextmenu items
                    
            img (str): A URL to an image file to be used as an icon for this
            entry.
            
            fanart (str): A URL to a fanart image for this entry.
            
            resolved (str): If not empty, ``queries`` will be ignored and 
            instead the added item will be the exact contentes of ``resolved``.
            
            total_items (int): Total number of items to be added in this list.
            If supplied it enables XBMC to show a progress bar as the list of
            items is being built.
            
            playlist (playlist object): If ``False`` (default), the item will 
            be added to the list of entries to be displayed in this directory. 
            If a playlist object is passed (see :meth:`get_playlist`) then 
            the item will be added to the playlist instead

            item_type (str): The type of item to add (eg. 'music', 'video' or
            'pictures')
        '''
        infolabels = self.unescape_dict(infolabels)
        if not resolved:
            if not is_folder:
                queries['play'] = 'True'
            play = self.build_plugin_url(queries)
        else: 
            play = resolved
        listitem = xbmcgui.ListItem(infolabels['title'], iconImage=img, 
                                    thumbnailImage=img)
        listitem.setInfo(item_type, infolabels)
        listitem.setProperty('IsPlayable', 'true')
        listitem.setProperty('fanart_image', fanart)
        if contextmenu_items:
            listitem.addContextMenuItems(contextmenu_items, replaceItems=context_replace)        
        if playlist is not False:
            self.log_debug('adding item: %s - %s to playlist' % \
                                                    (infolabels['title'], play))
            playlist.add(play, listitem)
        else:
            self.log_debug('adding item: %s - %s' % (infolabels['title'], play))
            xbmcplugin.addDirectoryItem(self.handle, play, listitem, 
                                        isFolder=is_folder, 
                                        totalItems=total_items)


    def add_video_item(self, queries, infolabels, contextmenu_items='', context_replace=False,
                       img='', fanart='', resolved=False, total_items=0, playlist=False):
        '''
        Convenience method to add a video item to the directory list or a 
        playlist.
        
        See :meth:`add_item` for full infomation
        '''
        self.add_item(queries, infolabels, contextmenu_items, context_replace, img, fanart,
                      resolved, total_items, playlist, item_type='video')


    def add_music_item(self, queries, infolabels, contextmenu_items='', context_replace=False,
                        img='', fanart='', resolved=False, total_items=0, playlist=False):
        '''
        Convenience method to add a music item to the directory list or a 
        playlist.
        
        See :meth:`add_item` for full infomation
        '''
        self.add_item(queries, infolabels, contextmenu_items, img, context_replace, fanart,
                      resolved, total_items, playlist, item_type='music')


    def add_directory(self, queries, infolabels, contextmenu_items='', context_replace=False,
                       img='', fanart='', total_items=0, is_folder=True):
        '''
        Convenience method to add a directory to the display list or a 
        playlist.
        
        See :meth:`add_item` for full infomation
        '''
        self.add_item(queries, infolabels, contextmenu_items, context_replace, img, fanart,
                      total_items=total_items, resolved=self.build_plugin_url(queries), 
                      is_folder=is_folder)

    def end_of_directory(self):
        '''Tell XBMC that we have finished adding items to this directory.'''
        xbmcplugin.endOfDirectory(self.handle)
        

    def _decode_callback(self, matches):
        '''Callback method used by :meth:`decode`.'''
        id = matches.group(1)
        try:
            return unichr(int(id))
        except:
            return id


    def decode(self, data):
        '''
        Regular expression to convert entities such as ``&#044`` to the correct
        characters. It is called by :meth:`unescape` and so it is not required
        to call it directly.
        
        This method was found `on the web <http://stackoverflow.com/questions/1208916/decoding-html-entities-with-python/1208931#1208931>`_
        
        Args:
            data (str): String to be cleaned.
            
        Returns:
            Cleaned string.
        '''
        return re.sub("&#(\d+)(;|(?=\s))", self._decode_callback, data).strip()


    def unescape(self, text):
        '''
        Decodes HTML entities in a string.
        
        You can add more entities to the ``rep`` dictionary.
        
        Args:
            text (str): String to be cleaned.
            
        Returns:
            Cleaned string.
        '''
        try:
            text = self.decode(text)
            rep = {'&lt;': '<',
                   '&gt;': '>',
                   '&quot': '"',
                   '&rsquo;': '\'',
                   '&acute;': '\'',
                   }
            for s, r in rep.items():
                text = text.replace(s, r)
            # this has to be last:
            text = text.replace("&amp;", "&")
        
        #we don't want to fiddle with non-string types
        except TypeError:
            pass

        return text
        

    def unescape_dict(self, d):
        '''
        Calls :meth:`unescape` on all values in a dictionary.
        
        Args:
            d (dict): A dictionary containing string values
            
        Returns:
            A dictionary with HTML entities removed from the values.
        '''
        out = {}
        for key, value in d.items():
            out[key] = self.unescape(value)
        return out
    
    def save_data(self, filename, data):
        '''
        Saves the data structure using pickle. If the addon data path does 
        not exist it will be automatically created. This save function has
        the same restrictions as the pickle module.
        
        Args:
            filename (string): name of the file you want to save data to. This 
            file will be saved in your addon's profile directory.
            
            data (data object/string): you want to save.
            
        Returns:
            True on success
            False on failure
        '''
        profile_path = self.get_profile()
        try:
            os.makedirs(profile_path)
        except:
            pass
        save_path = os.path.join(profile_path, filename)
        try:
            pickle.dump(data, open(save_path, 'wb'))
            return True
        except pickle.PickleError:
            return False
        
    def load_data(self,filename):
        '''
        Load the data that was saved with save_data() and returns the
        data structure.
        
        Args:
            filename (string): Name of the file you want to load data from. This
            file will be loaded from your addons profile directory.
            
        Returns:
            Data stucture on success
            False on failure
        '''
        profile_path = self.get_profile()
        load_path = os.path.join(profile_path, filename)
        print profile_path
        if not os.path.isfile(load_path):
            self.log_debug('%s does not exist' % load_path)
            return False
        try:
            data = pickle.load(open(load_path))
        except:
            return False
        return data
            
        

