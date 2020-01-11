import time
import calendar

import xbmcgui
import kodigui
import kodiutil
import cvutil
import cinemavision

from kodijsonrpc import rpc

cvutil.ratingParser()


class SeqAttrEditorDialog(kodigui.BaseDialog):
    xmlFile = 'script.cinemavision-sequence-attribute-editor.xml'
    path = kodiutil.ADDON_PATH
    theme = 'Main'
    res = '1080i'

    ATTRIBUTE_LIST_ID = 300
    SLIDER_ID = 401

    def __init__(self, *args, **kwargs):
        kodigui.BaseDialog.__init__(self, *args, **kwargs)
        self.sequenceData = kwargs['sequence_data']
        self.modified = False
        self.attributeList = None
        self.options = []

    def onFirstInit(self):
        self.attributeList = kodigui.ManagedControlList(self, self.ATTRIBUTE_LIST_ID, 10)
        # self.sliderControl = self.getControl(self.SLIDER_ID)
        self.fillAttributeList()

    def fillAttributeList(self, update=False):
        self.options = []
        # self.options.append(('active', 'Active'))
        self.options.append(('type', 'Type'))
        self.options.append(('ratings', 'Rating(s)'))
        self.options.append(('year', 'Year(s)'))
        self.options.append(('studios', 'Studio(s)'))
        self.options.append(('directors', 'Director(s)'))
        self.options.append(('actors', 'Actor(s)'))
        self.options.append(('genres', 'Genre(s)'))
        self.options.append(('tags', 'Tag(s)'))
        self.options.append(('dates', 'Date(s)'))
        self.options.append(('times', 'Time(s)'))

        items = []
        for o in self.options:
            mli = kodigui.ManagedListItem(data_source=o)
            self.updateItem(mli)
            items.append(mli)

        if update:
            self.attributeList.replaceItems(items)
        else:
            self.attributeList.reset()
            self.attributeList.addItems(items)

        self.setFocusId(self.ATTRIBUTE_LIST_ID)

    def onClick(self, controlID):
        if controlID == self.ATTRIBUTE_LIST_ID:
            self.attributeClicked()

    def attributeClicked(self):
        item = self.attributeList.getSelectedItem()
        if not item:
            return
        option = item.dataSource[0]
        label = item.dataSource[1]

        val = None

        if option == 'directors':
            val = self.getDBEntry(self.getDirectorList, 'director', 'Director', self.sequenceData.get('directors'))
        elif option == 'actors':
            val = self.getDBEntry(self.getActorList, 'actor', 'Actor', self.sequenceData.get('actors'))
        elif option == 'studios':
            val = self.getDBEntry(self.getStudioList, 'studio', 'Studio', self.sequenceData.get('studios'))
        elif option == 'genres':
            val = self.getDBEntry(self.getGenreList, 'genre', 'Genre', self.sequenceData.get('genres'))
        elif option == 'tags':
            val = self.getDBEntry(self.getTagList, 'tag', 'Tag', self.sequenceData.get('tags'))
        elif option == 'year':
            val = self.getRangedEntry(self.getYear, 'year', self.sequenceData.get('year'))
        elif option == 'ratings':
            val = self.getRangedEntry(self.getRating, 'ratings', self.sequenceData.get('ratings'))
        elif option == 'dates':
            val = self.getRangedEntry(self.getDate, 'dates', self.sequenceData.get('dates'))
        elif option == 'times':
            val = self.getRangedEntry(self.getTime, 'times', self.sequenceData.get('times'))
        elif option == 'active':
            val = not self.sequenceData.active
            self.sequenceData.active = val
            kodiutil.setGlobalProperty('ACTIVE', self.sequenceData.active and '1' or '0')
        elif option == 'type':
            if not self.sequenceData.get('type'):
                val = '2D'
            else:
                val = self.sequenceData.get('type') == '2D' and '3D' or ''
        else:
            val = xbmcgui.Dialog().input(u'Enter {0}'.format(label), self.sequenceData.get(option))

        if val is None:
            return

        self.sequenceData.set(option, val)
        self.modified = True
        self.updateItem(item)

    def updateItem(self, mli):
        o = mli.dataSource
        label2 = 'ANY'

        try:
            if o[0] == 'active':
                label2 = self.sequenceData.active and '[COLOR FF00FF00]YES[/COLOR]' or '[COLOR FFFF0000]NO[/COLOR]'
            elif o[0] == 'type':
                if self.sequenceData.get('type'):
                    label2 = self.sequenceData.get('type') == '3D' and '3D' or '2D'
            elif o[0] in ['year', 'dates', 'times', 'ratings']:
                data = self.sequenceData.get(o[0], [])
                if data:
                    parts = []
                    for d in data:
                        parts.append(self.getEntryDisplay(o[0], d))
                    label2 = ', '.join(parts)
            elif o[0] in ('genres', 'studios', 'directors', 'actors', 'tags'):
                items = self.sequenceData.get(o[0], [])
                if items:
                    label2 = ', '.join(items)
        except Exception:
            kodiutil.ERROR()

        mli.setLabel(o[1])
        mli.setLabel2(label2)
        mli.setProperty('name', o[1])

    def getEntryDisplay(self, itype, val):
        try:
            if itype == 'year':
                if len(val) > 1:
                    return u'{0} - {1}'.format(val[0], val[1] if val[1] else 'Now')
                else:
                    return u'{0}'.format(val[0])
            elif itype == 'ratings':
                if len(val) > 1:
                    return u'{0} - {1}'.format(val[0] if val[0] else 'Any', val[1] if val[1] else 'Any')
                else:
                    return u'{0}'.format(val[0])
            elif itype == 'dates':
                if len(val) > 1:
                    return u'{0} {1} - {2} {3}'.format(calendar.month_abbr[val[0][0]], val[0][1], calendar.month_abbr[val[1][0]], val[1][1])
                else:
                    return u'{0} {1}'.format(calendar.month_abbr[val[0][0]], val[0][1])
            elif itype == 'times':
                if len(val) > 1:
                    return u'{0:02d}:{1:02d} - {2:02d}:{3:02d}'.format(val[0][0], val[0][1], val[1][0], val[1][1])
                else:
                    return u'{0:02d}'.format(val[0][0])
        except Exception:
            kodiutil.ERROR()

        return val

    def getRangedEntry(self, func, itype, ret=None):
        ret = ret or []

        while True:
            options = []
            options.append(('range', 'Add Range'))
            options.append(('single', 'Add Single'))
            if len(ret) > 1:
                options.append(('remove', 'Remove Entry'))
            options.append(('clear', 'Clear'))
            options.append(('done', 'Done'))

            idx = xbmcgui.Dialog().select("Options", [o[1] for o in options])
            if idx < 0:
                return ret

            choice = options[idx][0]

            if choice == 'done':
                return ret
            elif choice == 'clear':
                return []
            elif choice == 'remove':
                idx = xbmcgui.Dialog().select("Options", [self.getEntryDisplay(itype, v) for v in ret])
                if idx < 0:
                    continue
                ret.pop(idx)
            elif choice == 'range':
                yStart = func(remove=ret, disp='Start')
                if yStart is None:
                    continue

                yStart = yStart or None

                if itype == 'year':
                    prefix = u'{0} thru '.format(yStart)
                elif itype == 'ratings':
                    prefix = u'{0} - '.format(yStart)
                elif itype == 'dates':
                    prefix = u'{0} {1} thru '.format(calendar.month_abbr[yStart[0]], yStart[1])
                elif itype == 'times':
                    prefix = u'{0:02d}:{1:02d} thru '.format(*yStart)

                yEnd = func(yStart, remove=ret, disp='End', prefix=prefix)
                if yEnd is None:
                    continue

                ret.append([yStart, yEnd or None])
            elif choice == 'single':
                year = func(remove=ret, single=True)
                if year is None:
                    continue
                ret.append([year])

    def chooseFromList(self, ilist, disp, mod, dlist=None):
        if dlist is None:
            dlist = ilist
        mod = ' ({0})'.format(mod) if mod else ''
        idx = xbmcgui.Dialog().select(u'Select {0}{1}'.format(disp, mod), [str(i) for i in dlist])
        if idx < 0:
            return None
        return ilist[idx]

    @staticmethod
    def getYear(start=None, remove=None, single=False, disp='', prefix=''):
        if start is not None:
            years = [[0, 'Now']]
        else:
            years = []
            start = 1900

        mod = ' ({0})'.format(disp) if disp else ''
        remove = remove or []
        for y in range(time.localtime().tm_year, start, -1):
            for r in remove:
                if len(r) > 1:
                    if not r[1]:
                        if r[0] <= y:
                            break
                    elif r[0] <= y <= r[1]:
                        break
                else:
                    if y == r[0]:
                        break
            else:
                years.append([y, str(y)])
        idx = xbmcgui.Dialog().select(u'Select Year{0}'.format(mod), ['{0}{1}'.format(prefix, y[1]) for y in years])
        if idx < 0:
            return None

        return years[idx][0]

    def getRating(self, start=None, remove=None, single=False, disp='', prefix=''):
        ratingsList = [r for r in cinemavision.ratings.defaultRatingsSystem() if start is None or r > start]
        if prefix:
            ratingsList.append(False)
        else:
            ratingsList.insert(0, False)
        rating = self.chooseFromList(ratingsList, 'Rating', disp, ['{0}{1}'.format(prefix, r if r else 'Any') for r in ratingsList])
        if rating is None:
            return None

        return rating

    def getDate(self, start=None, remove=None, single=False, disp='', prefix=''):
        month = self.chooseFromList(range(1, 13), 'Month', disp, [u'{0}{1}'.format(prefix, calendar.month_abbr[m]) for m in range(1, 13)])
        if month is None:
            return None

        if month in [4, 6, 9, 11]:
            dlist = range(1, 31)
        elif month == 2:
            dlist = range(1, 30)
        else:
            dlist = range(1, 32)

        monthName = calendar.month_abbr[month]
        day = self.chooseFromList(dlist, 'Day', disp, [u'{0}{1} {2}'.format(prefix, monthName, d) for d in dlist])
        if day is None:
            return None

        return [month, day]

    def getTime(self, start=None, remove=None, single=False, disp='', prefix=''):
        hours = []
        if single and remove:
            hours = [h for h in range(24) if [[h, None]] not in remove]
        else:
            hours = range(24)
        hour = self.chooseFromList(hours, 'Hour', disp, [u'{0}{1:02d}'.format(prefix, h) for h in hours])
        if hour is None:
            return None

        if single:
            return [hour, None]

        minute = self.chooseFromList(range(60), 'Minute', disp, [u'{0}{1:02d}:{2:02d}'.format(prefix, hour, m) for m in range(60)])
        if minute is None:
            return None

        return [hour, minute]

    def getGenreList(self, remove):
        return [g.get('title') for g in rpc.VideoLibrary.GetGenres(
            type='movie',
            properties=['title']
        ).get('genres', []) if g.get('title') and (not remove or not g.get('title') in remove)]

    def getTagList(self, remove):
        kodiutil.LOG(repr(remove))
        return [t.get('title') for t in rpc.VideoLibrary.GetTags(
            type='movie',
            properties=['title']
        ).get('tags', []) if t.get('title') and (not remove or not t.get('title') in remove)]

    def getStudioList(self, remove):
        # TODO: Get all studios?
        movies = rpc.VideoLibrary.GetMovies(properties=['studio'], limits={'start': 0, 'end': 100000}).get('movies', [])
        movies = [m for m in movies if not remove or not m in remove]
        return sorted(list(set([y for z in movies for y in z['studio']])))

    def getDirectorList(self, remove):
        # TODO: Get all directors?
        movies = rpc.VideoLibrary.GetMovies(properties=['director'], limits={'start': 0, 'end': 100000}).get('movies', [])
        movies = [m for m in movies if not remove or not m in remove]
        return sorted(list(set([y for z in movies for y in z['director']])))

    def getActorList(self, remove):
        # TODO: Get all directors?
        movies = rpc.VideoLibrary.GetMovies(properties=['cast'], limits={'start': 0, 'end': 100000}).get('movies', [])
        movies = [m for m in movies if not remove or not m in remove]
        return sorted(list(set([y['name'] for z in movies for y in z['cast']])))

    def getDBEntry(self, func, itype, disp, ret=None):
        allitems = func(ret)
        ret = ret or []

        while True:
            options = []
            if allitems:
                options.append(('list', 'Add From List'))
            if itype != 'genre':
                options.append(('manual', 'Add Manually'))
            if len(ret) > 1:
                options.append(('remove', 'Remove Entry'))
            options.append(('clear', 'Clear'))
            options.append(('done', 'Done'))

            idx = xbmcgui.Dialog().select("Options", [o[1] for o in options])
            if idx < 0:
                return ret

            choice = options[idx][0]

            if choice == 'done':
                return ret
            elif choice == 'clear':
                return []
            elif choice == 'remove':
                idx = xbmcgui.Dialog().select("Options", [self.getEntryDisplay(itype, v) for v in ret])
                if idx < 0:
                    continue
                ret.pop(idx)
            elif choice == 'manual':
                val = xbmcgui.Dialog().input(u'Enter {0} {1}'.format(disp, len(ret) + 1))
                if not val:
                    continue
                ret.append(val)
                if val in allitems:
                    allitems.remove(val)
            else:
                idx = xbmcgui.Dialog().select(u'Choose {0} {1}'.format(disp, len(ret) + 1), allitems)
                if idx < 0:
                    continue
                val = allitems[idx]
                ret.append(val)
                if val in allitems:
                    allitems.remove(val)


def setAttributes(sequenceData):
    w = SeqAttrEditorDialog.open(sequence_data=sequenceData)
    modified = w.modified
    del w
    return modified
