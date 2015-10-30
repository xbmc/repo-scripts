import os
import re
from xml.etree import ElementTree as ET

import util
import mutagen
import hachoir
import database as DB

try:
    ET.ParseError
except:
    ET.ParseError = Exception

mutagen.setFileOpener(util.vfs.File)

TYPE_IDS = {
    '3D Intro':       '3D.intro',
    '3D Outro':       '3D.outro',
    'Countdown':      'countdown',
    'Courtesy':       'courtesy',
    'Feature Intro':  'feature.intro',
    'Feature Outro':  'feature.outro',
    'Intermission':   'intermission',
    'Short Film':     'short.film',
    'Theater Intro':  'theater.intro',
    'Theater Outro':  'theater.outro',
    'Trailers Intro': 'trailers.intro',
    'Trailers Outro': 'trailers.outro',
    'Trivia Intro':   'trivia.intro',
    'Trivia Outro':   'trivia.outro'
}

CONTENT_3D_RE = '\([^\)]*3D[^\)]*\)'


def getBumperDir(ID):
    for dirname, tid in TYPE_IDS.items():
        if tid == ID:
            break
    else:
        return None

    return ('Video Bumpers', dirname)


class UserContent:
    _tree = (
        ('Audio Format Bumpers', (
            'Auro-3D',
            'Dolby Atmos',
            'Dolby Digital',
            'Dolby Digital Plus',
            'Dolby TrueHD',
            'DTS',
            'DTS-HD Master Audio',
            'DTS-X',
            'Datasat',
            'Other',
            'THX'
        )),
        'Music',
        'Actions',
        'Sequences',
        ('Ratings Bumpers', (
            'MPAA',
            'BBFC',
            'DEJUS',
            'FSK'
        )),
        'Trailers',
        'Trivia',
        ('Video Bumpers', (
            '3D Intro',
            '3D Outro',
            'Countdown',
            'Courtesy',
            'Feature Intro',
            'Feature Outro',
            'Intermission',
            'Short Film',
            'Theater Intro',
            'Theater Outro',
            'Trailers Intro',
            'Trailers Outro',
            'Trivia Intro',
            'Trivia Outro'
        ))
    )

    def __init__(self, content_dir=None, callback=None, db_path=None, trailer_sources=None):
        self._callback = callback
        self._trailer_sources = trailer_sources or []
        self.setupDB(db_path)
        self.musicHandler = MusicHandler(self)
        self.triviaDirectoryHandler = TriviaDirectoryHandler(self.log)
        self.setContentDirectoryPath(content_dir)
        if not db_path:
            self.setupContentDirectory()

        self.clean()
        self.loadContent()

    def setupDB(self, db_path):
        DB.initialize(db_path, self.dbCallback)

    def dbCallback(self, msg=None, heading=None):
        util.DEBUG_LOG(msg or heading)
        if self._callback:
            self._callback(msg, heading)

    def log(self, msg):
        util.DEBUG_LOG(msg)

        if not self._callback:
            return

        self._callback(msg)

    def logHeading(self, heading):
        util.DEBUG_LOG('')
        util.DEBUG_LOG('[- {0} -]'.format(heading))
        util.DEBUG_LOG('')

        if not self._callback:
            return

        self._callback(None, heading)

    def setContentDirectoryPath(self, content_dir):
        self._contentDirectory = content_dir

    def _addDirectory(self, current, tree):
        if not util.vfs.exists(current):
            util.DEBUG_LOG('Creating: {0}'.format(repr(current)))
            util.vfs.mkdirs(current)

        for branch in tree:
            if isinstance(branch, tuple):
                new = util.pathJoin(current, branch[0])
                self._addDirectory(new, branch[1])
            else:
                sub = util.pathJoin(current, branch)
                if util.vfs.exists(sub):
                    continue
                util.DEBUG_LOG('Creating: {0}'.format(repr(sub)))
                util.vfs.mkdirs(sub)

    # TODO: Remove
    def _fixTriviaSlidesDir(self):
        ts = util.pathJoin(self._contentDirectory, 'Trivia Slides')
        if not util.vfs.exists(ts):
            return
        t = util.pathJoin(self._contentDirectory, 'Trivia')
        util.vfs.rename(ts, t)

    def setupContentDirectory(self):
        if not self._contentDirectory:  # or util.vfs.exists(self._contentDirectory):
            return
        self._fixTriviaSlidesDir()
        self._addDirectory(self._contentDirectory, self._tree)

    def clean(self):
        self.logHeading('CLEANING DATABASE')
        cleaned = self.musicHandler.clean()
        cleaned = cleaned or self.triviaDirectoryHandler.clean()
        for bumper, name in ((DB.AudioFormatBumpers, 'AudioFormatBumper'), (DB.VideoBumpers, 'VideoBumper'), (DB.RatingsBumpers, 'RatingBumper')):
            for b in bumper.select():
                path = b.path
                if not util.vfs.exists(path):
                    cleaned = True
                    b.delete_instance()
                    self.log('{0} Missing: {1} - REMOVED'.format(repr(name), repr(path)))

        if not cleaned:
            self.log('Database clean - unchanged')

    def loadContent(self):
        self.loadMusic()
        self.loadTrivia()
        self.loadAudioFormatBumpers()
        self.loadVideoBumpers()
        self.loadRatingsBumpers()
        self.scrapeContent()

    def loadMusic(self):
        self.logHeading('LOADING MUSIC')

        self.musicHandler(util.pathJoin(self._contentDirectory, 'Music'))

    def loadTrivia(self):
        self.logHeading('LOADING TRIVIA')

        basePath = util.pathJoin(self._contentDirectory, 'Trivia')
        paths = util.vfs.listdir(basePath)

        total = float(len(paths))
        for ct, sub in enumerate(paths):
            pct = 20 + int((ct/total)*20)
            if not self._callback(pct=pct):
                break
            path = os.path.join(basePath, sub)
            if util.isDir(path):
                if sub.startswith('_Exclude'):
                    util.DEBUG_LOG('SKIPPING EXCLUDED DIR: {0}'.format(sub))
                    continue
            else:
                continue

            self.log('Processing trivia: {0}'.format(os.path.basename(path)))
            self.triviaDirectoryHandler(path, prefix=sub)

    def loadAudioFormatBumpers(self):
        self.logHeading('LOADING AUDIO FORMAT BUMPERS')

        basePath = util.pathJoin(self._contentDirectory, 'Audio Format Bumpers')

        self.createBumpers(basePath, DB.AudioFormatBumpers, 'format', None, 40)

    def loadVideoBumpers(self):
        self.logHeading('LOADING VIDEO BUMPERS')

        basePath = util.pathJoin(self._contentDirectory, 'Video Bumpers')

        self.createBumpers(basePath, DB.VideoBumpers, 'type', None, 60)

    def loadRatingsBumpers(self):
        self.logHeading('LOADING RATINGS BUMPERS')

        basePath = util.pathJoin(self._contentDirectory, 'Ratings Bumpers')

        self.createBumpers(basePath, DB.RatingsBumpers, 'system', 'style', 80, sub_default='Classic')

    def createBumpers(self, basePath, model, type_name, sub_name, pct_start, sub_default=''):
        paths = util.vfs.listdir(basePath)
        total = float(len(paths))

        for ct, sub in enumerate(paths):
            pct = pct_start + int((ct/total)*20)
            if not self._callback(pct=pct):
                break

            path = util.pathJoin(basePath, sub)
            if not util.isDir(path):
                continue

            if sub.startswith('_Exclude'):
                util.DEBUG_LOG('SKIPPING EXCLUDED DIR: {0}'.format(sub))
                continue

            if util.vfs.exists(util.pathJoin(path, 'system.xml')):  # For ratings
                self.loadRatingSystem(util.pathJoin(path, 'system.xml'))

            type_ = sub.replace(' Bumpers', '')
            self.addBumper(model, sub, path, type_name, sub_name, type_, sub_default)

    def addBumper(self, model, sub, path, type_name, sub_name, type_, sub_default, sub_val=None, prefix=None):
        for v in util.vfs.listdir(path):
            vpath = os.path.join(path, v)

            if util.isDir(vpath):
                if sub_name:
                    if not sub_val:
                        self.addBumper(model, sub, vpath, type_name, sub_name, type_, sub_default, v)
                else:
                    self.addBumper(model, sub, vpath, type_name, sub_name, type_, sub_default, prefix=v)

                continue

            name, ext = os.path.splitext(v)
            is3D = '3D' in name
            if is3D and type_name == 'system':  # Remove tags from rating bumpers
                name = re.sub(CONTENT_3D_RE, '', name).strip()

            isImage = False
            if ext in util.videoExtensions:
                isImage = False
            elif ext in util.imageExtensions:
                isImage = True
            else:
                continue

            name = prefix and (prefix + ':' + name) or name

            defaults = {
                type_name: TYPE_IDS.get(type_, type_),
                'name': name,
                'is3D': is3D,
                'isImage': isImage
            }

            if sub_name:
                sub_val = sub_val or sub_default
                defaults[sub_name] = sub_val
                self.log('Loading {0} ({1} - {2}): [ {3}{4} ]'.format(model.__name__, sub, sub_val, name, is3D and ': 3D' or ''))
            else:
                self.log('Loading {0} ({1}): [ {2}{3} ]'.format(model.__name__, sub, name, is3D and ': 3D' or ''))

            model.get_or_create(
                path=vpath,
                defaults=defaults
            )

    @DB.session
    def loadRatingSystem(self, path):
        import ratings
        with util.vfs.File(path, 'r') as f:
            system = ratings.addRatingSystemFromXML(f.read())

        for context, regEx in system.regEx.items():
            DB.RatingSystem.get_or_create(
                name=system.name,
                context=context,
                regEx=regEx,
                regions=system.regions and ','.join(system.regions) or None
            )

        for rating in system.ratings:
            DB.Rating.get_or_create(
                name=rating.name,
                internal=rating.internal,
                value=rating.value,
                system=system.name
            )

    @DB.sessionW
    def scrapeContent(self):
        import scrapers
        scrapers.setContentPath(self._contentDirectory)

        for stype, source in util.contentScrapers():
            if stype == 'trailers':
                util.DEBUG_LOG('Getting trailers from {0}'.format(source))
                self._callback(heading='Adding {0} trailers...'.format(source))
                self._callback('Getting trailer list...', pct=0)
                trailers = scrapers.getTrailers(source)
                total = len(trailers)
                util.DEBUG_LOG(' - Received {0} trailers'.format(total))
                if trailers:
                    DB.Trailers.update(verified=False).where(
                        DB.Trailers.source == source
                    ).execute()

                    total = float(total)
                    allct = 0
                    ct = 0

                    for t in trailers:
                        allct += 1
                        try:
                            dt = DB.Trailers.get(DB.Trailers.WID == t.ID)
                            dt.verified = True
                            dt.watched = t.watched or dt.watched
                            dt.save()
                        except DB.peewee.DoesNotExist:
                            ct += 1
                            url = t.getStaticURL()
                            DB.Trailers.create(
                                WID=t.ID,
                                source=source,
                                watched=t.watched,
                                title=t.title,
                                url=url,
                                userAgent=t.userAgent,
                                rating=str(t.rating),
                                genres=','.join(t.genres),
                                thumb=t.thumb,
                                release=t.release,
                                is3D=t.is3D,
                                verified=True
                            )
                        pct = int((allct/total)*100)
                        self._callback(t.title, pct=pct)

                    rows = DB.Trailers.delete().where(
                        DB.Trailers.verified == 0,
                        DB.Trailers.source == source
                    ).execute()

                    util.DEBUG_LOG(' - {0} new {1} trailers added to database'.format(ct, source))
                    util.DEBUG_LOG(' - {0} {1} trailers removed from database'.format(rows, source))
                else:
                    util.DEBUG_LOG(' - No new {0} trailers added to database'.format(source))


class MusicHandler:
    def __init__(self, owner=None):
        self.owner = owner

    def __call__(self, basePath):
        names = util.vfs.listdir(basePath)

        total = float(len(names))
        for ct, file in enumerate(names):
            pct = int((ct/total)*20)
            if not self.owner._callback(pct=pct):
                break
            self.addSongs(basePath, file)

    @DB.session
    def addSongs(self, base, file, sub=None):
        path = util.pathJoin(base, file)

        if util.isDir(path):
            paths = util.vfs.listdir(path)
            sub = sub and (sub + ':' + file) or file
            for p in paths:
                self.addSongs(path, p, sub)
            return

        name, ext = os.path.splitext(file)
        if ext.lower() in util.musicExtensions:
            if sub:
                name = sub + ':' + name

            try:
                DB.Song.get(DB.Song.path == path)
                self.owner.log('Loading Song (exists): [ {0} ]'.format(name))
            except DB.peewee.DoesNotExist:
                data = None
                try:
                    data = mutagen.File(path)
                except:
                    util.ERROR()

                if data:
                    duration = data.info.length
                    self.owner.log('Loading Song (new): [ {0} ({1}) ]'.format(name, data.info.pprint()))
                else:
                    duration = 0
                DB.Song.create(
                    path=path,
                    name=name,
                    duration=duration
                )

    @DB.session
    def clean(self):
        cleaned = False
        for s in DB.Song.select():
            path = s.path
            if not util.vfs.exists(path):
                cleaned = True
                s.delete_instance()
                self.owner.log('Song Missing: {0} - REMOVED'.format(path))

        return cleaned


class TriviaDirectoryHandler:
    _formatXML = 'slides.xml'
    _ratingNA = ('slide', 'rating')
    _questionNA = ('question', 'format')
    _clueNA = ('clue', 'format')
    _answerNA = ('answer', 'format')

    _defaultQRegEx = '_q\.jpg|png|gif|bmp'
    _defaultCRegEx = '_c(\d)?\.jpg|png|gif|bmp'
    _defaultARegEx = '_a\.jpg|png|gif|bmp'

    def __init__(self, callback=None):
        self._callback = callback

    @DB.session
    def __call__(self, basePath, prefix=None):
        hasSlidesXML = False
        slideXML = util.pathJoin(basePath, self._formatXML)
        if util.vfs.exists(slideXML):
            hasSlidesXML = True

        # pack = os.path.basename(basePath.rstrip('\\/'))

        xml = None
        slide = None

        if hasSlidesXML:
            try:
                f = util.vfs.File(slideXML, 'r')
                xml = f.read()
            finally:
                f.close()

            try:
                slides = ET.fromstring(xml)
                slide = slides.find('slide')
            except ET.ParseError:
                util.DEBUG_LOG('Bad slides.xml')
            except:
                util.ERROR()
                slide = None

        if slide:
            rating = self.getNodeAttribute(slide, self._ratingNA[0], self._ratingNA[1]) or ''
            questionRE = (self.getNodeAttribute(slide, self._questionNA[0], self._questionNA[1]) or '').replace('N/A', '')
            clueRE = self.getNodeAttribute(slide, self._clueNA[0], self._clueNA[1]) or ''.replace('N/A', '')
            answerRE = self.getNodeAttribute(slide, self._answerNA[0], self._answerNA[1]) or ''.replace('N/A', '')
        else:
            rating = ''
            questionRE = self._defaultQRegEx
            clueRE = self._defaultCRegEx
            answerRE = self._defaultARegEx

        contents = util.vfs.listdir(basePath)

        trivia = {}

        for c in contents:
            path = util.pathJoin(basePath, c)

            if util.isDir(path):
                self(path, prefix=prefix and (prefix + ':' + c) or c)
                continue

            base, ext = os.path.splitext(c)

            if not ext.lower() in util.imageExtensions:
                if ext.lower() in util.videoExtensions:
                    self.getSlide(basePath, c, prefix)
                continue

            ttype = ''
            clueCount = 0

            if re.search(questionRE, c):
                name = re.split(questionRE, c)[0]
                ttype = 'q'
            elif re.search(answerRE, c):
                name = re.split(answerRE, c)[0]
                ttype = 'a'
            elif re.search(clueRE, c):
                name = re.split(clueRE, c)[0]

                try:
                    clueCount = re.search(clueRE, c).group(1)
                except:
                    pass

                ttype = 'c'
            else:  # A still
                name, ext = os.path.splitext(c)
                # name = re.split(clueRE, c)[0]
                ttype = 'a'

            if name not in trivia:
                trivia[name] = {'q': None, 'c': {}, 'a': None}

            if ttype == 'q' or ttype == 'a':
                trivia[name][ttype] = path
            elif ttype == 'c':
                trivia[name]['c'][clueCount] = path

        for name, data in trivia.items():
            questionPath = data['q']
            answerPath = data['a']

            if not answerPath:
                continue

            if questionPath:
                ttype = 'QA'
                self._callback('Loading Trivia(QA): [ {0} ]'.format(name))
            else:
                ttype = 'fact'
                self._callback('Loading Trivia(single): [ {0} ]'.format(name))

            defaults = {
                    'type': ttype,
                    'TID': '{0}:{1}'.format(prefix, name),
                    'name': name,
                    'rating': rating,
                    'questionPath': questionPath
            }

            for ct, key in enumerate(sorted(data['c'].keys())):
                defaults['cluePath{0}'.format(ct)] = data['c'][key]
            try:
                DB.Trivia.get_or_create(
                    answerPath=answerPath,
                    defaults=defaults
                )
            except:
                print repr(data)
                util.ERROR()

    @DB.session
    def processSimpleDir(self, path):
        pack = os.path.basename(path.rstrip('\\/'))
        contents = util.vfs.listdir(path)
        for c in contents:
            self.getSlide(path, c, pack)

    def getSlide(self, path, c, pack=''):
        name, ext = os.path.splitext(c)
        duration = 0
        path = util.pathJoin(path, c)

        try:
            DB.Trivia.get(DB.Trivia.answerPath == path)
            self._callback('Loading Trivia (exists): [ {0} ]'.format(name))
        except DB.peewee.DoesNotExist:
            if ext.lower() in util.videoExtensions:
                ttype = 'video'
                parser = hachoir.hachoir_parser.createParser(path)
                metadata = hachoir.hachoir_metadata.extractMetadata(parser)
                durationDT = None
                if metadata:
                    durationDT = metadata.get('duration')
                    duration = durationDT and util.datetimeTotalSeconds(durationDT) or 0
                self._callback('Loading Trivia (video): [ {0} ({1}) ]'.format(name, durationDT))

            elif ext.lower() in util.imageExtensions:
                ttype = 'fact'
                self._callback('Loading Trivia (single): [ {0} ]'.format(name))
            else:
                return

            DB.Trivia.get_or_create(
                    answerPath=path,
                    defaults={
                        'type': ttype,
                        'TID': '{0}:{1}'.format(pack, name),
                        'name': name,
                        'duration': duration
                    }
                )

    def getNodeAttribute(self, node, sub_node_name, attr_name):
        subNode = node.find(sub_node_name)
        if subNode is not None:
            return subNode.attrib.get(attr_name)
        return None

    @DB.session
    def clean(self):
        cleaned = False
        for t in DB.Trivia.select():
            path = t.answerPath
            if not util.vfs.exists(path):
                cleaned = True
                t.delete_instance()
                self._callback('Trivia Missing: {0} - REMOVED'.format(path))

        return cleaned
