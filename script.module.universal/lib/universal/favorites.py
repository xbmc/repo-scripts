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
import sys
import hashlib

from t0mm0.common.addon import Addon

from universal import _common as common

HELPER = 'favorites'

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

class Favorites:

    local_db_name = 'favorites.db'

    def __init__(self, addon_id, sys_argv=''):
        
        #Check if a path has been set in the addon settings
        if common.db_path:
            self.path = xbmc.translatePath(common.db_path)
        else:
            self.path = xbmc.translatePath(common.default_path)
        
        self.addon_id = addon_id
        self.sys_argv = sys_argv
        self.cache_path = common.make_dir(self.path, '')
        self.addon = Addon(self.addon_id, self.sys_argv)
        
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
                
        self._create_favorites_tables()
    
    def __del__(self):
        ''' Cleanup db when object destroyed '''
        try:
            self.dbcur.close()
            self.dbcon.close()
        except: pass

    def _create_favorites_tables(self):
        
        sql_create = "CREATE TABLE IF NOT EXISTS favorites ("\
                            "addon_id TEXT,"\
                            "section_title TEXT,"\
                            "section_addon_title TEXT,"\
                            "sub_section_title TEXT,"\
                            "sub_section_addon_title TEXT,"\
                            "hash_title TEXT,"\
                            "title TEXT,"\
                            "fmtd_title TEXT,"\
                            "url TEXT,"\
                            "infolabels TEXT,"\
                            "image_url TEXT,"\
                            "fanart_url TEXT,"\
                            "isfolder TEXT,"\
                            "isplayable TEXT,"\
                            "UNIQUE(addon_id, section_title, sub_section_title, hash_title)"\
                            ");"
        if DB == 'mysql':
            sql_create = sql_create.replace("addon_id TEXT", "addon_id VARCHAR(100)")
            sql_create = sql_create.replace("hash_title TEXT"  ,"hash_title VARCHAR(32)")
            sql_create = sql_create.replace(",title TEXT"  ,",title VARCHAR(225)")
            sql_create = sql_create.replace("section_title TEXT"  ,"section_title VARCHAR(100)")
            sql_create = sql_create.replace("sub_section_title TEXT"  ,"sub_section_title VARCHAR(100)")
            sql_create = sql_create.replace("isfolder TEXT"  ,"isfolder VARCHAR(5)")
            sql_create = sql_create.replace("isplayable TEXT"  ,"isplayable VARCHAR(5)")
            self.dbcur.execute(sql_create)
            try: self.dbcur.execute('CREATE INDEX favindex on favorites (addon_id, section_title, sub_section_title, hash_title);')
            except: pass
            try: self.dbcur.execute('CREATE INDEX favsrtindex on favorites (addon_id, title);')
            except: pass
        else:
            self.dbcur.execute(sql_create)
            self.dbcur.execute('CREATE INDEX IF NOT EXISTS favindex on favorites (addon_id, section_title, sub_section_title, hash_title);')
            self.dbcur.execute('CREATE INDEX IF NOT EXISTS favsrtindex on favorites (addon_id, section_title, sub_section_title, title);')
        
        common.addon.log('-' + HELPER + '- -' +'Table watch_history initialized', 0)
            
    def _is_already_in_favorites(self, addon_id, section_title, section_addon_title, sub_section_title, sub_section_addon_title, title, item_mode='main'):
    
        item_column_section = ''
        item_column_sub_section = ''
        val_section=''
        val_sub_section=''
        if item_mode == 'main':
            item_column_section = 'section_title'
            val_section = section_title
            item_column_sub_section = 'sub_section_title'
            val_sub_section = sub_section_title
        elif item_mode == 'addon':
            item_column_section = 'section_addon_title'
            val_section = section_addon_title
            item_column_sub_section = 'sub_section_addon_title'
            val_sub_section = sub_section_addon_title
            
        hash_title = hashlib.md5(title).hexdigest()
            
        row_exists = True
        try:
            sql_select = ''
            if DB == 'mysql':
                sql_select = "SELECT title FROM favorites WHERE addon_id = %s AND " + item_column_section + " = %s AND " + item_column_sub_section + " = %s AND hash_title = %s " 
            else:
                sql_select = "SELECT title FROM favorites WHERE addon_id = ? AND " + item_column_section + " = ? AND " + item_column_sub_section + " = ? AND hash_title = ? " 
            self.dbcur.execute(sql_select, (addon_id, val_section, val_sub_section, hash_title) )    
            matchedrow = self.dbcur.fetchall()[0]
        except:
            row_exists = False
            
        return row_exists
        
    def is_already_in_favorites(self, section_title, section_addon_title, sub_section_title, sub_section_addon_title, title, item_mode='main'):
        return self._is_already_in_favorites(self.addon_id, section_title, section_addon_title, sub_section_title, sub_section_addon_title, title, item_mode=item_mode)
    
    def add_item_to_db(self, title, fmtd_title, url, section_title, section_addon_title, sub_section_title, sub_section_addon_title, infolabels, img, fanart, is_playable, is_folder):
        if url.find('&favorite=true'):
            url = url.replace('&favorite=true', '')
        elif url.find('?favorite=true&'):
            url = url.replace('?favorite=true&', '?')
            
        hash_title = hashlib.md5(title).hexdigest()
                       
        sql_insert = ''
        if self.is_already_in_favorites(section_title, section_addon_title, sub_section_title, sub_section_addon_title, title) == True:
            #common.notify(self.addon_id, 'small', '', 'Item: ' + fmtd_title + ' - already exists in Favorites.', '8000')
            common.notify(self.addon_id, 'small', '[B]' + fmtd_title + '[/B]', '[B]Already exists in Favorites.[/B]', '8000')
        else:
            if DB == 'mysql':
                sql_insert = "INSERT INTO favorites(addon_id, hash_title, title, fmtd_title, url, section_title, section_addon_title, sub_section_title, sub_section_addon_title, infolabels, image_url, fanart_url, isfolder, isplayable ) VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
            else:
                sql_insert = "INSERT INTO favorites(addon_id, hash_title, title, fmtd_title, url, section_title, section_addon_title, sub_section_title, sub_section_addon_title, infolabels, image_url, fanart_url, isfolder, isplayable ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"            
                
            if infolabels:
                infolabels = common.encode_dict(infolabels)
                
            common.addon.log('-' + HELPER + '- -' +'%s: %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s' % (sql_insert, self.addon_id, hash_title, title, fmtd_title, url, section_title, section_addon_title, sub_section_title, sub_section_addon_title, str(infolabels), img, fanart, common.bool2str(is_folder), common.bool2str(is_playable)), 2)
            
            try:
                self.dbcur.execute(sql_insert, (self.addon_id, hash_title, title, fmtd_title, url, section_title, section_addon_title, sub_section_title, sub_section_addon_title, str(infolabels), img, fanart, common.bool2str(is_folder), common.bool2str(is_playable) ))            
                self.dbcon.commit()
                #common.notify(self.addon_id, 'small', '', 'Item: ' + fmtd_title + ' - added successfully to Favorites.', '8000')
                common.notify(self.addon_id, 'small', '[B]' + fmtd_title + '[/B]', '[B]Added to Favorites.[/B]', '8000')
            except:
                #common.notify(self.addon_id, 'small', '', 'Item: ' + fmtd_title + ' - unable to add to Favorites.', '8000')                
                common.notify(self.addon_id, 'small', '[B]' + fmtd_title + '[/B]', '[B]Unable to add to Favorites.[/B]', '8000')
                pass
                
    def delete_item_from_db(self, title, fmtd_title, section_title, section_addon_title, sub_section_title, sub_section_addon_title, item_mode='main'):
    
        hash_title = hashlib.md5(title).hexdigest()
        
        item_column_section = ''
        item_column_sub_section = ''
        if item_mode == 'main':
            item_column_section = 'section_title'
            item_column_sub_section = 'sub_section_title'
        elif item_mode == 'addon':
            item_column_section = 'section_addon_title'
            item_column_sub_section = 'sub_section_addon_title'
        
        sql_delete = ''
        if DB == 'mysql':
            sql_delete = "DELETE FROM favorites WHERE addon_id = %s AND " + item_column_section + " = %s AND " + item_column_sub_section + " = %s AND hash_title = %s"
        else:
            sql_delete = "DELETE FROM favorites WHERE addon_id = ? AND " + item_column_section + " = ? AND " + item_column_sub_section + " = ? AND hash_title = ?"
        
        common.addon.log('-' + HELPER + '- -' + '%s: %s, %s, %s, %s' % (sql_delete, self.addon_id, section_title, sub_section_title, hash_title), 2)
        
        try:
            self.dbcur.execute(sql_delete, (self.addon_id, section_title, sub_section_title, hash_title) )            
            self.dbcon.commit()
            #common.notify(self.addon_id, 'small', '', 'Item: ' + fmtd_title + ' - removed successfully from Favorites.', '8000')
            common.notify(self.addon_id, 'small', '[B]' + fmtd_title + '[/B]', '[B]Removed from Favorites.[/B]', '8000')
        except:
            #common.notify(self.addon_id, 'small', '', 'Item: ' + fmtd_title + ' - unable to remove from Favorites.', '8000')                
            common.notify(self.addon_id, 'small', '[B]' + fmtd_title + '[/B]', '[B]Unable to remove from Favorites.[/B]', '8000')
            pass
        
    def build_url(self, queries):
        return self.addon.build_plugin_url(queries)
    
    def add_item(self, title, url, fmtd_title='', section_title='Misc.', section_addon_title='', sub_section_title='', sub_section_addon_title='', infolabels='', img='', fanart='', is_playable=False, is_folder=False):
        
        if not fmtd_title: fmtd_title = title
        if not section_addon_title: section_addon_title = section_title
        if not sub_section_addon_title: sub_section_addon_title = sub_section_title
        
        uni_fav = {
            'uni_fav_addon_id': self.addon_id,
            'uni_fav_mode': 'add',
            'uni_fav_title': title,
            'uni_fav_fmtd_title': fmtd_title,
            'uni_fav_url': url,
            'uni_fav_section_title': section_title,
            'uni_fav_section_addon_title': section_addon_title,
            'uni_fav_sub_section_title': sub_section_title,
            'uni_fav_sub_section_addon_title': sub_section_addon_title,
            'uni_fav_img': img,
            'uni_fav_fanart': fanart,
            'uni_fav_is_playable': common.bool2str(is_playable),
            'uni_fav_is_folder': common.bool2str(is_folder)            
            }
        
        uni_fav_add_script = 'XBMC.RunScript(%s, %s, %s, "%s")' % (self._get_script_path(), self.sys_argv[1], self._build_params(uni_fav, infolabels), 'script.module.universal.favorites')
        
        return uni_fav_add_script
        
    def add_video_item(self, title, url, fmtd_title='', section_title='', section_addon_title='', sub_section_title='', sub_section_addon_title='', infolabels='', img='', fanart='', is_playable=False):
        return self.add_item(title, url, fmtd_title=fmtd_title, section_title=section_title, section_addon_title=section_addon_title, sub_section_title=sub_section_title, sub_section_addon_title=sub_section_addon_title, infolabels=infolabels, img=img, fanart=fanart, is_playable=is_playable)
        
    def add_directory(self, title, url, fmtd_title='', section_title='', section_addon_title='', sub_section_title='', sub_section_addon_title='', infolabels='', img='', fanart=''):
        return self.add_item(title, url, fmtd_title=fmtd_title, section_title=section_title, section_addon_title=section_addon_title, sub_section_title=sub_section_title, sub_section_addon_title=sub_section_addon_title, infolabels=infolabels, img=img, fanart=fanart, is_folder=True)
        
    def delete_item(self, title, fmtd_title='', item_mode='main', section_title='Misc.', section_addon_title='', sub_section_title='', sub_section_addon_title=''):
        
        if not fmtd_title: fmtd_title = title
        if not section_addon_title: section_addon_title = section_title
        if not sub_section_addon_title: sub_section_addon_title = sub_section_title
        
        uni_fav = {
            'uni_fav_addon_id': self.addon_id,
            'uni_fav_mode': 'delete',
            'uni_fav_item_mode': item_mode,
            'uni_fav_title': title,
            'uni_fav_fmtd_title': fmtd_title,
            'uni_fav_section_title': section_title,
            'uni_fav_section_addon_title': section_addon_title,
            'uni_fav_sub_section_title': sub_section_title,
            'uni_fav_sub_section_addon_title': sub_section_addon_title
            }
        
        uni_fav_add_script = 'XBMC.RunScript(%s, %s, %s, "%s")' % (self._get_script_path(), self.sys_argv[1], self._build_params(uni_fav), 'script.module.universal.favorites')
        
        return uni_fav_add_script
    
    def _get_script_path(self):
        return os.path.join(common.addon.get_path(), 'lib', 'universal', 'favorites.py')
    
    def _build_params(self, uni_fav, infolabels=''):
        
        uni_fav_ps = '?' + common.dict_to_paramstr(uni_fav)
        
        if infolabels:
            uni_fav_ps = uni_fav_ps + '&' + common.dict_to_paramstr(infolabels)
            
        return uni_fav_ps
    
    def get_sub_sections(self, section_title, addon_id='all', item_mode='main'):
        sections = []
        
        item_column_section = ''
        item_column_sub_section = ''
        if item_mode == 'main':
            item_column_section = 'section_title'
            item_column_sub_section = 'sub_section_title'
        elif item_mode == 'addon':
            item_column_section = 'section_addon_title'
            item_column_sub_section = 'sub_section_addon_title'
            
        if DB == 'mysql':
            params_var = "%s"
        else:
            params_var = "?"
            
        params = []

        sql_select = "SELECT DISTINCT " + item_column_sub_section + " FROM favorites"
        
        whereadded = False
        if addon_id != 'all':
            params.append(addon_id)
            sql_select = sql_select + ' WHERE addon_id = ' + params_var
            whereadded = True
            
        if whereadded == False:
            sql_select = sql_select + ' WHERE '
            whereadded = True
        else:
            sql_select = sql_select + ' AND '        
            
        params.append(section_title)
        sql_select = sql_select + item_column_section + " = " + params_var + " AND " + item_column_sub_section + " != '' ORDER BY " + item_column_sub_section + " ASC" 
        
        params = tuple(params)
        
        common.addon.log('-' + HELPER + '- -' + sql_select + ":" + (" %s," * len(params)) % params, 2)

        self.dbcur.execute(sql_select, params)
                    
        for matchedrow in self.dbcur.fetchall():
        
            match = dict(matchedrow)
                        
            item = { 'title':match[item_column_sub_section] }
            
            sections.append(item)
            
        return sections
    
    def get_main_sections(self, addon_id='all', item_mode='main'):
        sections = []
        item_column_section = ''
        if item_mode == 'main':
            item_column_section = 'section_title'
        elif item_mode == 'addon':
            item_column_section = 'section_addon_title'
            
        if DB == 'mysql':
            params_var = "%s"
        else:
            params_var = "?"
        
        params = []
        
        sql_select = "SELECT DISTINCT " + item_column_section + " FROM favorites"
        
        whereadded = False
        if addon_id != 'all':
            params.append(addon_id)
            sql_select = sql_select + ' WHERE addon_id = ' + params_var
            whereadded = True
        
        sql_select = sql_select + " ORDER BY " + item_column_section + " ASC"
        
        params = tuple(params)
        
        common.addon.log('-' + HELPER + '- -' + sql_select + ":" + (" %s," * len(params)) % params, 2)

        self.dbcur.execute(sql_select, params)
        
        for matchedrow in self.dbcur.fetchall():
        
            match = dict(matchedrow)
                        
            item = { 'title':match[item_column_section] }
            
            sections.append(item)
            
        return sections
        
    def get_favorites(self, section_title='all', sub_section_title='all', addon_id='all', item_mode='main'):
        
        favorites = []
        
        item_column_section = ''
        item_column_sub_section = ''
        if item_mode == 'main':
            item_column_section = 'section_title'
            item_column_sub_section = 'sub_section_title'
        elif item_mode == 'addon':
            item_column_section = 'section_addon_title'
            item_column_sub_section = 'sub_section_addon_title'
            
        if DB == 'mysql':
            params_var = "%s"
        else:
            params_var = "?"
        
        try:
            import json
        except:
            import simplejson as json
            
        params = []

        sql_select = "SELECT * FROM favorites"
                
        
        whereadded = False
        if addon_id != 'all':
            params.append(addon_id)
            sql_select = sql_select + ' WHERE addon_id = ' + params_var
            whereadded = True
        
        if section_title != 'all':
            params.append(section_title)
            if whereadded == False:
                sql_select = sql_select + ' WHERE '
                whereadded = True
            else:
                sql_select = sql_select + ' AND '        
            sql_select = sql_select + item_column_section + " = " + params_var             
            
            if sub_section_title != 'all':
                params.append(sub_section_title)
                sql_select = sql_select + " AND " + item_column_sub_section + " = " + params_var 
        
        
        sql_select = sql_select + " ORDER BY title ASC"
        
        params = tuple(params)
            
        common.addon.log('-' + HELPER + '- -' + sql_select + ":" + (" %s," * len(params)) % params, 2)

        self.dbcur.execute(sql_select, params)
        
        for matchedrow in self.dbcur.fetchall():
        
            match = dict(matchedrow)
                        
            infolabels = {}
            if match['infolabels']:
                infolabels = json.loads(re.sub(r",\s*(\w+)", r", '\1'", re.sub(r"\{(\w+)", r"{'\1'", match['infolabels'].replace('\\','\\\\'))).replace("'", '"'))
            infolabels['title'] = match['fmtd_title']

            item = {'addon_id' : match['addon_id'], 'section_title':match['section_title'], 'sub_section_title':match['sub_section_title'], 'section_addon_title' :match['section_addon_title'], 'sub_section_addon_title':match['sub_section_addon_title'], 'title':match['title'], 'fmtd_title':match['fmtd_title'], 'url' : match['url'], 'infolabels': common.decode_dict(infolabels), 'image_url':match['image_url'], 'fanart_url':match['fanart_url'], 'isplayable' : match['isplayable'], 'isfolder':match['isfolder']}
            
            favorites.append(item)
            
        return favorites
        
    def get_my_favorites(self, section_title='all', sub_section_title='all', item_mode='main'):
        return self.get_favorites(section_title=section_title, sub_section_title=sub_section_title, addon_id=self.addon_id, item_mode=item_mode)
        
    def get_my_main_sections(self, item_mode='main'):
        return self.get_main_sections(addon_id=self.addon_id, item_mode=item_mode)
        
    def get_my_sub_sections(self, section_title, item_mode='main'):
        return self.get_sub_sections(section_title, addon_id=self.addon_id, item_mode=item_mode)
        
    def get_addons_that_have_favorites(self):
    
        addons = []
    
        sql_select = "SELECT DISTINCT addon_id FROM favorites ORDER BY addon_id"
    
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
        
    def add_my_fav_directory(self, title='Favorites', img='', fanart='', item_mode='main'):
        if not self.sys_argv:
            common.addon.log_error('-' + HELPER + '- -' +'sys.argv not passed in Favorites __init__(); Favorites directory will not be created.')
            return
            
        try:
            tmp_addon_id = 'plugin.video.favorites'
            tmp_addon = Addon(tmp_addon_id)
            tmp_addon_name = tmp_addon.get_name()                
        except:
            common.addon.log_error('-' + HELPER + '- -' +'Favorites video plugin not installed; Favorites directory will not be created.')
            common.notify(self.addon_id, 'small', ' - My Favorites video addon required', 'Please install My Favorites video addon from The ONE\'s XBMC Addons Repository.', '10000')                
            return
            
        
        listitem = xbmcgui.ListItem(title, iconImage=img, thumbnailImage=img)
        listitem.setProperty('fanart_image', fanart)
        uni_fav = {
            'uni_fav_addon_id': self.addon_id,
            'uni_fav_mode': 'display',
            'uni_fav_item_mode': item_mode
            }
        
        params = self._build_params( {'mode':'browse', 'addon_id':self.addon_id, 'local':'true', 'item_mode':item_mode} )
        xbmcplugin.addDirectoryItem(handle=int(self.sys_argv[1]),url='plugin://plugin.video.favorites/'+params,isFolder=True,listitem=listitem)
    
if sys.argv and len(sys.argv) >= 4 and sys.argv[3] == 'script.module.universal.favorites':    
    
    sys.argv[0] = 'script.module.universal'
    addon_fav = Addon('script.module.universal', sys.argv)
        
    addon_id = addon_fav.queries.pop('uni_fav_addon_id')
    fav_mode = addon_fav.queries.pop('uni_fav_mode')
    item_mode = addon_fav.queries.pop('uni_fav_item_mode', 'main')
    title = addon_fav.queries.pop('uni_fav_title', '')
    fmtd_title = addon_fav.queries.pop('uni_fav_fmtd_title', title)
    url = addon_fav.queries.pop('uni_fav_url', '')    
    section_title = addon_fav.queries.pop('uni_fav_section_title', '')
    section_addon_title = addon_fav.queries.pop('uni_fav_section_addon_title', '')
    sub_section_title = addon_fav.queries.pop('uni_fav_sub_section_title', '')
    sub_section_addon_title = addon_fav.queries.pop('uni_fav_sub_section_addon_title', '')
    img = addon_fav.queries.pop('uni_fav_img', '')
    fanart = addon_fav.queries.pop('uni_fav_fanart', '')
    is_playable = common.str2bool( addon_fav.queries.pop('uni_fav_is_playable', '') )
    is_folder = common.str2bool( addon_fav.queries.pop('uni_fav_is_folder', '') )
            
    fav = Favorites(addon_id)
    if fav_mode == 'add':
        fav.add_item_to_db(title, fmtd_title, url, section_title, section_addon_title, sub_section_title, sub_section_addon_title, addon_fav.queries, img, fanart, is_playable, is_folder)
    elif fav_mode == 'delete':
        fav.delete_item_from_db(title, fmtd_title, section_title, section_addon_title, sub_section_title, sub_section_addon_title, item_mode)
        xbmc.executebuiltin("Container.Refresh")
