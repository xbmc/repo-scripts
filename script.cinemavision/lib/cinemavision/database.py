import time
import datetime

try:
    datetime.datetime.strptime('0', '%H')
except TypeError:
    # Fix for datetime issues with XBMC/Kodi
    class new_datetime(datetime.datetime):
        @classmethod
        def strptime(cls, dstring, dformat):
            return datetime.datetime(*(time.strptime(dstring, dformat)[0:6]))

    datetime.datetime = new_datetime

from peewee import peewee
import util

DATABASE_VERSION = 6

fn = peewee.fn

DB = None
W_DB = None
DBVersion = None
Song = None
Trivia = None
AudioFormatBumpers = None
RatingsBumpers = None
VideoBumpers = None
RatingSystem = None
Rating = None
Trailers = None
WatchedTrivia = None


def session(func):
    def inner(*args, **kwargs):
        try:
            DB.connect()
            with DB.atomic():
                return func(*args, **kwargs)
        finally:
            DB.close()
    return inner


def sessionW(func):
    def inner(*args, **kwargs):
        try:
            W_DB.connect()
            with W_DB.atomic():
                return func(*args, **kwargs)
        finally:
            W_DB.close()
    return inner


def connect():
    DB.connect()


def close():
    DB.close()


def dummyCallback(*args, **kwargs):
    pass


def migrateDB(DB, version):
    util.LOG('Migrating database from version {0} to {1}'.format(version, DATABASE_VERSION))
    from peewee.playhouse import migrate
    migrator = migrate.SqliteMigrator(DB)
    migratorW = migrate.SqliteMigrator(W_DB)

    if version < 1:
        try:
            migrate.migrate(
                migrator.add_column('RatingsBumpers', 'style', peewee.CharField(default='Classic'))
            )
        except peewee.OperationalError:
            util.MINOR_ERROR('Migration (RatingsBumpers: Add style column)')
        except:
            util.ERROR()
            return False

    if version < 2:
        try:
            migrate.migrate(
                migrator.add_column('RatingSystem', 'regions', peewee.CharField(null=True)),
                migrator.drop_not_null('RatingSystem', 'context'),
            )
        except peewee.OperationalError:
            util.MINOR_ERROR('Migration (RatingSystem: Add region column)')
        except:
            util.ERROR()
            return False

    if version < 5:
        try:
            migrate.migrate(
                migratorW.add_column('Trailers', 'is3D', peewee.BooleanField(default=False)),
            )
        except peewee.OperationalError:
            util.MINOR_ERROR('Migration (Trailers: Add is3D column)')
        except:
            util.ERROR()
            return False

    if version < 6:
        try:
            migrate.migrate(
                migratorW.add_column('Trailers', 'verified', peewee.BooleanField(default=True)),
            )
        except peewee.OperationalError:
            util.MINOR_ERROR('Migration (Trailers: Add verified column)')
        except:
            util.ERROR()
            return False

    return True


def checkDBVersion(DB):
    vm = DBVersion.get_or_create(id=1, defaults={'version': 0})[0]
    if vm.version < DATABASE_VERSION:
        if migrateDB(DB, vm.version):
            vm.update(version=DATABASE_VERSION).execute()


def initialize(path=None, callback=None):
    callback = callback or dummyCallback

    callback(None, 'Creating/updating database...')

    global DB
    global W_DB
    global DBVersion
    global Song
    global Trivia
    global AudioFormatBumpers
    global RatingsBumpers
    global VideoBumpers
    global RatingSystem
    global Rating
    global Trailers
    global WatchedTrivia

    ###########################################################################################
    # Version
    ###########################################################################################
    dbDir = path or util.STORAGE_PATH
    if not util.vfs.exists(dbDir):
        util.vfs.mkdirs(dbDir)

    dbPath = util.pathJoin(dbDir, 'content.db')
    dbExists = util.vfs.exists(dbPath)

    DB = peewee.SqliteDatabase(dbPath)
    W_DB = peewee.SqliteDatabase(util.pathJoin(path or util.STORAGE_PATH, 'watched.db'))

    DB.connect()

    class DBVersion(peewee.Model):
        version = peewee.IntegerField(default=0)

        class Meta:
            database = DB

    DBVersion.create_table(fail_silently=True)

    if dbExists:  # Only check version if we had a DB, otherwise we're creating it fresh
        checkDBVersion(DB)

    ###########################################################################################
    # Content
    ###########################################################################################
    class ContentBase(peewee.Model):
        name = peewee.CharField()
        accessed = peewee.DateTimeField(null=True)
        pack = peewee.TextField(null=True)

        class Meta:
            database = DB

    callback(' - Music')

    class Song(ContentBase):
        rating = peewee.CharField(null=True)
        genre = peewee.CharField(null=True)
        year = peewee.CharField(null=True)

        path = peewee.CharField(unique=True)
        duration = peewee.FloatField(default=0)

    Song.create_table(fail_silently=True)

    callback(' - Tivia')

    class Trivia(ContentBase):
        type = peewee.CharField()

        TID = peewee.CharField(unique=True)

        rating = peewee.CharField(null=True)
        genre = peewee.CharField(null=True)
        year = peewee.CharField(null=True)
        duration = peewee.FloatField(default=0)

        questionPath = peewee.CharField(unique=True, null=True)
        cluePath0 = peewee.CharField(unique=True, null=True)
        cluePath1 = peewee.CharField(unique=True, null=True)
        cluePath2 = peewee.CharField(unique=True, null=True)
        cluePath3 = peewee.CharField(unique=True, null=True)
        cluePath4 = peewee.CharField(unique=True, null=True)
        cluePath5 = peewee.CharField(unique=True, null=True)
        cluePath6 = peewee.CharField(unique=True, null=True)
        cluePath7 = peewee.CharField(unique=True, null=True)
        cluePath8 = peewee.CharField(unique=True, null=True)
        cluePath9 = peewee.CharField(unique=True, null=True)
        answerPath = peewee.CharField(unique=True, null=True)

    Trivia.create_table(fail_silently=True)

    callback(' - AudioFormatBumpers')

    class BumperBase(ContentBase):
        is3D = peewee.BooleanField(default=False)
        isImage = peewee.BooleanField(default=False)
        path = peewee.CharField(unique=True)

    class AudioFormatBumpers(BumperBase):
        format = peewee.CharField()

    AudioFormatBumpers.create_table(fail_silently=True)

    callback(' - RatingsBumpers')

    class RatingsBumpers(BumperBase):
        system = peewee.CharField(default='MPAA')
        style = peewee.CharField(default='Classic')

    RatingsBumpers.create_table(fail_silently=True)

    callback(' - VideoBumpers')

    class VideoBumpers(BumperBase):
        type = peewee.CharField()

        rating = peewee.CharField(null=True)
        genre = peewee.CharField(null=True)
        year = peewee.CharField(null=True)

    VideoBumpers.create_table(fail_silently=True)

    ###########################################################################################
    # Ratings
    ###########################################################################################
    class RatingSystem(peewee.Model):
        name = peewee.CharField()
        context = peewee.CharField(null=True)
        regEx = peewee.CharField()
        regions = peewee.CharField(null=True)

        class Meta:
            database = DB

    RatingSystem.create_table(fail_silently=True)

    class Rating(peewee.Model):
        name = peewee.CharField(unique=True)
        internal = peewee.CharField()
        value = peewee.IntegerField(default=0)
        system = peewee.CharField()

        class Meta:
            database = DB

    Rating.create_table(fail_silently=True)

    ###########################################################################################
    # Watched Database
    ###########################################################################################
    class WatchedBase(peewee.Model):
        WID = peewee.CharField(unique=True)
        watched = peewee.BooleanField(default=False)
        date = peewee.DateTimeField(default=datetime.date(1900, 1, 1))

        class Meta:
            database = W_DB

    class Trailers(WatchedBase):
        source = peewee.CharField()
        rating = peewee.CharField(null=True)
        genres = peewee.CharField(null=True)
        title = peewee.CharField()
        release = peewee.DateTimeField(default=datetime.date(1900, 1, 1))
        url = peewee.CharField(null=True)
        userAgent = peewee.CharField(null=True)
        thumb = peewee.CharField(null=True)
        broken = peewee.BooleanField(default=False)
        is3D = peewee.BooleanField(default=False)
        verified = peewee.BooleanField(default=True)

    Trailers.create_table(fail_silently=True)

    callback(' - Trailers')

    class WatchedTrivia(WatchedBase):
        pass

    WatchedTrivia.create_table(fail_silently=True)

    callback(' - Trivia (watched status)')

    callback(None, 'Database created')

    DB.close()
