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

#necessary so that the metacontainers.py can use the scrapers
try: import xbmc, xbmcaddon
except:
     xbmc_imported = False
else:
     xbmc_imported = True

#append lib directory
addon = xbmcaddon.Addon(id='script.module.metahandler')
addon_path = addon.getAddonInfo('path')
sys.path.append((os.path.split(addon_path))[0])

'''
   Use SQLIte3 wherever possible, needed for newer versions of XBMC
   Keep pysqlite2 for legacy support
'''
try: 
    from sqlite3 import dbapi2 as sqlite
    print 'Metacontainers - Loading sqlite3 as DB engine'
except: 
    from pysqlite2 import dbapi2 as sqlite
    print 'Metacontainers - pysqlite2 as DB engine'

class MetaContainer:

    def __init__(self, path='special://profile/addon_data/script.module.metahandler'):
        #!!!! This must be matched to the path in meteahandler.py MetaData __init__

        #Check if a path has been set in the addon settings
        settings_path = addon.getSetting('meta_folder_location')
        
        if settings_path:
            self.path = xbmc.translatePath(settings_path)
        else:
            self.path = xbmc.translatePath(path)

        self.work_path = os.path.join(self.path, 'work')
        self.cache_path = os.path.join(self.path,  'meta_cache')
        self.videocache = os.path.join(self.cache_path, 'video_cache.db')
        self.work_videocache = os.path.join(self.work_path, 'video_cache.db')
        self.movie_images = os.path.join(self.cache_path, 'movie')
        self.tv_images = os.path.join(self.cache_path, 'tvshow')        
        
        self.table_list = ['movie_meta', 'tvshow_meta', 'season_meta', 'episode_meta']
     
        print '---------------------------------------------------------------------------------------'
        #delete and re-create work_path to ensure no previous files are left over
        if os.path.exists(self.work_path):
            import shutil
            try:
                print 'Removing previous work folder: %s' % self.work_path
                shutil.rmtree(self.work_path)
            except Exception, e:
                print 'Failed to delete work folder: %s' % e
                pass
        
        #Re-Create work folder
        self.make_dir(self.work_path)

               
    def get_workpath(self):
        return self._work_path


    def get_cachepath(self):
        return self._cache_path
            

    def make_dir(self, mypath):
        ''' Creates sub-directories if they are not found. '''
        if not os.path.exists(mypath): os.makedirs(mypath)   

   
    def _del_metadir(self, path=''):
    
        if path:
            cache_path = path
        else:
            catch_path = self.cache_path
      
        #Nuke the old meta_caches folder (if it exists) and install this meta_caches folder.
        #Will only ever delete a meta_caches folder, so is farly safe (won't delete anything it is fed)
    
        if os.path.exists(catch_path):
                try:
                    shutil.rmtree(catch_path)
                except:
                    print 'Failed to delete old meta'
                    return False
                else:
                    print 'deleted old meta'
                    return True


    def _del_path(self, path):
    
        if os.path.exists(path):
                try:
                    shutil.rmtree(path)
                except:
                    print 'Failed to delete old meta'
                    return False
                else:
                    print 'deleted old meta'
                    return True

    
    def _extract_zip(self, src, dest):
            try:
                print 'Extracting '+str(src)+' to '+str(dest)
                #make sure there are no double slashes in paths
                src=os.path.normpath(src)
                dest=os.path.normpath(dest) 
    
                #Unzip - Only if file size is > 1KB
                if os.path.getsize(src) > 10000:
                    xbmc.executebuiltin("XBMC.Extract("+src+","+dest+")")
                else:
                    print '************* Error: File size is too small'
                    return False
    
            except:
                print 'Extraction failed!'
                return False
            else:                
                print 'Extraction success!'
                return True


    def _insert_metadata(self, table):
        '''
        Batch insert records into existing cache DB

        Used to add extra meta packs to existing DB
        Duplicate key errors are ignored
        
        Args:
            table (str): table name to select from/insert into
        '''

        print 'Inserting records into table: %s' % table
        sql_insert = 'INSERT OR IGNORE INTO %s SELECT * FROM work_db.%s' % (table, table)        
        print 'SQL Insert: %s' % sql_insert
        print self.work_videocache

        try:
            dbcon = sqlite.connect(self.videocache)
            dbcur = dbcon.cursor()
            dbcur.execute('ATTACH DATABASE "%s" as work_db' % self.work_videocache)
            dbcur.execute(sql_insert)
            dbcon.commit()
        except Exception, e:
            print '************* Error attempting to insert into table: %s with error: %s' % (table, e)
            pass
            return False
        dbcur.close()
        dbcon.close() 
        return True

         
    def install_metadata_container(self, containerpath, installtype):
    
        print 'Attempting to install type: %s  path: %s' % (installtype, containerpath)

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
            print '********* Not a valid installtype: %s' % installtype
            return False
