import time
import xbmc
import xbmcgui
import kodigui
import base
import actiondialog

from lib import util
from lib import backgroundthread
from lib import player
from lib import tablo
from lib.util import T

import guide


RECORDING_FAILED_MESSAGES = {
    "no_hard_drive": T(32162),
    "full_hard_drive": T(32163),
    "no_tuner_available": T(32164),
    "weak_signal": T(32165),
    "internal_error": T(32166),
    None: T(32167)
}


class RecordingShowBase:
    def setDialogIndicators(self, airing, show, arg_dict):
        if airing.type == 'schedule':
            description = show.description or ''
        else:
            description = airing.description or ''

        failed = airing.data['video_details']['state'] == 'failed'

        if failed:
            msg = RECORDING_FAILED_MESSAGES.get(airing.data['video_details']['error']['details'], RECORDING_FAILED_MESSAGES.get(None))
            description += u'[CR][CR][COLOR FFC81010]{0}[/COLOR]'.format(msg)
        else:
            if airing.watched:
                arg_dict['indicator'] = ''
            else:
                if airing.data['user_info']['position']:
                    arg_dict['indicator'] = 'indicators/seen_partial_hd.png'
                else:
                    arg_dict['indicator'] = 'indicators/seen_unwatched_hd.png'

            if airing.data['user_info']['position'] and not airing.recording():
                left = airing.data['video_details']['duration'] - airing.data['user_info']['position']
                total = airing.data['video_details']['duration']
                description += u'[CR][CR]{0}'.format(T(32168)).format(util.durationToText(left), util.durationToText(total))
                arg_dict['seenratio'] = airing.data['user_info']['position'] / float(total)
                arg_dict['seen'] = airing.data['user_info']['position']
            else:
                if airing.recording():
                    description += u'[CR][CR]{1}'.format(T(32169))
                    if airing.data['user_info']['position']:
                        arg_dict['seen'] = airing.data['user_info']['position']
                else:
                    description += '[CR][CR]{0}: {1}'.format(T(32170), util.durationToText(airing.data['video_details']['duration']))
                    arg_dict['seen'] = None

                arg_dict['seenratio'] = None

        arg_dict['plot'] = description

    def airingsListClicked(self, item=None, get_args_only=False):
        item = item or self.airingsList.getSelectedItem()
        if not item:
            return

        airing = item.dataSource.get('airing')

        if airing and airing.deleted:
            if get_args_only:
                return {'SKIP': True}
            return

        while not airing and backgroundthread.BGThreader.working() and not xbmc.abortRequested:
            xbmc.sleep(100)
            airing = item.dataSource.get('airing')

        show = self._show or airing.getShow()

        info = T(32143).format(
            airing.displayChannel(),
            airing.network,
            airing.displayDay(),
            airing.displayTimeStart(),
            airing.displayTimeEnd()
        )

        kwargs = {
            'background': show.background,
            'callback': self.actionDialogCallback,
            'obj': airing,
            'show': show
        }

        if airing.type == 'schedule':
            title = show.title
        else:
            title = airing.title or show.title

        failed = airing.data['video_details']['state'] == 'failed'

        self.setDialogIndicators(airing, show, kwargs)

        if hasattr(self, 'airingItems'):
            kwargs['item_count'] = len(self.airingItems)
            kwargs['item_pos'] = int(item.getProperty('pos'))

        if get_args_only:
            kwargs['title'] = title
            kwargs['info'] = info
            kwargs['preview'] = airing.snapshot
            kwargs['failed'] = failed
            kwargs['button2'] = airing.watched and T(32171) or T(32172)
            kwargs['button3'] = airing.protected and T(32173) or T(32174)
            return kwargs

        pos = openDialog(
            title,
            info,
            airing.snapshot,
            failed,
            airing.watched and T(32171) or T(32172),
            airing.protected and T(32173) or T(32174),
            **kwargs
        )

        if isinstance(pos, int):
            item = self.getItemByPos(pos)
            if item:
                self.airingsList.selectItem(item.pos())

        self.updateIndicators()

    def updateActionDialog(self, pos):
        item = self.getItemByPos(pos)
        if not item:
            return

        kwargs = self.airingsListClicked(item=item, get_args_only=True)
        if not kwargs:
            return

        return kwargs

    def actionDialogCallback(self, obj, action):
        airing = obj
        changes = {}

        if action:
            if action == 'CHANGE.ITEM':
                return self.updateActionDialog(obj)
            elif action in ('watch', 'resume'):
                try:
                    show = self._show or airing.getShow()
                except:
                    show = None

                if airing.recording():
                    player.PLAYER.playLiveRecording(airing, show=show, resume=action == 'resume')
                else:
                    player.PLAYER.playRecording(airing, show=show, resume=action == 'resume')
            elif action == 'toggle':
                airing.markWatched(not airing.watched)
                self.modified = True
            elif action == 'protect':
                airing.markProtected(not airing.protected)
            elif action == 'delete':
                self.modified = True
                airing.delete()
                return None
            if action == 'toggle':
                changes['button2'] = airing.watched and T(32171) or T(32172)
            elif action == 'protect':
                changes['button3'] = airing.protected and T(32173) or T(32174)

            self.setDialogIndicators(airing, self._show, changes)

        return changes

    def updateItemIndicators(self, item):
        airing = item.dataSource['airing']
        if not airing:
            return

        if airing.data['video_details']['state'] == 'failed':
            item.setProperty('indicator', 'recordings/recording_failed_small_dark_hd.png')
        elif airing.watched:
            item.setProperty('indicator', '')
        else:
            if airing.data['user_info']['position']:
                item.setProperty('indicator', 'recordings/seen_small_partial_hd.png')
            else:
                item.setProperty('indicator', 'recordings/seen_small_unwatched_hd.png')

        item.setProperty('protected', airing.protected and '1' or '')
        if not airing.protected:
            self.setProperty('section.action.disabled', '')

        if airing.deleted:
            item.setProperty('disabled', '1')

    def updateIndicators(self):
        self.setProperty('section.action.disabled', '1')
        for item in self.airingsList:
            self.updateItemIndicators(item)

    def getAiringItem(self, airing):
        return self.airingItems[airing.path]

    def updateAiringItem(self, airing):
        item = self.getAiringItem(airing)

        item.dataSource['airing'] = airing
        show = self._show or airing.getShow()

        self.setProperty('busy', '')

        if airing.type == 'schedule':
            label = show.title
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
        item.setThumbnailImage(show.thumb)
        item.setProperty('show.title', show.title)

        if airing.recording():
            item.setProperty('duration', T(32169))
        else:
            item.setProperty('duration', util.durationToText(airing.data['video_details']['duration']))

        self.updateItemIndicators(item)


class RecordingsWindow(guide.GuideWindow, RecordingShowBase):
    name = 'RECORDINGS'
    view = 'recordings'
    section = T(32175)

    types = (
        (None, T(32120)),
        ('RECENT', T(32176)),
        ('SERIES', T(32121)),
        ('MOVIES', T(32122)),
        ('SPORTS', T(32123)),
        ('MANUAL', T(32177))
    )

    emptyMessage = (T(32178), T(32183))
    emptyMessageTVShows = (T(32179), T(32183))
    emptyMessageMovies = (T(32180), T(32183))
    emptyMessageSports = (T(32181), T(32183))
    emptyMessageProgram = (T(32182),)

    RECENT_LIST_ID = 500

    def onFirstInit(self):
        self._show = None  # Dummy for recent stuff
        self.airingsList = kodigui.ManagedControlList(self, self.RECENT_LIST_ID, 11)
        guide.GuideWindow.onFirstInit(self)

    def onAction(self, action):
        try:
            controlID = self.getFocusId()
            if controlID == self.RECENT_LIST_ID:
                if self.updateRecentSelection(action):
                    return
        except:
            util.ERROR()

        guide.GuideWindow.onAction(self, action)

    def onClick(self, controlID):
        if controlID == self.RECENT_LIST_ID:
            return self.showClicked()

        guide.GuideWindow.onClick(self, controlID)

    @base.dialogFunction
    def showClicked(self):
        if self.getFocusId() == self.RECENT_LIST_ID:
            return self.airingsListClicked()
        else:
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

        w = RecordingShowWindow.open(show=show)
        if w.modified:
            self.fillShows()
        del w

    def updateRecentSelection(self, action=None):
        item = self.airingsList.getSelectedItem()
        if not item:
            return False

        if item.getProperty('header'):
            pos = item.pos()
            if action == xbmcgui.ACTION_MOVE_UP or action == xbmcgui.ACTION_PAGE_UP:
                if pos < 1:
                    self.airingsList.selectItem(1)
                    return True

                for i in range(pos - 1, 0, -1):
                    nextItem = self.airingsList.getListItem(i)
                    if not nextItem.getProperty('header'):
                        self.airingsList.selectItem(nextItem.pos())
                        return True
            else:  # action == xbmcgui.ACTION_MOVE_DOWN or action == xbmcgui.ACTION_PAGE_DOWN:
                for i in range(pos + 1, self.airingsList.size()):
                    nextItem = self.airingsList.getListItem(i)
                    if not nextItem.getProperty('header'):
                        self.airingsList.selectItem(nextItem.pos())
                        return True
        else:
            return False

    def fillShows(self, reset=False):
        if self.filter == 'RECENT':
            return self.fillRecent()

        self.setProperty('show.recent', '')
        self.airingsList.reset()
        guide.GuideWindow.fillShows(self, reset=reset)

    @base.tabloErrorHandler
    def fillRecent(self):
        self.setProperty('show.recent', '1')
        self.showList.reset()
        self.airingsList.reset()
        self.showItems = {}
        airings = []

        self.setProperty('busy', '1')

        recentDates = tablo.API.views.recordings.recent.get()

        first = True
        now = time.localtime()
        for date in recentDates:
            tt = time.strptime(date['key'], '%Y-%m-%d')
            label = None
            if tt.tm_year == now.tm_year:
                if tt.tm_yday == now.tm_yday:
                    label = T(32184)
                elif tt.tm_yday == now.tm_yday - 1:
                    label = T(32185)
            label = label or time.strftime('%A, %B %d', tt)

            item = kodigui.ManagedListItem(label, data_source={'path': None, 'airing': None})
            item.setProperty('header', '1')
            item.setProperty('top', '1')
            if not first:
                item.setProperty('after.firstrow', '1')

            self.airingsList.addItem(item)

            for airingPath in date['contents']:
                airings.append(airingPath)
                item = kodigui.ManagedListItem('', data_source={'path': airingPath, 'airing': None})
                if first:
                    first = False
                    item.setProperty('top', '1')
                else:
                    item.setProperty('after.firstrow', '1')
                self.showItems[airingPath] = item
                self.airingsList.addItem(item)

        if self.airingsList.size():
            self.setProperty('empty.message', '')
            self.setProperty('empty.message2', '')

            if self.getFocusId() in (51, 400):
                self.setFocusId(self.RECENT_LIST_ID)

            self.getAiringData(airings)
        else:
            self.setProperty('busy', '')

            self.setProperty('empty.message', T(32186))

    def getAiringItem(self, airing):
        return self.showItems[airing.path]

    def getAiringData(self, paths):
        self.cancelTasks()

        while paths:
            current50 = paths[:50]
            paths = paths[50:]
            t = guide.AiringsTask()
            self._tasks.append(t)
            t.setup(current50, self.updateAiringItem, None)  # self._show.airingType)

        backgroundthread.BGThreader.addTasks(self._tasks)


class RecordingShowWindow(RecordingShowBase, guide.GuideShowWindow):
    sectionAction = T(32187)

    def setAiringLabel(self):
        self.setProperty('airing.label', util.LOCALIZED_RECORDING_TYPES_PLURAL[self._show.type])

    def scheduleButtonClicked(self, controlID):
        action = self.scheduleButtonActions.get(controlID)
        if not action or action != 'delete':
            return

        self.setProperty('action.busy', '1')
        try:
            self._show.deleteAll()
            # Check if we have protected airings. If so don't close
            for item in self.airingsList:
                airing = item.dataSource.get('airing')
                if not airing:
                    continue
                if not airing.deleted and airing.protected:
                    self.fillAirings()
                    break
            else:
                self.doClose()
        except tablo.APIError:
            util.ERROR()
        finally:
            self.setProperty('action.busy', '')

        self.modified = True

        self.updateIndicators()

    def setupScheduleDialog(self):
        self.setProperty(
            'schedule.message', T(32188).format(
                util.LOCALIZED_RECORDING_TYPES_PLURAL[self._show.type].lower()
            )
        )

        self.scheduleButtonActions = {}

        self.scheduleButtonActions[self.SCHEDULE_BUTTON_TOP_ID] = 'delete'
        self.scheduleButtonActions[self.SCHEDULE_BUTTON_BOT_ID] = 'cancel'
        self.setProperty('schedule.top.color', '52FF0000')
        self.setProperty('schedule.top', T(32189).format(util.LOCALIZED_RECORDING_TYPES_PLURAL[self._show.type]))
        self.setProperty('schedule.bottom', T(32149))
        # self.setProperty('title.indicator', 'indicators/rec_all_pill_hd.png')

    def fillAirings(self):
        self.setProperty('section.action.disabled', '1')
        guide.GuideShowWindow.fillAirings(self)
        self.setProperty('hide.menu', not self.airingsList.size() and '1' or '')


class RecordingDialog(actiondialog.ActionDialog):
    name = 'GUIDE'
    xmlFile = 'script-tablo-recording-action.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'

    BUTTONS_GROUP_ID = 399
    WATCH_BUTTON_ID = 400
    TOGGLE_BUTTON_ID = 401
    PROTECT_BUTTON_ID = 402
    DELETE_BUTTON_ID = 403

    DIALOG_GROUP_ID = 500
    DIALOG_TOP_BUTTON_ID = 501
    DIALOG_BOTTOM_BUTTON_ID = 502

    SEEN_PROGRESS_IMAGE_ID = 600
    SEEN_PROGRESS_WIDTH = 356

    def __init__(self, *args, **kwargs):
        actiondialog.ActionDialog.__init__(self, *args, **kwargs)
        util.CRON.registerReceiver(self)

    def init(self, kwargs):
        actiondialog.ActionDialog.init(self, kwargs)
        self.title = kwargs.get('title')
        self.info = kwargs.get('info')
        self.plot = kwargs.get('plot')
        self.preview = kwargs.get('preview', '')
        self.failed = kwargs.get('failed', '')
        self.indicator = kwargs.get('indicator', '')
        self.seen = kwargs.get('seen')
        self.seenratio = kwargs.get('seenratio')
        self.background = kwargs.get('background')
        self.callback = kwargs.get('callback')
        self.object = kwargs.get('obj')
        self._show = kwargs.get('show')
        self.button2 = kwargs.get('button2')
        self.button3 = kwargs.get('button3')
        self.action = None
        self.parentAction = None

    def onFirstInit(self):
        self.updateDisplayProperties()
        self.setPrevNextIndicators()

        self.setProperty('title', self.title)
        self.setProperty('info', self.info)
        self.setProperty('plot', self.plot)
        self.setProperty('preview', self.preview)
        self.setProperty('failed', self.failed and '1' or '')
        self.setProperty('seen', self.seenratio and '1' or '')
        self.setProperty('indicator', self.indicator)
        self.setProperty('background', self.background)
        self.setProperty('button2', self.button2)
        self.setProperty('button3', self.button3)

        if self.seenratio:
            self.getControl(self.SEEN_PROGRESS_IMAGE_ID).setWidth(int(self.seenratio * self.SEEN_PROGRESS_WIDTH))

        if self.failed:
            self.getControl(self.WATCH_BUTTON_ID).setEnabled(False)
            self.getControl(self.TOGGLE_BUTTON_ID).setEnabled(False)
            self.getControl(self.PROTECT_BUTTON_ID).setEnabled(False)
            self.setFocusId(self.DELETE_BUTTON_ID)
        else:
            self.setFocusId(self.WATCH_BUTTON_ID)

        self.setProperty('protected', self.object.protected and '1' or '')

        if self.object.protected:
            self.getControl(self.DELETE_BUTTON_ID).setEnabled(False)
        else:
            self.getControl(self.DELETE_BUTTON_ID).setEnabled(True)

    def onReInit(self):
        actiondialog.ActionDialog.onReInit(self)
        player.PLAYER.stopAndWait()
        self.action = 'dummy'

    def onAction(self, action):
        try:
            if action == xbmcgui.ACTION_NAV_BACK or action == xbmcgui.ACTION_PREVIOUS_MENU:
                if xbmc.getCondVisibility('ControlGroup({0}).HasFocus(0)'.format(self.DIALOG_GROUP_ID)):
                    self.setFocusId(self.BUTTONS_GROUP_ID)
                else:
                    self.doClose()
                return
        except:
            util.ERROR()

        actiondialog.ActionDialog.onAction(self, action)

    def onClick(self, controlID):
        if controlID == self.WATCH_BUTTON_ID:
            if self.seen:
                self.setProperty('dialog.message', T(32190).format(util.durationToText(self.seen)))
                self.setProperty('dialog.top.color', '52FFFFFF')
                self.setProperty('dialog.top', T(32191))
                self.setProperty('dialog.bottom', T(32192))
                self.parentAction = 'watch'
                self.setFocusId(self.DIALOG_GROUP_ID)
                return
            else:
                self.action = 'watch'
        elif controlID == self.DIALOG_TOP_BUTTON_ID:
            if self.parentAction == 'watch':
                self.action = 'watch'
            elif self.parentAction == 'delete':
                self.action = 'delete'
                self.setProperty('delete.busy', '1')
                try:
                    if not self.doCallback():
                        self.doClose()
                finally:
                    self.setProperty('delete.busy', '')
                self.parentAction = ''
                return
            self.parentAction = ''
        elif controlID == self.DIALOG_BOTTOM_BUTTON_ID:
            if self.parentAction == 'watch':
                self.action = 'resume'
            else:
                self.parentAction = ''
                return
            self.parentAction = ''
        elif controlID == self.TOGGLE_BUTTON_ID:
            self.action = 'toggle'
            self.setProperty('button2.busy', '1')
            try:
                if not self.doCallback():
                    self.doClose()
            finally:
                self.setProperty('button2.busy', '')
            return
        elif controlID == self.PROTECT_BUTTON_ID:
            self.action = 'protect'
            self.setProperty('button3.busy', '1')
            try:
                if not self.doCallback():
                    self.doClose()
            finally:
                self.setProperty('button3.busy', '')
            return
        elif controlID == self.DELETE_BUTTON_ID:
            self.setProperty('dialog.message', T(32193).format(util.LOCALIZED_RECORDING_TYPES[self._show.type].lower()))
            self.setProperty('dialog.top.color', '52FF0000')
            self.setProperty('dialog.top', T(32194))
            self.setProperty('dialog.bottom', T(32149))
            self.parentAction = 'delete'
            return

        if not self.doCallback():
            self.doClose()

    def tick(self):
        self.doCallback()

    def doCallback(self):
        if not self.callback:
            return False

        action = self.action
        self.action = None
        changes = self.callback(self.object, action)

        if not changes:
            return False

        self.button2 = changes.get('button2') or self.button2
        self.button3 = changes.get('button3') or self.button3
        self.plot = changes.get('plot') or self.plot
        self.seen = changes.get('seen')
        self.seenratio = changes.get('seenratio')
        self.indicator = changes.get('indicator') or ''

        self.updateDisplayProperties()

        return True

    def updateDisplayProperties(self):
        self.setProperty('button2', self.button2)
        self.setProperty('button3', self.button3)
        self.setProperty('plot', self.plot)
        self.setProperty('indicator', self.indicator)
        self.setProperty('seen', self.seen and '1' or '')
        self.setProperty('protected', self.object.protected and '1' or '')
        if self.object.protected:
            self.getControl(self.DELETE_BUTTON_ID).setEnabled(False)
        else:
            self.getControl(self.DELETE_BUTTON_ID).setEnabled(True)

        self.getControl(self.SEEN_PROGRESS_IMAGE_ID).setWidth(int((self.seenratio or 0) * self.SEEN_PROGRESS_WIDTH))


def openDialog(
    title, info, preview, failed, button2, button3, **kwargs
):

    w = RecordingDialog.open(
        title=title,
        info=info,
        preview=preview,
        failed=failed,
        button2=button2,
        button3=button3,
        **kwargs
    )

    util.CRON.cancelReceiver(w)

    action = w.action
    pos = w.itemPos
    del w
    return action or pos
