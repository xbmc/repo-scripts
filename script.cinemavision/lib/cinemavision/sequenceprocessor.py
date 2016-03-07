import os
import random
import re
import time
import datetime
import database as DB
import sequence
import scrapers
import ratings
import actions
import util


# Playabe is implemented as a dict to be easily serializable to JSON
class PlayableBase(dict):
    type = None

    @property
    def module(self):
        if hasattr(self, '_module'):
            return self._module

    def fromModule(self, module):
        self._module = module
        self['module'] = module._type
        return self


class Playable(PlayableBase):
    type = None

    @property
    def path(self):
        return self['path']

    def __repr__(self):
        return '{0}: {1}'.format(self.type, repr(self.path))


class PlayableQueue(PlayableBase):
    pass


class Image(Playable):
    type = 'IMAGE'

    def __init__(self, path, duration=10, set_number=0, set_id=None, fade=0, *args, **kwargs):
        Playable.__init__(self, *args, **kwargs)
        self['path'] = path
        self['duration'] = duration
        self['setNumber'] = set_number
        self['setID'] = set_id
        self['fade'] = fade

    def __repr__(self):
        return 'IMAGE ({0}s): {1}'.format(self.duration, self.path)

    @property
    def setID(self):
        return self['setID']

    @property
    def duration(self):
        return self['duration']

    @duration.setter
    def duration(self, val):
        self['duration'] = val

    @property
    def setNumber(self):
        return self['setNumber']

    @property
    def fade(self):
        return self['fade']


class Song(Playable):
    type = 'SONG'

    def __init__(self, path, duration=0, *args, **kwargs):
        self['path'] = path
        self['duration'] = duration
        Playable.__init__(self, *args, **kwargs)

    @property
    def duration(self):
        return self['duration']

    @property
    def durationInt(self):
        return int(self['duration'])


class ImageQueue(PlayableQueue):
    type = 'IMAGE.QUEUE'

    def __init__(self, handler, s_item, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        self._handler = handler
        self.sItem = s_item
        self.maxDuration = s_item.getLive('duration') * 60
        self.pos = -1
        self.transition = None
        self.transitionDuration = 400
        self.music = None
        self.musicVolume = 85
        self.musicFadeIn = 3.0
        self.musicFadeOut = 3.0

    def __iadd__(self, other):
        for o in other:
            self.duration += o.duration

        self.queue += other
        return self

    def __contains__(self, images):
        paths = [i.path for i in self.queue]
        if isinstance(images, list):
            for i in images:
                if i.path in paths:
                    return True
        else:
            return images.path in paths

        return False

    def __repr__(self):
        return '{0}: {1}secs'.format(self.type, self.duration)

    def reset(self):
        self.pos = -1

    def size(self):
        return len(self.queue)

    @property
    def duration(self):
        return self.get('duration', 0)

    @duration.setter
    def duration(self, val):
        self['duration'] = val

    @property
    def queue(self):
        return self.get('queue', [])

    @queue.setter
    def queue(self, q):
        self['queue'] = q

    def current(self):
        return self.queue[self.pos]

    def add(self, image):
        self.queue.append(image)

    def next(self, start=0, count=1, extend=False):
        overtime = start and time.time() - start >= self.maxDuration
        if overtime and not self.current().setNumber:
            return None

        if count > 1:  # Handle big skips. Here we skip by slide sets
            self.pos += self.current().setNumber  # Move to the end of the current set

            for c in range(count - 1):
                while True:
                    if self.pos >= self.size() - 1:  # We need more slides
                        if not self._next():
                            break
                    else:
                        self.pos += 1

                    if not self.current().setNumber:  # We're at the end of a set
                        break

        if self.pos >= self.size() - 1:
            if extend or not overtime:
                return self._next()
            else:
                return None

        self.pos += 1

        return self.current()

    def _next(self):
        util.DEBUG_LOG('ImageQueue: Requesting next...')
        images = self._handler.next(self)
        if not images:
            util.DEBUG_LOG('ImageQueue: No next images')
            return None

        util.DEBUG_LOG('ImageQueue: {0} returned'.format(len(images)))
        self.queue += images
        self.pos += 1

        return self.current()

    def prev(self, count=1):
        if self.pos < 1:
            return None

        if count > 1:
            for c in range(count + 1):
                while self.pos > -1:
                    self.pos -= 1
                    if not self.current().setNumber:  # We're at the end of a set
                        break

            self.pos += 1

            return self.current()

        self.pos -= 1

        if self.pos < 0:
            self.pos = 0

        return self.current()

    def mark(self, image):
        if not image.setNumber:
            util.DEBUG_LOG('ImageQueue: Marking image as watched')
            self._handler.mark(image)

    def onFirst(self):
        return self.pos == 0

    def onLast(self):
        return self.pos == self.size() - 1


class Video(Playable):
    type = 'VIDEO'

    def __init__(self, path, user_agent='', duration=0, set_id=None, title='', thumb='', volume=100):
        self['path'] = path
        self['userAgent'] = user_agent
        self['duration'] = duration
        self['setID'] = set_id
        self['title'] = title or os.path.splitext(os.path.basename(path))[0]
        self['thumb'] = thumb
        self['volume'] = volume

    @property
    def title(self):
        return self.get('title', '')

    @title.setter
    def title(self, val):
        self['title'] = val

    @property
    def thumb(self):
        return self.get('thumb', '')

    @thumb.setter
    def thumb(self, val):
        self['thumb'] = val

    @property
    def setID(self):
        return self['setID']

    @property
    def userAgent(self):
        return self['userAgent']

    @property
    def duration(self):
        return self.get('duration', 0)

    @property
    def volume(self):
        return self.get('volume', 100)

    @volume.setter
    def volume(self, val):
        self['volume'] = val


class VideoQueue(PlayableQueue):
    type = 'VIDEO.QUEUE'

    def __init__(self, handler, s_item, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        self._handler = handler
        self.sItem = s_item
        self.duration = 0
        self['queue'] = []

    def __contains__(self, video):
        paths = [v.path for v in self.queue]
        return video.path in paths

    def __repr__(self):
        return '{0}: {1}secs'.format(self.type, self.duration)

    def append(self, video):
        self.duration += video.duration

        self['queue'].append(video)

    @property
    def queue(self):
        return self['queue']

    @queue.setter
    def queue(self, q):
        self['queue'] = q

    def mark(self, video):
        util.DEBUG_LOG('VideoQueue: Marking video as watched')
        self._handler.mark(video)


class Feature(Video):
    type = 'FEATURE'

    def __repr__(self):
        return 'FEATURE [ {0} ]:\n    Path: {1}\n    Rating: ({2})\n    Genres: {3}\n    3D: {4}\n    Audio: {5}'.format(
            repr(self.title),
            repr(self.path),
            repr(self.rating),
            repr(self.genres),
            self.is3D and 'Yes' or 'No',
            repr(self.audioFormat)
        )

    @property
    def ID(self):
        return self.get('ID', '')

    @ID.setter
    def ID(self, val):
        self['ID'] = val

    @property
    def dbType(self):
        return self.get('dbType', '')

    @dbType.setter
    def dbType(self, val):
        self['dbType'] = val

    @property
    def rating(self):
        if not getattr(self, '_rating', None):
            ratingString = self.get('rating')
            if ratingString:
                self._rating = ratings.getRating(ratingString)
            else:
                self._rating = None
        return self._rating

    @rating.setter
    def rating(self, val):
        self['rating'] = val

    @property
    def genres(self):
        return self.get('genres', [])

    @genres.setter
    def genres(self, val):
        self['genres'] = val

    @property
    def is3D(self):
        return self.get('is3D', False)

    @is3D.setter
    def is3D(self, val):
        self['is3D'] = val

    @property
    def audioFormat(self):
        return self.get('audioFormat', '')

    @audioFormat.setter
    def audioFormat(self, val):
        self['audioFormat'] = val

    @property
    def codec(self):
        return self.get('codec', '')

    @codec.setter
    def codec(self, val):
        self['codec'] = val

    @property
    def channels(self):
        return self.get('channels', '')

    @channels.setter
    def channels(self, val):
        self['channels'] = val

    @property
    def thumb(self):
        return self.get('thumbnail', '')

    @thumb.setter
    def thumb(self, val):
        self['thumbnail'] = val

    @property
    def runtime(self):
        return self.get('runtime', '')

    @runtime.setter
    def runtime(self, val):
        self['runtime'] = val

    @property
    def year(self):
        return self.get('year', '')

    @year.setter
    def year(self, val):
        self['year'] = val

    @property
    def durationMinutesDisplay(self):
        if not self.runtime:
            return

        return '{0} minutes'.format(self.runtime/60)


class Action(dict):
    type = 'ACTION'

    def __init__(self, processor, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        self.processor = processor
        self['path'] = processor.path

    def __repr__(self):
        return '{0}: {1} - {2}'.format(self.type, self['path'], self.processor)

    def run(self):
        self.processor.run()


class FeatureHandler:
    @DB.session
    def getRatingBumper(self, sItem, feature, image=False):
        try:
            if not feature.rating:
                return None

            if sItem.getLive('ratingStyleSelection') == 'style':
                return DB.RatingsBumpers.select().where(
                    (DB.RatingsBumpers.system == feature.rating.system) &
                    (DB.RatingsBumpers.name == feature.rating.name) &
                    (DB.RatingsBumpers.is3D == feature.is3D) &
                    (DB.RatingsBumpers.isImage == image) &
                    (DB.RatingsBumpers.style == sItem.getLive('ratingStyle'))
                )[0]

            else:
                return random.choice(
                    [
                        x for x in DB.RatingsBumpers.select().where(
                            (DB.RatingsBumpers.system == feature.rating.system) &
                            (DB.RatingsBumpers.name == feature.rating.name) &
                            (DB.RatingsBumpers.is3D == feature.is3D) &
                            (DB.RatingsBumpers.isImage == image)
                        )
                    ]
                )
        except IndexError:
            return None

    def __call__(self, caller, sItem):
        count = sItem.getLive('count')

        util.DEBUG_LOG('[{0}] x {1}'.format(sItem.typeChar, count))

        features = caller.getNextFeatures(count)

        playables = []
        mediaType = sItem.getLive('ratingBumper')

        for f in features:
            f.fromModule(sItem)
            f.volume = sItem.getLive('volume')
            bumper = None
            if mediaType == 'video':
                bumper = self.getRatingBumper(sItem, f)
                if bumper:
                    playables.append(Video(bumper.path, volume=sItem.getLive('volume')).fromModule(sItem))
                    util.DEBUG_LOG('    - Video Rating: {0}'.format(repr(bumper.path)))
            if mediaType == 'image' or mediaType == 'video' and not bumper:
                bumper = self.getRatingBumper(sItem, f, image=True)
                if bumper:
                    playables.append(Image(bumper.path, duration=10, fade=3000).fromModule(sItem))
                    util.DEBUG_LOG('    - Image Rating: {0}'.format(repr(bumper.path)))

            playables.append(f)

        return playables


class TriviaHandler:
    def __init__(self):
        pass

    def __call__(self, caller, sItem):
        duration = sItem.getLive('duration')

        util.DEBUG_LOG('[{0}] {1}m'.format(sItem.typeChar, duration))

        durationLimit = duration * 60
        queue = ImageQueue(self, sItem).fromModule(sItem)
        queue.transition = sItem.getLive('transition')
        queue.transitionDuration = sItem.getLive('transitionDuration')

        vqueue = VideoQueue(self, sItem).fromModule(sItem)

        for slides in self.getTriviaImages(sItem):
            if isinstance(slides, Video):
                vqueue.append(slides)
            else:
                queue += slides

            if queue.duration + vqueue.duration >= durationLimit:
                break

        ret = []

        if queue.duration:
            ret.append(queue)
            queue.maxDuration -= vqueue.duration
        if vqueue.duration:
            ret.append(vqueue)

        self.addMusic(sItem, queue)

        return ret

    @DB.session
    def addMusic(self, sItem, queue):
        mode = sItem.getLive('music')
        if mode == 'off':
            return

        if mode == 'content':
            queue.music = [Song(s.path, s.duration) for s in DB.Song.select().order_by(DB.fn.Random())]
        elif mode == 'dir':
            path = sItem.getLive('musicDir')
            if not path:
                return

            import mutagen
            mutagen.setFileOpener(util.vfs.File)

            queue.music = []
            for p in util.listFilePaths(path):
                try:
                    data = mutagen.File(p)
                except:
                    data = None
                    util.ERROR()

                d = 0
                if data:
                    d = data.info.length
                queue.music.append(Song(p, d))

            random.shuffle(queue.music)
        elif mode == 'file':
            path = sItem.getLive('musicFile')
            if not path:
                return

            import mutagen
            mutagen.setFileOpener(util.vfs.File)

            data = mutagen.File(path)
            d = 0
            if data:
                d = data.info.length
            queue.music = [Song(path, d)]

        duration = sum([s.duration for s in queue.music])

        if duration:  # Maybe they were all zero - we'll be here forever :)
            while duration < queue.duration:
                for i in range(len(queue.music)):
                    song = queue.music[i]
                    duration += song.duration
                    queue.music.append(song)
                    if duration >= queue.duration:
                        break

        queue.musicVolume = util.getSettingDefault('trivia.musicVolume')
        queue.musicFadeIn = util.getSettingDefault('trivia.musicFadeIn')
        queue.musicFadeOut = util.getSettingDefault('trivia.musicFadeOut')

    @DB.session
    @DB.sessionW
    def getTriviaImages(self, sItem):  # TODO: Probably re-do this separate for slides and video?
        useVideo = sItem.getLive('format') == 'video'
        # Do this each set in reverse so the setNumber counts down
        clue = sItem.getLive('cDuration')
        durations = (
            sItem.getLive('aDuration'),
            clue, clue, clue, clue, clue, clue, clue, clue, clue, clue,
            sItem.getLive('qDuration')
        )
        for trivia in DB.Trivia.select().order_by(DB.fn.Random()):
            if useVideo:
                if trivia.type != 'video':
                    continue
            else:
                if trivia.type == 'video':
                    continue

            try:
                DB.WatchedTrivia.get((DB.WatchedTrivia.WID == trivia.TID) & DB.WatchedTrivia.watched)
            except DB.peewee.DoesNotExist:
                yield self.createTriviaImages(sItem, trivia, durations)

        # Grab the oldest 4 trivias, shuffle and yield... repeat
        pool = []
        for watched in DB.WatchedTrivia.select().where(DB.WatchedTrivia.watched).order_by(DB.WatchedTrivia.date):
            try:
                trivia = DB.Trivia.get(DB.Trivia.TID == watched.WID)
            except DB.peewee.DoesNotExist:
                continue

            if useVideo:
                if trivia.type != 'video':
                    continue
            else:
                if trivia.type == 'video':
                    continue

            pool.append(trivia)

            if len(pool) > 3:
                random.shuffle(pool)
                for t in pool:
                    yield self.createTriviaImages(sItem, t, durations)
                pool = []

        if pool:
            random.shuffle(pool)
            for t in pool:
                yield self.createTriviaImages(sItem, t, durations)

    def createTriviaImages(self, sItem, trivia, durations):
        if trivia.type == 'video':
            return Video(trivia.answerPath, duration=trivia.duration, set_id=trivia.TID).fromModule(sItem)
        else:
            clues = [getattr(trivia, 'cluePath{0}'.format(x)) for x in range(9, -1, -1)]
            paths = [trivia.answerPath] + clues + [trivia.questionPath]
            slides = []
            setNumber = 0
            for p, d in zip(paths, durations):
                if p:
                    slides.append(Image(p, d, setNumber, trivia.TID).fromModule(sItem))
                    setNumber += 1

            slides.reverse()  # Slides are backwards

            if len(slides) == 1:  # This is a still - set duration accordingly
                slides[0].duration = sItem.getLive('sDuration')

            return slides

    def next(self, image_queue):
        for slides in self.getTriviaImages(image_queue.sItem):
            if slides not in image_queue:
                return slides
        return None

    @DB.sessionW
    def mark(self, image):
        trivia = DB.WatchedTrivia.get_or_create(WID=image.setID)[0]
        trivia.update(
            watched=True,
            date=datetime.datetime.now()
        ).where(DB.WatchedTrivia.WID == image.setID).execute()


class TrailerHandler:
    def __init__(self):
        self.caller = None
        self.sItem = None

    def __call__(self, caller, sItem):
        self.caller = caller
        self.sItem = sItem

        source = sItem.getLive('source')
        count = sItem.getLive('count')

        playables = []
        if source == 'content':
            scrapers.setContentPath(self.caller.contentPath)
            util.DEBUG_LOG('[{0}] {1} x {2}'.format(self.sItem.typeChar, source, count))
            scrapersList = (sItem.getLive('scrapers') or '').split(',')
            if util.getSettingDefault('trailer.preferUnwatched'):
                scrapersInfo = [(s.strip(), True, False) for s in scrapersList]
                scrapersInfo += [(s.strip(), False, True) for s in scrapersList]
            else:
                scrapersInfo = [(s.strip(), True, True) for s in scrapersList]

            for scraper, unwatched, watched in scrapersInfo:
                util.DEBUG_LOG('    - [{0}]'.format(scraper))
                playables += self.scraperHandler(scraper, count, unwatched=unwatched, watched=watched)
                count -= min(len(playables), count)
                if count <= 0:
                    break

        elif source == 'dir' or source == 'content':
            playables = self.dirHandler(sItem)
        elif source == 'file':
            playables = self.fileHandler(sItem)

        if not playables:
            util.DEBUG_LOG('    - NOT SHOWING')

        return playables

    def _getTrailersFromDBRating(self, source, watched=False):
        ratingLimitMethod = self.sItem.getLive('ratingLimit')
        false = False  # To make my IDE happy about == and false

        where = [
            DB.Trailers.source == source,
            DB.Trailers.broken == false,
            DB.Trailers.watched == watched
        ]

        if self.sItem.getLive('order') == 'newest':
            util.DEBUG_LOG('    - Order: Newest')
            orderby = [
                DB.Trailers.release.desc(),
                DB.Trailers.date
            ]
        else:
            util.DEBUG_LOG('    - Order: Random')
            orderby = [
                DB.fn.Random()
            ]

        if self.sItem.getLive('filter3D'):
            where.append(DB.Trailers.is3D == self.caller.nextQueuedFeature.is3D)

        if ratingLimitMethod and ratingLimitMethod != 'none':
            if ratingLimitMethod == 'max':
                maxr = ratings.getRating(self.sItem.getLive('ratingMax').replace('.', ':', 1))
                for t in DB.Trailers.select().where(*where).order_by(*orderby):
                    if ratings.getRating(t.rating).value <= maxr.value:
                        yield t
            elif self.caller.ratings:
                minr = min(self.caller.ratings, key=lambda x: x.value)
                maxr = max(self.caller.ratings, key=lambda x: x.value)

                for t in DB.Trailers.select().where(*where).order_by(*orderby):
                    if minr.value <= ratings.getRating(t.rating).value <= maxr.value:
                        yield t
        else:
            for t in DB.Trailers.select().where(*where).order_by(*orderby):
                yield t

    def _getTrailersFromDBGenre(self, source, watched=False):
        if self.sItem.getLive('limitGenre') and self.caller.genres:
            for t in self._getTrailersFromDBRating(source, watched=watched):
                if any(x in self.caller.genres for x in (t.genres or '').split(',')):
                    yield t
        else:
            for t in self._getTrailersFromDBRating(source, watched=watched):
                yield t

    def getTrailersFromDB(self, source, count, watched=False):
        # Get trailers + a few to make the random more random
        quality = self.sItem.getLive('quality')

        poolSize = count + 5
        trailers = []
        pool = []
        ct = 0
        for t in self._getTrailersFromDBGenre(source, watched=watched):
            pool.append(t)
            ct += 1
            if ct >= poolSize:
                random.shuffle(pool)

                for t in pool:
                    t = self.updateTrailer(t, source, quality)
                    if t:
                        trailers.append(t)
                        if len(trailers) >= count:
                            break
                pool = []
                ct = 0

            if len(trailers) >= count:
                break
        else:
            if pool:
                for t in pool:
                    t = self.updateTrailer(t, source, quality)
                    if t:
                        trailers.append(t)
                        if len(trailers) >= count:
                            break

        return [
            Video(
                t.url,
                t.userAgent,
                title=t.title,
                thumb=t.thumb,
                volume=self.sItem.getLive('volume')
            ).fromModule(self.sItem) for t in trailers
        ]

    def updateTrailer(self, t, source, quality):
        url = scrapers.getPlayableURL(t.WID.split(':', 1)[-1], quality, source, t.url) or ''
        watched = t.watched

        t.watched = True
        t.date = datetime.datetime.now()
        t.url = url
        t.broken = not url
        t.save()
        if not t.broken:
            util.DEBUG_LOG(
                '    - {0}: {1} ({2:%Y-%m-%d}){3}'.format(repr(t.title).lstrip('u').strip("'"), t.rating, t.release, watched and ' - WATCHED' or '')
            )
            return t

        return None

    def updateTrailers(self, source):
        trailers = scrapers.updateTrailers(source)
        if trailers:
            total = len(trailers)
            util.DEBUG_LOG('    - Received {0} trailers'.format(total))
            total = float(total)
            ct = 0

            for t in trailers:
                try:
                    DB.Trailers.get(DB.Trailers.WID == t.ID)
                except DB.peewee.DoesNotExist:
                    ct += 1
                    url = t.getStaticURL()
                    DB.Trailers.create(
                        WID=t.ID,
                        source=source,
                        watched=False,
                        title=t.title,
                        url=url,
                        userAgent=t.userAgent,
                        rating=str(t.rating),
                        genres=','.join(t.genres),
                        thumb=t.thumb,
                        release=t.release or datetime.date(1900, 1, 1)
                    )

            util.DEBUG_LOG('    - {0} trailers added to database'.format(ct))

    @DB.sessionW
    def scraperHandler(self, source, count, unwatched=False, watched=False):
        trailers = []

        if unwatched:
            self.updateTrailers(source)
            util.DEBUG_LOG('    - Searching un-watched trailers')
            trailers += self.getTrailersFromDB(source, count)
            if not watched:
                return trailers

            count -= min(len(trailers), count)
            if count <= 0:
                return trailers

        if watched:
            util.DEBUG_LOG('    - Searching watched trailers')
            trailers += self.getTrailersFromDB(source, count, watched=True)

        return trailers

    def dirHandler(self, sItem):
        count = sItem.getLive('count')

        path = sItem.getLive('dir')
        util.DEBUG_LOG('[{0}] Directory x {1}'.format(sItem.typeChar, count))

        if not path:
            util.DEBUG_LOG('    - Empty path!')
            return []

        try:
            files = [f for f in util.vfs.listdir(path) if os.path.splitext(f)[-1].lower() in util.videoExtensions]
            if self.sItem.getLive('filter3D'):
                files = [f for f in files if self.caller.nextQueuedFeature.is3D == util.pathIs3D(f)]
            files = random.sample(files, min((count, len(files))))
            [util.DEBUG_LOG('    - Using: {0}'.format(repr(f))) for f in files] or util.DEBUG_LOG('    - No matching files')
            return [Video(util.pathJoin(path, p), volume=sItem.getLive('volume')).fromModule(sItem) for p in files]
        except:
            util.ERROR()
            return []

    def fileHandler(self, sItem):
        path = sItem.getLive('file')
        if not path:
            return []

        util.DEBUG_LOG('[{0}] File: {1}'.format(sItem.typeChar, repr(path)))

        return [Video(path, volume=sItem.getLive('volume')).fromModule(sItem)]


class VideoBumperHandler:
    def __init__(self):
        self.caller = None
        self.handlers = {
            '3D.intro': self._3DIntro,
            '3D.outro': self._3DOutro,
            'countdown': self.countdown,
            'courtesy': self.courtesy,
            'feature.intro': self.featureIntro,
            'feature.outro': self.featureOutro,
            'intermission': self.intermission,
            'short.film': self.shortFilm,
            'theater.intro': self.theaterIntro,
            'theater.outro': self.theaterOutro,
            'trailers.intro': self.trailersIntro,
            'trailers.outro': self.trailersOutro,
            'trivia.intro': self.triviaIntro,
            'trivia.outro': self.triviaOutro,
            'dir': self.dir,
            'file': self.file
        }

    def __call__(self, caller, sItem):
        self.caller = caller
        util.DEBUG_LOG('[{0}] {1}'.format(sItem.typeChar, sItem.display()))

        if not sItem.vtype:
            util.DEBUG_LOG('    - {0}'.format('No bumper type - SKIPPING'))
            return []

        playables = self.handlers[sItem.vtype](sItem)
        if playables:
            if sItem.vtype == 'dir':
                util.DEBUG_LOG('    - {0}'.format(' x {0}'.format(sItem.count) or ''))
        else:
            util.DEBUG_LOG('    - {0}'.format('NOT SHOWING'))

        return playables

    @DB.session
    def defaultHandler(self, sItem):
        is3D = self.caller.nextQueuedFeature.is3D and sItem.play3D

        if sItem.random:
            util.DEBUG_LOG('    - Random')

            bumpers = [x for x in DB.VideoBumpers.select().where((DB.VideoBumpers.type == sItem.vtype) & (DB.VideoBumpers.is3D == is3D))]
            bumpers = random.sample(bumpers, min(sItem.count, len(bumpers)))
            bumpers = [Video(bumper.path, volume=sItem.getLive('volume')).fromModule(sItem) for bumper in bumpers]

            if not bumpers and is3D and util.getSettingDefault('bumper.fallback2D'):
                util.DEBUG_LOG('    - Falling back to 2D bumper')

                bumpers = [x for x in DB.VideoBumpers.select().where((DB.VideoBumpers.type == sItem.vtype))]
                bumpers = random.sample(bumpers, min(sItem.count, len(bumpers)))
                bumpers = [Video(bumper.path, volume=sItem.getLive('volume')).fromModule(sItem) for bumper in bumpers]

            if not bumpers:
                util.DEBUG_LOG('    - No matches!')

            return bumpers

        else:
            util.DEBUG_LOG('    - Via source')
            if sItem.source:
                return [Video(sItem.source, volume=sItem.getLive('volume')).fromModule(sItem)]
            else:
                util.DEBUG_LOG('    - Empty path!')

        return []

    def _3DIntro(self, sItem):
        if not self.caller.nextQueuedFeature.is3D:
            return []
        return self.defaultHandler(sItem)

    def _3DOutro(self, sItem):
        if not self.caller.nextQueuedFeature.is3D:
            return []
        return self.defaultHandler(sItem)

    def countdown(self, sItem):
        return self.defaultHandler(sItem)

    def courtesy(self, sItem):
        return self.defaultHandler(sItem)

    def featureIntro(self, sItem):
        return self.defaultHandler(sItem)

    def featureOutro(self, sItem):
        return self.defaultHandler(sItem)

    def intermission(self, sItem):
        return self.defaultHandler(sItem)

    def shortFilm(self, sItem):
        return self.defaultHandler(sItem)

    def theaterIntro(self, sItem):
        return self.defaultHandler(sItem)

    def theaterOutro(self, sItem):
        return self.defaultHandler(sItem)

    def trailersIntro(self, sItem):
        return self.defaultHandler(sItem)

    def trailersOutro(self, sItem):
        return self.defaultHandler(sItem)

    def triviaIntro(self, sItem):
        return self.defaultHandler(sItem)

    def triviaOutro(self, sItem):
        return self.defaultHandler(sItem)

    def file(self, sItem):
        if sItem.file:
            return [Video(sItem.file, volume=sItem.getLive('volume')).fromModule(sItem)]
        else:
            return []

    def dir(self, sItem):
        if not sItem.dir:
            return []

        try:
            files = util.vfs.listdir(sItem.dir)
            if sItem.random:
                files = random.sample(files, min((sItem.count, len(files))))
            else:
                files = files[:sItem.count]

            return [Video(util.pathJoin(sItem.dir, p), volume=sItem.getLive('volume')).fromModule(sItem) for p in files]
        except:
            util.ERROR()
            return []


class AudioFormatHandler:
    _atmosRegex = re.compile('[._ -]Atmos[._ -]', re.IGNORECASE)
    _dtsxRegex = re.compile('[._ -]DTS[._ -]X[._ -]', re.IGNORECASE)

    def _checkFileNameForFormat(self, feature):
        featureFileName = os.path.basename(feature.path)
        
        if feature.audioFormat == 'Dolby TrueHD' and re.search(self._atmosRegex, featureFileName):
            util.DEBUG_LOG('    - Detect: Used file path {0} to determine audio format is {1}'.format(featureFileName, 'Dolby Atmos'))
            return 'Dolby Atmos'
        elif feature.audioFormat == 'DTS-HD Master Audio' and re.search(self._dtsxRegex, featureFileName):
            util.DEBUG_LOG('    - Detect: Used file path {0} to determine audio format is {1}'.format(featureFileName, 'DTS-X'))
            return 'DTS-X'
        else:
            util.DEBUG_LOG('    - Detect: Looked at the file path {0} and decided to keep audio format {1}'.format(featureFileName, repr(feature.audioFormat)))
            return feature.audioFormat
    
    @DB.session
    def __call__(self, caller, sItem):
        bumper = None
        method = sItem.getLive('method')
        fallback = sItem.getLive('fallback')
        format_ = sItem.getLive('format')

        util.DEBUG_LOG('[{0}] Method: {1} Fallback: {2} Format: {3}'.format(sItem.typeChar, method, fallback, format_))

        is3D = caller.nextQueuedFeature.is3D and sItem.play3D

        if method == 'af.detect':
            util.DEBUG_LOG('    - Detect')
            audioFormat = self._checkFileNameForFormat(caller.nextQueuedFeature)
            if audioFormat:
                try:
                    bumper = random.choice(
                        [x for x in DB.AudioFormatBumpers.select().where(
                            (DB.AudioFormatBumpers.format == audioFormat) & (DB.AudioFormatBumpers.is3D == is3D)
                        )]
                    )
                    util.DEBUG_LOG('    - Detect: Using bumper based on feature codec info ({0})'.format(repr(caller.nextQueuedFeature.title)))
                except IndexError:
                    util.DEBUG_LOG('    - Detect: No codec matches!')
                    if is3D and util.getSettingDefault('bumper.fallback2D'):
                        try:
                            bumper = random.choice(
                                [x for x in DB.AudioFormatBumpers.select().where(DB.AudioFormatBumpers.format == audioFormat)]
                            )
                            util.DEBUG_LOG(
                                '    - Using bumper based on feature codec info and falling back to 2D ({0})'.format(repr(caller.nextQueuedFeature.title))
                            )
                        except IndexError:
                            pass
            else:
                util.DEBUG_LOG('    - No feature audio format!')

        if (
            format_ and not bumper and (
                method == 'af.format' or (
                    method == 'af.detect' and fallback == 'af.format'
                )
            )
        ):
            util.DEBUG_LOG('    - Format')
            try:
                bumper = random.choice(
                    [x for x in DB.AudioFormatBumpers.select().where(
                        (DB.AudioFormatBumpers.format == format_) & (DB.AudioFormatBumpers.is3D == is3D)
                    )]
                )
                util.DEBUG_LOG('    - Format: Using bumper based on setting ({0})'.format(repr(caller.nextQueuedFeature.title)))
            except IndexError:
                util.DEBUG_LOG('    - Format: No matches!')
                if is3D and util.getSettingDefault('bumper.fallback2D'):
                    try:
                        bumper = random.choice([x for x in DB.AudioFormatBumpers.select().where(DB.AudioFormatBumpers.format == format_)])
                        util.DEBUG_LOG('    - Using bumper based on format setting and falling back to 2D ({0})'.format(repr(caller.nextQueuedFeature.title)))
                    except IndexError:
                        pass
        if (
            sItem.getLive('file') and not bumper and (
                method == 'af.file' or (
                    method == 'af.detect' and fallback == 'af.file'
                )
            )
        ):
            util.DEBUG_LOG('    - File: Using bumper based on setting ({0})'.format(repr(caller.nextQueuedFeature.title)))
            return [Video(sItem.getLive('file'), volume=sItem.getLive('volume')).fromModule(sItem)]

        if bumper:
            return [Video(bumper.path, volume=sItem.getLive('volume')).fromModule(sItem)]

        util.DEBUG_LOG('    - NOT SHOWING')
        return []


class ActionHandler:
    def __call__(self, caller, sItem):
        if not sItem.file:
            util.DEBUG_LOG('[{0}] NO PATH SET'.format(sItem.typeChar))
            return []

        util.DEBUG_LOG('[{0}] {1}'.format(sItem.typeChar, sItem.file))
        processor = actions.ActionFileProcessor(sItem.file)
        return [Action(processor)]


class SequenceProcessor:
    def __init__(self, sequence_path, db_path=None, content_path=None):
        DB.initialize(db_path)
        self.pos = -1
        self.size = 0
        self.sequence = []
        self.featureQueue = []
        self.playables = []
        self.genres = []
        self.contentPath = content_path
        self.lastFeature = None
        self._lastAction = None
        self.loadSequence(sequence_path)
        self.createDefaultFeature()

    def atEnd(self, pos=None):
        if pos is None:
            pos = self.pos
        return pos >= self.end

    @property
    def nextQueuedFeature(self):
        return self.featureQueue and self.featureQueue[0] or self.lastFeature

    def getNextFeatures(self, count):
        features = self.featureQueue[:count]
        self.featureQueue = self.featureQueue[count:]
        if features:
            self.lastFeature = features[-1]
        return features

    def createDefaultFeature(self):
        self.defaultFeature = Feature('')
        self.defaultFeature.title = 'Default Feature'
        self.defaultFeature.rating = 'MPAA:NR'
        self.defaultFeature.audioFormat = 'Other'

    def addFeature(self, feature):
        if feature.genres:
            self.genres += feature.genres

        self.featureQueue.append(feature)

    @property
    def ratings(self):
        return [feature.rating for feature in self.featureQueue if feature.rating]

    def commandHandler(self, sItem):
        if sItem.condition == 'feature.queue=full' and not self.featureQueue:
            return 0
        if sItem.condition == 'feature.queue=empty' and self.featureQueue:
            return 0
        if sItem.command == 'back':
            return sItem.arg * -1
        elif sItem.command == 'skip':
            return sItem.arg

    # SEQUENCE PROCESSING
    handlers = {
        'feature': FeatureHandler(),
        'trivia': TriviaHandler(),
        'trailer': TrailerHandler(),
        'video': VideoBumperHandler(),
        'audioformat': AudioFormatHandler(),
        'action': ActionHandler(),
        'command': commandHandler
    }

    def process(self):
        util.DEBUG_LOG('Processing sequence...')
        util.DEBUG_LOG('Feature count: {0}'.format(len(self.featureQueue)))
        util.DEBUG_LOG('Ratings: {0}'.format(', '.join([str(r) for r in self.ratings])))
        util.DEBUG_LOG('Genres: {0}'.format(repr(self.genres)))

        if self.featureQueue:
            util.DEBUG_LOG('\n\n' + '\n\n'.join([str(f) for f in self.featureQueue]) + '\n.')
        else:
            util.DEBUG_LOG('NO FEATURES QUEUED')

        self.playables = []
        pos = 0
        while pos < len(self.sequence):
            sItem = self.sequence[pos]

            if not sItem.enabled:
                util.DEBUG_LOG('[{0}] ({1}) DISABLED'.format(sItem.typeChar, sItem.display()))
                pos += 1
                continue

            handler = self.handlers.get(sItem._type)
            if handler:
                if sItem._type == 'command':
                    offset = handler(self, sItem)
                    pos += offset
                    if offset:
                        continue
                else:
                    self.playables += handler(self, sItem)

            pos += 1
        self.playables.append(None)  # Keeps it from being empty until AFTER the last item
        self.end = len(self.playables) - 1

        util.DEBUG_LOG('Sequence processing finished')

    def loadSequence(self, sequence_path):
        self.sequence = sequence.loadSequence(sequence_path)

        if util.DEBUG:  # Dump some info
            util.DEBUG_LOG('')
            util.DEBUG_LOG('[- Non-Module Defaults -]')

            for sett in (
                'bumper.fallback2D', 'trivia.music', 'trivia.musicVolume', 'trivia.musicFadeIn', 'trivia.musicFadeOut',
                'trailer.preferUnwatched', 'trailer.ratingMax', 'rating.system.default'
            ):
                util.DEBUG_LOG('{0}: {1}'.format(sett, repr(util.getSettingDefault(sett))))

            util.DEBUG_LOG('')

            for si in self.sequence:
                util.DEBUG_LOG('[- {0} -]'.format(si._type))
                for e in si._elements:
                    util.DEBUG_LOG('{0}: {1}'.format(e['attr'], repr(si.getLive(e['attr']))))

                util.DEBUG_LOG('')

    def next(self):
        if self.atEnd():
            return None

        self.pos += 1
        playable = self.playables[self.pos]

        if playable and playable.type == 'ACTION':
            self._lastAction = playable

        return playable

    def prev(self):
        if self.pos > 0:
            self.pos -= 1

        playable = self.playables[self.pos]

        while playable.type == 'ACTION' and self.pos > 0:
            self.pos -= 1
            playable = self.playables[self.pos]

        return playable

    def upNext(self):
        if self.atEnd():
            return None

        pos = self.pos + 1
        playable = self.playables[pos]
        while not self.atEnd(pos) and playable and playable.type in ('ACTION', 'COMMAND'):
            pos += 1
            playable = self.playables[pos]
        else:
            return playable

        return None

    def nextFeature(self):
        for i in range(self.pos + 1, len(self.playables) - 1):
            p = self.playables[i]
            if p.type == 'FEATURE':
                return p
        return None

    def lastAction(self):
        return self._lastAction
