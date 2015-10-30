import util
import database as DB
from xml.etree import ElementTree as ET

COUNTRY_SYSTEMS = {
    'DE': 'FSK',
    'GB': 'BFS',
    'BR': 'DEJUS',
    'ES': 'ICAA',
    'US': 'MPAA'
}

DEFAULT_RATING_SYSTEM = None


def getSystemByCountry(country_code):
    return COUNTRY_SYSTEMS.get(country_code)


def genValidIdentifier(seq):
    ret = ''
    saw_first_char = False
    for ch in seq:
        if not saw_first_char and (ch == '_' or ch.isalpha()):
            saw_first_char = True
            ret += ch
        elif saw_first_char and (ch == '_' or ch.isalpha() or ch.isdigit()):
            ret += ch
        else:
            ret += '_'
    return ret


class RatingSystem:
    name = ''
    ratings = None
    regEx = None
    regions = None

    def __repr__(self):
        return '{0}: {1}'.format(self.name, self.ratings)

    def __str__(self):
        return self.__repr__()

    def getRatingByName(self, name):
        name = name.upper()
        for r in self.ratings:
            if r.name == name:
                return r
        return NO_RATING

    def addRating(self, rating):
        if not self.ratings:
            self.ratings = []
        rating.system = self.name
        self.ratings.append(rating)

    def addRegEx(self, context, regex):
        if not self.regEx:
            self.regEx = {}
        self.regEx[context] = regex

    def getRegEx(self, context):
        if not self.regEx or context not in self.regEx:
            return None

        return self.regEx[context]

    def addRegion(self, region):
        COUNTRY_SYSTEMS[region] = self.name
        if not self.regions:
            self.regions = []
        self.regions.append(region)


class Rating:
    system = ''

    def __init__(self, name, value, internal=None):
        self.name = name
        self.value = value
        self.internal = internal or self.name

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.system and '{0}:{1}'.format(self.system, self.name) or 'Unknown'

    def __nonzero__(self):
        return bool(self.system)

    @classmethod
    def fromNode(cls, node):
        return cls(node.text, int(node.attrib.get('value')), node.attrib.get('internal'))

    def __lt__(self, other):
        return self.value < other.value

    def __le__(self, other):
        return self.value <= other.value

    def __eq__(self, other):
        return self.value == other.value

    def __ge__(self, other):
        return self.value >= other.value

    def __gt__(self, other):
        return self.value > other.value

    def __ne__(self, other):
        return self.value != other.value


class MPAA(RatingSystem):
    class MPAARating(Rating):
        system = 'MPAA'

    NC_17 = MPAARating('NC-17', 170)
    R = MPAARating('R', 160)
    PG_13 = MPAARating('PG-13', 130)
    PG = MPAARating('PG', 120)
    G = MPAARating('G', 0)
    NR = MPAARating('NR', 1000)

    name = 'MPAA'
    ratings = [NR, G, PG, PG_13, R, NC_17]
    regions = ['US']


class XMLRatingSystem(RatingSystem):
    @classmethod
    def fromXML(cls, xml_string):
        system = cls()

        e = ET.fromstring(xml_string)

        system.name = e.attrib.get('name')
        system.ratings = []

        for node in e.findall('regex'):
            system.addRegEx(node.attrib.get('context'), node.text)

        for node in e.findall('rating'):
            rating = Rating.fromNode(node)
            name = genValidIdentifier(rating.name)
            setattr(system, name, rating)
            system.addRating(rating)

        for node in e.findall('region'):
            system.addRegion(node.text)

        return system


RATINGS_SYSTEMS = {
    'MPAA': MPAA()
}


NO_RATING = Rating('', 1000)


def getRatingsSystem(name):
    name = name.upper()
    return RATINGS_SYSTEMS.get(name)


def getRating(system_or_name, name=None):
    system = system_or_name

    if not name:
        if ':' in system_or_name:
            system, name = system_or_name.split(':', 1)
        elif DEFAULT_RATING_SYSTEM:
            name = system_or_name
            system = DEFAULT_RATING_SYSTEM

    if not name:
        return NO_RATING

    system = getRatingsSystem(system)

    if not system:
        return NO_RATING

    return system.getRatingByName(name)


def addRatingSystemFromXML(xml):
    system = XMLRatingSystem.fromXML(xml)

    RATINGS_SYSTEMS[system.name.upper()] = system

    return system


def getRegExs(context=None):
    ret = {}
    for system in RATINGS_SYSTEMS.values():
        regEx = system.getRegEx(context)
        if regEx:
            ret[system.name] = regEx
    return ret


def setCountry(country_code):
    global DEFAULT_RATING_SYSTEM
    DEFAULT_RATING_SYSTEM = getSystemByCountry(country_code)
    util.DEBUG_LOG('Default rating system: {0}'.format(DEFAULT_RATING_SYSTEM))


def setDefaultRatingSystem(system):
    global DEFAULT_RATING_SYSTEM
    DEFAULT_RATING_SYSTEM = system
    util.DEBUG_LOG('Default rating system: {0}'.format(DEFAULT_RATING_SYSTEM))


def loadFromXML():
    import os
    import inspect

    systemsFolder = os.path.join(os.path.realpath(os.path.abspath(os.path.split(inspect.getfile(inspect.currentframe()))[0])), 'rating_systems')
    for p in os.listdir(systemsFolder):
        path = os.path.join(systemsFolder, p)

        with open(path, 'r') as f:
            addRatingSystemFromXML(f.read())


@DB.session
def loadFromDB():
    for system in DB.RatingSystem.select():
        if system.name in RATINGS_SYSTEMS:
            RATINGS_SYSTEMS[system.name].addRegEx(system.context, system.regEx)
        else:
            rs = RatingSystem()
            rs.name = system.name
            rs.addRegEx(system.context, system.regEx)
            RATINGS_SYSTEMS[system.name] = rs
            if system.regions:
                for r in system.regions.split(','):
                    rs.addRegion(r)

    for rating in DB.Rating.select():
        if rating.system not in RATINGS_SYSTEMS:
            continue
        RATINGS_SYSTEMS[rating.system].addRating(Rating(rating.name, rating.value, rating.internal))


def load():
    DB.initialize()
    loadFromXML()
    loadFromDB()

    util.DEBUG_LOG('Rating Systems:')
    for rs in RATINGS_SYSTEMS.values():
        util.DEBUG_LOG('  {0}'.format(repr(rs)))


load()
