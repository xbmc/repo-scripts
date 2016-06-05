import xbmc
import xbmcgui
import kodigui
import base
import message
import actiondialog
import time
import threading

from lib import util
from lib import backgroundthread
from lib import tablo
from lib import player
from lib.tablo import grid
from lib.util import T

WM = None


class ShowsTask(backgroundthread.Task):
    def setup(self, paths, callback):
        self.paths = paths
        self.callback = callback

    def run(self):
        shows = {}
        ct = 0

        shows = tablo.API.batch.post(self.paths)
        if self.isCanceled():
            return

        ct += len(shows)
        util.DEBUG_LOG('Retrieved {0} shows'.format(ct))
        for path, show in shows.items():
            if self.isCanceled():
                return

            self.callback(tablo.Show.newFromData(show))

        self.callback(None)


class DelayedShowUpdater(object):
    def __init__(self, window):
        self._window = window
        self._timeout = 0
        self._item = None
        self._thread = None
        self._abort = False
        self._delay = 0.2

    def reset(self):
        self._timeout = time.time() + self._delay
        if not self._thread or not self._thread.isAlive():
            self._thread = threading.Thread(target=self.wait)
            self._thread.start()

    def aborted(self):
        return self._abort or xbmc.abortRequested or self._window._closing

    def wait(self):
        while not self.aborted():
            if time.time() > self._timeout:
                break
            xbmc.sleep(100)
        else:
            return

        self._thread = None
        self._timeout = 0

        if not self._item.dataSource.get('show'):
            self._window.getSingleShowData(self._item.dataSource['path'])

    def setItem(self, item):
        self._item = item
        self.reset()

    def abort(self):
        self._abort = True


class GuideNoSubscriptionWindow(message.MessageWindow):
    name = 'GUIDE_NO_SUBSCRIPTION'

    def __init__(self, *args, **kwargs):
        kodigui.BaseWindow.__init__(self, *args, **kwargs)
        self.title = T(32113)
        self.message = u'{0}[CR]{1}'.format(T(32114), T(32115))


class GuideWindow(kodigui.BaseWindow):
    name = 'GUIDE'
    xmlFile = 'script-tablo-guide.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    emptyMessage = (T(32116),)
    emptyMessageTVShows = (T(32117),)
    emptyMessageMovies = (T(32118),)
    emptyMessageSports = (T(32119),)

    types = (
        (None, T(32120)),
        ('SERIES', T(32121)),
        ('MOVIES', T(32122)),
        ('SPORTS', T(32123))
    )

    MENU_GROUP_ID = 100
    MENU_LIST_ID = 200
    SHOW_GROUP_ID = 300
    SHOW_PANEL_ID = 301
    KEY_LIST_ID = 400

    view = 'guide'
    state = None
    section = T(32124)

    def onFirstInit(self):
        self._showingDialog = False
        self.filter = None

        self.typeList = kodigui.ManagedControlList(self, self.MENU_LIST_ID, 3)
        self.showList = kodigui.ManagedControlList(self, self.SHOW_PANEL_ID, 11)
        self.keysList = kodigui.ManagedControlList(self, self.KEY_LIST_ID, 10)
        self.keys = {}
        self.lastKey = None
        self.lastSelectedKey = None
        self.showItems = {}

        self.setFilter(None)

        self.delayedShowUpdater = DelayedShowUpdater(self)

        self._tasks = []

        self.fillTypeList()

        self.onReInit()

    def onReInit(self):
        self.setFilter()

        if not self._showingDialog and not WM.windowWasLast(self):
            self.fillShows()

        self.onWindowFocus()

    def onWindowFocus(self):
        if self.getProperty('hide.menu'):
            self.setShowFocus()

    def onAction(self, action):
        try:
            self.updateKey(action)

            if action == xbmcgui.ACTION_NAV_BACK or action == xbmcgui.ACTION_PREVIOUS_MENU:
                if xbmc.getCondVisibility('ControlGroup({0}).HasFocus(0)'.format(self.MENU_GROUP_ID)) or self.getProperty('hide.menu'):
                    WM.showMenu()
                    return
                else:
                    self.setFocusId(self.MENU_GROUP_ID)
                    return
            elif self.getFocusId() == self.SHOW_PANEL_ID:
                if action in (xbmcgui.ACTION_MOVE_UP, xbmcgui.ACTION_MOVE_DOWN, xbmcgui.ACTION_MOVE_LEFT, xbmcgui.ACTION_MOVE_RIGHT):
                    self.updateSelected()
            elif action == xbmcgui.ACTION_MOVE_RIGHT and self.getFocusId() == self.MENU_LIST_ID:
                self.onClick(self.MENU_LIST_ID)
        except:
            util.ERROR()

        kodigui.BaseWindow.onAction(self, action)

    def onClick(self, controlID):
        if controlID == self.MENU_LIST_ID:
            item = self.typeList.getSelectedItem()
            if item:
                if self.setFilter(item.dataSource) or not xbmc.getCondVisibility('Control.IsVisible(601)'):
                    self.fillShows(reset=True)

            self.setShowFocus()

        elif controlID == self.SHOW_PANEL_ID:
            self.showClicked()
        elif controlID == self.KEY_LIST_ID:
            self.setFocusId(self.SHOW_PANEL_ID)

    def onFocus(self, controlID):
        if controlID == 50:
            self.setFocusId(self.MENU_GROUP_ID)
            WM.showMenu()
            return
        elif controlID == self.SHOW_PANEL_ID:
            self.updateKey()

    def doClose(self):
        kodigui.BaseWindow.doClose(self)
        self.cancelTasks()

    def setShowFocus(self):
        xbmc.sleep(100)  # Give window states time to adjust
        if xbmc.getCondVisibility('Control.IsVisible(301)'):
            self.setFocusId(self.SHOW_GROUP_ID)
        else:
            if self.getFocusId() != self.SHOW_PANEL_ID:
                self.setFocusId(51)

    def updateSelected(self):
        item = self.showList.getSelectedItem()
        if not item:
            return

        if not item.dataSource.get('show'):
            self.getSingleShowData(item.dataSource['path'])

    @base.dialogFunction
    def showClicked(self):
        item = self.showList.getSelectedItem()
        if not item:
            return

        show = item.dataSource.get('show')

        if not show:
            self.getSingleShowData(item.dataSource['path'])
            while not show and backgroundthread.BGThreader.working() and not xbmc.abortRequested:
                xbmc.sleep(100)
                show = item.dataSource.get('show')
        if self.closing():
            return

        GuideShowWindow.open(show=show)

        self.updateShowItem(show)

    def setFilter(self, filter_=False):
        if filter_ is False:
            filter_ = self.filter

        ret = True
        if filter_ == self.filter:
            ret = False

        self.filter = filter_

        util.setGlobalProperty('section', self.section)
        util.setGlobalProperty('guide.filter', [t[1] for t in self.types if t[0] == filter_][0])

        return ret

    def updateKey(self, action=None):
        if not action or self.getFocusId() == self.SHOW_PANEL_ID:
            item = self.showList.getSelectedItem()
            if not item:
                return

            key = item.getProperty('key')
            if key == self.lastKey or not key:
                return
            self.lastKey = key

            self.keysList.selectItem(self.keys[key])
        elif self.getFocusId() == self.KEY_LIST_ID:
            if action == xbmcgui.ACTION_PAGE_DOWN or action == xbmcgui.ACTION_PAGE_UP:
                if self.lastSelectedKey:
                    self.keysList.selectItem(self.keys[self.lastSelectedKey])
                return

            item = self.keysList.getSelectedItem()

            if not item:
                return

            if not item.getProperty('has.contents'):
                pos = item.pos()

                if action == xbmcgui.ACTION_MOVE_DOWN or action == xbmcgui.ACTION_PAGE_DOWN:
                    for i in range(pos + 1, len(self.keysList)):
                        item = self.keysList[i]
                        if item.getProperty('has.contents'):
                            self.keysList.selectItem(item.pos())
                            break
                    else:
                        self.keysList.selectItem(self.keys[self.lastSelectedKey])
                        return
                elif action == xbmcgui.ACTION_MOVE_UP or action == xbmcgui.ACTION_PAGE_UP:
                    for i in range(pos - 1, -1, -1):
                        item = self.keysList[i]
                        if item.getProperty('has.contents'):
                            self.keysList.selectItem(item.pos())
                            break
                    else:
                        self.keysList.selectItem(self.keys[self.lastSelectedKey])
                        return
                else:
                    return

            key = item.getProperty('key')
            if key == self.lastSelectedKey:
                return

            self.lastSelectedKey = key
            for i in self.showList:
                if i.getProperty('key') == key:
                    self.showList.selectItem(i.pos())
                    return

    def fillTypeList(self):
        items = []
        for ID, label in self.types:
            items.append(kodigui.ManagedListItem(label, data_source=ID))

        self.typeList.addItems(items)

        self.setFocusId(self.MENU_GROUP_ID)

    def cancelTasks(self):
        if not self._tasks:
            return

        util.DEBUG_LOG('Canceling {0} tasks ({1})'.format(len(self._tasks), self.name))
        for t in self._tasks:
            t.cancel()
        self._tasks = []

    def getSingleShowData(self, path):
        t = ShowsTask()
        self._tasks.append(t)
        t.setup([path], self.updateShowItem)
        backgroundthread.BGThreader.addTasks([t])

    def getShowData(self, paths):
        self.cancelTasks()

        while paths:
            current50 = paths[:50]
            paths = paths[50:]
            t = ShowsTask()
            self._tasks.append(t)
            t.setup(current50, self.updateShowItem)

        backgroundthread.BGThreader.addTasks(self._tasks)

    def updateShowItem(self, show):
        self.setProperty('busy', '')

        if not show:
            return

        if show.path not in self.showItems:
            return

        item = self.showItems[show.path]
        key = item.dataSource['key']
        item.dataSource['show'] = show
        item.setLabel(show.title)
        item.setThumbnailImage(show.thumb)
        item.setProperty('background', show.background)
        item.setProperty('key', key)
        item.setProperty('no.title', not show.thumbHasTitle and '1' or '')

        if show.showCounts and show.showCounts.get('conflicted_count'):
            item.setProperty('badge', 'guide/guide_badge_conflict_hd.png')
            item.setProperty('badge.count', '')
        elif show.scheduleRule:
            if show.scheduleRule == 'conflict':
                item.setProperty('badge', 'guide/guide_badge_conflict_hd.png')
            else:
                if show.type == 'PROGRAM':
                    item.setProperty('badge', 'guide/guide_badge_scheduled_program_hd.png')
                else:
                    item.setProperty('badge', 'guide/guide_badge_scheduled_hd.png')
            item.setProperty('badge.count', '')
        elif show.showCounts and show.showCounts.get('scheduled_count'):
            if show.type == 'PROGRAM':
                item.setProperty('badge', 'guide/guide_badge_recurring_program_hd.png')
            else:
                item.setProperty('badge', 'guide/guide_badge_recurring_hd.png')
            item.setProperty('badge.count', str(show.showCounts.get('scheduled_count')))
        elif show.showCounts and show.showCounts.get('unwatched_count'):
            item.setProperty('badge', 'recordings/recordings_badge_unwatched_hd.png')
            item.setProperty('badge.count', str(show.showCounts.get('unwatched_count')))
        else:
            item.setProperty('badge', '')
            item.setProperty('badge.count', '')

    @base.tabloErrorHandler
    def fillShows(self, reset=False, clear=False):
        self.setProperty('show.recent', '')
        self.cancelTasks()

        self.setProperty('busy', '1')

        self.lastKey = None

        lastPath = None
        selectItem = None
        lastPos = None

        if not reset:
            currentItem = self.showList.getSelectedItem()
            if currentItem:
                lastPath = currentItem.dataSource['path']
                lastPos = currentItem.pos()

        self.showItems = {}

        if clear:
            self.showList.reset()
            self.keysList.reset()

        args = {}
        if self.state:
            args = {'state': self.state}

        try:
            if self.filter == 'SERIES':
                keys = tablo.API.views(self.view).series.get(**args)
            elif self.filter == 'MOVIES':
                keys = tablo.API.views(self.view).movies.get(**args)
            elif self.filter == 'SPORTS':
                keys = tablo.API.views(self.view).sports.get(**args)
            elif self.filter == 'MANUAL':
                keys = tablo.API.views(self.view).programs.get(**args)
            else:
                keys = tablo.API.views(self.view).shows.get(**args)
        except tablo.ConnectionError:
            self.setProperty('busy', '')
            msg = T(32125).format(tablo.API.device.displayName)
            self.showList.reset()
            self.keysList.reset()
            self.setProperty('empty.message', msg)
            # xbmcgui.Dialog().ok('Connection Failure', msg)
            return
        except:
            msg = util.ERROR()
            self.showList.reset()
            self.keysList.reset()
            self.setProperty('busy', '')
            self.setProperty('empty.message', u'{0}: {1}'.format(T(32126), msg))
            xbmcgui.Dialog().ok(T(32126), u'{0}: {1}'.format(T(32126), msg))
            return

        paths = []

        keyitems = []
        items = []
        ct = 0
        for i, k in enumerate(keys):
            key = k['key']
            keyitem = kodigui.ManagedListItem(key.upper())
            keyitem.setProperty('key', key)
            self.lastSelectedKey = self.lastSelectedKey or key

            if k.get('contents'):
                keyitem.setProperty('has.contents', '1')
                for p in k['contents']:
                    ct += 1
                    paths.append(p)
                    item = kodigui.ManagedListItem(data_source={'path': p, 'key': key, 'show': None})
                    if p == lastPath:
                        selectItem = item
                    item.setProperty('key', key)
                    if ct > 6:
                        item.setProperty('after.firstrow', '1')
                    self.showItems[p] = item
                    items.append(item)

            keyitems.append(keyitem)
            self.keys[k['key']] = i

        self.showList.reset()
        self.keysList.reset()

        self.keysList.addItems(keyitems)
        self.showList.addItems(items)

        if selectItem:
            self.showList.selectItem(selectItem.pos())
        elif lastPos:
            if self.showList.positionIsValid(lastPos):
                self.showList.selectItem(lastPos)
            else:
                if lastPos > 0:
                    self.showList.selectItem(self.showList.size() - 1)  # Select last item

        if items:
            self.setProperty('empty.message', '')
            self.setProperty('empty.message2', '')

            if self.getFocusId() in (51, 400):
                self.setFocusId(self.SHOW_PANEL_ID)
        else:
            self.setProperty('busy', '')
            if self.filter == 'SERIES':
                message = self.emptyMessageTVShows
            elif self.filter == 'MOVIES':
                message = self.emptyMessageMovies
            elif self.filter == 'SPORTS':
                message = self.emptyMessageSports
            else:
                message = self.emptyMessage

            self.setProperty('empty.message', message[0])
            if len(message) > 1:
                self.setProperty('empty.message2', message[1])

        self.getShowData(paths)

        self.updateKey()


class AiringsTask(backgroundthread.Task):
    def setup(self, paths, callback, airing_type):
        self.paths = paths
        self.callback = callback
        self.airingType = airing_type

    def run(self):
        airings = tablo.API.batch.post(self.paths)
        if self.isCanceled():
            return

        util.DEBUG_LOG('Retrieved {0} airings'.format(len(airings)))
        for path, airing in airings.items():
            if self.isCanceled():
                return
            if not airing:
                continue

            self.callback(tablo.Airing(airing, self.airingType))


class GuideShowWindow(kodigui.BaseWindow):
    name = 'GUIDE'
    xmlFile = 'script-tablo-show.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'

    SHOW_BUTTONS_GROUP_ID = 100
    AIRINGS_BUTTON_ID = 400
    SCHEDULE_BUTTON_ID = 401
    AIRINGS_LIST_ID = 300

    SCHEDULE_GROUP_ID = 500
    SCHEDULE_BUTTON_TOP_ID = 501
    SCHEDULE_BUTTON_BOT_ID = 502

    sectionAction = 'Schedule...'

    EMPTY_MESSAGES = {
        'SERIES': (T(32127), T(32130)),
        'MOVIE': (T(32128), T(32131)),
        'PROGRAM': (T(32128), T(32132)),
        'SPORT': (T(32129), T(32133)),
        None: ('', '')

    }

    def __init__(self, *args, **kwargs):
        kodigui.BaseWindow.__init__(self, *args, **kwargs)
        self._show = kwargs.get('show')
        self.scheduleButtonActions = {}
        self.modified = False

    def onFirstInit(self):
        self._tasks = []
        self.seasonCount = 0
        self.airingItems = {}

        self.setProperty('thumb', self._show.thumb)
        self.setProperty('background', self._show.background)
        self.setProperty('title', self._show.title)
        self.setProperty('plot', self._show.plot or self._show.description)
        self.setProperty('section.action', self.sectionAction)
        self.setProperty('is.movie', self._show.type == 'MOVIE' and '1' or '')
        self.setProperty('dialog.top.color', '52FFFFFF')
        self.setProperty('schedule.top.color', '52FFFFFF')

        self.setAiringLabel()

        if self._show.type == 'MOVIE' and self._show.quality_rating:
            info = []
            if self._show.film_rating:
                info.append(self._show.film_rating.upper())
            if self._show.release_year:
                info.append(str(self._show.release_year))

            self.setProperty('info', u' / '.join(info) + u' / ')
            self.setProperty('stars', str(self._show.quality_rating / 2))
            self.setProperty('half.star', str(self._show.quality_rating % 2))
        elif self._show.type == 'SPORT':
            if self._show.showCounts.get('airing_count'):
                self.setProperty(
                    'info', '{0} {1}'.format(self._show.showCounts['airing_count'], self._show.showCounts['airing_count'] > 1 and T(32139) or T(32138))
                )
            self.setProperty('plot', self._show.title)

        self.airingsList = kodigui.ManagedControlList(self, self.AIRINGS_LIST_ID, 20)

        self.setupScheduleDialog()
        self.fillAirings()

        if self._show.type == 'SERIES':
            info = []
            if self.seasonCount:
                info.append('{0} {1}'.format(self.seasonCount, self.seasonCount > 1 and T(32135) or T(32134)))
            if self._show.showCounts.get('airing_count'):
                info.append('{0} {1}'.format(self._show.showCounts['airing_count'], self._show.showCounts['airing_count'] > 1 and T(32137) or T(32136)))

            self.setProperty('info', u' / '.join(info))

    def onClick(self, controlID):
        if controlID == self.AIRINGS_LIST_ID:
            self.airingsListClicked()
        elif self.SCHEDULE_BUTTON_TOP_ID <= controlID <= self.SCHEDULE_BUTTON_BOT_ID:
            self.scheduleButtonClicked(controlID)

    def onAction(self, action):
        controlID = self.getFocusId()

        try:
            if action == xbmcgui.ACTION_NAV_BACK or action == xbmcgui.ACTION_PREVIOUS_MENU:
                if xbmc.getCondVisibility('ControlGroup({0}).HasFocus(0)'.format(self.SCHEDULE_GROUP_ID)):
                    self.setFocusId(self.SHOW_BUTTONS_GROUP_ID)
                else:
                    self.doClose()
                return
            elif controlID == self.AIRINGS_LIST_ID:
                self.updateAiringSelection(action)
            elif action == xbmcgui.ACTION_PAGE_DOWN:
                if xbmc.getCondVisibility('ControlGroup(100).HasFocus(0)'):
                    xbmc.executebuiltin('Action(down)')
        except:
            util.ERROR()

        kodigui.BaseWindow.onAction(self, action)

    def doClose(self):
        self.setProperty('busy', '')
        kodigui.BaseWindow.doClose(self)
        self.cancelTasks()

    def scheduleButtonClicked(self, controlID):
        action = self.scheduleButtonActions.get(controlID)
        if not action:
            return
        self.setProperty('action.busy', '1')
        self.modified = True
        try:
            self._show.schedule(action)
        finally:
            self.setProperty('action.busy', '')

        for item in self.airingsList:
            if item.dataSource.get('airing'):
                grid.addPending(airing=item.dataSource['airing'])

        self.setupScheduleDialog()
        self.updateAirings()

    def setEmptyMessage(self, clear=False):
        emptyMessages = not clear and self.EMPTY_MESSAGES.get(self._show.type) or self.EMPTY_MESSAGES[None]
        self.setProperty('empty.message', emptyMessages[0])
        self.setProperty('empty.message2', emptyMessages[1])

    def setAiringLabel(self):
        self.setProperty('airing.label', util.LOCALIZED_AIRING_TYPES_PLURAL[self._show.type])

    def setDialogButtons(self, airing, arg_dict):
        if airing.airingNow():
            arg_dict['button1'] = ('watch', T(32140))
            button = 'button2'
        else:
            button = 'button1'

        if airing.conflicted:
            arg_dict[button] = ('unschedule', T(32141).format(util.LOCALIZED_AIRING_TYPES[self._show.type]))
            arg_dict['title_indicator'] = 'indicators/conflict_pill_hd.png'
        elif airing.scheduled:
            arg_dict[button] = ('unschedule', T(32141).format(util.LOCALIZED_AIRING_TYPES[self._show.type]))
            arg_dict['title_indicator'] = 'indicators/rec_pill_hd.png'
        else:
            arg_dict[button] = ('record', T(32142).format(util.LOCALIZED_AIRING_TYPES[self._show.type]))

    def airingsListClicked(self, item=None, get_args_only=False):
        item = item or self.airingsList.getSelectedItem()
        if not item:
            return

        airing = item.dataSource.get('airing')

        while not airing and backgroundthread.BGThreader.working() and not xbmc.abortRequested:
            xbmc.sleep(100)
            airing = item.dataSource.get('airing')

        if not airing:
            util.DEBUG_LOG('GuideShowWindow.airingsListClicked(): Failed to get airing!')
            return

        info = T(32143).format(
            airing.displayChannel(),
            airing.network,
            airing.displayDay(),
            airing.displayTimeStart(),
            airing.displayTimeEnd()
        )

        kwargs = {
            'number': airing.number,
            'background': self._show.background,
            'callback': self.actionDialogCallback,
            'obj': airing,
            'start_indicator1': 'new' in airing.qualifiers and 'indicators/qualifier_new_hd.png' or '',
            'start_indicator2': 'live' in airing.qualifiers and 'indicators/qualifier_live_hd.png' or ''
        }

        self.setDialogButtons(airing, kwargs)

        if airing.ended():
            secs = airing.secondsSinceEnd()
            start = T(32144).format(util.durationToText(secs))
            kwargs['button1'] = None
            kwargs['button2'] = None
        else:
            secs = airing.secondsToStart()

            if secs < 1:
                start = T(32145).format(util.durationToText(secs * -1))
            else:
                start = T(32146).format(util.durationToText(secs))

        kwargs['item_count'] = len(self.airingItems)
        kwargs['item_pos'] = int(item.getProperty('pos'))

        if airing.type == 'schedule':
            description = self._show.plot or self._show.description
        else:
            description = airing.description

        if get_args_only:
            kwargs['title'] = airing.title or self._show.title
            kwargs['info'] = info
            kwargs['plot'] = description
            kwargs['start'] = start
            return kwargs

        pos = actiondialog.openDialog(
            airing.title or self._show.title,
            info,
            description,
            start,
            **kwargs
        )

        if isinstance(pos, int):
            item = self.getItemByPos(pos)
            if item:
                self.airingsList.selectItem(item.pos())

        self.updateIndicators()

    def getItemByPos(self, pos):
        for item in self.airingsList:
            if item.getProperty('pos') == str(pos):
                return item

        return None

    def updateActionDialog(self, pos):
        item = self.getItemByPos(pos)
        if not item:
            return

        kwargs = self.airingsListClicked(item=item, get_args_only=True)
        if not kwargs:
            return

        self.setDialogButtons(kwargs['obj'], kwargs)

        return kwargs

    def actionDialogCallback(self, obj, action):
        airing = obj
        changes = {}

        if action:
            if action == 'CHANGE.ITEM':
                return self.updateActionDialog(obj)
            elif action == 'watch':
                player.PLAYER.playAiringChannel(airing.gridAiring or airing)
            elif action == 'record':
                self.modified = True
                airing.schedule()
                self._show.update()
                grid.addPending(airing=airing)
            elif action == 'unschedule':
                self.modified = True
                airing.schedule(False)
                self._show.update()
                grid.addPending(airing=airing)

        self.setDialogButtons(airing, changes)

        if airing.ended():
            secs = airing.secondsSinceEnd()
            changes['start'] = T(32144).format(util.durationToText(secs))
            changes['button1'] = None
            changes['button2'] = None
        else:
            secs = airing.secondsToStart()

            if secs < 1:
                start = T(32145).format(util.durationToText(secs * -1))
            else:
                start = T(32146).format(util.durationToText(secs))

            changes['start'] = start

        return changes

    def updateAiringSelection(self, action=None):
        item = self.airingsList.getSelectedItem()
        if not item:
            return

        if item.getProperty('header'):
            pos = item.pos()
            if action == xbmcgui.ACTION_MOVE_UP or action == xbmcgui.ACTION_PAGE_UP:
                if pos < 2:
                    self.airingsList.selectItem(0)
                    self.setFocusId(self.AIRINGS_BUTTON_ID)
                    return

                for i in range(pos - 1, 0, -1):
                    nextItem = self.airingsList.getListItem(i)
                    if not nextItem.getProperty('header'):
                        self.airingsList.selectItem(nextItem.pos())
                        return
            else:  # action == xbmcgui.ACTION_MOVE_DOWN or action == xbmcgui.ACTION_PAGE_DOWN:
                for i in range(pos + 1, self.airingsList.size()):
                    nextItem = self.airingsList.getListItem(i)
                    if not nextItem.getProperty('header'):
                        self.airingsList.selectItem(nextItem.pos())
                        return

    def cancelTasks(self):
        if not self._tasks:
            return

        util.DEBUG_LOG('Canceling {0} show tasks'.format(len(self._tasks)))
        for t in self._tasks:
            t.cancel()
        self._tasks = []

    def getAiringData(self, paths):
        self.cancelTasks()

        while paths:
            current50 = paths[:50]
            paths = paths[50:]
            t = AiringsTask()
            self._tasks.append(t)
            t.setup(current50, self.updateAiringItem, self._show.airingType)

        backgroundthread.BGThreader.addTasks(self._tasks)

    def updateItemIndicators(self, item):
        airing = item.dataSource['airing']
        if not airing:
            return

        if airing.scheduled:
            item.setProperty('badge', 'livetv/livetv_badge_scheduled_hd.png')
        elif airing.conflicted:
            item.setProperty('badge', 'livetv/livetv_badge_conflict_hd.png')
        else:
            item.setProperty('badge', '')

    def updateIndicators(self):
        for item in self.airingsList:
            self.updateItemIndicators(item)

    def updateAiringItem(self, airing):
        item = self.airingItems[airing.path]
        item.setProperty('disabled', '')
        item.dataSource['airing'] = airing

        if airing.type == 'schedule':
            label = self._show.title
        else:
            label = airing.title

        if not label:
            label = T(32147).format(
                airing.displayChannel(),
                airing.network,
                airing.displayTimeStart(),
                airing.displayTimeEnd()
            )

        item.setLabel(label)
        item.setLabel2(airing.displayDay())
        item.setProperty('number', str(airing.number or ''))
        item.setProperty('airing', airing.airingNow() and '1' or '')
        if 'new' in airing.qualifiers:
            item.setProperty('qualifier', 'indicators/qualifier_new_hd')
        else:
            item.setProperty('qualifier', 'live' in airing.qualifiers and 'indicators/qualifier_live_hd' or '')

        self.updateItemIndicators(item)

    def setupScheduleDialog(self):
        self.scheduleButtonActions = {}

        if self._show.type == 'PROGRAM':
            self.setProperty(
                'schedule.message', T(32148)
            )

            if self._show.scheduleRule == 'all':
                self.scheduleButtonActions[self.SCHEDULE_BUTTON_TOP_ID] = 'none'
                self.scheduleButtonActions[self.SCHEDULE_BUTTON_BOT_ID] = None
                self.setProperty('schedule.top.color', '52FFFFFF')
                self.setProperty('schedule.top', T(32150))
                self.setProperty('schedule.bottom', T(32149))
                self.setProperty('title.indicator', 'indicators/rec_all_pill_hd.png')
            else:
                self.scheduleButtonActions[self.SCHEDULE_BUTTON_TOP_ID] = 'all'
                self.scheduleButtonActions[self.SCHEDULE_BUTTON_BOT_ID] = None
                self.setProperty('schedule.top.color', '52FFFFFF')
                self.setProperty('schedule.top', T(32151))
                self.setProperty('schedule.bottom', T(32149))
                self.setProperty('title.indicator', '')
        else:
            self.setProperty(
                'schedule.message', T(32152).format(
                    util.LOCALIZED_AIRING_TYPES_PLURAL[self._show.type].lower(),
                    util.LOCALIZED_SHOW_TYPES[self._show.type].lower(),
                )
            )

            if self._show.scheduleRule == 'all':
                self.scheduleButtonActions[self.SCHEDULE_BUTTON_TOP_ID] = 'none'
                self.scheduleButtonActions[self.SCHEDULE_BUTTON_BOT_ID] = 'new'
                self.setProperty('schedule.top.color', '52FFFFFF')
                self.setProperty('schedule.top', T(32153))
                self.setProperty('schedule.bottom', T(32154))
                self.setProperty('title.indicator', 'indicators/rec_all_pill_hd.png')
            elif self._show.scheduleRule == 'new':
                self.scheduleButtonActions[self.SCHEDULE_BUTTON_TOP_ID] = 'none'
                self.scheduleButtonActions[self.SCHEDULE_BUTTON_BOT_ID] = 'all'
                self.setProperty('schedule.top.color', '52FFFFFF')
                self.setProperty('schedule.top', T(32153))
                self.setProperty('schedule.bottom', T(32151))
                self.setProperty('title.indicator', 'indicators/rec_new_pill_hd.png')
            else:
                self.scheduleButtonActions[self.SCHEDULE_BUTTON_TOP_ID] = 'all'
                self.scheduleButtonActions[self.SCHEDULE_BUTTON_BOT_ID] = 'new'
                self.setProperty('schedule.top.color', '52FFFFFF')
                self.setProperty('schedule.top', T(32151))
                self.setProperty('schedule.bottom', T(32154))
                self.setProperty('title.indicator', '')

    def updateAirings(self):
        self.getAiringData(self.airingItems.keys())

    @util.busyDialog
    @base.tabloErrorHandler
    def fillAirings(self):
        self.setEmptyMessage(clear=True)
        self.airingsList.reset()
        self.airingItems = {}
        airings = []
        airingIDX = 0

        if isinstance(self._show, tablo.Series):
            seasons = self._show.seasons()
            if seasons:
                seasonsData = tablo.API.batch.post(seasons)

            first = True
            for seasonPath in seasons:
                self.seasonCount += 1
                season = seasonsData[seasonPath]

                number = season['season']['number']
                title = number and T(32155).format(number) or T(32156)

                item = kodigui.ManagedListItem('', data_source={'path': None, 'airing': None})
                item.setProperty('header', '1')
                self.airingsList.addItem(item)

                item = kodigui.ManagedListItem(title, data_source={'path': None, 'airing': None})
                item.setProperty('header', '1')
                item.setProperty('top', '1')
                self.airingsList.addItem(item)

                seasonEps = tablo.API(seasonPath).episodes.get()
                airings += seasonEps
                for p in seasonEps:
                    item = kodigui.ManagedListItem('', data_source={'path': p, 'airing': None})
                    item.setProperty('pos', str(airingIDX))
                    airingIDX += 1
                    if first:
                        first = False
                        item.setProperty('top', '1')
                    self.airingItems[p] = item
                    self.airingsList.addItem(item)
        else:
            airings = self._show.airings()

            item = kodigui.ManagedListItem('', data_source={'path': None, 'airing': None})
            item.setProperty('header', '1')
            self.airingsList.addItem(item)

            first = True
            for p in airings:
                item = kodigui.ManagedListItem('', data_source={'path': p, 'airing': None})
                item.setProperty('pos', str(airingIDX))
                airingIDX += 1
                if first:
                    first = False
                    item.setProperty('top', '1')
                self.airingItems[p] = item
                self.airingsList.addItem(item)

        if not self.airingItems:
            self.setEmptyMessage()

        self.getAiringData(airings)
