import os
import re
import xbmc
import kodiutil
import cinemavision

from kodiutil import T

DEFAULT_3D_RE = '(?i)3DSBS|3D.SBS|HSBS|H.SBS|H-SBS|[\. _]SBS[\. _]|FULL-SBS|FULL.SBS|FULLSBS|FSBS|HALF-SBS|' +\
    '3DTAB|3D.TAB|HTAB|H.TAB|3DOU|3D.OU|3D.HOU|[\. _]HOU[\. _]|[\. _]OU[\. _]|HALF-TAB|[\. _]TAB[\. _]'

cinemavision.init(kodiutil.DEBUG(), kodiutil.Progress, kodiutil.T, kodiutil.getSetting('3D.tag.regex', DEFAULT_3D_RE))


def defaultSavePath(for_3D=False):
    return os.path.join(kodiutil.ADDON_PATH, 'resources', 'script.cinemavision.default{0}.cvseq'.format(for_3D and '3D' or '2D'))


def lastSavePath():
    name = kodiutil.getSetting('save.name', '')
    return getSavePath(name)


def getSavePath(name):
    contentPath = kodiutil.getSetting('content.path')
    if not name or not contentPath:
        return

    return cinemavision.util.pathJoin(contentPath, 'Sequences', name + '.cvseq')


def getSequenceName(path):
    if 'script.cinemavision.default2D.cvseq' in path:
        return u'[ {0} ]'.format(T(32599, 'Default 2D'))
    elif 'script.cinemavision.default3D.cvseq' in path:
        return u'[ {0} ]'.format(T(32600, 'Default 3D'))

    return re.split(r'[/\\]', path)[-1][:-6]


def getSequencePath(for_3D=False, with_name=False):
    if for_3D:
        name = kodiutil.getSetting('sequence.3D')
    else:
        name = kodiutil.getSetting('sequence.2D')

    if name:
        path = getSavePath(name)
    else:
        path = defaultSavePath()

    if with_name:
        return (path, getSequenceName(path))

    return path


def selectSequence():
    import xbmcgui

    default2D = 2
    default3D = 3

    contentPath = kodiutil.getSetting('content.path')
    if not contentPath:
        xbmcgui.Dialog().ok(T(32500, 'Not Found'), ' ', T(32501, 'No sequences found.'))
        return None

    sequencesPath = cinemavision.util.pathJoin(contentPath, 'Sequences')
    options = cinemavision.util.vfs.listdir(sequencesPath)
    options = [(n, n[:-6]) for n in options if n.endswith('.cvseq')]
    options.append((default2D, u'[ {0} ]'.format(T(32599, 'Default 2D'))))
    options.append((default3D, u'[ {0} ]'.format(T(32600, 'Default 3D'))))

    if not options:
        xbmcgui.Dialog().ok(T(32500, 'Not Found'), ' ', T(32501, 'No sequences found.'))
        return None

    idx = xbmcgui.Dialog().select(T(32502, 'Choose Sequence'), [o[1] for o in options])
    if idx < 0:
        return None

    result = options[idx][0]

    if result == default2D:
        path = defaultSavePath()
    elif result == default3D:
        path = defaultSavePath(for_3D=True)
    else:
        path = cinemavision.util.pathJoin(sequencesPath, options[idx][0])

    return {'path': path, 'name': options[idx][1]}


def getContentPath(from_load=False):
    contentPath = kodiutil.getSetting('content.path')
    demoPath = os.path.join(kodiutil.PROFILE_PATH, 'demo')

    if contentPath:
        kodiutil.setSetting('content.initialized', True)
        if os.path.exists(demoPath):
            try:
                import shutil
                shutil.rmtree(demoPath)
            except:
                kodiutil.ERROR()

        return contentPath
    else:
        if not os.path.exists(demoPath):
            copyDemoContent()
            downloadDemoContent()
            if not from_load:
                loadContent()
        return demoPath


def loadContent(from_settings=False):
    import xbmcgui

    if from_settings and not kodiutil.getSetting('content.path'):
        xbmcgui.Dialog().ok(T(32503, 'No Content Path'), ' ', T(32504, 'Content path not set or not applied'))
        return

    contentPath = getContentPath(from_load=True)

    kodiutil.DEBUG_LOG('Loading content...')

    with kodiutil.Progress(T(32505, 'Loading Content')) as p:
        cinemavision.content.UserContent(contentPath, callback=p.msg, trailer_sources=kodiutil.getSetting('trailer.scrapers', '').split(','))

    createSettingsRSDirs()


def createSettingsRSDirs():
    base = os.path.join(kodiutil.PROFILE_PATH, 'settings', 'ratings')
    if not os.path.exists(base):
        os.makedirs(base)
    defaultPath = os.path.join(kodiutil.PROFILE_PATH, 'settings', 'ratings_default')

    if os.path.exists(defaultPath):
        import shutil
        shutil.rmtree(defaultPath)

    defaultSystem = kodiutil.getSetting('rating.system.default', 'MPAA')

    for system in cinemavision.ratings.RATINGS_SYSTEMS.values():
        systemPaths = [os.path.join(base, system.name)]
        if system.name == defaultSystem:
            systemPaths.append(defaultPath)

        for path in systemPaths:
            if not os.path.exists(path):
                os.makedirs(path)

            for rating in system.ratings:
                with open(os.path.join(path, str(rating).replace(':', '.', 1)), 'w'):
                    pass

    kodiutil.setSetting('settings.ratings.initialized', 'true')
    kodiutil.setSetting('settings.ratings.initialized2', 'true')


def downloadDemoContent():
    import xbmc
    import requests
    import zipfile
    url = 'http://cinemavision.tv/cvdemo/Demo.zip'
    output = os.path.join(kodiutil.PROFILE_PATH, 'demo.zip')
    target = os.path.join(kodiutil.PROFILE_PATH, 'demo', 'Trivia Slides')
    # if not os.path.exists(target):
    #     os.makedirs(target)

    with open(output, 'wb') as handle:
        response = requests.get(url, stream=True)
        total = float(response.headers.get('content-length', 1))
        sofar = 0
        blockSize = 4096
        if not response.ok:
            return False

        with kodiutil.Progress(T(32506, 'Download'), T(32507, 'Downloading demo content')) as p:
            for block in response.iter_content(blockSize):
                sofar += blockSize
                pct = int((sofar/total) * 100)
                p.update(pct)
                handle.write(block)

    z = zipfile.ZipFile(output)
    z.extractall(target)
    xbmc.sleep(500)
    try:
        os.remove(output)
    except:
        kodiutil.ERROR()

    return True


def copyDemoContent():
    source = os.path.join(kodiutil.ADDON_PATH, 'resources', 'demo')
    dest = os.path.join(kodiutil.PROFILE_PATH, 'demo')
    import shutil
    shutil.copytree(source, dest)


def setRatingBumperStyle():
    import xbmcgui

    styles = cinemavision.sequence.Feature.DBChoices('ratingStyle')

    if not styles:
        xbmcgui.Dialog().ok(T(32508, 'No Content'), '', T(32509, 'No content found for current rating system.'))
        return

    idx = xbmcgui.Dialog().select(T(32510, 'Select Style'), [x[1] for x in styles])

    if idx < 0:
        return

    kodiutil.setSetting('feature.ratingStyle', styles[idx][0])


def evalActionFile(paths, test=True):
    import xbmcgui

    if not paths:
        xbmcgui.Dialog().ok(T(32511, 'None found'), T(32512, 'No action file(s) set'))
        return

    if not isinstance(paths, list):
        paths = [paths]

    messages = []

    abortPath = kodiutil.getSetting('action.onAbort.file')
    if not kodiutil.getSetting('action.onAbort', False):
        abortPath = None

    # if not abortPath:
    #     yes = xbmcgui.Dialog().yesno('No Abort', 'Abort action not set.', '')
    #     Test = False

    for path in paths:
        processor = cinemavision.actions.ActionFileProcessor(path, test=True)
        messages.append(u'[B]VALIDATE ({0}):[/B]'.format(os.path.basename(path)))
        messages.append('')
        parseMessages = []
        hasParseMessages = False
        hasErrors = False

        if not processor.fileExists:
            messages.append(u'{0} - [COLOR FFFF0000]{1}[/COLOR]'.format(os.path.basename(path), T(32513, 'MISSING!')))
            messages.append('')
            continue

        if processor.parserLog:
            hasParseMessages = True
            for type_, msg in processor.parserLog:
                hasErrors = hasErrors or type_ == 'ERROR'
                parseMessages .append(u'[COLOR {0}]{1}[/COLOR]'.format(type_ == 'ERROR' and 'FFFF0000' or 'FFFFFF00', msg))
        else:
            parseMessages.append('[COLOR FF00FF00]OK[/COLOR]')

        messages += parseMessages
        messages.append('')

        if test:
            if hasErrors:
                messages += [u'[B]TEST ({0}):[/B]'.format(os.path.basename(path)), '']
                messages.append(u'[COLOR FFFF0000]{0}[/COLOR]'.format('SKIPPED DUE TO ERRORS'))
            else:
                with kodiutil.Progress('Testing', 'Executing actions...'):
                    messages += ['[B]TEST ({0}):[/B]'.format(os.path.basename(path)), '']
                    for line in processor.test():
                        if line.startswith('Action ('):
                            lsplit = line.split(': ', 1)
                            line = '[COLOR FFAAAAFF]{0}:[/COLOR] {1}'.format(lsplit[0], lsplit[1])
                        elif line.startswith('ERROR:'):
                            line = '[COLOR FFFF0000]{0}[/COLOR]'.format(line)
                        messages.append(line)
            messages.append('')

    if not test and not hasParseMessages:
        xbmcgui.Dialog().ok(T(32515, 'Done'), T(32516, 'Action file(s) parsed OK'))
    else:
        showText(T(32514, 'Parser Messages'), '[CR]'.join(messages))

    if test and abortPath:
        runAbort = kodiutil.getSetting('action.test.runAbort', 0)
        if runAbort and (runAbort != 2 or xbmcgui.Dialog().yesno(T(32597, 'Cleanup'), T(32598, 'Run abort action?'))):
            processor = cinemavision.actions.ActionFileProcessor(abortPath)
            processor.run()


_RATING_PARSER = None


def ratingParser():
    global _RATING_PARSER
    if not _RATING_PARSER:
        _RATING_PARSER = RatingParser()
    return _RATING_PARSER


class RatingParser:
    SYSTEM_RATING_REs = {
        # 'MPAA': r'(?i)^Rated\s(?P<rating>Unrated|NR|PG-13|PG|G|R|NC-17)',
        'BBFC': r'(?i)^UK(?:\s+|:)(?P<rating>Uc|U|12A|12|PG|15|R18|18)',
        'FSK': r'(?i)^(?:FSK|Germany)(?:\s+|:)(?P<rating>0|6|12|16|18|Unrated)',
        'DEJUS': r'(?i)(?P<rating>Livre|10 Anos|12 Anos|14 Anos|16 Anos|18 Anos)'
    }

    RATING_REs = {
        'MPAA': r'(?i)(?P<rating>Unrated|NR|PG-13|PG|G|R|NC-17)',
        'BBFC': r'(?i)(?P<rating>Uc|U|12A|12|PG|15|R18|18)',
        'FSK': r'(?i)(?P<rating>0|6|12|16|18|Unrated)',
        'DEJUS': r'(?i)(?P<rating>Livre|10 Anos|12 Anos|14 Anos|16 Anos|18 Anos)'
    }

    SYSTEM_RATING_REs.update(cinemavision.ratings.getRegExs('kodi'))
    RATING_REs.update(cinemavision.ratings.getRegExs())

    LANGUAGE = xbmc.getLanguage(xbmc.ISO_639_1, region=True)

    def __init__(self):
        kodiutil.DEBUG_LOG('Language: {0}'.format(self.LANGUAGE))
        self.setRatingDefaults()

    def setRatingDefaults(self):
        ratingSystem = kodiutil.getSetting('rating.system.default', 'MPAA')

        if not ratingSystem:
            try:
                countryCode = self.LANGUAGE.split('-')[1].strip()
                if countryCode:
                    cinemavision.ratings.setCountry(countryCode)
            except IndexError:
                pass
            except:
                kodiutil.ERROR()
        else:
            cinemavision.ratings.setDefaultRatingSystem(ratingSystem)

    def getActualRatingFromMPAA(self, rating, debug=False):
        if debug:
            kodiutil.DEBUG_LOG('Rating from Kodi: {0}'.format(kodiutil.strRepr(rating)))

        if not rating:
            return 'UNKNOWN:NR'

        # Try a definite match
        for system, ratingRE in self.SYSTEM_RATING_REs.items():
            m = re.search(ratingRE, rating)
            if m:
                return '{0}:{1}'.format(system, m.group('rating'))

        rating = rating.upper().replace('RATED', '').strip(': ')

        # Try to match against default system if set
        defaultSystem = cinemavision.ratings.DEFAULT_RATING_SYSTEM
        if defaultSystem and defaultSystem in self.RATING_REs:
            m = re.search(self.RATING_REs[defaultSystem], rating)
            if m:
                return '{0}:{1}'.format(defaultSystem, m.group('rating'))

        # Try to extract rating from know ratings systems
        for system, ratingRE in self.RATING_REs.items():
            m = re.search(ratingRE, rating)
            if m:
                return m.group('rating')

        # Just return what we have
        return rating


def multiSelect(options, default=False):
    import kodigui

    class ModuleMultiSelectDialog(kodigui.MultiSelectDialog):
        xmlFile = 'script.cinemavision-multi-select-dialog.xml'
        path = kodiutil.ADDON_PATH
        theme = 'Main'
        res = '1080i'

        OPTIONS_LIST_ID = 300
        OK_BUTTON_ID = 201
        CANCEL_BUTTON_ID = 202
        USE_DEFAULT_BUTTON_ID = 203
        HELP_TEXTBOX_ID = 250

        TOGGLE_MOVE_DIVIDER_X = 190

    w = ModuleMultiSelectDialog.open(options=options, default=default)
    result = w.result
    del w
    if result:
        return ','.join(result)

    return result


def showText(heading, text):
    import kodigui

    class TextView(kodigui.BaseDialog):
        xmlFile = 'script.cinemavision-text-dialog.xml'
        path = kodiutil.ADDON_PATH
        theme = 'Main'
        res = '1080i'

        def __init__(self, *args, **kwargs):
            kodigui.BaseDialog.__init__(self, *args, **kwargs)
            self.heading = kwargs.get('heading', '')
            self.text = kwargs.get('text', '')

        def onFirstInit(self):
            self.setProperty('heading', self.heading)
            self.getControl(100).setText(self.text)

    w = TextView.open(heading=heading, text=text)
    del w
