import json
import os

import util
from util import T

LIMIT_FILE = 0
LIMIT_FILE_DEFAULT = 1
LIMIT_DIR = 2
LIMIT_DB_CHOICE = 3
LIMIT_BOOL = 4
LIMIT_BOOL_DEFAULT = 5
LIMIT_MULTI_SELECT = 6
LIMIT_ACTION = 7


SETTINGS_DISPLAY = {
    '3D.intro': T(32300, '3D Intro'),
    '3D.outro': T(32301, '3D Outro'),
    'countdown': T(32302, 'Countdown'),
    'courtesy': T(32303, 'Courtesy'),
    'feature.intro': T(32304, 'Feature Intro'),
    'feature.outro': T(32305, 'Feature Outro'),
    'intermission': T(32306, 'Intermission'),
    'short.film': T(32307, 'Short Film'),
    'theater.intro': T(32308, 'Theater Intro'),
    'theater.outro': T(32309, 'Theater Outro'),
    'trailers.intro': T(32310, 'Trailers Intro'),
    'trailers.outro': T(32311, 'Trailers Outro'),
    'trivia.intro': T(32312, 'Trivia Intro'),
    'trivia.outro': T(32313, 'Trivia Outro'),
    'back': T(32314, 'Back'),
    'skip': T(32315, 'Skip'),
    'feature.queue=full': T(32316, 'Feature queue is full'),
    'feature.queue=empty': T(32317, 'Feature queue is empty'),
    'itunes': 'Apple iTunes',
    'kodidb': T(32318, 'Kodi Database'),
    'scrapers': T(32319, 'Scrapers'),
    'dir': T(32047, 'Directory'),
    'file': T(32053, 'Single File'),
    'content': T(32007, 'Content'),
    'af.detect': T(32069, 'Auto-detect from source'),
    'af.format': T(32070, 'Choose format'),
    'af.file': T(32071, 'Choose file'),
    'True': T(32320, 'Yes'),
    'False': T(32321, 'No'),
    'off': T(32037, 'None'),
    'none': T(32037, 'None'),
    'fade': T(32038, 'Fade'),
    'max': T(32062, 'Max'),
    'match': T(32063, 'Match features'),
    'slideL': T(32039, 'Slide Left'),
    'slideR': T(32040, 'Slide Right'),
    'slideU': T(32041, 'Slide Up'),
    'slideD': T(32042, 'Slide Down'),
    'video': T(32023, 'Video'),
    'image': T(32078, 'Image'),
    'slide': T(32046, 'Slide'),
    'random': T(32057, 'Random'),
    'newest': T(32056, 'Newest'),
    'style': T(32079, 'Style'),
    'DTS-X': 'DTS:X'
}


def settingDisplay(setting):
    if setting is None or setting is 0:
        return 'Default'

    try:
        return SETTINGS_DISPLAY.get(str(setting), setting)
    except:
        pass

    return setting


def strToBool(val):
    return bool(val == 'True')


def strToBoolWithDefault(val):
    if val is None:
        return None
    return bool(val == 'True')


################################################################################
# BASE class for all content items
################################################################################
class Item:
    _tag = 'item'   # XML tag when serialized
    _type = 'BASE'  # Name of the type of content. Equal to the xml tag type attribute when serialized
    _elements = ()  # Tuple of attributes to serialize
    displayName = ''
    typeChar = ''

    def __init__(self):
        self.enabled = True
        self.name = ''

    def _set(self, attr, value):
        conv = self.elementData('type')
        if conv:
            value = conv(value)
        setattr(self, attr, value)

    def copy(self):
        new = self.__class__()
        new.enabled = self.enabled
        new.name = self.name
        for e in self._elements:
            setattr(new, e['attr'], getattr(self, e['attr']))
        return new

    @property
    def fileChar(self):
        return self.typeChar

    # -- Serialize: XML ---------------------------------------
    def toNode(self):
        from xml.etree import ElementTree as ET
        item = ET.Element(self._tag)
        item.set('type', self._type)
        item.set('enabled', str(self.enabled))
        if self.name:
            item.set('name', self.name)

        for e in self._elements:
            sub = ET.Element(e['attr'])
            val = getattr(self, e['attr'])
            if not val and val is not False:
                continue
            sub.text = unicode(val)
            item.append(sub)
        return item

    @staticmethod
    def fromNode(node):
        itype = node.attrib.get('type')
        if itype in CONTENT_CLASSES:
            return CONTENT_CLASSES[itype]._fromNode(node)

    @classmethod
    def _fromNode(cls, node):
        new = cls()
        new.enabled = node.attrib.get('enabled') == 'True'
        new.name = node.attrib.get('name') or ''
        for e in new._elements:
            sub = node.find(e['attr'])
            if sub is not None:
                if e['type']:
                    new._set(e['attr'], e['type'](sub.text))
                else:
                    new._set(e['attr'], sub.text)
        return new

    # -- Serialize: JSON --------------------------------------
    def toDict(self):
        data = {}
        data['type'] = self._type
        data['enabled'] = self.enabled
        data['name'] = self.name
        data['settings'] = {}

        for e in self._elements:
            val = getattr(self, e['attr'])
            if not val and val is not False:
                continue
            data['settings'][e['attr']] = val
        return data

    @staticmethod
    def fromDict(data):
        itype = data['type']
        if itype in CONTENT_CLASSES:
            return CONTENT_CLASSES[itype]._fromDict(data)

    @classmethod
    def _fromDict(cls, data):
        new = cls()
        new.enabled = data.get('enabled', True)
        new.name = data.get('name', '')
        for e in new._elements:
            attr = e['attr']
            if attr not in data['settings']:
                continue

            setattr(new, attr, data['settings'][attr])
        return new

    def elementData(self, element_name):
        for e in self._elements:
            if element_name == e['attr']:
                return e

    def getSettingOptions(self, attr):
        limits = self.elementData(attr)['limits']
        if isinstance(limits, list):
            limits = [(x, settingDisplay(x)) for x in limits]
        return limits

    def setSetting(self, setting, value):
        setattr(self, setting, value)

    def getSetting(self, attr):
        return getattr(self, attr)

    def getLive(self, attr):
        val = self.getSetting(attr)
        if val is None or val is 0:
            return util.getSettingDefault('{0}.{1}'.format(self._type, attr))
        return val

    def globalDefault(self, attr):
        return util.getSettingDefault('{0}.{1}'.format(self._type, attr))

    def getSettingIndex(self, attr):
        for i, e in enumerate(self._elements):
            if e['attr'] == attr:
                return i

    def getElement(self, attr):
        return self._elements[self.getSettingIndex(attr)]

    def getLimits(self, attr):
        return self._elements[self.getSettingIndex(attr)]['limits']

    def getType(self, attr):
        return self._elements[self.getSettingIndex(attr)]['type']

    def display(self):
        return self.name or self.displayName

    def displayRaw(self):
        return self.name or self.displayName

    def getSettingDisplay(self, setting):
        val = getattr(self, setting)
        limits = self.getLimits(setting)
        if limits == LIMIT_BOOL_DEFAULT:
            if val is None:
                return u'{0} ({1})'.format(T(32322, 'Default'), settingDisplay(util.getSettingDefault('{0}.{1}'.format(self._type, setting))))
            return val is True and T(32320, 'Yes') or T(32321, 'No')

        if val is None or val is 0:
            return u'{0} ({1})'.format(T(32322, 'Default'), settingDisplay(util.getSettingDefault('{0}.{1}'.format(self._type, setting))))

        return unicode(settingDisplay(val))

    def DBChoices(self, attr):
        return None

    def elementVisible(self, e):
        return True


################################################################################
# FEATURE PRESENTATION
################################################################################
class Feature(Item):
    _type = 'feature'
    _elements = (
        {
            'attr': 'count',
            'type': int,
            'limits': (0, 10, 1),
            'name': T(32060, 'Count'),
            'default': 0
        },
        {
            'attr': 'ratingBumper',
            'type': None,
            'limits': [None, 'none', 'video', 'image'],
            'name': T(32077, 'Rating bumper'),
            'default': None
        },
        {
            'attr': 'ratingStyleSelection',
            'type': None,
            'limits': [None, 'random', 'style'],
            'name': T(32080, 'Rating style selection'),
            'default': None
        },
        {
            'attr': 'ratingStyle',
            'type': None,
            'limits': LIMIT_DB_CHOICE,
            'name': T(32081, 'Rating style'),
            'default': None
        },
        {
            'attr': 'volume',
            'type': int,
            'limits': (0, 100, 1),
            'name': T(32025, 'Volume (% of current)'),
            'default': 0
        }
    )
    displayName = T(32073, 'Features')
    typeChar = 'F'

    def __init__(self):
        Item.__init__(self)
        self.count = 0
        self.ratingBumper = None
        self.ratingStyleSelection = None
        self.ratingStyle = None
        self.volume = 0

    def display(self):
        name = self.name or self.displayName
        if self.count > 1:
            return u'{0} x {1}'.format(name, self.count)
        return name

    def elementVisible(self, e):
        attr = e['attr']
        if attr == 'ratingStyle':
            return self.getLive('ratingStyleSelection') == 'style' and self.getLive('ratingBumper') in ('video', 'image')
        elif attr == 'ratingStyleSelection':
            return self.getLive('ratingBumper') in ('video', 'image')

        return True

    @staticmethod
    def DBChoices(attr):
        import database as DB
        DB.initialize()

        ratingSystem = util.getSettingDefault('rating.system.default')

        DB.connect()
        try:
            return [
                (x.style, x.style) for x in DB.RatingsBumpers.select(DB.fn.Distinct(DB.RatingsBumpers.style)).where(DB.RatingsBumpers.system == ratingSystem)
            ]
        finally:
            DB.close()


################################################################################
# TRIVIA
################################################################################
class Trivia(Item):
    _type = 'trivia'
    _elements = (
        {
            'attr': 'format',
            'type': None,
            'limits': [None, 'slide', 'video'],
            'name': T(32030, 'Format'),
            'default': None
        },
        {'attr': 'duration',    'type': int, 'limits': (0, 60, 1), 'name': T(32031, 'Duration (minutes)'),          'default': 0},
        {'attr': 'qDuration',   'type': int, 'limits': (0, 60, 1), 'name': T(32032, 'Question Duration (seconds)'), 'default': 0},
        {'attr': 'cDuration',   'type': int, 'limits': (0, 60, 1), 'name': T(32033, 'Clue Duration (seconds)'),     'default': 0},
        {'attr': 'aDuration',   'type': int, 'limits': (0, 60, 1), 'name': T(32034, 'Answer Duration (seconds)'),   'default': 0},
        {'attr': 'sDuration',   'type': int, 'limits': (0, 60, 1), 'name': T(32035, 'Single Duration (seconds)'),   'default': 0},
        {
            'attr': 'transition',
            'type': None,
            'limits': [None, 'none', 'fade', 'slideL', 'slideR', 'slideU', 'slideD'],
            'name': T(32036, 'Transition'),
            'default': None
        },
        {
            'attr': 'transitionDuration',
            'type': int,
            'limits': (0, 2000, 100),
            'name': T(32043, 'Transition: Duration (milliseconds)'),
            'default': 0
        },
        {
            'attr': 'music',
            'type': None,
            'limits': [None, 'off', 'content', 'dir', 'file'],
            'name': T(32027, 'Music'),
            'default': None
        },
        {
            'attr': 'musicDir',
            'type': None,
            'limits': LIMIT_DIR,
            'name': T(32044, 'Music: Path'),
            'default': None
        },
        {
            'attr': 'musicFile',
            'type': None,
            'limits': LIMIT_FILE_DEFAULT,
            'name': T(32045, 'Music: File'),
            'default': None
        }
    )
    displayName = T(32026, 'Trivia Slides')
    typeChar = 'Q'

    def __init__(self):
        Item.__init__(self)
        self.format = None
        self.duration = 0
        self.qDuration = 0
        self.cDuration = 0
        self.aDuration = 0
        self.sDuration = 0
        self.transition = None
        self.transitionDuration = 0
        self.music = None
        self.musicDir = None
        self.musicFile = None

    def display(self):
        name = self.name or self.displayName
        if self.duration > 0:
            return u'{0} ({1}m)'.format(name, self.duration)
        return name

    def getLive(self, attr):
        if not attr == 'musicDir' or self.music is not None:
            return Item.getLive(self, attr)

        return util.getSettingDefault('{0}.{1}'.format(self._type, attr))

    def elementVisible(self, e):
        attr = e['attr']
        if attr != 'format' and self.getLive('format') == 'video':
            return False

        if attr == 'musicDir':
            if self.getLive('music') != 'dir':
                return False
        elif attr == 'musicFile':
            if self.getLive('music') != 'file':
                return False
        elif attr == 'transitionDuration':
            transition = self.getLive('transition')
            if not transition or transition == 'none':
                return False

        return True


################################################################################
# Trailer
################################################################################
class Trailer(Item):
    _type = 'trailer'
    _elements = (
        {
            'attr': 'source',
            'type': None,
            'limits': [None, 'content', 'dir', 'file'],
            'name': T(32052, 'Source'),
            'default': None
        },
        {
            'attr': 'scrapers',
            'type': None,
            'limits': LIMIT_MULTI_SELECT,
            'name': u'- {0}'.format(T(32323, 'Scrapers filter (scrapers)')),
            'default': None
        },
        {
            'attr': 'order',
            'type': None,
            'limits': [None, 'newest', 'random'],
            'name': u'- {0}'.format(T(32324, 'Content order')),
            'default': None
        },
        {
            'attr': 'file',
            'type': None,
            'limits': LIMIT_FILE_DEFAULT,
            'name': u'- {0}'.format(T(32325, 'Path')),
            'default': ''
        },
        {
            'attr': 'dir',
            'type': None,
            'limits': LIMIT_DIR,
            'name': u'- {0}'.format(T(32325, 'Path')),
            'default': ''
        },
        {
            'attr': 'count',
            'type': int,
            'limits': (0, 10, 1),
            'name': T(32060, 'Count'),
            'default': 0
        },
        {
            'attr': 'ratingLimit',
            'type': None,
            'limits': [None, 'none', 'max', 'match'],
            'name': T(32061, 'Rating Limit'),
            'default': None
        },
        {
            'attr': 'ratingMax',
            'type': None,
            'limits': LIMIT_DB_CHOICE,
            'name': u'- {0}'.format(T(32062, 'Max')),
            'default': None
        },
        {
            'attr': 'limitGenre',
            'type': strToBoolWithDefault,
            'limits': LIMIT_BOOL_DEFAULT,
            'name': T(32065, 'Match feature genres'),
            'default': None
        },
        {
            'attr': 'filter3D',
            'type': strToBoolWithDefault,
            'limits': LIMIT_BOOL_DEFAULT,
            'name': T(32066, 'Filter for 3D based on feature'),
            'default': None
        },
        {
            'attr': 'quality',
            'type': None,
            'limits': [None, '480p', '720p', '1080p'],
            'name': T(32067, 'Quality'),
            'default': None
        },
        {
            'attr': 'volume',
            'type': int,
            'limits': (0, 100, 1),
            'name': T(32025, 'Volume (% of current)'),
            'default': 0
        }
    )
    displayName = T(32049, 'Trailers')
    typeChar = 'T'

    _scrapers = [
        ['Content', T(32326, 'Content Folder'), 'content'],
        ['KodiDB', T(32318, 'Kodi Database'), 'kodidb'],
        ['iTunes', 'Apple iTunes', 'itunes'],
        ['StereoscopyNews', 'StereoscopyNews.com', 'stereoscopynews']
    ]

    def __init__(self):
        Item.__init__(self)
        self.count = 0
        self.scrapers = None
        self.source = None
        self.order = None
        self.file = None
        self.dir = None
        self.ratingLimit = None
        self.ratingMax = None
        self.limitGenre = None
        self.filter3D = None
        self.quality = None
        self.volume = 0

    def display(self):
        name = self.name or self.displayName
        if self.count > 1:
            return u'{0} x {1}'.format(name, self.count)
        return name

    def liveScrapers(self):
        return (self.getLive('scrapers') or '').split(',')

    def elementVisible(self, e):
        attr = e['attr']
        if attr == 'file':
            if self.getLive('source') != 'file':
                return False
        elif attr == 'dir':
            if self.getLive('source') != 'dir':
                return False
        elif attr == 'count':
            if self.getLive('source') not in ('dir', 'content'):
                return False
        elif attr == 'filter3D':
            if self.getLive('source') not in ('content', 'dir'):
                return False
        elif attr in ('scrapers', 'order', 'limitRating', 'limitGenre'):
            if self.getLive('source') != 'content':
                return False
        elif attr == 'quality':
            if self.getLive('source') != 'content' or 'iTunes' not in self.liveScrapers():
                return False
        elif attr == 'ratingMax':
            if self.getLive('ratingLimit') != 'max':
                return False
        return True

    @staticmethod
    def DBChoices(attr):
        default = util.getSettingDefault('rating.system.default')
        import ratings
        system = ratings.getRatingsSystem(default)
        if not system:
            return None
        return [(u'{0}.{1}'.format(r.system, r.name), str(r)) for r in system.ratings]

    def Select(self, attr):
        selected = [s.strip().lower() for s in self.liveScrapers()]
        contentScrapers = util.contentScrapers()
        temp = [list(x) for x in self._scrapers]
        ret = []
        for s in temp:
            for ctype, c in contentScrapers:
                if ctype == 'trailers' and c == s[0]:
                    s[2] = s[2] in selected
                    ret.append(s)
        ret.sort(key=lambda i: i[0].lower() in selected and selected.index(i[0].lower())+1 or 99)
        return ret

    def getLive(self, attr):
        if attr != 'scrapers':
            return Item.getLive(self, attr)

        val = Item.getLive(self, attr)
        if not val:
            return val

        inSettings = (val).split(',')

        contentScrapers = [s for t, s in util.contentScrapers() if t == 'trailers']
        return ','.join([s for s in inSettings if s in contentScrapers])


################################################################################
# VIDEO
################################################################################
class Video(Item):
    _type = 'video'
    _elements = (
        {
            'attr': 'vtype',
            'type': None,
            'limits': [
                '3D.intro',
                '3D.outro',
                'countdown',
                'courtesy',
                'feature.intro',
                'feature.outro',
                'intermission',
                'short.film',
                'theater.intro',
                'theater.outro',
                'trailers.intro',
                'trailers.outro',
                'trivia.intro',
                'trivia.outro',
                'dir',
                'file'
            ],
            'name': T(32327, 'Type')
        },
        {
            'attr': 'random',
            'type': strToBool,
            'limits': LIMIT_BOOL,
            'name': T(32057, 'Random')
        },
        {
            'attr': 'source',
            'type': None,
            'limits': LIMIT_DB_CHOICE,
            'name': T(32052, 'Source')
        },
        {
            'attr': 'dir',
            'type': None,
            'limits': LIMIT_DIR,
            'name': T(32047, 'Directory')
        },
        {
            'attr': 'count',
            'type': int,
            'limits': (1, 10, 1),
            'name': T(32060, 'Count'),
            'default': 0
        },
        {
            'attr': 'file',
            'type': None,
            'limits': LIMIT_FILE_DEFAULT,
            'name': T(32048, 'File')
        },
        {
            'attr': 'play3D',
            'type': strToBool,
            'limits': LIMIT_BOOL,
            'name': T(32328, 'Play 3D If 3D Feature')
        },
        {
            'attr': 'volume',
            'type': int,
            'limits': (0, 100, 1),
            'name': T(32025, 'Volume (% of current)'),
            'default': 0
        }
    )
    displayName = T(32023, 'Video')
    typeChar = 'V'

    def __init__(self):
        Item.__init__(self)
        self.vtype = ''
        self.random = True
        self.source = ''
        self.dir = ''
        self.count = 1
        self.file = ''
        self.play3D = True
        self.volume = 0

    def elementVisible(self, e):
        attr = e['attr']
        if attr == 'source':
            return self.vtype not in ('file', 'dir') and not self.random
        elif attr == 'dir':
            return self.vtype == 'dir'
        elif attr == 'count':
            return self.vtype == 'dir' or (self.vtype != 'file' and self.random)
        elif attr == 'file':
            return self.vtype == 'file'
        elif attr == 'random':
            return self.vtype != 'file'
        elif attr == 'play3D':
            return self.random and self.vtype not in ('3D.intro', '3D.outro', 'dir', 'file')

        return True

    def display(self):
        if self.name:
            name = self.name

        elif not self.vtype:
            name = self.displayName

        else:
            name = settingDisplay(self.vtype)

        if self.count > 1 and (self.vtype == 'dir' or (self.vtype != 'file' and self.random)):
            return u'{0} x {1}'.format(name, self.count)

        return name

    def DBChoices(self, attr):
        import database as DB
        DB.initialize()

        DB.connect()
        try:
            return [(x.path, os.path.basename(x.path)) for x in DB.VideoBumpers.select().where(DB.VideoBumpers.type == self.vtype)]
        finally:
            DB.close()


################################################################################
# AUDIOFORMAT
################################################################################
class AudioFormat(Item):
    _type = 'audioformat'
    _elements = (
        {
            'attr': 'method',
            'type': None,
            'limits': [None, 'af.detect', 'af.format', 'af.file'],
            'name': T(32068, 'Method'),
            'default': None
        },
        {
            'attr': 'fallback',
            'type': None,
            'limits': [None, 'af.format', 'af.file'],
            'name': T(32072, 'Fallback'),
            'default': None
        },
        {
            'attr': 'file',
            'type': None,
            'limits': LIMIT_FILE_DEFAULT,
            'name': T(32325, 'Path'),
            'default': ''
        },
        {
            'attr': 'format',
            'type': None,
            'limits': [
                None, 'Auro-3D', 'Dolby Digital', 'Dolby Digital Plus', 'Dolby TrueHD',
                'Dolby Atmos', 'DTS', 'DTS-HD Master Audio', 'DTS-X', 'Datasat', 'THX', 'Other'
            ],
            'name': T(32030, 'Format'),
            'default': None
        },
        {
            'attr': 'play3D',
            'type': strToBool,
            'limits': LIMIT_BOOL,
            'name': T(32328, 'Play 3D if 3D feature')
        },
        {
            'attr': 'volume',
            'type': int,
            'limits': (0, 100, 1),
            'name': T(32025, 'Volume (% of current)'),
            'default': 0
        }
    )
    displayName = T(32329, 'Audio Format Bumper')
    typeChar = 'A'

    def __init__(self):
        Item.__init__(self)
        self.method = None
        self.fallback = None
        self.format = None
        self.file = None
        self.play3D = True
        self.volume = 0

    def elementVisible(self, e):
        attr = e['attr']
        if attr == 'fallback':
            return self.getLive('method') == 'af.detect'
        elif attr == 'file':
            return self.getLive('method') == 'af.file' or (self.getLive('method') == 'af.detect' and self.getLive('fallback') == 'af.file')
        elif attr == 'format':
            return self.getLive('method') == 'af.format' or (self.getLive('method') == 'af.detect' and self.getLive('fallback') == 'af.format')
        elif attr == 'play3D':
            return self.getLive('method') in (None, 'af.detect', 'af.format')

        return True


################################################################################
# ACTION
################################################################################
class Action(Item):
    _type = 'action'
    _elements = (
        {
            'attr': 'file',
            'type': None,
            'limits': LIMIT_FILE,
            'name': T(32085, 'Action file path'),
            'default': ''
        },
        {
            'attr': 'eval',
            'type': None,
            'limits': LIMIT_ACTION,
            'name': T(32089, 'Test'),
            'default': ''
        }
    )
    displayName = T(32083, 'Actions')
    typeChar = '!'
    fileChar = '_'

    def __init__(self):
        Item.__init__(self)
        self.file = ''
        self.eval = None

    def elementVisible(self, e):
        attr = e['attr']
        if attr == 'eval':
            return bool(self.file)

        return True


################################################################################
# COMMAND
################################################################################
class Command(Item):
    _type = 'command'
    _elements = (
        {
            'attr': 'command',
            'type': None,
            'limits': ['back', 'skip'],
            'name': T(32331, 'Command')
        },
        {
            'attr': 'arg',
            'type': None,
            'limits': None,
            'name': T(32332, 'Argument')
        },
        {
            'attr': 'condition',
            'type': None,
            'limits': ['feature.queue=full', 'feature.queue=empty', 'none'],
            'name': T(32333, 'Condition')
        }
    )
    displayName = T(32331, 'Command')
    typeChar = 'C'

    def _set(self, attr, value):
        if self.command in ('back', 'skip'):
            if attr == 'arg':
                value = int(value)
        Item._set(self, attr, value)

    def __init__(self):
        Item.__init__(self)
        self.command = ''
        self.arg = ''
        self.condition = ''

    def getLimits(self, attr):
        e = self.getElement(attr)
        if not e['attr'] == 'arg' or self.command not in ('skip', 'back'):
            return Item.getLimits(self, attr)

        return (1, 99, 1)

    def getType(self, attr):
        e = self.getElement(attr)
        if not e['attr'] == 'arg' or self.command not in ('skip', 'back'):
            return Item.getType(self, attr)

        return int

    def getSettingOptions(self, setting):
        if setting == 'arg':
            if self.command in ('back', 'skip'):
                return (1, 99, 1)
        else:
            return Item.getSettingOptions(self, setting)

    def setSetting(self, setting, value):
        Item.setSetting(self, setting, value)

        if setting == 'command':
            if self.command == 'back':
                if not self.condition:
                    self.condition = 'feature.queue=full'
                if not self.arg:
                    self.arg = 2
            elif self.command == 'skip':
                if not self.condition:
                    self.condition = 'feature.queue=empty'
                if not self.arg:
                    self.arg = 2
            else:
                self.condition = ''

    def getSetting(self, setting):
        if self.command in ('back', 'skip'):
            if setting == 'arg':
                if not self.arg:
                    self.arg = 2
        return Item.getSetting(self, setting)

    def display(self):
        name = self.name or self.displayName
        command = self.command and u' ({0}:{1})'.format(self.command, self.arg) or ''
        return u'{0}{1}'.format(name, command)


CONTENT_CLASSES = {
    'action':       Action,
    'audioformat':  AudioFormat,
    'command':      Command,
    'feature':      Feature,
    'trivia':       Trivia,
    'trailer':      Trailer,
    'video':        Video
}

ITEM_TYPES = [
    ('V', T(32334, 'Video Bumper'), 'V', Video),
    ('Q', T(32026, 'Trivia'), 'Q', Trivia),
    ('T', T(32049, 'Trailers'), 'T', Trailer),
    ('A', T(32329, 'Audio Format Bumper'), 'A', AudioFormat),
    ('F', T(32073, 'Features'), 'F', Feature),
    ('C', T(32331, 'Command'), 'C', Command),
    ('!', T(32083, 'Actions'), '_', Action)
]


def getItem(token):
    for i in ITEM_TYPES:
        if i[0] == token:
            return i[3]

# - Old XML save methods
# def prettify(elem):
#     from xml.etree import ElementTree as ET
#     import xml.dom.minidom as minidom
#     """Return a pretty-printed XML string for the Element.
#     """
#     rough_string = ET.tostring(elem)
#     reparsed = minidom.parseString(rough_string)

#     uglyXml = reparsed.toprettyxml(indent='    ').encode('ascii', 'xmlcharrefreplace')
#     text_re = re.compile('>\n\s+([^<>\s].*?)\n\s+</', re.DOTALL)
#     prettyXml = text_re.sub('>\g<1></', uglyXml)
#     return prettyXml
#     # return reparsed.toprettyxml().encode('ascii', 'xmlcharrefreplace')

# def getSaveString(items):
#     from xml.etree import ElementTree as ET
#     base = ET.Element('sequence')
#     for item in items:
#         base.append(item.toNode())

#     return prettify(base)


def getItemsFromXMLString(dstring):
    from xml.etree import ElementTree as ET
    e = ET.fromstring(dstring)
    items = []
    for node in e.findall('item'):
        items.append(Item.fromNode(node))
    return items


def getSaveString(items):
    data = []
    for i in items:
        data.append(i.toDict())

    return json.dumps({'version': 1, 'items': data}, indent=1)


def getItemsFromString(dstring):
    try:
        data = json.loads(dstring)
        return [Item.fromDict(ddict) for ddict in data['items']]
    except ValueError:
        if dstring and dstring.startswith('{'):
            util.LOG(repr(dstring[:100]))
            util.ERROR()
        else:
            try:
                return getItemsFromXMLString(dstring)
            except:
                util.ERROR()

    return None


def loadSequence(path):
    import xbmcvfs
    f = xbmcvfs.File(path, 'r')
    dstring = f.read().decode('utf-8')
    f.close()
    return getItemsFromString(dstring)
