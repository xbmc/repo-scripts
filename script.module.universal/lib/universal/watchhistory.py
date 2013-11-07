'''
    universal XBMC module
    Copyright (C) 2013 the-one @ XUNITYTALK.COM

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
import datetime
import xbmc, xbmcgui, xbmcplugin
import re
import hashlib

from t0mm0.common.addon import Addon

from universal import _common as common

HELPER = 'watchhistory'

try:
    if  common.use_remote_db=='true' and   \
        common.db_address is not None and  \
        common.db_user is not None and     \
        common.db_pass is not None and     \
        common.db_name is not None:
        import mysql.connector as database
        common.addon.log('-' + HELPER + '- -' +'Loading MySQLdb as DB engine', 2)
        DB = 'mysql'
    else:
        raise ValueError('MySQL not enabled or not setup correctly')
except:
    try: 
        import sqlite3
        from sqlite3 import dbapi2 as database
        common.addon.log('-' + HELPER + '- -' +'Loading sqlite3 as DB engine version: %s' % database.sqlite_version, 2)
    except Exception, e:
        from pysqlite2 import dbapi2 as database
        common.addon.log('-' + HELPER + '- -' +'pysqlite2 as DB engine', 2)
    DB = 'sqlite'



class WatchHistory:
    '''
    This class provides all the handling of watch history.  

    Example:
        from universal import watchhistory
        wh = watchhistory.WatchHistory(addon_id, sys.argv)
        wh.add_item( ... )        
    '''
    
    local_db_name = 'watch_history.db'
    
    def __init__(self, addon_id, sys_argv=''):
        '''
            Args:
                addon_id (str): addon id of the plugin using the watch history
                
            Kwargs:
                sys_argv (array): sys.argv
        '''
        
        #Check if a path has been set in the addon settings
        if common.db_path:
            self.path = xbmc.translatePath(common.db_path)
        else:
            self.path = xbmc.translatePath(common.default_path)
        
        self.addon_id = addon_id
        self.sys_argv = sys_argv
        self.cache_path = common.make_dir(self.path, '')
        
        self.db = os.path.join(self.cache_path, self.local_db_name)
        
        # connect to db at class init and use it globally
        if DB == 'mysql':
            class MySQLCursorDict(database.cursor.MySQLCursor):
                def _row_to_python(self, rowdata, desc=None):
                    row = super(MySQLCursorDict, self)._row_to_python(rowdata, desc)
                    if row:
                        return dict(zip(self.column_names, row))
                    return None
            self.dbcon = database.connect(common.db_name, common.db_user, common.db_pass, common.db_address, buffered=True, charset='utf8')
            self.dbcur = self.dbcon.cursor(cursor_class=MySQLCursorDict, buffered=True)
        else:
            self.dbcon = database.connect(self.db)
            self.dbcon.row_factory = database.Row # return results indexed by field names and not numbers so we can convert to dict
            self.dbcon.text_factory = str
            self.dbcur = self.dbcon.cursor()
                
        self._create_watch_history_tables()
    
    def __del__(self):
        ''' Cleanup db when object destroyed '''
        try:
            self.dbcur.close()
            self.dbcon.close()
        except: pass

    def _create_watch_history_tables(self):
        ''' Create the watch history database table '''
        sql_create = "CREATE TABLE IF NOT EXISTS watch_history ("\
                            "addon_id TEXT,"\
                            "hash_title TEXT,"\
                            "title TEXT,"\
                            "fmtd_title TEXT,"\
                            "url TEXT,"\
                            "infolabels TEXT,"\
                            "image_url TEXT,"\
                            "fanart_url TEXT,"\
                            "isfolder TEXT,"\
                            "isplayable TEXT,"\
                            "level TEXT,"\
                            "parent_title TEXT,"\
                            "indent_title TEXT,"\
                            "lastwatched TIMESTAMP,"\
                            "UNIQUE(addon_id, hash_title)"\
                            ");"
        if DB == 'mysql':
            sql_create = sql_create.replace("addon_id TEXT", "addon_id VARCHAR(100)")
            sql_create = sql_create.replace("hash_title TEXT"  ,"hash_title VARCHAR(32)")
            sql_create = sql_create.replace(",title TEXT"  ,",title VARCHAR(225)")
            sql_create = sql_create.replace("isfolder TEXT"  ,"isfolder VARCHAR(5)")
            sql_create = sql_create.replace("isplayable TEXT"  ,"isplayable VARCHAR(5)")
            sql_create = sql_create.replace("level TEXT"  ,"level VARCHAR(1)")
            sql_create = sql_create.replace("parent_title TEXT"  ,"parent_title VARCHAR(32)")
            self.dbcur.execute(sql_create)
            try: self.dbcur.execute('CREATE INDEX whindex on watch_history (addon_id, hash_title);')                
            except: pass
            try: self.dbcur.execute('CREATE INDEX lwindex on watch_history (lastwatched, title, level);')
            except: pass            
        else:
            self.dbcur.execute(sql_create)
            self.dbcur.execute('CREATE INDEX IF NOT EXISTS whindex on watch_history (addon_id, title);')
            self.dbcur.execute('CREATE INDEX IF NOT EXISTS lwindex on watch_history (lastwatched, fmtd_title, level);')
        common.addon.log('-' + HELPER + '- -' +'Table watch_history initialized', 0)    
        
    def _settings_add_as_dir(self):
        return common.addon.get_setting('add_dir')
        
    def _settings_cleanup_history(self):
        
        _ch = common.addon.get_setting('cleanup-history')
        
        ch = ''
        
        if _ch == '0':
            ch = 'days'            
        elif _ch == '1':
            ch = 'count'
            
        return ch
        
    def _settings_cleanup_history_max(self, ch):
        
        chm = ''
    
        if ch == 'days':
            chm = common.addon.get_setting('cleanup-history-days')
        elif ch == 'count':
            chm = common.addon.get_setting('cleanup-history-count')
            
        return chm
    
    def add_item(self, title, url, fmtd_title = '', level='0', parent_title='', indent_title='', infolabels='', img='', fanart='', is_playable=False, is_folder=False):
        '''
            Add an item to watch history.
            
            Args:
                title (str): title of the item; used to generate title-hash and sorting
                
                url (str): the compelte plugin url that would be called when this item is selected
                
            Kwargs:
                fmtd_title (str): title of the item as it will be displayed in the list. 
                        if fmtd_title is None:
                            fmtd_title = title
                            
                level (str): item level in the hierarchy. Used if playable-item's parent is also being added to the favorites.
                        Non-parent's level is '0'
                        Parent's level starts with '1'
                        Should be covnertiable to integer
                        
                parent_title (str): If the item has a parent, then the title used to identify the parent
                
                indent_title (str): Title to be used in parent-indent mode (WIP)
                        If indent_title is None:
                            indent_title = fmtd_title
                            
                info_labels (hash): Any information that the calling plugin might need when the item is being retreived goes here.
                        This is also used to set support for metadata for the item with watch history.
                        infolabels = { 'supports_meta' : 'true', 'video_type':video_type, 'name':title, 'imdb_id':imdb_id, 
                            'season':season, 'episode':episode, 'year':year 
                        }
                        
                img (str): url or path of the image to be used as thumbnail and icon of the item
                
                fanart (str): url or path of the image to be used as fanart of the item
                
                is_playable (bool): set the item isPlayable property
                
                is_folder (bool): set the item isFolder property
        '''
        if url.find('&watchhistory=true'):
            url = url.replace('&watchhistory=true', '')
        elif url.find('?watchhistory=true&'):
            url = url.replace('?watchhistory=true&', '?')
            
        title = common.str_conv(title)                
            
        if not fmtd_title:
            fmtd_title = title
        else:
            fmtd_title = common.str_conv(fmtd_title)
            
        if not indent_title:
            indent_title = fmtd_title
        else:
            indent_title = common.str_conv(indent_title)
            
        hash_title = hashlib.md5(title).hexdigest()

        if parent_title:
            parent_title = common.str_conv(parent_title)

        if parent_title:
            parent_title = hashlib.md5(parent_title).hexdigest()
                       
        row_exists = True
        try:
            if DB == 'mysql':
                sql_select = "SELECT * FROM watch_history WHERE addon_id = %s AND hash_title = %s"
            else:
                sql_select = "SELECT * FROM watch_history WHERE addon_id = ? AND hash_title = ?"
            common.addon.log('-' + HELPER + '- -' + '%s : %s, %s' %(sql_select, self.addon_id, hash_title), 2 )
            self.dbcur.execute(sql_select, (self.addon_id, hash_title))
            common.addon.log('-' + HELPER + '- -' + str(self.dbcur.fetchall()[0]), 2)
        except:
            row_exists = False
                
        sql_update_or_insert = ''
        if row_exists == True:
            if DB == 'mysql':
                sql_update_or_insert = "UPDATE watch_history SET lastwatched = %s WHERE addon_id = %s AND hash_title = %s" 
            else:
                sql_update_or_insert = "UPDATE watch_history SET lastwatched = ? WHERE addon_id = ? AND hash_title = ?" 
            common.addon.log('-' + HELPER + '- -' + '%s : %s, %s, %s' %(sql_update_or_insert, 'datetime.datetime.now()', self.addon_id, hash_title), 2 )
            self.dbcur.execute(sql_update_or_insert, (datetime.datetime.now(), self.addon_id, hash_title))
        else:        
            if DB == 'mysql':
                sql_update_or_insert = "INSERT INTO watch_history(addon_id, hash_title, title, fmtd_title, url, infolabels, image_url, fanart_url, isplayable, isfolder, lastwatched, level, parent_title, indent_title) VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
            else:
                sql_update_or_insert = "INSERT INTO watch_history(addon_id, hash_title, title, fmtd_title, url, infolabels, image_url, fanart_url, isplayable, isfolder, lastwatched, level, parent_title, indent_title) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
                
            if infolabels:
                infolabels = common.encode_dict(infolabels)
                
            is_playable = common.bool2str(is_playable)
            is_folder = common.bool2str(is_folder)
            infolabels = str(infolabels)
            
            common.addon.log('-' + HELPER + '- -' + '%s : %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s' %(sql_update_or_insert, self.addon_id, hash_title, title, fmtd_title, common.str_conv(url), infolabels, img, fanart, is_playable, is_folder, 'datetime.datetime.now()', level, parent_title, indent_title), 2 )
            self.dbcur.execute(sql_update_or_insert, (self.addon_id, hash_title, title, fmtd_title, url, infolabels, img, fanart, is_playable, is_folder, datetime.datetime.now(), level, parent_title, indent_title))
        self.dbcon.commit()
    
    def add_video_item(self, title, url, fmtd_title='', level='0', parent_title='', indent_title='', infolabels='', img='', fanart='', is_playable=False):
        '''Add a video item to watch history. See add_item() for more details'''
        self.add_item(title, url, fmtd_title=fmtd_title, level=level, parent_title=parent_title, indent_title=indent_title, infolabels=infolabels, img=img, fanart=fanart, is_playable=is_playable)
        
    def add_directory(self, title, url, fmtd_title = '', level='0', parent_title='', indent_title='', infolabels='', img='', fanart=''):
        '''Add a directory to watch history. See add_item() for more details'''
        self.add_item(title, url, fmtd_title=fmtd_title, level=level, parent_title=parent_title, indent_title=indent_title, infolabels=infolabels, img=img, fanart=fanart, is_folder=True)
        
    def get_watch_history(self, addon_id):
        '''
            Get the watch history for the addon with provided addon_id
            If addon_id == 'all': get the entire watch history
            
            Args:
                addon_id (str): addon id of the plugin requesting its watch history
        '''
        history_items = []
        
        try:
            import json
        except:
            import simplejson as json

        sql_select = "SELECT * FROM watch_history"
        
        whereadded = False
        if addon_id != 'all':
            sql_select = sql_select + ' WHERE addon_id = \'' + addon_id + '\''
            whereadded = True
        
        if self._settings_add_as_dir() == 'true':
            sql_select = sql_select + " ORDER BY lastwatched DESC, title ASC, level DESC"
        else:
            if whereadded == False:
                sql_select = sql_select + ' WHERE '
                whereadded = True
            else:
                sql_select = sql_select + ' AND '
                
            sql_select = sql_select + " level = '0' ORDER BY lastwatched DESC, title ASC"
                
        common.addon.log('-' + HELPER + '- -' +sql_select, 2)

        self.dbcur.execute(sql_select)
        
        parent_items = {}
        parent_items_legacy = []
        
        for matchedrow in self.dbcur.fetchall():
        
            match = dict(matchedrow)
            
            item_level = match['level']
            match_hash_title = match['hash_title']
            item_parent = match['parent_title']
            if item_parent:
                item_parent = match['addon_id'] + '-' + item_parent
            match_title = match['title']
            
            if self._settings_add_as_dir() == 'true' and item_level == '0' and ( 
                (item_parent != '' and parent_items.get(item_parent, None) != None) or 
                (match_title[0:match_title.find(' - ')] in parent_items_legacy)
                ):
                continue
            
            infolabels = {}
            if match['infolabels']:
                infolabels = json.loads(re.sub(r",\s*(\w+)", r", '\1'", re.sub(r"\{(\w+)", r"{'\1'", match['infolabels'].replace('\\','\\\\'))).replace("'", '"'))
            infolabels['title'] = match['fmtd_title']

            item = {'title_trunc':match['title'] ,'title':match['fmtd_title'], 'url' : match['url'], 'infolabels': common.decode_dict(infolabels), 'image_url':match['image_url'], 'fanart_url':match['fanart_url'], 'isplayable':match['isplayable'], 'isfolder':match['isfolder']}
            
            history_items.append(item)
            
            if int(item_level) > 0: 
                parent_items[ match['addon_id'] + '-' + match_hash_title] = match
                parent_items_legacy.append(match_title)
            
        return history_items
        
    def get_my_watch_history(self):
        
        return self.get_watch_history(self.addon_id)
        
    def get_watch_history_for_all(self):
        
        return self.get_watch_history('all')
        
    def has_watch_history(self):
    
        has_wh = True
        
        try:
            sql_select = "SELECT * FROM watch_history WHERE addon_id = '%s'" % self.addon_id
            self.dbcur.execute(sql_select)    
            matchedrow = self.dbcur.fetchall()[0]
        except:
            has_wh = False
            
        return has_wh
        
    def get_addons_that_have_watch_history(self):
    
        addons = []
    
        sql_select = "SELECT DISTINCT addon_id FROM watch_history ORDER BY addon_id"
    
        self.dbcur.execute(sql_select)
    
        for matchedrow in self.dbcur.fetchall():
        
            match = dict(matchedrow)
            
            try:
                tmp_addon_id = match['addon_id']
                tmp_addon = Addon(tmp_addon_id)
                tmp_addon_name = tmp_addon.get_name()
                tmp_addon_img = tmp_addon.get_icon()                
                tmp_addon_fanart = tmp_addon.get_fanart() 
            except:
                tmp_addon_name = tmp_addon_id
                tmp_addon_img = ''          
                tmp_addon_fanart = ''
                pass
            
            tmp_addon_dtl = {'title' : tmp_addon_name, 'id' : tmp_addon_id, 'img':tmp_addon_img, 'fanart':tmp_addon_fanart}
            
            addons.append(tmp_addon_dtl)
            
        return addons
        
    def add_my_history_directory(self, title='Watch History', img='', fanart=''):
        if not self.sys_argv:
            common.addon.log_error('-' + HELPER + '- -' +'sys.argv not passed in WatchHistory __init__(); Watch History directory will not be created.')
            return
            
        try:
            tmp_addon_id = 'plugin.video.watchhistory'
            tmp_addon = Addon(tmp_addon_id)
            tmp_addon_name = tmp_addon.get_name()                
        except:
            common.addon.log_error('-' + HELPER + '- -' +'Watch History video plugin not installed; Watch History directory will not be created.')
            common.notify(self.addon_id, 'small', ' - Watch History video addon required', 'Please install Watch History video addon from The ONE\'s XBMC Addons Repository.', '10000')                            
            return
        
        listitem = xbmcgui.ListItem(title, iconImage=img, thumbnailImage=img)
        listitem.setProperty('fanart_image', fanart)
        
        params = '?' + common.dict_to_paramstr( {'mode':'browse', 'addon_id':self.addon_id, 'local':'true'} )
        xbmcplugin.addDirectoryItem(handle=int(self.sys_argv[1]),url='plugin://plugin.video.watchhistory/'+params,isFolder=True,listitem=listitem)
        
    def cleanup_history(self):
        
        ch = self._settings_cleanup_history()                
        chm = self._settings_cleanup_history_max(ch)
        
        sql_delete = ''
        
        if ch == 'days':
            cutoff_date = str(datetime.date.today() - datetime.timedelta(int(chm)))
            sql_delete = "DELETE FROM watch_history WHERE lastwatched < '%s'" % cutoff_date            
        elif ch == 'count':
            if DB == 'mysql':
                sql_delete = "DELETE FROM watch_history WHERE (addon_id, title) NOT IN (SELECT * FROM (SELECT wh1.addon_id, wh1.title FROM watch_history wh1 JOIN (SELECT addon_id, title FROM watch_history ORDER BY lastwatched DESC LIMIT %s) as wh2 on wh1.addon_id = wh2.addon_id AND wh1.title = wh2.title) as wh3)" % chm
            else:
                sql_delete = "DELETE FROM watch_history WHERE addon_id || '-' || title NOT IN (SELECT addon_id || '-' || title FROM watch_history ORDER BY lastwatched DESC LIMIT %s)" % chm            
                
        common.addon.log('-' + HELPER + '- -' +sql_delete,2)
        
        self.dbcur.execute(sql_delete)
        self.dbcon.commit()
