'''
    These classes cache metadata from TheMovieDB and TVDB.
    It uses sqlite databases.
       
    It uses themoviedb JSON api class and TVDB XML api class.
    For TVDB it currently uses a modified version of 
    Python API by James Smith (http://loopj.com)
    
    Metahandler intially created for IceFilms addon, reworked to be it's own 
    script module to be used by many addons.

    Created/Modified by: Eldorado
    
    Initial creation and credits: Daledude / Anarchintosh / WestCoast13 
    
    
*To-Do:
- write a clean database function (correct imgs_prepacked by checking if the images actually exist)
  for pre-packed container creator. also retry any downloads that failed.
  also, if  database has just been created for pre-packed container, purge all images are not referenced in database.

'''

import os
import re
import sys
from datetime import datetime
import time
import common
from TMDB import TMDB
from thetvdbapi import TheTVDB

#necessary so that the metacontainers.py can use the scrapers
import xbmc
import xbmcvfs

''' Use addon.common library for http calls '''
from addon.common.net import Net
net = Net()

sys.path.append((os.path.split(common.addon_path))[0])

'''
   Use SQLIte3 wherever possible, needed for newer versions of XBMC
   Keep pysqlite2 for legacy support
'''
try:
    if  common.addon.get_setting('use_remote_db')=='true' and   \
        common.addon.get_setting('db_address') is not None and  \
        common.addon.get_setting('db_user') is not None and     \
        common.addon.get_setting('db_pass') is not None and     \
        common.addon.get_setting('db_name') is not None:
        import mysql.connector as database
        common.addon.log('Loading MySQLdb as DB engine version: %s' % database.version.VERSION_TEXT, 2)
        DB = 'mysql'
    else:
        raise ValueError('MySQL not enabled or not setup correctly')
except:
    try: 
        from sqlite3 import dbapi2 as database
        common.addon.log('Loading sqlite3 as DB engine version: %s' % database.sqlite_version, 2)
    except: 
        from pysqlite2 import dbapi2 as database
        common.addon.log('pysqlite2 as DB engine', 2)
    DB = 'sqlite'


def make_dir(mypath, dirname):
    ''' Creates sub-directories if they are not found. '''
    subpath = os.path.join(mypath, dirname)
    try:
        if not xbmcvfs.exists(subpath): xbmcvfs.mkdirs(subpath)
    except:
        if not os.path.exists(subpath): os.makedirs(subpath)              
    return subpath


def bool2string(myinput):
    ''' Neatens up usage of prepack_images flag. '''
    if myinput is False: return 'false'
    elif myinput is True: return 'true'

        
class MetaData:  
    '''
    This class performs all the handling of meta data, requesting, storing and sending back to calling application

        - Create cache DB if it does not exist
        - Create a meta data zip file container to share
        - Get the meta data from TMDB/IMDB/TVDB
        - Store/Retrieve meta from cache DB
        - Download image files locally
    '''  

     
    def __init__(self, prepack_images=False, preparezip=False, tmdb_api_key=common.addon.get_setting('tmdb_api_key'), omdb_api_key=common.addon.get_setting('omdb_api_key')):

        #Check if a path has been set in the addon settings
        settings_path = common.addon.get_setting('meta_folder_location')
        
        # TMDB constants
        self.tmdb_image_url = ''
        self.tmdb_api_key = common.addon.get_setting('tmdb_api_key') if common.addon.get_setting('override_keys') == 'true' else tmdb_api_key
        self.omdb_api_key = omdb_api_key
               
        if settings_path:
            self.path = xbmc.translatePath(settings_path)
        else:
            self.path = common.profile_path()
        
        self.cache_path = make_dir(self.path, 'meta_cache')

        if prepack_images:
            #create container working directory
            #!!!!!Must be matched to workdir in metacontainers.py create_container()
            self.work_path = make_dir(self.path, 'work')
            
        #set movie/tvshow constants
        self.type_movie = 'movie'
        self.type_tvshow = 'tvshow'
        self.type_season = 'season'        
        self.type_episode = 'episode'
            
        #this init auto-constructs necessary folder hierarchies.

        # control whether class is being used to prepare pre-packaged .zip
        self.prepack_images = bool2string(prepack_images)
        self.videocache = os.path.join(self.cache_path, 'video_cache.db')

        self.tvpath = make_dir(self.cache_path, self.type_tvshow)
        self.tvcovers = make_dir(self.tvpath, 'covers')
        self.tvbackdrops = make_dir(self.tvpath, 'backdrops')
        self.tvbanners = make_dir(self.tvpath, 'banners')

        self.mvpath = make_dir(self.cache_path, self.type_movie)
        self.mvcovers = make_dir(self.mvpath, 'covers')
        self.mvbackdrops = make_dir(self.mvpath, 'backdrops')

        # connect to db at class init and use it globally
        if DB == 'mysql':
            class MySQLCursorDict(database.cursor.MySQLCursor):
                def _row_to_python(self, rowdata, desc=None):
                    row = super(MySQLCursorDict, self)._row_to_python(rowdata, desc)
                    if row:
                        return dict(zip(self.column_names, row))
                    return None
            db_address = common.addon.get_setting('db_address')
            db_port = common.addon.get_setting('db_port')
            if db_port: db_address = '%s:%s' %(db_address,db_port)
            db_user = common.addon.get_setting('db_user')
            db_pass = common.addon.get_setting('db_pass')
            db_name = common.addon.get_setting('db_name')
            self.dbcon = database.connect(database=db_name, user=db_user, password=db_pass, host=db_address, buffered=True)
            self.dbcur = self.dbcon.cursor(cursor_class=MySQLCursorDict, buffered=True)
        else:
            self.dbcon = database.connect(self.videocache)
            self.dbcon.row_factory = database.Row # return results indexed by field names and not numbers so we can convert to dict
            self.dbcur = self.dbcon.cursor()

        # initialize cache db
        self._cache_create_movie_db()
        
        # Check TMDB configuration, update if necessary
        self._set_tmdb_config()

        ## !!!!!!!!!!!!!!!!!! Temporary code to update movie_meta columns cover_url and backdrop_url to store only filename !!!!!!!!!!!!!!!!!!!!!
 
        ## We have matches with outdated url, so lets strip the url out and only keep filename 
        try:

            if DB == 'mysql':
                sql_select = "SELECT imdb_id, tmdb_id, cover_url, backdrop_url "\
                                "FROM movie_meta "\
                                "WHERE (substring(cover_url, 1, 36 ) = 'http://d3gtl9l2a4fn1j.cloudfront.net' "\
                                "OR substring(backdrop_url, 1, 36 ) = 'http://d3gtl9l2a4fn1j.cloudfront.net')"
                self.dbcur.execute(sql_select)
                matchedrows = self.dbcur.fetchall()[0]
                
                if matchedrows:
                    sql_update = "UPDATE movie_meta "\
                                    "SET cover_url = SUBSTRING_INDEX(cover_url, '/', -1), "\
                                    "backdrop_url = SUBSTRING_INDEX(backdrop_url, '/', -1) "\
                                    "where substring(cover_url, 1, 36 ) = 'http://d3gtl9l2a4fn1j.cloudfront.net' "\
                                    "or substring(backdrop_url, 1, 36 ) = 'http://d3gtl9l2a4fn1j.cloudfront.net'"
                    self.dbcur.execute(sql_update)
                    self.dbcon.commit()
                    common.addon.log('MySQL rows successfully updated')

                else:
                    common.addon.log('No MySQL rows requiring update')                    
                
            else:
          
                sql_select = "SELECT imdb_id, tmdb_id, cover_url, thumb_url, backdrop_url "\
                                "FROM movie_meta "\
                                "WHERE substr(cover_url, 1, 36 ) = 'http://d3gtl9l2a4fn1j.cloudfront.net' "\
                                "OR substr(thumb_url, 1, 36 ) = 'http://d3gtl9l2a4fn1j.cloudfront.net' "\
                                "OR substr(backdrop_url, 1, 36 ) = 'http://d3gtl9l2a4fn1j.cloudfront.net' "\
                                "OR substr(cover_url, 1, 1 ) in ('w', 'o') "\
                                "OR substr(thumb_url, 1, 1 ) in ('w', 'o') "\
                                "OR substr(backdrop_url, 1, 1 ) in ('w', 'o') "
                self.dbcur.execute(sql_select)
                matchedrows = self.dbcur.fetchall()

                if matchedrows:
                    dictrows = [dict(row) for row in matchedrows]
                    for row in dictrows:
                        if row["cover_url"]:
                            row["cover_url"] = '/' + row["cover_url"].split('/')[-1]
                        if row["thumb_url"]:
                            row["thumb_url"] = '/' + row["thumb_url"].split('/')[-1]
                        if row["backdrop_url"]:
                            row["backdrop_url"] = '/' + row["backdrop_url"].split('/')[-1]

                    sql_update = "UPDATE movie_meta SET cover_url = :cover_url, thumb_url = :thumb_url, backdrop_url = :backdrop_url  WHERE imdb_id = :imdb_id and tmdb_id = :tmdb_id"
                    
                    self.dbcur.executemany(sql_update, dictrows)
                    self.dbcon.commit()
                    common.addon.log('SQLite rows successfully updated')
                else:
                    common.addon.log('No SQLite rows requiring update')                    
           
        except Exception as e:
            common.addon.log('************* Error updating cover and backdrop columns: %s' % e, 4)
            pass
        
        ## !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

    def __del__(self):
        ''' Cleanup db when object destroyed '''
        try:
            self.dbcur.close()
            self.dbcon.close()
        except: pass


    def _cache_create_movie_db(self):
        ''' Creates the cache tables if they do not exist.  '''   

        # Create Movie table
        sql_create = "CREATE TABLE IF NOT EXISTS movie_meta ("\
                           "imdb_id TEXT, "\
                           "tmdb_id TEXT, "\
                           "title TEXT, "\
                           "year INTEGER,"\
                           "director TEXT, "\
                           "writer TEXT, "\
                           "tagline TEXT, cast TEXT,"\
                           "rating FLOAT, "\
                           "votes TEXT, "\
                           "duration TEXT, "\
                           "plot TEXT,"\
                           "mpaa TEXT, "\
                           "premiered TEXT, "\
                           "genre TEXT, "\
                           "studio TEXT,"\
                           "thumb_url TEXT, "\
                           "cover_url TEXT, "\
                           "trailer_url TEXT, "\
                           "backdrop_url TEXT,"\
                           "imgs_prepacked TEXT,"\
                           "overlay INTEGER,"\
                           "UNIQUE(imdb_id, tmdb_id, title, year)"\
                           ");"
        if DB == 'mysql':
            sql_create = sql_create.replace("imdb_id TEXT","imdb_id VARCHAR(10)")
            sql_create = sql_create.replace("tmdb_id TEXT","tmdb_id VARCHAR(10)")
            sql_create = sql_create.replace("title TEXT"  ,"title VARCHAR(255)")

            # hack to bypass bug in myconnpy
            # create table if not exists fails bc a warning about the table
            # already existing bubbles up as an exception. This suppresses the
            # warning which would just be logged anyway.
            # http://stackoverflow.com/questions/1650946/mysql-create-table-if-not-exists-error-1050
            sql_hack = "SET sql_notes = 0;"
            self.dbcur.execute(sql_hack)
            
            self.dbcur.execute(sql_create)
            try: self.dbcur.execute('CREATE INDEX nameindex on movie_meta (title);')
            except: pass
        else:
            self.dbcur.execute(sql_create)
            self.dbcur.execute('CREATE INDEX IF NOT EXISTS nameindex on movie_meta (title);')
        common.addon.log('Table movie_meta initialized', 0)
        
        # Create TV Show table
        sql_create = "CREATE TABLE IF NOT EXISTS tvshow_meta ("\
                           "imdb_id TEXT, "\
                           "tvdb_id TEXT, "\
                           "title TEXT, "\
                           "year INTEGER,"\
                           "cast TEXT,"\
                           "rating FLOAT, "\
                           "duration TEXT, "\
                           "plot TEXT,"\
                           "mpaa TEXT, "\
                           "premiered TEXT, "\
                           "genre TEXT, "\
                           "studio TEXT,"\
                           "status TEXT,"\
                           "banner_url TEXT, "\
                           "cover_url TEXT,"\
                           "trailer_url TEXT, "\
                           "backdrop_url TEXT,"\
                           "imgs_prepacked TEXT,"\
                           "overlay INTEGER,"\
                           "UNIQUE(imdb_id, tvdb_id, title)"\
                           ");"

        if DB == 'mysql':
            sql_create = sql_create.replace("imdb_id TEXT","imdb_id VARCHAR(10)")
            sql_create = sql_create.replace("tvdb_id TEXT","tvdb_id VARCHAR(10)")
            sql_create = sql_create.replace("title TEXT"  ,"title VARCHAR(255)")
            self.dbcur.execute(sql_create)
            try: self.dbcur.execute('CREATE INDEX nameindex on tvshow_meta (title);')
            except: pass
        else:
            self.dbcur.execute(sql_create)
            self.dbcur.execute('CREATE INDEX IF NOT EXISTS nameindex on tvshow_meta (title);')
        common.addon.log('Table tvshow_meta initialized', 0)

        # Create Season table
        sql_create = "CREATE TABLE IF NOT EXISTS season_meta ("\
                           "imdb_id TEXT, "\
                           "tvdb_id TEXT, " \
                           "season INTEGER, "\
                           "cover_url TEXT,"\
                           "overlay INTEGER,"\
                           "UNIQUE(imdb_id, tvdb_id, season)"\
                           ");"
               
        if DB == 'mysql':
            sql_create = sql_create.replace("imdb_id TEXT","imdb_id VARCHAR(10)")
            sql_create = sql_create.replace("tvdb_id TEXT","tvdb_id VARCHAR(10)")
            self.dbcur.execute(sql_create)
        else:
            self.dbcur.execute(sql_create)
        common.addon.log('Table season_meta initialized', 0)
                
        # Create Episode table
        sql_create = "CREATE TABLE IF NOT EXISTS episode_meta ("\
                           "imdb_id TEXT, "\
                           "tvdb_id TEXT, "\
                           "episode_id TEXT, "\
                           "season INTEGER, "\
                           "episode INTEGER, "\
                           "title TEXT, "\
                           "director TEXT, "\
                           "writer TEXT, "\
                           "plot TEXT, "\
                           "rating FLOAT, "\
                           "premiered TEXT, "\
                           "poster TEXT, "\
                           "overlay INTEGER, "\
                           "UNIQUE(imdb_id, tvdb_id, episode_id, title)"\
                           ");"
        if DB == 'mysql':
            sql_create = sql_create.replace("imdb_id TEXT"   ,"imdb_id VARCHAR(10)")
            sql_create = sql_create.replace("tvdb_id TEXT"   ,"tvdb_id VARCHAR(10)")
            sql_create = sql_create.replace("episode_id TEXT","episode_id VARCHAR(10)")
            sql_create = sql_create.replace("title TEXT"     ,"title VARCHAR(255)")
            self.dbcur.execute(sql_create)
        else:
            self.dbcur.execute(sql_create)

        common.addon.log('Table episode_meta initialized', 0)

        # Create Addons table
        sql_create = "CREATE TABLE IF NOT EXISTS addons ("\
                           "addon_id TEXT, "\
                           "movie_covers TEXT, "\
                           "tv_covers TEXT, "\
                           "tv_banners TEXT, "\
                           "movie_backdrops TEXT, "\
                           "tv_backdrops TEXT, "\
                           "last_update TEXT, "\
                           "UNIQUE(addon_id)"\
                           ");"

        if DB == 'mysql':
            sql_create = sql_create.replace("addon_id TEXT", "addon_id VARCHAR(255)")
            self.dbcur.execute(sql_create)
        else:
            self.dbcur.execute(sql_create)
        common.addon.log('Table addons initialized', 0)

        # Create Configuration table
        sql_create = "CREATE TABLE IF NOT EXISTS config ("\
                           "setting TEXT, "\
                           "value TEXT, "\
                           "UNIQUE(setting)"\
                           ");"

        if DB == 'mysql':
            sql_create = sql_create.replace("setting TEXT", "setting VARCHAR(255)")
            sql_create = sql_create.replace("value TEXT", "value VARCHAR(255)")
            self.dbcur.execute(sql_create)
        else:
            self.dbcur.execute(sql_create)
        common.addon.log('Table config initialized', 0)
        

    def _init_movie_meta(self, imdb_id, tmdb_id, name, year=0):
        '''
        Initializes a movie_meta dictionary with default values, to ensure we always
        have all fields
        
        Args:
            imdb_id (str): IMDB ID
            tmdb_id (str): TMDB ID
            name (str): full name of movie you are searching
            year (int): 4 digit year
                        
        Returns:
            DICT in the structure of what is required to write to the DB
        '''                
        
        if year:
            int(year)
        else:
            year = 0
            
        meta = {}
        meta['imdb_id'] = imdb_id
        meta['tmdb_id'] = str(tmdb_id)
        meta['title'] = name
        meta['year'] = int(year)
        meta['writer'] = ''
        meta['director'] = ''
        meta['tagline'] = ''
        meta['cast'] = []
        meta['rating'] = 0
        meta['votes'] = ''
        meta['duration'] = ''
        meta['plot'] = ''
        meta['mpaa'] = ''
        meta['premiered'] = ''
        meta['trailer_url'] = ''
        meta['genre'] = ''
        meta['studio'] = ''
        
        #set whether that database row will be accompanied by pre-packed images.                        
        meta['imgs_prepacked'] = self.prepack_images
        
        meta['thumb_url'] = ''
        meta['cover_url'] = ''
        meta['backdrop_url'] = ''
        meta['overlay'] = 6
        return meta


    def _init_tvshow_meta(self, imdb_id, tvdb_id, name, year=0):
        '''
        Initializes a tvshow_meta dictionary with default values, to ensure we always
        have all fields
        
        Args:
            imdb_id (str): IMDB ID
            tvdb_id (str): TVDB ID
            name (str): full name of movie you are searching
            year (int): 4 digit year
                        
        Returns:
            DICT in the structure of what is required to write to the DB
        '''
        
        if year:
            int(year)
        else:
            year = 0
            
        meta = {}
        meta['imdb_id'] = imdb_id
        meta['tvdb_id'] = tvdb_id
        meta['title'] = name
        meta['TVShowTitle'] = name
        meta['rating'] = 0
        meta['duration'] = ''
        meta['plot'] = ''
        meta['mpaa'] = ''
        meta['premiered'] = ''
        meta['year'] = int(year)
        meta['trailer_url'] = ''
        meta['genre'] = ''
        meta['studio'] = ''
        meta['status'] = ''        
        meta['cast'] = []
        meta['banner_url'] = ''
        
        #set whether that database row will be accompanied by pre-packed images.
        meta['imgs_prepacked'] = self.prepack_images
        
        meta['cover_url'] = ''
        meta['backdrop_url'] = ''
        meta['overlay'] = 6
        meta['episode'] = 0
        meta['playcount'] = 0
        return meta


    def __init_episode_meta(self, imdb_id, tvdb_id, episode_title, season, episode, air_date):
        '''
        Initializes a movie_meta dictionary with default values, to ensure we always
        have all fields
        
        Args:
            imdb_id (str): IMDB ID
            tvdb_id (str): TVDB ID
            episode_title (str): full name of Episode you are searching - NOT TV Show name
            season (int): episode season number
            episode (int): episode number
            air_date (str): air date (premiered data) of episode - YYYY-MM-DD
                        
        Returns:
            DICT in the structure of what is required to write to the DB
        '''

        meta = {}
        meta['imdb_id']=imdb_id
        meta['tvdb_id']=''
        meta['episode_id'] = ''                
        meta['season']= int(season)
        meta['episode']= int(episode)
        meta['title']= episode_title
        meta['director'] = ''
        meta['writer'] = ''
        meta['plot'] = ''
        meta['rating'] = 0
        meta['premiered'] = air_date
        meta['poster'] = ''
        meta['cover_url']= ''
        meta['trailer_url']=''
        meta['premiered'] = ''
        meta['backdrop_url'] = ''
        meta['overlay'] = 6
        return meta
        

    def __get_tmdb_language(self):
        tmdb_language = common.addon.get_setting('tmdb_language')
        if tmdb_language:
            return re.sub(".*\((\w+)\).*","\\1",tmdb_language)
        else:
            return 'en'

            
    def __get_tvdb_language(self) :
        tvdb_language = common.addon.get_setting('tvdb_language')
        if tvdb_language and tvdb_language!='':
            return re.sub(".*\((\w+)\).*","\\1",tvdb_language)
        else:
            return 'en'

            
    def _string_compare(self, s1, s2):
        """ Method that takes two strings and returns True or False, based
            on if they are equal, regardless of case.
        """
        try:
            return s1.lower() == s2.lower()
        except AttributeError:
            common.addon.log("Please only pass strings into this method.", 4)
            common.addon.log("You passed a %s and %s" % (s1.__class__, s2.__class__), 4)


    def _clean_string(self, string):
        """ 
            Method that takes a string and returns it cleaned of any special characters
            in order to do proper string comparisons
        """        
        try:
            return ''.join(e for e in string if e.isalnum())
        except:
            return string


    def _convert_date(self, string, in_format, out_format):
        ''' Helper method to convert a string date to a given format '''
        
        #Legacy check, Python 2.4 does not have strptime attribute, instroduced in 2.5
        if hasattr(datetime, 'strptime'):
            strptime = datetime.strptime
        else:
            strptime = lambda date_string, format: datetime(*(time.strptime(date_string, format)[0:6]))
        
        #strptime = lambda date_string, format: datetime(*(time.strptime(date_string, format)[0:6]))
        try:
            a = strptime(string, in_format).strftime(out_format)
        except Exception as e:
            common.addon.log('************* Error Date conversion failed: %s' % e, 4)
            return None
        return a


    def _downloadimages(self, url, path, name):
        '''
        Download images to save locally
        
        Args:
            url (str): picture url
            path (str): destination path
            name (str): filename
        '''                 

        if not xbmcvfs.exists(path):
            make_dir('', path)
        
        full_path = os.path.join(path, name)
        self._dl_code(url, full_path)              


    def _picname(self,url):
        '''
        Get image name from url (ie my_movie_poster.jpg)      
        
        Args:
            url (str): full url of image                        
        Returns:
            picname (str) representing image name from file
        '''           
        picname = re.split('\/+', url)
        return picname[-1]
         
        
    def _dl_code(self,url,mypath):
        '''
        Downloads images to store locally       
        
        Args:
            url (str): url of image to download
            mypath (str): local path to save image to
        '''        
        common.addon.log('Attempting to download image from url: %s ' % url, 0)
        common.addon.log('Saving to destination: %s ' % mypath, 0)
        if url.startswith('http://'):
          
            try:
                 data = net.http_GET(url).content
                 fh = open(mypath, 'wb')
                 fh.write(data)  
                 fh.close()
            except Exception as e:
                common.addon.log('Image download failed: %s ' % e, 4)
        else:
            if url is not None:
                common.addon.log('Not a valid url: %s ' % url, 4)


    def _valid_imdb_id(self, imdb_id):
        '''
        Check and return a valid IMDB ID    
        
        Args:
            imdb_id (str): IMDB ID
        Returns:
            imdb_id (str) if valid with leading tt, else None
        '''      
        # add the tt if not found. integer aware.
        if imdb_id:
            if not imdb_id.startswith('tt'):
                imdb_id = 'tt%s' % imdb_id
            if re.search('tt[0-9]{7}', imdb_id):
                return imdb_id
            else:
                return None


    def _remove_none_values(self, meta):
        ''' Ensure we are not sending back any None values, XBMC doesn't like them '''
        for item in meta:
            if meta[item] is None:
                meta[item] = ''            
        return meta


    def __insert_from_dict(self, table, size):
        ''' Create a SQL Insert statement with dictionary values '''
        sql = 'INSERT INTO %s ' % table
        
        if DB == 'mysql':
            format = ', '.join(['%s'] * size)
        else:
            format = ', '.join('?' * size)
        
        sql_insert = sql + 'Values (%s)' % format
        return sql_insert


    def __set_playcount(self, overlay):
        '''
        Quick function to check overlay and set playcount
        Playcount info label is required to have > 0 in order for watched flag to display in Frodo
        '''
        if int(overlay) == 7:
            return 1
        else:
            return 0


    def _get_config(self, setting):
        '''
        Query local Config table for values
        '''
        
        #Query local table first for current values
        sql_select = "SELECT * FROM config where setting = '%s'" % setting

        common.addon.log('Looking up in local cache for config data: %s' % setting, 0)
        common.addon.log('SQL Select: %s' % sql_select, 0)        

        try:    
            self.dbcur.execute(sql_select)
            matchedrow = self.dbcur.fetchone()
        except Exception as e:
            common.addon.log('************* Error selecting from cache db: %s' % e, 4)
            return None

        if matchedrow:
            common.addon.log('Found config data in cache table for setting: %s value: %s' % (setting, dict(matchedrow)), 0)
            return dict(matchedrow)['value']
        else:
            common.addon.log('No match in local DB for config setting: %s' % setting, 0)
            return None            
            

    def _set_config(self, setting, value):
        '''
        Set local Config table for values
        '''
        
        try:
            sql_insert = "REPLACE INTO config (setting, value) VALUES(%s,%s)"
            if DB == 'sqlite':
                sql_insert = 'INSERT OR ' + sql_insert.replace('%s', '?')

            common.addon.log('Updating local cache for config data: %s value: %s' % (setting, value), 0)
            common.addon.log('SQL Insert: %s' % sql_insert, 0)                 

            self.dbcur.execute(sql_insert, (setting, value))
            self.dbcon.commit()
        except Exception as e:
            common.addon.log('************* Error updating cache db: %s' % e, 4)
            return None
            

    def _set_tmdb_config(self):
        '''
        Query config database for required TMDB config values, set constants as needed
        Validate cache timestamp to ensure it is only refreshed once every 7 days
        '''

        common.addon.log('Looking up TMDB config cache values', 0)        
        tmdb_image_url = self._get_config('tmdb_image_url')
        tmdb_config_timestamp = self._get_config('tmdb_config_timestamp')
        
        #Grab current time in seconds            
        now = time.time()
        age = 0

        #Cache limit is 7 days, value needs to be in seconds: 60 seconds * 60 minutes * 24 hours * 7 days
        expire = 60 * 60 * 24 * 7
              
        #Check if image and timestamp values are valid
        if tmdb_image_url and tmdb_config_timestamp:
            created = float(tmdb_config_timestamp)
            age = now - created
            common.addon.log('Cache age: %s , Expire: %s' % (age, expire), 0)
            
            #If cache hasn't expired, set constant values
            if age <= float(expire):
                common.addon.log('Cache still valid, setting values', 0)
                common.addon.log('Setting tmdb_image_url: %s' % tmdb_image_url, 0)
                self.tmdb_image_url = tmdb_image_url
            else:
                common.addon.log('Cache is too old, need to request new values', 0)
        
        #Either we don't have the values or the cache has expired, so lets request and set them - update cache in the end
        if (not tmdb_image_url or not tmdb_config_timestamp) or age > expire:
            common.addon.log('No cached config data found or cache expired, requesting from TMDB', 0)

            tmdb = TMDB(tmdb_api_key=self.tmdb_api_key, omdb_api_key=self.omdb_api_key, lang=self.__get_tmdb_language())
            config_data = tmdb.call_config()

            if config_data:
                self.tmdb_image_url = config_data['images']['base_url']
                self._set_config('tmdb_image_url', config_data['images']['base_url'])
                self._set_config('tmdb_config_timestamp', now)
            else:
                self.tmdb_image_url = tmdb_image_url
                

    def check_meta_installed(self, addon_id):
        '''
        Check if a meta data pack has been installed for a specific addon

        Queries the 'addons' table, if a matching row is found then we can assume the pack has been installed
        
        Args:
            addon_id (str): unique name/id to identify an addon
                        
        Returns:
            matchedrow (dict) : matched row from addon table
        '''

        if addon_id:
            sql_select = "SELECT * FROM addons WHERE addon_id = '%s'" % addon_id
        else:
            common.addon.log('Invalid addon id', 3)
            return False
        
        common.addon.log('Looking up in local cache for addon id: %s' % addon_id, 0)
        common.addon.log('SQL Select: %s' % sql_select, 0)
        try:    
            self.dbcur.execute(sql_select)
            matchedrow = self.dbcur.fetchone()            
        except Exception as e:
            common.addon.log('************* Error selecting from cache db: %s' % e, 4)
            return None
        
        if matchedrow:
            common.addon.log('Found addon id in cache table: %s' % dict(matchedrow), 0)
            return dict(matchedrow)
        else:
            common.addon.log('No match in local DB for addon_id: %s' % addon_id, 0)
            return False


    def insert_meta_installed(self, addon_id, last_update, movie_covers='false', tv_covers='false', tv_banners='false', movie_backdrops='false', tv_backdrops='false'):
        '''
        Insert a record into addons table

        Insert a unique addon id AFTER a meta data pack has been installed
        
        Args:
            addon_id (str): unique name/id to identify an addon
            last_update (str): date of last meta pack installed - use to check to install meta updates
        Kwargs:
            movie_covers (str): true/false if movie covers has been downloaded/installed
            tv_covers (str): true/false if tv covers has been downloaded/installed            
            movie_backdrops (str): true/false if movie backdrops has been downloaded/installed
            tv_backdrops (str): true/false if tv backdrops has been downloaded/installed
        '''

        if addon_id:
            sql_insert = "INSERT INTO addons(addon_id, movie_covers, tv_covers, tv_banners, movie_backdrops, tv_backdrops, last_update) VALUES (?,?,?,?,?,?,?)"
        else:
            common.addon.log('Invalid addon id', 3)
            return
        
        common.addon.log('Inserting into addons table addon id: %s' % addon_id, 0)
        common.addon.log('SQL Insert: %s' % sql_insert, 0)
        try:
            self.dbcur.execute(sql_insert, (addon_id, movie_covers, tv_covers, tv_banners, movie_backdrops, tv_backdrops, last_update))
            self.dbcon.commit()            
        except Exception as e:
            common.addon.log('************* Error inserting into cache db: %s' % e, 4)
            return


    def update_meta_installed(self, addon_id, movie_covers=False, tv_covers=False, tv_banners=False, movie_backdrops=False, tv_backdrops=False, last_update=False):
        '''
        Update a record into addons table

        Insert a unique addon id AFTER a meta data pack has been installed
        
        Args:
            addon_id (str): unique name/id to identify an addon
        Kwargs:
            movie_covers (str): true/false if movie covers has been downloaded/installed
            tv_covers (str): true/false if tv covers has been downloaded/installed
            tv_bannerss (str): true/false if tv banners has been downloaded/installed
            movie_backdrops (str): true/false if movie backdrops has been downloaded/installed
            tv_backdrops (str): true/false if tv backdrops has been downloaded/installed            
        '''

        if addon_id:
            if movie_covers:
                sql_update = "UPDATE addons SET movie_covers = '%s'" % movie_covers
            elif tv_covers:
                sql_update = "UPDATE addons SET tv_covers = '%s'" % tv_covers
            elif tv_banners:
                sql_update = "UPDATE addons SET tv_banners = '%s'" % tv_banners
            elif movie_backdrops:
                sql_update = "UPDATE addons SET movie_backdrops = '%s'" % movie_backdrops
            elif tv_backdrops:
                sql_update = "UPDATE addons SET tv_backdrops = '%s'" % tv_backdrops
            elif last_update:
                sql_update = "UPDATE addons SET last_update = '%s'" % last_update
            else:
                common.addon.log('No update field specified', 3)
                return
        else:
            common.addon.log('Invalid addon id', 3)
            return
        
        common.addon.log('Updating addons table addon id: %s movie_covers: %s tv_covers: %s tv_banners: %s movie_backdrops: %s tv_backdrops: %s last_update: %s' % (addon_id, movie_covers, tv_covers, tv_banners, movie_backdrops, tv_backdrops, last_update), 0)
        common.addon.log('SQL Update: %s' % sql_update, 0)
        try:    
            self.dbcur.execute(sql_update)
            self.dbcon.commit()
        except Exception as e:
            common.addon.log('************* Error updating cache db: %s' % e, 4)
            return
                    

    def get_meta(self, media_type, name, imdb_id='', tmdb_id='', year='', overlay=6, update=False):
        '''
        Main method to get meta data for movie or tvshow. Will lookup by name/year 
        if no IMDB ID supplied.       
        
        Args:
            media_type (str): 'movie' or 'tvshow'
            name (str): full name of movie/tvshow you are searching
        Kwargs:
            imdb_id (str): IMDB ID        
            tmdb_id (str): TMDB ID
            year (str): 4 digit year of video, recommended to include the year whenever possible
                        to maximize correct search results.
            overlay (int): To set the default watched status (6=unwatched, 7=watched) on new videos
                        
        Returns:
            DICT of meta data or None if cannot be found.
        '''
       
        common.addon.log('---------------------------------------------------------------------------------------', 0)
        common.addon.log('Attempting to retrieve meta data for %s: %s %s %s %s' % (media_type, name, year, imdb_id, tmdb_id), 0)
 
        if imdb_id:
            imdb_id = self._valid_imdb_id(imdb_id)

        if not update:
            if imdb_id:
                meta = self._cache_lookup_by_id(media_type, imdb_id=imdb_id)
            elif tmdb_id:
                meta = self._cache_lookup_by_id(media_type, tmdb_id=tmdb_id)
            else:
                meta = self._cache_lookup_by_name(media_type, name, year)
        else:
            meta = {}

        if not meta:
            
            if media_type==self.type_movie:
                meta = self._get_tmdb_meta(imdb_id, tmdb_id, name, year)
            elif media_type==self.type_tvshow:
                meta = self._get_tvdb_meta(imdb_id, name, year)
            
            self._cache_save_video_meta(meta, name, media_type, overlay)
            
        meta = self.__format_meta(media_type, meta, name)
        
        return meta


    def __format_meta(self, media_type, meta, name):
        '''
        Format and massage movie/tv show data to prepare for return to addon
        
        Args:
            media_type (str): 'movie' or 'tvshow'
            meta (dict): movie / tv show meta data dictionary returned from cache or online
            name (str): full name of movie/tvshow you are searching
        Returns:
            DICT. Data formatted and corrected for proper return to xbmc addon
        '''      

        try:
            #We want to send back the name that was passed in   
            meta['title'] = name
            
            #Change cast back into a tuple
            if meta['cast']:
                meta['cast'] = eval(str(meta['cast']))
                
            #Return a trailer link that will play via youtube addon
            try:
                meta['trailer'] = ''
                trailer_id = ''
                if meta['trailer_url']:
                    r = re.match('^[^v]+v=(.{3,11}).*', meta['trailer_url'])
                    if r:
                        trailer_id = r.group(1)
                    else:
                        trailer_id = meta['trailer_url']
                 
                if trailer_id:
                    meta['trailer'] = 'plugin://plugin.video.youtube/?action=play_video&videoid=%s' % trailer_id
                    
            except Exception as e:
                meta['trailer'] = ''
                common.addon.log('Failed to set trailer: %s' % e, 3)
    
            #Ensure we are not sending back any None values, XBMC doesn't like them
            meta = self._remove_none_values(meta)
            
            #Add TVShowTitle infolabel
            if media_type==self.type_tvshow:
                meta['TVShowTitle'] = meta['title']
            
            #Set Watched flag for movies
            if media_type==self.type_movie:
                meta['playcount'] = self.__set_playcount(meta['overlay'])
            
            #if cache row says there are pre-packed images then either use them or create them
            if meta['imgs_prepacked'] == 'true':
    
                    #define the image paths               
                    if media_type == self.type_movie:
                        root_covers = self.mvcovers
                        root_backdrops = self.mvbackdrops
                    elif media_type == self.type_tvshow:
                        root_covers = self.tvcovers
                        root_backdrops = self.tvbackdrops
                        root_banners = self.tvbanners
                    
                    if meta['cover_url']:
                        cover_name = self._picname(meta['cover_url'])
                        if cover_name:
                            cover_path = os.path.join(root_covers, cover_name[0].lower())
                            if self.prepack_images == 'true':
                                self._downloadimages(meta['cover_url'], cover_path, cover_name)
                            meta['cover_url'] = os.path.join(cover_path, cover_name)
                    
                    if meta['backdrop_url']:
                        backdrop_name = self._picname(meta['backdrop_url'])
                        if backdrop_name:
                            backdrop_path=os.path.join(root_backdrops, backdrop_name[0].lower())
                            if self.prepack_images == 'true':
                                self._downloadimages(meta['backdrop_url'], backdrop_path, backdrop_name)
                            meta['backdrop_url'] = os.path.join(backdrop_path, backdrop_name)
    
                    if meta.has_key('banner_url'):
                        if meta['banner_url']:
                            banner_name = self._picname(meta['banner_url'])
                            if banner_name:
                                banner_path=os.path.join(root_banners, banner_name[0].lower())
                                if self.prepack_images == 'true':
                                    self._downloadimages(meta['banner_url'], banner_path, banner_name)
                                meta['banner_url'] = os.path.join(banner_path, banner_name)
    
            #Else - they are online so piece together the full URL from TMDB 
            else:
                if media_type == self.type_movie:
                    if meta['cover_url'] and len(meta['cover_url']) > 1:
                        if not meta['cover_url'].startswith('http'):
                            meta['cover_url'] = self.tmdb_image_url  + common.addon.get_setting('tmdb_poster_size') + meta['cover_url']
                    else:
                        meta['cover_url'] = ''
                    if meta['backdrop_url'] and len(meta['backdrop_url']) > 1:
                        if not meta['backdrop_url'].startswith('http'):
                            meta['backdrop_url'] = self.tmdb_image_url  + common.addon.get_setting('tmdb_backdrop_size') + meta['backdrop_url']
                    else:
                        meta['backdrop_url'] = ''
    
            common.addon.log('Returned Meta: %s' % meta, 0)
            return meta  
        except Exception as e:
            common.addon.log('************* Error formatting meta: %s' % e, 4)
            return meta  


    def update_meta(self, media_type, name, imdb_id, tmdb_id='', new_imdb_id='', new_tmdb_id='', year=''):
        '''
        Updates and returns meta data for given movie/tvshow, mainly to be used with refreshing individual movies.
        
        Searches local cache DB for record, delete if found, calls get_meta() to grab new data

        name, imdb_id, tmdb_id should be what is currently in the DB in order to find current record
        
        new_imdb_id, new_tmdb_id should be what you would like to update the existing DB record to, which you should have already found
        
        Args:
            name (int): full name of movie you are searching            
            imdb_id (str): IMDB ID of CURRENT entry
        Kwargs:
            tmdb_id (str): TMDB ID of CURRENT entry
            new_imdb_id (str): NEW IMDB_ID to search with
            new_tmdb_id (str): NEW TMDB ID to search with
            year (str): 4 digit year of video, recommended to include the year whenever possible
                        to maximize correct search results.
                        
        Returns:
            DICT of meta data or None if cannot be found.
        '''
        common.addon.log('---------------------------------------------------------------------------------------', 0)
        common.addon.log('Updating meta data: %s Old: %s %s New: %s %s Year: %s' % (name.encode('ascii','replace'), imdb_id, tmdb_id, new_imdb_id, new_tmdb_id, year), 0)
        
        if imdb_id:
            imdb_id = self._valid_imdb_id(imdb_id)        
        
        if imdb_id:
            meta = self._cache_lookup_by_id(media_type, imdb_id=imdb_id)
        elif tmdb_id:
            meta = self._cache_lookup_by_id(media_type, tmdb_id=tmdb_id)
        else:
            meta = self._cache_lookup_by_name(media_type, name, year)
            
        #if no old meta found, the year is probably not in the database
        if not imdb_id and not tmdb_id:
            year = ''
            
        if meta:
            overlay = meta['overlay']
            self._cache_delete_video_meta(media_type, imdb_id, tmdb_id, name, year)
        else:
            overlay = 6
            common.addon.log('No match found in cache db', 3)
        
        if not new_imdb_id:
            new_imdb_id = imdb_id
        elif not new_tmdb_id:
            new_tmdb_id = tmdb_id
            
        return self.get_meta(media_type, name, new_imdb_id, new_tmdb_id, year, overlay, True)


    def _cache_lookup_by_id(self, media_type, imdb_id='', tmdb_id=''):
        '''
        Lookup in SQL DB for video meta data by IMDB ID
        
        Args:
            imdb_id (str): IMDB ID
            media_type (str): 'movie' or 'tvshow'
        Kwargs:
            imdb_id (str): IDMB ID
            tmdb_id (str): TMDB ID                        
        Returns:
            DICT of matched meta data or None if no match.
        '''        
        if media_type == self.type_movie:
            sql_select = "SELECT * FROM movie_meta"
            if imdb_id:
                sql_select = sql_select + " WHERE imdb_id = '%s'" % imdb_id
            else:
                sql_select = sql_select + " WHERE tmdb_id = '%s'" % tmdb_id

        elif media_type == self.type_tvshow:
            sql_select = ("SELECT a.*, "
                               "CASE "
                                   "WHEN b.episode ISNULL THEN 0 "
                                   "ELSE b.episode "
                               "END AS episode, "
                               "CASE "
                                   "WHEN c.playcount ISNULL THEN 0 "
                                   "ELSE c.playcount "
                               "END AS playcount "
                       "FROM tvshow_meta a "
                       "LEFT JOIN "
                         "(SELECT imdb_id, "
                                 "count(imdb_id) AS episode "
                          "FROM episode_meta "
                          "WHERE imdb_id = '%s' "
                          "GROUP BY imdb_id) b ON a.imdb_id = b.imdb_id "
                       "LEFT JOIN "
                         "(SELECT imdb_id, "
                                 "count(imdb_id) AS playcount "
                          "FROM episode_meta "
                          "WHERE imdb_id = '%s' "
                            "AND OVERLAY=7 "
                          "GROUP BY imdb_id) c ON a.imdb_id = c.imdb_id "
                       "WHERE a.imdb_id = '%s'") % (imdb_id, imdb_id, imdb_id)

            if DB == 'mysql':
                sql_select = sql_select.replace("ISNULL", "IS NULL")

        common.addon.log('Looking up in local cache by id for: %s %s %s' % (media_type, imdb_id, tmdb_id), 0)
        common.addon.log( 'SQL Select: %s' % sql_select, 0)

        try:    
            self.dbcur.execute(sql_select)
            matchedrow = self.dbcur.fetchone()            
        except Exception as e:
            common.addon.log('************* Error selecting from cache db: %s' % e, 4)
            return None
        
        if matchedrow:
            common.addon.log('Found meta information by id in cache table: %s' % dict(matchedrow), 0)
            return dict(matchedrow)
        else:
            common.addon.log('No match in local DB', 0)
            return None


    def _cache_lookup_by_name(self, media_type, name, year=''):
        '''
        Lookup in SQL DB for video meta data by name and year
        
        Args:
            media_type (str): 'movie' or 'tvshow'
            name (str): full name of movie/tvshow you are searching
        Kwargs:
            year (str): 4 digit year of video, recommended to include the year whenever possible
                        to maximize correct search results.
                        
        Returns:
            DICT of matched meta data or None if no match.
        '''        

        name =  self._clean_string(name.lower())
        if media_type == self.type_movie:
            sql_select = "SELECT * FROM movie_meta WHERE title = '%s'" % name
        elif media_type == self.type_tvshow:
            sql_select = "SELECT a.*, CASE WHEN b.episode ISNULL THEN 0 ELSE b.episode END AS episode, CASE WHEN c.playcount ISNULL THEN 0 ELSE c.playcount END as playcount FROM tvshow_meta a LEFT JOIN (SELECT imdb_id, count(imdb_id) AS episode FROM episode_meta GROUP BY imdb_id) b ON a.imdb_id = b.imdb_id LEFT JOIN (SELECT imdb_id, count(imdb_id) AS playcount FROM episode_meta WHERE overlay=7 GROUP BY imdb_id) c ON a.imdb_id = c.imdb_id WHERE a.title = '%s'" % name
            if DB == 'mysql':
                sql_select = sql_select.replace("ISNULL", "IS NULL")
        common.addon.log('Looking up in local cache by name for: %s %s %s' % (media_type, name, year), 0)
        
        if year and (media_type == self.type_movie or media_type == self.type_tvshow):
            sql_select = sql_select + " AND year = %s" % year
        common.addon.log('SQL Select: %s' % sql_select, 0)
        
        try:
            self.dbcur.execute(sql_select)            
            matchedrow = self.dbcur.fetchone()
        except Exception as e:
            common.addon.log('************* Error selecting from cache db: %s' % e, 4)
            return None
            
        if matchedrow:
            common.addon.log('Found meta information by name in cache table: %s' % dict(matchedrow), 0)
            return dict(matchedrow)
        else:
            common.addon.log('No match in local DB', 0)
            return None

    
    def _cache_save_video_meta(self, meta_group, name, media_type, overlay=6):
        '''
        Saves meta data to SQL table given type
        
        Args:
            meta_group (dict/list): meta data of video to be added to database
                                    can be a list of dicts (batch insert)or a single dict
            media_type (str): 'movie' or 'tvshow'
        Kwargs:
            overlay (int): To set the default watched status (6=unwatched, 7=watched) on new videos                        
        '''            
        
        try:

            if media_type == self.type_movie:
                table='movie_meta'
            elif media_type == self.type_tvshow:
                table='tvshow_meta'

            for meta in meta_group:
        
                #If a list of dicts (batch insert) has been passed in, ensure individual list item is converted to a dict
                if type(meta_group) is list:
                    meta = dict(meta)
                    name = meta['title']
                
                #Else ensure we use the dict passed in
                else:
                    meta = meta_group
                    
                #strip title
                meta['title'] =  self._clean_string(name.lower())
                       
                if meta.has_key('cast'):
                    meta['cast'] = str(meta['cast'])
        
                #set default overlay - watched status
                meta['overlay'] = overlay
                
                common.addon.log('Saving cache information: %s' % meta, 0)

                if media_type == self.type_movie:
                    sql_insert = self.__insert_from_dict(table, 22)
    
                    self.dbcur.execute(sql_insert, (meta['imdb_id'], meta['tmdb_id'], meta['title'],
                                    meta['year'], meta['director'], meta['writer'], meta['tagline'], meta['cast'],
                                    meta['rating'], meta['votes'], meta['duration'], meta['plot'], meta['mpaa'],
                                    meta['premiered'], meta['genre'], meta['studio'], meta['thumb_url'], meta['cover_url'],
                                    meta['trailer_url'], meta['backdrop_url'], meta['imgs_prepacked'], meta['overlay']))
    
                elif media_type == self.type_tvshow:
                    sql_insert = self.__insert_from_dict(table, 19)
                    common.addon.log('SQL INSERT: %s' % sql_insert, 0)
    
                    self.dbcur.execute(sql_insert, (meta['imdb_id'], meta['tvdb_id'], meta['title'], meta['year'], 
                            meta['cast'], meta['rating'], meta['duration'], meta['plot'], meta['mpaa'],
                            meta['premiered'], meta['genre'], meta['studio'], meta['status'], meta['banner_url'],
                            meta['cover_url'], meta['trailer_url'], meta['backdrop_url'], meta['imgs_prepacked'], meta['overlay']))

                #Break loop if we are dealing with just 1 record
                if type(meta_group) is dict:
                    break

            #Commit all transactions
            self.dbcon.commit()
            common.addon.log('SQL INSERT Successfully Commited', 0)
        except Exception as e:
            common.addon.log('************* Error attempting to insert into %s cache table: %s ' % (table, e), 4)
            common.addon.log('Meta data: %s' % meta, 4)
            pass 


    def _cache_delete_video_meta(self, media_type, imdb_id, tmdb_id, name, year):
        '''
        Delete meta data from SQL table
        
        Args:
            media_type (str): 'movie' or 'tvshow'
            imdb_id (str): IMDB ID
            tmdb_id (str): TMDB ID   
            name (str): Full movie name
            year (int): Movie year
                        
        '''         
        
        if media_type == self.type_movie:
            table = 'movie_meta'
        elif media_type == self.type_tvshow:
            table = 'tvshow_meta'
            
        if imdb_id:
            sql_delete = "DELETE FROM %s WHERE imdb_id = '%s'" % (table, imdb_id)
        elif tmdb_id:
            sql_delete = "DELETE FROM %s WHERE tmdb_id = '%s'" % (table, tmdb_id)
        else:
            name =  self._clean_string(name.lower())
            sql_delete = "DELETE FROM %s WHERE title = '%s'" % (table, name)
            if year:
                sql_delete = sql_delete + ' AND year = %s' % (year)

        common.addon.log('Deleting table entry: %s %s %s %s ' % (imdb_id, tmdb_id, name, year), 0)
        common.addon.log('SQL DELETE: %s' % sql_delete, 0)
        try:
            self.dbcur.execute(sql_delete)
            self.dbcon.commit()
        except Exception as e:
            common.addon.log('************* Error attempting to delete from cache table: %s ' % e, 4)
            pass    
        

    def _get_tmdb_meta(self, imdb_id, tmdb_id, name, year=''):
        '''
        Requests meta data from TMDB and creates proper dict to send back
        
        Args:
            imdb_id (str): IMDB ID
            name (str): full name of movie you are searching
        Kwargs:
            year (str): 4 digit year of movie, when imdb_id is not available it is recommended
                        to include the year whenever possible to maximize correct search results.
                        
        Returns:
            DICT. It must also return an empty dict when
            no movie meta info was found from tmdb because we should cache
            these "None found" entries otherwise we hit tmdb alot.
        '''        
        
        tmdb = TMDB(tmdb_api_key=self.tmdb_api_key, omdb_api_key=self.omdb_api_key, lang=self.__get_tmdb_language())
        meta = tmdb.tmdb_lookup(name,imdb_id,tmdb_id, year)
        
        if meta is None:
            # create an empty dict so below will at least populate empty data for the db insert.
            meta = {}

        return self._format_tmdb_meta(meta, imdb_id, name, year)


    def _format_tmdb_meta(self, md, imdb_id, name, year):
        '''
        Copy tmdb to our own for conformity and eliminate KeyError. Set default for values not returned
        
        Args:
            imdb_id (str): IMDB ID
            name (str): full name of movie you are searching
        Kwargs:
            year (str): 4 digit year of movie, when imdb_id is not available it is recommended
                        to include the year whenever possible to maximize correct search results.
                        
        Returns:
            DICT. It must also return an empty dict when
            no movie meta info was found from tvdb because we should cache
            these "None found" entries otherwise we hit tvdb alot.
        '''      
        
        #Intialize movie_meta dictionary    
        meta = self._init_movie_meta(imdb_id, md.get('id', ''), name, year)
        
        meta['imdb_id'] = md.get('imdb_id', imdb_id)
        meta['title'] = md.get('name', name)      
        meta['tagline'] = md.get('tagline', '')
        meta['rating'] = float(md.get('rating', 0))
        meta['votes'] = str(md.get('votes', ''))
        meta['duration'] = int(str(md.get('runtime', 0))) * 60
        meta['plot'] = md.get('overview', '')
        meta['mpaa'] = md.get('certification', '')       
        meta['premiered'] = md.get('released', '')
        meta['director'] = md.get('director', '')
        meta['writer'] = md.get('writer', '')       

        #Do whatever we can to set a year, if we don't have one lets try to strip it from premiered
        if not year and meta['premiered']:
            #meta['year'] = int(self._convert_date(meta['premiered'], '%Y-%m-%d', '%Y'))
            meta['year'] = int(meta['premiered'][:4])
            
        meta['trailer_url'] = md.get('trailers', '')
        meta['genre'] = md.get('genre', '')
        
        #Get cast, director, writers
        cast_list = []
        cast_list = md.get('cast','')
        if cast_list:
            for cast in cast_list:
                char = cast.get('character','')
                if not char:
                    char = ''
                meta['cast'].append((cast.get('name',''),char ))
                        
        crew_list = []
        crew_list = md.get('crew','')
        if crew_list:
            for crew in crew_list:
                job=crew.get('job','')
                if job == 'Director':
                    meta['director'] = crew.get('name','')
                elif job == 'Screenplay':
                    if meta['writer']:
                        meta['writer'] = meta['writer'] + ' / ' + crew.get('name','')
                    else:
                        meta['writer'] = crew.get('name','')
                    
        genre_list = []
        genre_list = md.get('genres', '')
        if(genre_list):
            meta['genre'] = ''
        for genre in genre_list:
            if meta['genre'] == '':
                meta['genre'] = genre.get('name','')
            else:
                meta['genre'] = meta['genre'] + ' / ' + genre.get('name','')
        
        if md.has_key('tvdb_studios'):
            meta['studio'] = md.get('tvdb_studios', '')
        try:
            meta['studio'] = (md.get('studios', '')[0])['name']
        except:
            try:
                meta['studio'] = (md.get('studios', '')[1])['name']
            except:
                try:
                    meta['studio'] = (md.get('studios', '')[2])['name']
                except:
                    try:    
                        meta['studio'] = (md.get('studios', '')[3])['name']
                    except:
                        common.addon.log('Studios failed: %s ' % md.get('studios', ''), 0)
                        pass
        
        meta['cover_url'] = md.get('cover_url', '')
        meta['backdrop_url'] = md.get('backdrop_url', '')
        if md.has_key('posters'):
            # find first thumb poster url
            for poster in md['posters']:
                if poster['image']['size'] == 'thumb':
                    meta['thumb_url'] = poster['image']['url']
                    break
            # find first cover poster url
            for poster in md['posters']:
                if poster['image']['size'] == 'cover':
                    meta['cover_url'] = poster['image']['url']
                    break

        if md.has_key('backdrops'):
            # find first original backdrop url
            for backdrop in md['backdrops']:
                if backdrop['image']['size'] == 'original':
                    meta['backdrop_url'] = backdrop['image']['url']
                    break

        return meta
        
        
    def _get_tvdb_meta(self, imdb_id, name, year=''):
        '''
        Requests meta data from TVDB and creates proper dict to send back
        
        Args:
            imdb_id (str): IMDB ID
            name (str): full name of movie you are searching
        Kwargs:
            year (str): 4 digit year of movie, when imdb_id is not available it is recommended
                        to include the year whenever possible to maximize correct search results.
                        
        Returns:
            DICT. It must also return an empty dict when
            no movie meta info was found from tvdb because we should cache
            these "None found" entries otherwise we hit tvdb alot.
        '''      
        common.addon.log('Starting TVDB Lookup', 0)
        tvdb = TheTVDB(language=self.__get_tvdb_language())
        tvdb_id = ''
        
        try:
            if imdb_id:
                tvdb_id = tvdb.get_show_by_imdb(imdb_id)
        except Exception as e:
            common.addon.log('************* Error retreiving from thetvdb.com: %s ' % e, 4)
            tvdb_id = ''
            pass
            
        #Intialize tvshow meta dictionary
        meta = self._init_tvshow_meta(imdb_id, tvdb_id, name, year)

        # if not found by imdb, try by name
        if tvdb_id == '':
            try:
                #If year is passed in, add it to the name for better TVDB search results
                #if year:
                #    name = name + ' ' + year
                show_list=tvdb.get_matching_shows(name)
            except Exception as e:
                common.addon.log('************* Error retreiving from thetvdb.com: %s ' % e, 4)
                show_list = []
                pass
            common.addon.log('Found TV Show List: %s' % show_list, 0)
            tvdb_id=''
            for show in show_list:
                (junk1, junk2, junk3) = show
                try:
                    #if we match imdb_id or full name (with year) then we know for sure it is the right show
                    if (imdb_id and junk3==imdb_id) or (year and self._string_compare(self._clean_string(junk2),self._clean_string(name + year))):
                        tvdb_id = self._clean_string(junk1)
                        if not imdb_id:
                            imdb_id = self._clean_string(junk3)
                        name = junk2
                        break
                    #if we match just the cleaned name (without year) keep the tvdb_id
                    elif self._string_compare(self._clean_string(junk2),self._clean_string(name)):
                        tvdb_id = self._clean_string(junk1)
                        if not imdb_id:
                            imdb_id = self._clean_string(junk3)
                        break
                        
                except Exception as e:
                    common.addon.log('************* Error retreiving from thetvdb.com: %s ' % e, 4)

        if tvdb_id:
            common.addon.log('Show *** ' + name + ' *** found in TVdb. Getting details...', 0)

            try:
                show = tvdb.get_show(tvdb_id)
            except Exception as e:
                common.addon.log('************* Error retreiving from thetvdb.com: %s ' % e, 4)
                show = None
                pass
            
            if show is not None:
                meta['imdb_id'] = imdb_id
                meta['tvdb_id'] = tvdb_id
                meta['title'] = name
                if str(show.rating) != '' and show.rating != None:
                    meta['rating'] = float(show.rating)
                meta['duration'] = int(show.runtime) * 60
                meta['plot'] = show.overview
                meta['mpaa'] = show.content_rating
                meta['premiered'] = str(show.first_aired)

                #Do whatever we can to set a year, if we don't have one lets try to strip it from show.first_aired/premiered
                if not year and show.first_aired:
                        #meta['year'] = int(self._convert_date(meta['premiered'], '%Y-%m-%d', '%Y'))
                        meta['year'] = int(meta['premiered'][:4])

                if show.genre != '':
                    temp = show.genre.replace("|",",")
                    temp = temp[1:(len(temp)-1)]
                    meta['genre'] = temp
                meta['studio'] = show.network
                meta['status'] = show.status
                if show.actors:
                    for actor in show.actors:
                        meta['cast'].append(actor)
                meta['banner_url'] = show.banner_url
                meta['imgs_prepacked'] = self.prepack_images
                meta['cover_url'] = show.poster_url
                meta['backdrop_url'] = show.fanart_url
                meta['overlay'] = 6

                if meta['plot'] == 'None' or meta['plot'] == '' or meta['plot'] == 'TBD' or meta['plot'] == 'No overview found.' or meta['rating'] == 0 or meta['duration'] == 0 or meta['cover_url'] == '':
                    common.addon.log(' Some info missing in TVdb for TVshow *** '+ name + ' ***. Will search imdb for more', 0)
                    tmdb = TMDB(tmdb_api_key=self.tmdb_api_key, omdb_api_key=self.omdb_api_key, lang=self.__get_tmdb_language())
                    imdb_meta = tmdb.search_imdb(name, imdb_id)
                    if imdb_meta:
                        imdb_meta = tmdb.update_imdb_meta(meta, imdb_meta)
                        if imdb_meta.has_key('overview'):
                            meta['plot'] = imdb_meta['overview']
                        if imdb_meta.has_key('rating'):
                            meta['rating'] = float(imdb_meta['rating'])
                        if imdb_meta.has_key('runtime'):
                            meta['duration'] = int(imdb_meta['runtime']) * 60
                        if imdb_meta.has_key('cast'):
                            meta['cast'] = imdb_meta['cast']
                        if imdb_meta.has_key('cover_url'):
                            meta['cover_url'] = imdb_meta['cover_url']

                return meta
            else:
                tmdb = TMDB(tmdb_api_key=self.tmdb_api_key, omdb_api_key=self.omdb_api_key, lang=self.__get_tmdb_language())
                imdb_meta = tmdb.search_imdb(name, imdb_id)
                if imdb_meta:
                    meta = tmdb.update_imdb_meta(meta, imdb_meta)
                return meta    
        else:
            return meta


    def search_movies(self, name):
        '''
        Requests meta data from TMDB for any movie matching name
        
        Args:
            name (str): full name of movie you are searching
                        
        Returns:
            Arry of dictionaries with trimmed down meta data, only returned data that is required:
            - IMDB ID
            - TMDB ID
            - Name
            - Year
        ''' 
        common.addon.log('---------------------------------------------------------------------------------------', 0)
        common.addon.log('Meta data refresh - searching for movie: %s' % name, 0)
        tmdb = TMDB(tmdb_api_key=self.tmdb_api_key, omdb_api_key=self.omdb_api_key, lang=self.__get_tmdb_language())
        movie_list = []
        meta = tmdb.tmdb_search(name)
        if meta:
            if meta['total_results'] == 0:
                common.addon.log('No results found', 0)
                return None
            for movie in meta['results']:
                if movie['release_date']:
                    year = movie['release_date'][:4]
                else:
                    year = None
                movie_list.append({'title': movie['title'],'original_title': movie['original_title'], 'imdb_id': '', 'tmdb_id': movie['id'], 'year': year})
        else:
            common.addon.log('No results found', 0)
            return None

        common.addon.log('Returning results: %s' % movie_list, 0)
        return movie_list


    def similar_movies(self, tmdb_id, page=1):
        '''
        Requests list of similar movies matching given tmdb id
        
        Args:
            tmdb_id (str): MUST be a valid TMDB ID
        Kwargs:
            page (int): page number of result to fetch
        Returns:
            List of dicts - each movie in it's own dict with supporting info
        ''' 
        common.addon.log('---------------------------------------------------------------------------------------', 0)
        common.addon.log('TMDB - requesting similar movies: %s' % tmdb_id, 0)
        tmdb = TMDB(tmdb_api_key=self.tmdb_api_key, omdb_api_key=self.omdb_api_key, lang=self.__get_tmdb_language())
        movie_list = []
        meta = tmdb.tmdb_similar_movies(tmdb_id, page)
        if meta:
            if meta['total_results'] == 0:
                common.addon.log('No results found', 0)
                return None
            for movie in meta['results']:
                movie_list.append(movie)
        else:
            common.addon.log('No results found', 0)
            return None

        common.addon.log('Returning results: %s' % movie_list, 0)
        return movie_list


    def get_episode_meta(self, tvshowtitle, imdb_id, season, episode, air_date='', episode_title='', overlay=''):
        '''
        Requests meta data from TVDB for TV episodes, searches local cache db first.
        
        Args:
            tvshowtitle (str): full name of tvshow you are searching
            imdb_id (str): IMDB ID
            season (int): tv show season number, number only no other characters
            episode (int): tv show episode number, number only no other characters
        Kwargs:
            air_date (str): In cases where episodes have no episode number but only an air date - eg. daily talk shows
            episode_title (str): The title of the episode, gets set to the title infolabel which must exist
            overlay (int): To set the default watched status (6=unwatched, 7=watched) on new videos
                        
        Returns:
            DICT. It must also return an empty dict when
            no meta info was found in order to save these.
        '''  
              
        common.addon.log('---------------------------------------------------------------------------------------', 0)
        common.addon.log('Attempting to retrieve episode meta data for: imdbid: %s season: %s episode: %s air_date: %s' % (imdb_id, season, episode, air_date), 0)
               
        if not season:
            season = 0
        if not episode:
            episode = 0
        
        if imdb_id:
            imdb_id = self._valid_imdb_id(imdb_id)

        #Find tvdb_id for the TVshow
        tvdb_id = self._get_tvdb_id(tvshowtitle, imdb_id)

        #Check if it exists in local cache first
        meta = self._cache_lookup_episode(imdb_id, tvdb_id, season, episode, air_date)
        
        #If not found lets scrape online sources
        if not meta:

            #I need a tvdb id to scrape The TVDB
            if tvdb_id:
                meta = self._get_tvdb_episode_data(tvdb_id, season, episode, air_date)
            else:
                common.addon.log("No TVDB ID available, could not find TVshow with imdb: %s " % imdb_id, 0)

            #If nothing found
            if not meta:
                #Init episode meta structure
                meta = self.__init_episode_meta(imdb_id, tvdb_id, episode_title, season, episode, air_date)
            
            #set overlay if used, else default to unwatched
            if overlay:
                meta['overlay'] = int(overlay)
            else:
                meta['overlay'] = 6
                    
            if not meta['title']:
                meta['title']= episode_title
            
            meta['tvdb_id'] = tvdb_id
            meta['imdb_id'] = imdb_id
            meta['cover_url'] = meta['poster']
            meta = self._get_tv_extra(meta)
                           
            self._cache_save_episode_meta(meta)

        #Ensure we are not sending back any None values, XBMC doesn't like them
        meta = self._remove_none_values(meta)

        #Set Watched flag
        meta['playcount'] = self.__set_playcount(meta['overlay'])
        
        #Add key for subtitles to work
        meta['TVShowTitle']= tvshowtitle
        
        common.addon.log('Returned Meta: %s' % meta, 0)
        return meta


    def _get_tv_extra(self, meta):
        '''
        When requesting episode information, not all data may be returned
        Fill in extra missing meta information from tvshow_meta table which should
        have already been populated.
        
        Args:
            meta (dict): current meta dict
                        
        Returns:
            DICT containing the extra values
        '''
        
        if meta['imdb_id']:
            sql_select = "SELECT * FROM tvshow_meta WHERE imdb_id = '%s'" % meta['imdb_id']
        elif meta['tvdb_id']:
            sql_select = "SELECT * FROM tvshow_meta WHERE tvdb_id = '%s'" % meta['tvdb_id']
        else:
            sql_select = "SELECT * FROM tvshow_meta WHERE title = '%s'" % self._clean_string(meta['title'].lower())
            
        common.addon.log('Retrieving extra TV Show information from tvshow_meta', 0)
        common.addon.log('SQL SELECT: %s' % sql_select, 0)
        
        try:     
            self.dbcur.execute(sql_select)
            matchedrow = self.dbcur.fetchone()
        except Exception as e:
            common.addon.log('************* Error attempting to select from tvshow_meta table: %s ' % e, 4)
            pass   

        if matchedrow:
            match = dict(matchedrow)
            meta['genre'] = match['genre']
            meta['duration'] = match['duration']
            meta['studio'] = match['studio']
            meta['mpaa'] = match['mpaa']
            meta['backdrop_url'] = match['backdrop_url']
        else:
            meta['genre'] = ''
            meta['duration'] = '0'
            meta['studio'] = ''
            meta['mpaa'] = ''
            meta['backdrop_url'] = ''

        return meta


    def _get_tvdb_id(self, name, imdb_id):
        '''
        Retrieves TVID for a tv show that has already been scraped and saved in cache db.
        
        Used when scraping for season and episode data
        
        Args:
            name (str): full name of tvshow you are searching            
            imdb_id (str): IMDB ID
                        
        Returns:
            (str) imdb_id 
        '''      
        
        #clean tvshow name of any extras       
        name =  self._clean_string(name.lower())
        
        if imdb_id:
            sql_select = "SELECT tvdb_id FROM tvshow_meta WHERE imdb_id = '%s'" % imdb_id
        elif name:
            sql_select = "SELECT tvdb_id FROM tvshow_meta WHERE title = '%s'" % name
        else:
            return None
            
        common.addon.log('Retrieving TVDB ID', 0)
        common.addon.log('SQL SELECT: %s' % sql_select, 0)
        
        try:
            self.dbcur.execute(sql_select)
            matchedrow = self.dbcur.fetchone()
        except Exception as e:
            common.addon.log('************* Error attempting to select from tvshow_meta table: %s ' % e, 4)
            pass
                        
        if matchedrow:
                return dict(matchedrow)['tvdb_id']
        else:
            return None

     
    def update_episode_meta(self, name, imdb_id, season, episode, tvdb_id='', new_imdb_id='', new_tvdb_id=''):
        '''
        Updates and returns meta data for given episode, 
        mainly to be used with refreshing individual tv show episodes.
        
        Searches local cache DB for record, delete if found, calls get_episode_meta() to grab new data
               
        
        Args:
            name (int): full name of movie you are searching
            imdb_id (str): IMDB ID
            season (int): season number
            episode (int): episode number
        Kwargs:
            tvdb_id (str): TVDB ID
                        
        Returns:
            DICT of meta data or None if cannot be found.
        '''
        common.addon.log('---------------------------------------------------------------------------------------', 0)
        common.addon.log('Updating episode meta data: %s IMDB: %s SEASON: %s EPISODE: %s TVDB ID: %s NEW IMDB ID: %s NEW TVDB ID: %s' % (name, imdb_id, season, episode, tvdb_id, new_imdb_id, new_tvdb_id), 0)

      
        if imdb_id:
            imdb_id = self._valid_imdb_id(imdb_id)
        else:
            imdb_id = ''

        #Find tvdb_id for the TVshow
        tvdb_id = self._get_tvdb_id(name, imdb_id)
        
        #Lookup in cache table for existing entry
        meta = self._cache_lookup_episode(imdb_id, tvdb_id, season, episode)
        
        #We found an entry in the DB, so lets delete it
        if meta:
            overlay = meta['overlay']
            self._cache_delete_episode_meta(imdb_id, tvdb_id, name, season, episode)
        else:
            overlay = 6
            common.addon.log('No match found in cache db', 0)
       
        if not new_imdb_id:
            new_imdb_id = imdb_id
        elif not new_tvdb_id:
            new_tvdb_id = tvdb_id
            
        return self.get_episode_meta(name, imdb_id, season, episode, overlay=overlay)


    def _cache_lookup_episode(self, imdb_id, tvdb_id, season, episode, air_date=''):
        '''
        Lookup in local cache db for episode data
        
        Args:
            imdb_id (str): IMDB ID
            tvdb_id (str): TheTVDB ID
            season (str): tv show season number, number only no other characters
            episode (str): tv show episode number, number only no other characters
        Kwargs:
            air_date (str): date episode was aired - YYYY-MM-DD

        Returns:
            DICT. Returns results found or None.
        ''' 
        common.addon.log('Looking up episode data in cache db, imdb id: %s season: %s episode: %s air_date: %s' % (imdb_id, season, episode, air_date), 0)
        
        try:

            sql_select = ('SELECT '
                               'episode_meta.title as title, '
                               'episode_meta.plot as plot, '
                               'episode_meta.director as director, '
                               'episode_meta.writer as writer, '
                               'tvshow_meta.genre as genre, '
                               'tvshow_meta.duration as duration, '
                               'episode_meta.premiered as premiered, '
                               'tvshow_meta.studio as studio, '
                               'tvshow_meta.mpaa as mpaa, '
                               'tvshow_meta.title as TVShowTitle, '
                               'episode_meta.imdb_id as imdb_id, '
                               'episode_meta.rating as rating, '
                               '"" as trailer_url, '
                               'episode_meta.season as season, '
                               'episode_meta.episode as episode, '
                               'episode_meta.overlay as overlay, '
                               'tvshow_meta.backdrop_url as backdrop_url, '                               
                               'episode_meta.poster as cover_url ' 
                               'FROM episode_meta, tvshow_meta '
                               'WHERE episode_meta.imdb_id = tvshow_meta.imdb_id AND '
                               'episode_meta.tvdb_id = tvshow_meta.tvdb_id AND '
                               'episode_meta.imdb_id = "%s" AND episode_meta.tvdb_id = "%s" AND '
                               )  % (imdb_id, tvdb_id)
            
            #If air_date is supplied, select on it instead of season & episode #
            if air_date:
                sql_select = sql_select + 'episode_meta.premiered = "%s" ' % air_date
            else:
                sql_select = sql_select + 'season = %s AND episode_meta.episode = %s ' % (season, episode)

            common.addon.log('SQL SELECT: %s' % sql_select, 0)
            
            self.dbcur.execute(sql_select)
            matchedrow = self.dbcur.fetchone()
        except Exception as e:
            common.addon.log('************* Error attempting to select from Episode table: %s ' % e, 4)
            return None
                        
        if matchedrow:
            common.addon.log('Found episode meta information in cache table: %s' % dict(matchedrow), 0)
            return dict(matchedrow)
        else:
            return None


    def _cache_delete_episode_meta(self, imdb_id, tvdb_id, name, season, episode, air_date=''):
        '''
        Delete meta data from SQL table
        
        Args:
            imdb_id (str): IMDB ID
            tvdb_id (str): TVDB ID
            name (str): Episode title
            season (int): Season #
            episode(int): Episode #
        Kwargs:
            air_date (str): Air Date of episode
        '''

        if imdb_id:
            sql_delete = "DELETE FROM episode_meta WHERE imdb_id = '%s' AND tvdb_id = '%s' AND season = %s" % (imdb_id, tvdb_id, season)
            if air_date:
                sql_delete = sql_delete + ' AND premiered = "%s"' % air_date
            else:
                sql_delete = sql_delete + ' AND episode = %s' % episode

        common.addon.log('Deleting table entry: IMDB: %s TVDB: %s Title: %s Season: %s Episode: %s ' % (imdb_id, tvdb_id, name, season, episode), 0)
        common.addon.log('SQL DELETE: %s' % sql_delete, 0)
        try:
            self.dbcur.execute(sql_delete)
            self.dbcon.commit()
        except Exception as e:
            common.addon.log('************* Error attempting to delete from episode cache table: %s ' % e, 4)
            pass


    def _get_tvdb_episode_data(self, tvdb_id, season, episode, air_date=''):
        '''
        Initiates lookup for episode data on TVDB
        
        Args:
            tvdb_id (str): TVDB id
            season (str): tv show season number, number only no other characters
            episode (str): tv show episode number, number only no other characters
        Kwargs:
            air_date (str): Date episode was aired
                        
        Returns:
            DICT. Data found from lookup
        '''      
        
        meta = {}
        tvdb = TheTVDB(language=self.__get_tvdb_language())
        if air_date:
            try:
                episode = tvdb.get_episode_by_airdate(tvdb_id, air_date)
            except:
                common.addon.log('************* Error retreiving from thetvdb.com: %s ' % e, 4)
                episode = None
                pass
                
            
            #We do this because the airdate method returns just a part of the overview unfortunately
            if episode:
                ep_id = episode.id
                if ep_id:
                    try:
                        episode = tvdb.get_episode(ep_id)
                    except:
                        common.addon.log('************* Error retreiving from thetvdb.com: %s ' % e, 4)
                        episode = None
                        pass
        else:
            try:
                episode = tvdb.get_episode_by_season_ep(tvdb_id, season, episode)
            except Exception as e:
                common.addon.log('************* Error retreiving from thetvdb.com: %s ' % e, 4)
                episode = None
                pass
            
        if episode is None:
            return None
        
        meta['episode_id'] = episode.id
        meta['plot'] = self._check(episode.overview)
        if episode.guest_stars:
            guest_stars = episode.guest_stars
            if guest_stars.startswith('|'):
                guest_stars = guest_stars[1:-1]
            guest_stars = guest_stars.replace('|', ', ')
            meta['plot'] = meta['plot'] + '\n\nGuest Starring: ' + guest_stars
        meta['rating'] = float(self._check(episode.rating,0))
        meta['premiered'] = self._check(episode.first_aired)
        meta['title'] = self._check(episode.name)
        meta['poster'] = self._check(episode.image)
        meta['director'] = self._check(episode.director)
        meta['writer'] = self._check(episode.writer)
        meta['season'] = int(self._check(episode.season_number,0))
        meta['episode'] = int(self._check(episode.episode_number,0))
              
        return meta


    def _check(self, value, ret=None):
        if value is None or value == '':
            if ret == None:
                return ''
            else:
                return ret
        else:
            return value
            
        
    def _cache_save_episode_meta(self, meta):
        '''
        Save episode data to local cache db.
        
        Args:
            meta (dict): episode data to be stored
                        
        '''      
        if meta['imdb_id']:
            sql_select = 'SELECT * FROM episode_meta WHERE imdb_id = "%s" AND season = %s AND episode = %s AND premiered = "%s" AND episode_id = "%s"'  % (meta['imdb_id'], meta['season'], meta['episode'], meta['premiered'], meta['episode_id'])
            sql_delete = 'DELETE FROM episode_meta WHERE imdb_id = "%s" AND season = %s AND episode = %s AND premiered = "%s" AND episode_id = "%s"'  % (meta['imdb_id'], meta['season'], meta['episode'], meta['premiered'], meta['episode_id'])
        elif meta['tvdb_id']:
            sql_select = 'SELECT * FROM episode_meta WHERE tvdb_id = "%s" AND season = %s AND episode = %s AND premiered = "%s" AND episode_id = "%s"'  % (meta['tvdb_id'], meta['season'], meta['episode'], meta['premiered'], meta['episode_id'])
            sql_delete = 'DELETE FROM episode_meta WHERE tvdb_id = "%s" AND season = %s AND episode = %s AND premiered = "%s" AND episode_id = "%s"'  % (meta['tvdb_id'], meta['season'], meta['episode'], meta['premiered'], meta['episode_id'])
        else:         
            sql_select = 'SELECT * FROM episode_meta WHERE title = "%s" AND season = %s AND episode = %s AND premiered = "%s" AND episode_id = "%s"'  % (self._clean_string(meta['title'].lower()), meta['season'], meta['episode'], meta['premiered'], meta['episode_id'])
            sql_delete = 'DELETE FROM episode_meta WHERE title = "%s" AND season = %s AND episode = %s AND premiered = "%s" AND episode_id = "%s"'  % (self._clean_string(meta['title'].lower()), meta['season'], meta['episode'], meta['premiered'], meta['episode_id'])
        common.addon.log('Saving Episode Meta', 0)
        common.addon.log('SQL Select: %s' % sql_select, 0)
        
        try: 
            self.dbcur.execute(sql_select)
            matchedrow = self.dbcur.fetchone()
            if matchedrow:
                    common.addon.log('Episode matched row found, deleting table entry', 0)
                    common.addon.log('SQL Delete: %s' % sql_delete, 0)
                    self.dbcur.execute(sql_delete) 
        except Exception as e:
            common.addon.log('************* Error attempting to delete from cache table: %s ' % e, 4)
            common.addon.log('Meta data: %' % meta, 4)
            pass        
        
        common.addon.log('Saving episode cache information: %s' % meta, 0)
        try:
            sql_insert = self.__insert_from_dict('episode_meta', 13)
            common.addon.log('SQL INSERT: %s' % sql_insert, 0)
            self.dbcur.execute(sql_insert, (meta['imdb_id'], meta['tvdb_id'], meta['episode_id'], meta['season'], 
                                meta['episode'], meta['title'], meta['director'], meta['writer'], meta['plot'], 
                                meta['rating'], meta['premiered'], meta['poster'], meta['overlay'])
            )
            self.dbcon.commit()
        except Exception as e:
            common.addon.log('************* Error attempting to insert into episodes cache table: %s ' % e, 4)
            common.addon.log('Meta data: %s' % meta, 4)
            pass        


    def update_trailer(self, media_type, imdb_id, trailer, tmdb_id=''):
        '''
        Change videos trailer
        
        Args:
            media_type (str): media_type of video to update, 'movie', 'tvshow' or 'episode'
            imdb_id (str): IMDB ID
            trailer (str): url of youtube video
        Kwargs:            
            tmdb_id (str): TMDB ID
                        
        '''      
        if media_type == 'movie':
            table='movie_meta'
        elif media_type == 'tvshow':
            table='tvshow_meta'
        
        if imdb_id:
            imdb_id = self._valid_imdb_id(imdb_id)

        if imdb_id:
            sql_update = "UPDATE %s set trailer_url='%s' WHERE imdb_id = '%s'" % (table, trailer, imdb_id)
        elif tmdb_id:
            sql_update = "UPDATE %s set trailer_url='%s' WHERE tmdb_id = '%s'" % (table, trailer, tmdb_id)
               
        common.addon.log('Updating trailer for type: %s, imdb id: %s, tmdb_id: %s, trailer: %s' % (media_type, imdb_id, tmdb_id, trailer), 0)
        common.addon.log('SQL UPDATE: %s' % sql_update, 0)
        try:    
            self.dbcur.execute(sql_update)
            self.dbcon.commit()
        except Exception as e:
            common.addon.log('************* Error attempting to update table: %s ' % e, 4)
            pass          


    def change_watched(self, media_type, name, imdb_id, tmdb_id='', season='', episode='', year='', watched='', air_date=''):
        '''
        Change watched status on video
        
        Args:
            imdb_id (str): IMDB ID
            media_type (str): type of video to update, 'movie', 'tvshow' or 'episode'
            name (str): name of video
        Kwargs:            
            season (int): season number
            episode (int): episode number
            year (int): Year
            watched (int): Can specify what to change watched status (overlay) to
                        
        '''   
        common.addon.log('---------------------------------------------------------------------------------------', 0)
        common.addon.log('Updating watched flag for: %s %s %s %s %s %s %s %s %s' % (media_type, name, imdb_id, tmdb_id, season, episode, year, watched, air_date), 0)

        if imdb_id:
            imdb_id = self._valid_imdb_id(imdb_id)

        tvdb_id = ''
        if media_type in (self.type_tvshow, self.type_season):
            tvdb_id = self._get_tvdb_id(name, imdb_id)                                  
        
        if media_type in (self.type_movie, self.type_tvshow, self.type_season):
            if not watched:
                watched = self._get_watched(media_type, imdb_id, tmdb_id, season=season)
                if watched == 6:
                    watched = 7
                else:
                    watched = 6
            self._update_watched(imdb_id, media_type, watched, tmdb_id=tmdb_id, name=self._clean_string(name.lower()), year=year, season=season, tvdb_id=tvdb_id)                
        elif media_type == self.type_episode:
            if tvdb_id is None:
                tvdb_id = ''
            tmp_meta = {}
            tmp_meta['imdb_id'] = imdb_id
            tmp_meta['tvdb_id'] = tvdb_id 
            tmp_meta['title'] = name
            tmp_meta['season']  = season
            tmp_meta['episode'] = episode
            tmp_meta['premiered'] = air_date
            
            if not watched:
                watched = self._get_watched_episode(tmp_meta)
                if watched == 6:
                    watched = 7
                else:
                    watched = 6
            self._update_watched(imdb_id, media_type, watched, name=name, season=season, episode=episode, tvdb_id=tvdb_id, air_date=air_date)
                

    def _update_watched(self, imdb_id, media_type, new_value, tmdb_id='', name='', year='', season='', episode='', tvdb_id='', air_date=''):
        '''
        Commits the DB update for the watched status
        
        Args:
            imdb_id (str): IMDB ID
            media_type (str): type of video to update, 'movie', 'tvshow' or 'episode'
            new_value (int): value to update overlay field with
        Kwargs:
            name (str): name of video        
            season (str): season number
            tvdb_id (str): tvdb id of tvshow                        

        '''      
        if media_type == self.type_movie:
            if imdb_id:
                sql_update="UPDATE movie_meta SET overlay = %s WHERE imdb_id = '%s'" % (new_value, imdb_id)
            elif tmdb_id:
                sql_update="UPDATE movie_meta SET overlay = %s WHERE tmdb_id = '%s'" % (new_value, tmdb_id)
            else:
                sql_update="UPDATE movie_meta SET overlay = %s WHERE title = '%s'" % (new_value, name)
                if year:
                    sql_update = sql_update + ' AND year=%s' % year
        elif media_type == self.type_tvshow:
            if imdb_id:
                sql_update="UPDATE tvshow_meta SET overlay = %s WHERE imdb_id = '%s'" % (new_value, imdb_id)
            elif tvdb_id:
                sql_update="UPDATE tvshow_meta SET overlay = %s WHERE tvdb_id = '%s'" % (new_value, tvdb_id)
        elif media_type == self.type_season:
            sql_update="UPDATE season_meta SET overlay = %s WHERE imdb_id = '%s' AND season = %s" % (new_value, imdb_id, season)        
        elif media_type == self.type_episode:
            if imdb_id:
                sql_update="UPDATE episode_meta SET overlay = %s WHERE imdb_id = '%s'" % (new_value, imdb_id)
            elif tvdb_id:
                sql_update="UPDATE episode_meta SET overlay = %s WHERE tvdb_id = '%s'" % (new_value, tvdb_id)
            else:
                return None
            
            #If we have an air date use that instead of season/episode #
            if air_date:
                sql_update = sql_update + " AND premiered = '%s'" % air_date
            else:
                sql_update = sql_update + ' AND season = %s AND episode = %s' % (season, episode)
                
        else: # Something went really wrong
            return None

        common.addon.log('Updating watched status for type: %s, imdb id: %s, tmdb_id: %s, new value: %s' % (media_type, imdb_id, tmdb_id, new_value), 0)
        common.addon.log('SQL UPDATE: %s' % sql_update, 0)
        try:
            self.dbcur.execute(sql_update)
            self.dbcon.commit()
        except Exception as e:
            common.addon.log('************* Error attempting to update table: %s ' % e, 4)
            pass    


    def _get_watched(self, media_type, imdb_id, tmdb_id, season=''):
        '''
        Finds the watched status of the video from the cache db
        
        Args:
            media_type (str): type of video to update, 'movie', 'tvshow' or 'episode'                    
            imdb_id (str): IMDB ID
            tmdb_id (str): TMDB ID
        Kwargs:
            season (int): tv show season number    

        ''' 
        sql_select = ''
        if media_type == self.type_movie:
            if imdb_id:
                sql_select="SELECT overlay FROM movie_meta WHERE imdb_id = '%s'" % imdb_id
            elif tmdb_id:
                sql_select="SELECT overlay FROM movie_meta WHERE tmdb_id = '%s'" % tmdb_id
        elif media_type == self.type_tvshow:
            sql_select="SELECT overlay FROM tvshow_meta WHERE imdb_id = '%s'" % imdb_id
        elif media_type == self.type_season:
            sql_select = "SELECT overlay FROM season_meta WHERE imdb_id = '%s' AND season = %s" % (imdb_id, season)
        
        common.addon.log('SQL Select: %s' % sql_select, 0)
        try:
            self.dbcur.execute(sql_select)
            matchedrow = self.dbcur.fetchone()
        except Exception as e:
            common.addon.log('************* Error attempting to select from %s table: %s ' % (table, e), 4)
            pass  
                    
        if matchedrow:
            return dict(matchedrow)['overlay']
        else:
            return 6

        
    def _get_watched_episode(self, meta):
        '''
        Finds the watched status of the video from the cache db
        
        Args:
            meta (dict): full data of episode                    

        '''       
        if meta['imdb_id']:
            sql_select = "SELECT * FROM episode_meta WHERE imdb_id = '%s'"  % meta['imdb_id']
        elif meta['tvdb_id']:
            sql_select = "SELECT * FROM episode_meta WHERE tvdb_id = '%s'"  % meta['tvdb_id']
        else:         
            sql_select = "SELECT * FROM episode_meta WHERE title = '%s'"  % self._clean_string(meta['title'].lower())
        
        if meta['premiered']:
            sql_select += " AND premiered = '%s'" % meta['premiered']
        else:
            sql_select += ' AND season = %s AND episode = %s' % (meta['season'], meta['episode'])
            
        common.addon.log('Getting episode watched status', 0)
        common.addon.log('SQL Select: %s' % sql_select, 0)
        try:
            self.dbcur.execute(sql_select)
            matchedrow = self.dbcur.fetchone()
        except Exception as e:
            common.addon.log('************* Error attempting to select from episode_meta table: %s ' % e, 4)
            pass  
                   
        if matchedrow:
                return dict(matchedrow)['overlay']
        else:
            return 6


    def _find_cover(self, season, images):
        '''
        Finds the url of the banner to be used as the cover 
        from a list of images for a given season
        
        Args:
            season (str): tv show season number, number only no other characters
            images (dict): all images related
                        
        Returns:
            (str) cover_url: url of the selected image
        '''         
        cover_url = ''
        
        for image in images:
            (banner_url, banner_type, banner_season) = image
            if banner_season == season and banner_type == 'season':
                cover_url = banner_url
                break
        
        return cover_url


    def get_seasons(self, tvshowtitle, imdb_id, seasons, overlay=6):
        '''
        Requests from TVDB a list of images for a given tvshow
        and list of seasons
        
        Args:
            tvshowtitle (str): TV Show Title
            imdb_id (str): IMDB ID
            seasons (str): a list of seasons, numbers only
                        
        Returns:
            (list) list of covers found for each season
        '''     
        if imdb_id:
            imdb_id = self._valid_imdb_id(imdb_id)
                
        coversList = []
        tvdb_id = self._get_tvdb_id(tvshowtitle, imdb_id)
        images  = None
        for season in seasons:
            meta = self._cache_lookup_season(imdb_id, tvdb_id, season)
            if meta is None:
                meta = {}
                if tvdb_id is None or tvdb_id == '':
                    meta['cover_url']=''
                elif images:
                    meta['cover_url']=self._find_cover(season, images )
                else:
                    if len(str(season)) == 4:
                        meta['cover_url']=''
                    else:
                        images = self._get_season_posters(tvdb_id, season)
                        meta['cover_url']=self._find_cover(season, images )
                        
                meta['season'] = int(season)
                meta['tvdb_id'] = tvdb_id
                meta['imdb_id'] = imdb_id
                meta['overlay'] = overlay
                meta['backdrop_url'] = self._get_tvshow_backdrops(imdb_id, tvdb_id)
                              
                #Ensure we are not sending back any None values, XBMC doesn't like them
                meta = self._remove_none_values(meta)
                                
                self._cache_save_season_meta(meta)

            #Set Watched flag
            meta['playcount'] = self.__set_playcount(meta['overlay'])
            
            coversList.append(meta)
                   
        return coversList


    def update_season(self, tvshowtitle, imdb_id, season):
        '''
        Update an individual season:
            - looks up and deletes existing entry, saving watched flag (overlay)
            - re-scans TVDB for season image
        
        Args:
            tvshowtitle (str): TV Show Title
            imdb_id (str): IMDB ID
            season (int): season number to be refreshed
                        
        Returns:
            (list) list of covers found for each season
        '''     

        #Find tvdb_id for the TVshow
        tvdb_id = self._get_tvdb_id(tvshowtitle, imdb_id)

        common.addon.log('---------------------------------------------------------------------------------------', 0)
        common.addon.log('Updating season meta data: %s IMDB: %s TVDB ID: %s SEASON: %s' % (tvshowtitle, imdb_id, tvdb_id, season), 0)

      
        if imdb_id:
            imdb_id = self._valid_imdb_id(imdb_id)
        else:
            imdb_id = ''
       
        #Lookup in cache table for existing entry
        meta = self._cache_lookup_season(imdb_id, tvdb_id, season)
        
        #We found an entry in the DB, so lets delete it
        if meta:
            overlay = meta['overlay']
            self._cache_delete_season_meta(imdb_id, tvdb_id, season)
        else:
            overlay = 6
            common.addon.log('No match found in cache db', 0)

        return self.get_seasons(tvshowtitle, imdb_id, season, overlay)


    def _get_tvshow_backdrops(self, imdb_id, tvdb_id):
        '''
        Gets the backdrop_url from tvshow_meta to be included with season & episode meta
        
        Args:              
            imdb_id (str): IMDB ID
            tvdb_id (str): TVDB ID

        ''' 

        sql_select = "SELECT backdrop_url FROM tvshow_meta WHERE imdb_id = '%s' AND tvdb_id = '%s'" % (imdb_id, tvdb_id)
        
        common.addon.log('SQL Select: %s' % sql_select, 0)
        try:
            self.dbcur.execute(sql_select)
            matchedrow = self.dbcur.fetchone()
        except Exception as e:
            common.addon.log('************* Error attempting to select from tvshow_meta table: %s ' % e, 4)
            pass  
                    
        if matchedrow:
            return dict(matchedrow)['backdrop_url']
        else:
            return ''


    def _get_season_posters(self, tvdb_id, season):
        tvdb = TheTVDB(language=self.__get_tvdb_language())
        
        try:
            images = tvdb.get_show_image_choices(tvdb_id)
        except Exception as e:
            common.addon.log('************* Error retreiving from thetvdb.com: %s ' % e, 4)
            images = None
            pass
            
        return images
        

    def _cache_lookup_season(self, imdb_id, tvdb_id, season):
        '''
        Lookup data for a given season in the local cache DB.
        
        Args:
            imdb_id (str): IMDB ID
            tvdb_id (str): TVDB ID
            season (str): tv show season number, number only no other characters
                        
        Returns:
            (dict) meta data for a match
        '''      
        
        common.addon.log('Looking up season data in cache db, imdb id: %s tvdb_id: %s season: %s' % (imdb_id, tvdb_id, season), 0)
        
        if imdb_id:
            sql_select = "SELECT a.*, b.backdrop_url FROM season_meta a, tvshow_meta b WHERE a.imdb_id = '%s' AND season =%s and a.imdb_id=b.imdb_id and a.tvdb_id=b.tvdb_id"  % (imdb_id, season)
        elif tvdb_id:
            sql_select = "SELECT a.*, b.backdrop_url FROM season_meta a, tvshow_meta b WHERE a.tvdb_id = '%s' AND season =%s  and a.imdb_id=b.imdb_id and a.tvdb_id=b.tvdb_id"  % (tvdb_id, season)
        else:
            return None
            
          
        common.addon.log('SQL Select: %s' % sql_select, 0)
        try:
            self.dbcur.execute(sql_select)
            matchedrow = self.dbcur.fetchone()
        except Exception as e:
            common.addon.log('************* Error attempting to select from season_meta table: %s ' % e, 4)
            pass 
                    
        if matchedrow:
            common.addon.log('Found season meta information in cache table: %s' % dict(matchedrow), 0)
            return dict(matchedrow)
        else:
            return None


    def _cache_save_season_meta(self, meta):
        '''
        Save data for a given season in local cache DB.
        
        Args:
            meta (dict): full meta data for season
        '''     
        try:
            self.dbcur.execute("SELECT * FROM season_meta WHERE imdb_id = '%s' AND season ='%s' " 
                               % ( meta['imdb_id'], meta['season'] ) ) 
            matchedrow = self.dbcur.fetchone()
            if matchedrow:
                common.addon.log('Season matched row found, deleting table entry', 0)
                self.dbcur.execute("DELETE FROM season_meta WHERE imdb_id = '%s' AND season ='%s' " 
                                   % ( meta['imdb_id'], meta['season'] ) )
        except Exception as e:
            common.addon.log('************* Error attempting to delete from cache table: %s ' % e, 4)
            common.addon.log('Meta data: %s' % meta, 4)
            pass 
                    
        common.addon.log('Saving season cache information: %s' % meta, 0)
        try:
            sql_insert = self.__insert_from_dict('season_meta', 5)
            common.addon.log('SQL Insert: %s' % sql_insert, 0)
            self.dbcur.execute(sql_insert, (meta['imdb_id'],meta['tvdb_id'],meta['season'],
                               meta['cover_url'],meta['overlay'])
                               )
            self.dbcon.commit()
        except Exception as e:
            common.addon.log('************* Error attempting to insert into seasons cache table: %s ' % e, 4)
            common.addon.log('Meta data: %s' % meta, 4)
            pass         


    def _cache_delete_season_meta(self, imdb_id, tvdb_id, season):
        '''
        Delete meta data from SQL table
        
        Args:
            imdb_id (str): IMDB ID
            tvdb_id (str): TVDB ID
            season (int): Season #
        '''

        sql_delete = "DELETE FROM season_meta WHERE imdb_id = '%s' AND tvdb_id = '%s' and season = %s" % (imdb_id, tvdb_id, season)

        common.addon.log('Deleting table entry: IMDB: %s TVDB: %s Season: %s ' % (imdb_id, tvdb_id, season), 0)
        common.addon.log('SQL DELETE: %s' % sql_delete, 0)
        try:
            self.dbcur.execute(sql_delete)
            self.dbcon.commit()
        except Exception as e:
            common.addon.log('************* Error attempting to delete from season cache table: %s ' % e, 4)
            pass


    def get_batch_meta(self, media_type, batch_ids):
        '''
        Main method to get meta data for movie or tvshow. Will lookup by name/year 
        if no IMDB ID supplied.       
        
        Args:
            media_type (str): 'movie' or 'tvshow'
            batch_ids (tuple): a list of tuples containing the following in order:
                                - imdb_id (str)
                                - tmdb_id (str)
                                - movie/tvshow name (str)
                                - year (int)
        Returns:
            DICT of meta data or None if cannot be found.
        '''
       
        common.addon.log('---------------------------------------------------------------------------------------', 0)
        common.addon.log('Starting batch meta grab', 0)
        common.addon.log('Batch meta information passed in: %s' % batch_ids, 0)

        #Ensure IMDB ID's are formatted properly first
        new_batch_ids = []
        for i,(imdb_id, tmdb_id, vidname, year) in enumerate(batch_ids):
            new_batch_ids.append((self._valid_imdb_id(imdb_id), tmdb_id, vidname, year))

        #Check each record and determine if should query cache db against ID's or Name & Year
        batch_ids = []
        batch_names = []
        for x in new_batch_ids:
            if x[0] or x[1]:
                batch_ids.append((x[0], x[1], x[2], x[3]))
            else:
                batch_names.append((x[0], x[1], x[2], x[3]))
        
        cache_meta = []
        #Determine how and then check local cache for meta data
        if batch_ids:
            temp_cache = self.__cache_batch_lookup_by_id(media_type, batch_ids)
            if temp_cache:
                cache_meta += temp_cache
        
        if batch_names:
            temp_cache = self.__cache_batch_lookup_by_id(media_type, batch_names)
            if temp_cache:
                cache_meta += temp_cache            
            print cache_meta


        #Check if any records were not found in cache, store them in list if not found
        no_cache_ids = []
        if cache_meta:
            for m in new_batch_ids:
                try:
                    x = next((i for i,v in enumerate(cache_meta) if v['imdb_id'] == m[0] or v['tmdb_id'] == m[1] or v['name'] == m[2] ), None)
                except:
                    x = None
                if x is None:
                    no_cache_ids.append(m)
        else:
            cache_meta = []
            no_cache_ids = new_batch_ids

        new_meta = []

        for record in no_cache_ids:
            
            if media_type==self.type_movie:
                meta = self._get_tmdb_meta(record[0], record[1], record[2], record[3])
                common.addon.log('---------------------------------------------------------------------------------------', 0)
            elif media_type==self.type_tvshow:
                meta = self._get_tvdb_meta(record[0], record[1], record[2], record[3])
                common.addon.log('---------------------------------------------------------------------------------------', 0)

            new_meta.append(meta)
            
        #If we found any new meta, add it to our cache list
        if new_meta:
            cache_meta += new_meta
            
            #Save any new meta to cache
            self._cache_save_video_meta(new_meta, 'test', media_type)
        
        #Format and return final list of meta
        return_meta = []
        for meta in cache_meta:
            if type(meta) is database.Row:
                meta = dict(meta)
            meta = self.__format_meta(media_type, meta,'test')
            return_meta.append(meta)
        
        return return_meta


    def __cache_batch_lookup_by_id(self, media_type, batch_ids):
        '''
        Lookup in SQL DB for video meta data by IMDB ID
        
        Args:
            media_type (str): 'movie' or 'tvshow'
            batch_ids (tuple): a list of list items containing the following in order:
                                - imdb_id (str)*
                                - tmdb_id (str)
                                - name (str)
                                - year (int)
        Returns:
            DICT of matched meta data or None if no match.
        '''        

        placeholder= '?'
        placeholders= ', '.join(placeholder for x in batch_ids)
        
        ids = []
        if media_type == self.type_movie:
            sql_select = "SELECT * FROM movie_meta a"
            
            #If there is an IMDB ID given then use it for entire operation
            if batch_ids[0][0]:
                sql_select = sql_select + " WHERE a.imdb_id IN (%s)" % placeholders
                for x in batch_ids:
                    ids.append(x[0])
                    
            #If no IMDB but TMDB then use that instead
            elif batch_ids[0][1]:
                sql_select = sql_select + " WHERE a.tmdb_id IN (%s)" % placeholders
                for x in batch_ids:
                    ids.append(x[1])
                    
            #If no id's given then default to use the name and year
            elif batch_ids[0][2]:
                 
                #If we have a year then need to inner join with same table
                if batch_ids[0][3]:
                    sql_select = sql_select + (" INNER JOIN "
                                                    "(SELECT title, year FROM movie_meta "
                                                             "WHERE year IN (%s)) b "
                                                  "ON a.title = b.title AND a.year = b.year "
                                                "WHERE a.title in (%s) ") % (placeholders, placeholders)

                #If no year then just straight select on name
                else:
                    sql_select = sql_select + " WHERE a.title IN (%s)" % placeholders
                    for x in batch_ids:
                        ids.append(self._clean_string(x[2].lower()))
            else:
                common.addon.log( 'No data given to create SQL SELECT or data types are currently unsupported', 4)
                return None

        common.addon.log( 'SQL Select: %s' % sql_select, 0)

        try:
            self.dbcur.execute(sql_select, ids)
            matchedrows = self.dbcur.fetchall()            
        except Exception as e:
            common.addon.log('************* Error selecting from cache db: %s' % e, 4)
            return None
        
        if matchedrows:
            for row in matchedrows:
                common.addon.log('Found meta information by id in cache table: %s' % dict(row), 0)
            return matchedrows
        else:
            common.addon.log('No match in local DB', 0)
            return None
