'''
create/install metadata containers,
v1.0
currently very specific to icefilms.info
'''

# NOTE: these are imported later on in the create container function:
# from cleaners import *
# import clean_dirs

import os,sys
import shutil
import xbmcvfs
import common

#necessary so that the metacontainers.py can use the scrapers
try: import xbmc
except:
     xbmc_imported = False
else:
     xbmc_imported = True


#append lib directory
sys.path.append((os.path.split(common.addon_path))[0])

'''
   Use MySQL settings if applicable, else:
       Use SQLIte3 wherever possible, needed for newer versions of XBMC
       Keep pysqlite2 for legacy support
'''
try:
    if  common.addon.get_setting('use_remote_db')=='true' and \
        common.addon.get_setting('db_address') is not None and \
        common.addon.get_setting('db_user') is not None and \
        common.addon.get_setting('db_pass') is not None and \
        common.addon.get_setting('db_name') is not None:
        import mysql.connector as database
        common.addon.log('Metacontainers - Loading MySQLdb as DB engine', 2)
        DB = 'mysql'
    else:
        raise ValueError('MySQL not enabled or not setup correctly')
except:
    try: 
        from sqlite3 import dbapi2 as database
        common.addon.log('Loading sqlite3 as DB engine version: %s' % database.sqlite_version, 2)
    except: 
        from pysqlite2 import dbapi2 as database
        common.addon.log('Metacontainers - pysqlite2 as DB engine', 2)
    DB = 'sqlite'


class MetaContainer:

    def __init__(self):

        #Check if a path has been set in the addon settings
        settings_path = common.addon.get_setting('meta_folder_location')
        
        if settings_path:
            self.path = xbmc.translatePath(settings_path)
        else:
            self.path = xbmc.translatePath('special://profile/addon_data/script.module.metahandler')

        self.work_path = os.path.join(self.path, 'work', '')
        self.cache_path = os.path.join(self.path,  'meta_cache')
        self.videocache = os.path.join(self.cache_path, 'video_cache.db')
        self.work_videocache = os.path.join(self.work_path, 'video_cache.db')
        self.movie_images = os.path.join(self.cache_path, 'movie')
        self.tv_images = os.path.join(self.cache_path, 'tvshow')        
        
        self.table_list = ['movie_meta', 'tvshow_meta', 'season_meta', 'episode_meta']
     
        common.addon.log('---------------------------------------------------------------------------------------', 0)
        #delete and re-create work_path to ensure no previous files are left over
        self._del_path(self.work_path)
        
        #Re-Create work folder
        self.make_dir(self.work_path)

               
    def get_workpath(self):
        return self._work_path


    def get_cachepath(self):
        return self._cache_path
            

    def make_dir(self, mypath):
        ''' Creates sub-directories if they are not found. '''
        try:
            if not xbmcvfs.exists(mypath): xbmcvfs.mkdirs(mypath)
        except:
            if not os.path.exists(mypath): os.makedirs(mypath)  


    def _del_path(self, path):

        common.addon.log('Attempting to remove folder: %s' % path, 0)
        if xbmcvfs.exists(path):
            try:
                common.addon.log('Removing folder: %s' % path, 0)
                try:
                    dirs, files = xbmcvfs.listdir(path)
                    for file in files:
                        xbmcvfs.delete(os.path.join(path, file))
                    success = xbmcvfs.rmdir(path)
                    if success == 0:
                        raise
                except Exception as e:
                    try:
                        common.addon.log('Failed to delete path using xbmcvfs: %s' % e, 4)
                        common.addon.log('Attempting to remove with shutil: %s' % path, 0)
                        shutil.rmtree(path)
                    except:
                        raise
            except Exception as e:
                common.addon.log('Failed to delete path: %s' % e, 4)
                return False
        else:
            common.addon.log('Folder does not exist: %s' % path)


    def _extract_zip(self, src, dest):
            try:
                common.addon.log('Extracting '+str(src)+' to '+str(dest), 0)
                #make sure there are no double slashes in paths
                src=os.path.normpath(src)
                dest=os.path.normpath(dest) 

                #Unzip - Only if file size is > 1KB
                if os.path.getsize(src) > 10000:
                    xbmc.executebuiltin("XBMC.Extract("+src+","+dest+")")
                else:
                    common.addon.log('************* Error: File size is too small', 4)
                    return False

            except:
                common.addon.log('Extraction failed!', 4)
                return False
            else:                
                common.addon.log('Extraction success!', 0)
                return True


    def _insert_metadata(self, table):
        '''
        Batch insert records into existing cache DB

        Used to add extra meta packs to existing DB
        Duplicate key errors are ignored
        
        Args:
            table (str): table name to select from/insert into
        '''

        common.addon.log('Inserting records into table: %s' % table, 0)
        # try:
        if DB == 'mysql':
            try: 	from sqlite3  import dbapi2 as sqlite
            except: from pysqlite2 import dbapi2 as sqlite

            db_address = common.addon.get_setting('db_address')
            db_port = common.addon.get_setting('db_port')
            if db_port: db_address = '%s:%s' %(db_address,db_port)
            db_user = common.addon.get_setting('db_user')
            db_pass = common.addon.get_setting('db_pass')
            db_name = common.addon.get_setting('db_name')

            db = database.connect(db_name, db_user, db_pass, db_address, buffered=True)
            mysql_cur = db.cursor()
            work_db = sqlite.connect(self.work_videocache);
            rows = work_db.execute('SELECT * FROM %s' %table).fetchall()

            cur = work_db.cursor()
            rows = cur.execute('SELECT * FROM %s' %table).fetchall()
            if rows:
                cols = ','.join([c[0] for c in cur.description])
                num_args = len(rows[0])
                args = ','.join(['%s']*num_args)
                sql_insert = 'INSERT IGNORE INTO %s (%s) VALUES(%s)'%(table, cols, args)
                mysql_cur.executemany(sql_insert, rows)
            work_db.close()

        else:
            sql_insert = 'INSERT OR IGNORE INTO %s SELECT * FROM work_db.%s' % (table, table)        
            common.addon.log('SQL Insert: %s' % sql_insert, 0)
            common.addon.log(self.work_videocache, 0)
            db = database.connect(self.videocache)
            db.execute('ATTACH DATABASE "%s" as work_db' % self.work_videocache)
            db.execute(sql_insert)
        # except Exception as e:
            # common.addon.log('************* Error attempting to insert into table: %s with error: %s' % (table, e), 4)
            # pass
            # return False
        db.commit()
        db.close()
        return True

         
    def install_metadata_container(self, containerpath, installtype):

        common.addon.log('Attempting to install type: %s  path: %s' % (installtype, containerpath), 0)

        if installtype=='database':
            extract = self._extract_zip(containerpath, self.work_path)
            #Sleep for 5 seconds to ensure DB is unzipped - else insert will fail
            xbmc.sleep(5000)
            for table in self.table_list:
                install = self._insert_metadata(table)
            
            if extract and install:
                return True
                
        elif installtype=='movie_images':
            return self._extract_zip(containerpath, self.movie_images)

        elif installtype=='tv_images':
            return self._extract_zip(containerpath, self.tv_images)

        else:
            common.addon.log('********* Not a valid installtype: %s' % installtype, 3)
            return False
