from __future__ import absolute_import
from kodi_six import xbmc
from kodi_six import xbmcgui
from . import kodigui

from lib import util
from lib import backgroundthread
from lib import metadata
from lib import player

from plexnet import plexapp, playlist, plexplayer
from plexnet.util import INTERFACE

from . import busy
from . import videoplayer
from . import dropdown
from . import windowutils
from . import opener
from . import search
from . import playersettings
from . import info
from . import optionsdialog
from . import preplayutils
from . import pagination
from . import playbacksettings

from lib.util import T
from .mixins import SeasonsMixin

VIDEO_RELOAD_KW = dict(includeExtras=1, includeExtrasCount=10, includeChapters=1)


class EpisodeReloadTask(backgroundthread.Task):
    def setup(self, episode, callback, with_progress=False):
        self.episode = episode
        self.callback = callback
        self.withProgress = with_progress
        return self

    def run(self):
        if self.isCanceled():
            return

        if not plexapp.SERVERMANAGER.selectedServer:
            # Could happen during sign-out for instance
            return

        try:
            self.episode.reload(checkFiles=1, includeChapters=1, fromMediaChoice=self.episode.mediaChoice is not None)
            if self.isCanceled():
                return
            self.callback(self, self.episode, with_progress=self.withProgress)
        except:
            util.ERROR()


class EpisodesPaginator(pagination.MCLPaginator):
    thumbFallback = 'script.plex/thumb_fallbacks/show.png'
    _currentEpisode = None

    def reset(self):
        super(EpisodesPaginator, self).reset()
        self._currentEpisode = None

    def getData(self, offset, amount):
        return (self.parentWindow.season or self.parentWindow.show_).episodes(offset=offset, limit=amount)

    def createListItem(self, data):
        mli = super(EpisodesPaginator, self).createListItem(data)
        self.parentWindow.setItemInfo(data, mli)
        return mli

    def prepareListItem(self, data, mli):
        if not mli.dataSource.isWatched:
            mli.setProperty('unwatched.count', str(mli.dataSource.unViewedLeafCount))
        mli.setProperty('progress', util.getProgressImage(mli.dataSource))

    def setEpisode(self, ep):
        self._currentEpisode = ep

    @property
    def initialPage(self):
        episode = self.parentWindow.episode
        offset = 0
        amount = self.initialPageSize
        if episode:
            self.setEpisode(episode)
            # try cutting the query short while not querying all episodes, to find the slice with the currently
            # selected episode in it
            episodes = []
            _amount = self.initialPageSize + self.orphans
            epSeasonIndex = int(episode.index or 1) - 1  # .index is 1-based
            if _amount < self.leafCount:
                _amount = self.initialPageSize * 2
                notFound = False
                while episode not in episodes:
                    offset = int(max(0, epSeasonIndex - _amount / 2))
                    episodes = self.getData(offset, int(_amount))

                    if _amount >= self.leafCount:
                        # ep not found?
                        notFound = True
                        break

                    # in case the episode wasn't found inside the slice, increase the slice's size
                    _amount *= 2

                if notFound:
                    # search conservatively
                    util.DEBUG_LOG("Episode not found with intelligent index-based search, re-trying conservatively")
                    _amount = self.initialPageSize * 2
                    offset = 0
                    episodes = self.getData(offset, int(_amount))
                    while episode not in episodes:
                        offset = _amount
                        episodes = self.getData(offset, int(_amount))

                        if _amount >= self.leafCount:
                            break

                        _amount *= 2
            else:
                # shortcut for short seasons
                episodes = self.getData(offset, int(_amount))

        else:
            return super(EpisodesPaginator, self).initialPage

        episodeFound = episode and episode in episodes
        if episodeFound:
            if self.initialPageSize + self.orphans < self.leafCount:
                # slice around the episode
                # Clamp the left side dynamically based on the item index and how many items are left in the season.
                # The episodes list might be longer than our limit, because the season doesn't necessarily have all the
                # episodes in it and we're basing the initial load on the current episode's index, which is the actual
                # index of the episode in the season, not what's physically there. To find the episode, we're
                # dynamically increasing the window size above. Re-clamp to :amount:, adding slack to both sides if
                # the remaining episodes would fit inside half of :amount:.
                tmpEpIdx = episodes.index(episode)
                leftBoundary = self.initialPageSize - len(episodes[tmpEpIdx:tmpEpIdx + self.orphans])

                left = max(tmpEpIdx - leftBoundary, 0)
                offset += left
                epsLeft = self.leafCount - offset
                # avoid short pages on the right end
                if epsLeft <= self.initialPageSize + self.orphans:
                    amount = epsLeft

                # avoid short pages on the left end
                if offset < self.orphans and amount + offset < self.initialPageSize + self.orphans:
                    amount += offset
                    left = 0
                    offset = 0

                episodes = episodes[left:left + amount]

        self.offset = offset
        self._currentAmount = len(episodes)

        return episodes

    def selectItem(self, amount, more_left=False, more_right=False, items=None):
        if not super(EpisodesPaginator, self).selectItem(amount, more_left):
            if (self._currentEpisode and items) and self._currentEpisode in items:
                self.control.selectItem(items.index(self._currentEpisode) + (1 if more_left else 0))


class RelatedPaginator(pagination.BaseRelatedPaginator):
    def getData(self, offset, amount):
        return self.parentWindow.show_.getRelated(offset=offset, limit=amount)


class EpisodesWindow(kodigui.ControlledWindow, windowutils.UtilMixin, SeasonsMixin,
                     playbacksettings.PlaybackSettingsMixin):
    xmlFile = 'script-plex-episodes.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    THUMB_AR16X9_DIM = util.scaleResolution(657, 393)
    POSTER_DIM = util.scaleResolution(420, 630)
    RELATED_DIM = util.scaleResolution(268, 397)
    EXTRA_DIM = util.scaleResolution(329, 185)
    ROLES_DIM = util.scaleResolution(334, 334)

    LIST_OPTIONS_BUTTON_ID = 111

    EPISODE_LIST_ID = 400
    SEASONS_LIST_ID = 401
    EXTRA_LIST_ID = 402
    RELATED_LIST_ID = 403
    ROLES_LIST_ID = 404

    OPTIONS_GROUP_ID = 200

    HOME_BUTTON_ID = 201
    SEARCH_BUTTON_ID = 202
    PLAYER_STATUS_BUTTON_ID = 204

    PROGRESS_IMAGE_ID = 250

    PLAY_BUTTON_ID = 301
    SHUFFLE_BUTTON_ID = 302
    OPTIONS_BUTTON_ID = 303
    INFO_BUTTON_ID = 304
    SETTINGS_BUTTON_ID = 305
    MEDIA_BUTTON_ID = 307

    SEASONS_CONTROL_ATTR = "seasonsListControl"

    def __init__(self, *args, **kwargs):
        kodigui.ControlledWindow.__init__(self, *args, **kwargs)
        windowutils.UtilMixin.__init__(self)
        self.episode = None
        self.reset(kwargs.get('episode'), kwargs.get('season'), kwargs.get('show'))
        self.initialEpisode = kwargs.get('episode')
        self.parentList = kwargs.get('parentList')
        self.lastItem = None
        self.lastFocusID = None
        self.lastNonOptionsFocusID = None
        self.episodesPaginator = None
        self.relatedPaginator = None
        self.cameFrom = kwargs.get('came_from')
        self.tasks = backgroundthread.Tasks()
        self.initialized = False
        self.closing = False
        self._reloadVideos = []

    def reset(self, episode, season=None, show=None):
        self.episode = episode
        self.season = season if season is not None else self.episode.season()
        try:
            self.show_ = show or (self.episode or self.season).show().reload(includeExtras=1, includeExtrasCount=10)
        except IndexError:
            raise util.NoDataException

        self.parentList = None
        self.seasons = None
        self._reloadVideos = []
        #self.initialized = False

    def doClose(self):
        self.closing = True
        self.episodesPaginator = None
        self.relatedPaginator = None
        kodigui.ControlledWindow.doClose(self)
        if self.tasks:
            self.tasks.cancel()
            self.tasks = None
        try:
            player.PLAYER.off('new.video', self.onNewVideo)
        except KeyError:
            pass

    @busy.dialog()
    def _onFirstInit(self):
        self.episodeListControl = kodigui.ManagedControlList(self, self.EPISODE_LIST_ID, 5)
        self.progressImageControl = self.getControl(self.PROGRESS_IMAGE_ID)

        self.extraListControl = kodigui.ManagedControlList(self, self.EXTRA_LIST_ID, 5)
        self.relatedListControl = kodigui.ManagedControlList(self, self.RELATED_LIST_ID, 5)
        self.rolesListControl = kodigui.ManagedControlList(self, self.ROLES_LIST_ID, 5)
        self.seasonsListControl = kodigui.ManagedControlList(self, self.SEASONS_LIST_ID, 5)

        self._setup()
        self.postSetup()

    def doAutoPlay(self):
        # First reload the video to get all the other info
        self.initialEpisode.reload(checkFiles=1, **VIDEO_RELOAD_KW)
        return self.playButtonClicked(force_episode=self.initialEpisode)

    def onFirstInit(self):
        self._onFirstInit()

        if self.show_ and self.show_.theme and not util.getSetting("slow_connection", False) and \
                (not self.cameFrom or self.cameFrom != self.show_.ratingKey):
            volume = self.show_.settings.getThemeMusicValue()
            if volume > 0:
                player.PLAYER.playBackgroundMusic(self.show_.theme.asURL(True), volume,
                                                  self.show_.ratingKey)

    @busy.dialog()
    def onReInit(self):
        if not self.tasks:
            self.tasks = backgroundthread.Tasks()

        try:
            self.selectEpisode()
        except AttributeError:
            raise util.NoDataException

        mli = self.episodeListControl.getSelectedItem()
        if not mli or not self.episodesPaginator:
            return

        reloadItems = [mli]
        for v in self._reloadVideos:
            for m in self.episodeListControl:
                if m.dataSource == v:
                    reloadItems.append(m)
                    self.episodesPaginator.prepareListItem(v, m)

        # re-set current item's progress to a loading state
        if util.getSetting("slow_connection", False):
            self.progressImageControl.setWidth(1)
            mli.setProperty('remainingTime', T(32914, "Loading"))

        self.reloadItems(items=reloadItems, with_progress=True)
        self.episodesPaginator.setEpisode(self._reloadVideos and self._reloadVideos[-1] or mli)
        self._reloadVideos = []
        self.fillRelated()

    def postSetup(self, from_select_episode=False):
        self.selectEpisode(from_select_episode=from_select_episode)
        self.checkForHeaderFocus(xbmcgui.ACTION_MOVE_DOWN)
        self.setFocusId(self.PLAY_BUTTON_ID)
        self.initialized = True

    @busy.dialog()
    def setup(self):
        self._setup()

    def _setup(self, from_select_episode=False):
        player.PLAYER.on('new.video', self.onNewVideo)
        (self.season or self.show_).reload(checkFiles=1, **VIDEO_RELOAD_KW)

        if not from_select_episode or not self.episodesPaginator:
            self.episodesPaginator = EpisodesPaginator(self.episodeListControl,
                                                       leaf_count=int(self.season.leafCount) if self.season else 0,
                                                       parent_window=self)

        if not from_select_episode or not self.episodesPaginator:
            self.relatedPaginator = RelatedPaginator(self.relatedListControl, leaf_count=int(self.show_.relatedCount),
                                                     parent_window=self)

        self.updateProperties()
        self.setBoolProperty("initialized", True)
        self.fillEpisodes()
        hasSeasons = self.fillSeasons(self.show_, seasonsFilter=lambda x: len(x) > 1, selectSeason=self.season)
        hasPrev = self.fillExtras(hasSeasons)

        if not hasPrev and hasSeasons:
            hasPrev = True
        hasPrev = self.fillRelated(hasPrev)
        self.fillRoles(hasPrev)

    def selectEpisode(self, from_select_episode=False):
        if not self.episode:
            return

        for mli in self.episodeListControl:
            if mli.dataSource == self.episode:
                self.episodeListControl.selectItem(mli.pos())
                self.episodesPaginator.setEpisode(self.episode)
                break
        else:
            if not from_select_episode:
                self.reset(self.episode)
                self._setup(from_select_episode=True)
                self.postSetup(from_select_episode=True)

        self.episode = None

    def onAction(self, action):
        try:
            controlID = self.getFocusId()

            if not controlID and self.lastFocusID and not action == xbmcgui.ACTION_MOUSE_MOVE:
                self.setFocusId(self.lastFocusID)

            if action == xbmcgui.ACTION_LAST_PAGE and xbmc.getCondVisibility('ControlGroup(300).HasFocus(0)'):
                next(self)
            elif action == xbmcgui.ACTION_NEXT_ITEM:
                next(self)
            elif action == xbmcgui.ACTION_FIRST_PAGE and xbmc.getCondVisibility('ControlGroup(300).HasFocus(0)'):
                self.prev()
            elif action == xbmcgui.ACTION_PREV_ITEM:
                self.prev()

            if action == xbmcgui.ACTION_MOVE_UP and controlID in (self.EPISODE_LIST_ID, self.SEASONS_LIST_ID):
                self.updateBackgroundFrom((self.show_ or self.season.show()))

            if controlID == self.EPISODE_LIST_ID:
                if self.checkForHeaderFocus(action):
                    return

            elif controlID == self.RELATED_LIST_ID:
                if self.relatedPaginator.boundaryHit:
                    self.relatedPaginator.paginate()
                    return
                elif action in (xbmcgui.ACTION_MOVE_LEFT, xbmcgui.ACTION_MOVE_RIGHT):
                    self.updateBackgroundFrom(self.relatedListControl.getSelectedItem().dataSource)

            if controlID == self.LIST_OPTIONS_BUTTON_ID and self.checkOptionsAction(action):
                return
            elif action == xbmcgui.ACTION_CONTEXT_MENU:
                if not xbmc.getCondVisibility('ControlGroup({0}).HasFocus(0)'.format(self.OPTIONS_GROUP_ID)):
                    self.lastNonOptionsFocusID = self.lastFocusID
                    self.setFocusId(self.OPTIONS_GROUP_ID)
                    return
                else:
                    if self.lastNonOptionsFocusID:
                        self.setFocusId(self.lastNonOptionsFocusID)
                        self.lastNonOptionsFocusID = None
                        return

            elif action == xbmcgui.ACTION_NAV_BACK:
                if (not xbmc.getCondVisibility('ControlGroup({0}).HasFocus(0)'.format(
                        self.OPTIONS_GROUP_ID)) or not controlID) and \
                        not util.advancedSettings.fastBack:
                    if self.getProperty('on.extras'):
                        self.setFocusId(self.OPTIONS_GROUP_ID)
                        return

            if action in (xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_PREVIOUS_MENU):
                self.doClose()
        except:
            util.ERROR()

        kodigui.ControlledWindow.onAction(self, action)

    def onNewVideo(self, video=None, **kwargs):
        if not video:
            return

        if not video.type == 'episode':
            return

        util.DEBUG_LOG('Updating selected episode: {0}'.format(video))
        self.episode = video
        self._reloadVideos.append(video)

        return True

    def checkOptionsAction(self, action):
        if action == xbmcgui.ACTION_MOVE_UP:
            mli = self.episodeListControl.getSelectedItem()
            if not mli or mli.getProperty("is.boundary"):
                return False
            pos = mli.pos() - 1
            if self.episodeListControl.positionIsValid(pos):
                self.setFocusId(self.EPISODE_LIST_ID)
                self.episodeListControl.selectItem(pos)
            return True
        elif action == xbmcgui.ACTION_MOVE_DOWN:
            mli = self.episodeListControl.getSelectedItem()
            if not mli or mli.getProperty("is.boundary"):
                return False
            pos = mli.pos() + 1
            if self.episodeListControl.positionIsValid(pos):
                self.setFocusId(self.EPISODE_LIST_ID)
                self.episodeListControl.selectItem(pos)
            return True

        return False

    def onClick(self, controlID):
        if controlID == self.HOME_BUTTON_ID:
            self.goHome()
        elif controlID == self.EPISODE_LIST_ID:
            self.episodeListClicked()
        elif controlID == self.PLAYER_STATUS_BUTTON_ID:
            self.showAudioPlayer()
        elif controlID == self.PLAY_BUTTON_ID:
            self.playButtonClicked()
        elif controlID == self.SHUFFLE_BUTTON_ID:
            self.shuffleButtonClicked()
        elif controlID == self.OPTIONS_BUTTON_ID:
            self.optionsButtonClicked()
        elif controlID == self.SETTINGS_BUTTON_ID:
            self.settingsButtonClicked()
        elif controlID == self.MEDIA_BUTTON_ID:
            self.mediaButtonClicked()
        elif controlID == self.INFO_BUTTON_ID:
            self.infoButtonClicked()
        elif controlID == self.SEARCH_BUTTON_ID:
            self.searchButtonClicked()
        elif controlID == self.SEASONS_LIST_ID:
            mli = self.seasonsListControl.getSelectedItem()
            if not mli:
                return
            item = mli.dataSource
            if item != self.season:
                self.openItem(self.seasonsListControl, came_from=self.season.parentRatingKey)
            else:
                self.setFocusId(self.EPISODE_LIST_ID)
        elif controlID == self.EXTRA_LIST_ID:
            self.openItem(self.extraListControl)
        elif controlID == self.RELATED_LIST_ID:
            self.openItem(self.relatedListControl)
        elif controlID == self.ROLES_LIST_ID:
            self.roleClicked()

    def onFocus(self, controlID):
        self.lastFocusID = controlID

        if 399 < controlID < 500:
            self.setProperty('hub.focus', str(controlID - 400))
            if controlID == self.RELATED_LIST_ID:
                self.updateBackgroundFrom(self.relatedListControl.getSelectedItem().dataSource)
        if xbmc.getCondVisibility('ControlGroup(50).HasFocus(0) + ControlGroup(300).HasFocus(0)'):
            self.setProperty('on.extras', '')
        elif xbmc.getCondVisibility('ControlGroup(50).HasFocus(0) + !ControlGroup(300).HasFocus(0)'):
            self.setProperty('on.extras', '1')

        if player.PLAYER.bgmPlaying and player.PLAYER.handler.currentlyPlaying != self.season.show().ratingKey:
            player.PLAYER.stopAndWait()

    def openItem(self, control=None, item=None, came_from=None):
        if not item:
            mli = control.getSelectedItem()
            if not mli:
                return
            item = mli.dataSource

        self.processCommand(opener.open(item, came_from=came_from))

    def roleClicked(self):
        mli = self.rolesListControl.getSelectedItem()
        if not mli:
            return

        sectionRoles = busy.widthDialog(mli.dataSource.sectionRoles, '')

        if not sectionRoles:
            util.DEBUG_LOG('No sections found for actor')
            return

        if len(sectionRoles) > 1:
            x, y = self.getRoleItemDDPosition()

            options = [{'role': r, 'display': r.reasonTitle} for r in sectionRoles]
            choice = dropdown.showDropdown(options, (x, y), pos_is_bottom=True, close_direction='bottom')

            if not choice:
                return

            role = choice['role']
        else:
            role = sectionRoles[0]

        self.processCommand(opener.open(role))

    def getRoleItemDDPosition(self):
        y = 980
        if xbmc.getCondVisibility('Control.IsVisible(500)'):
            y += 360
        if xbmc.getCondVisibility('Control.IsVisible(501)'):
            y += 520
        if xbmc.getCondVisibility('Control.IsVisible(502)'):
            y += 520
        if xbmc.getCondVisibility('!String.IsEmpty(Window.Property(on.extras))'):
            y -= 125
        if xbmc.getCondVisibility('Integer.IsGreater(Window.Property(hub.focus),0) + Control.IsVisible(500)'):
            y -= 500
        if xbmc.getCondVisibility('Integer.IsGreater(Window.Property(hub.focus),1) + Control.IsVisible(501)'):
            y -= 500
        if xbmc.getCondVisibility('Integer.IsGreater(Window.Property(hub.focus),1) + Control.IsVisible(502)'):
            y -= 500

        focus = int(xbmc.getInfoLabel('Container(403).Position'))

        x = ((focus + 1) * 304) - 100
        return x, y

    def getSeasons(self):
        if not self.seasons:
            self.seasons = self.show_.seasons()

        if not self.seasons:
            return False

        return True

    def next(self):
        if not self._next():
            return
        self.setup()

    __next__ = next

    @busy.dialog()
    def _next(self):
        if self.parentList:
            mli = self.parentList.getListItemByDataSource(self.season)
            if not mli:
                return False

            pos = mli.pos() + 1
            if not self.parentList.positionIsValid(pos):
                pos = 0

            self.season = self.parentList.getListItem(pos).dataSource
        else:
            if not self.getSeasons():
                return False

            if self.season not in self.seasons:
                return False

            pos = self.seasons.index(self.season)
            pos += 1
            if pos >= len(self.seasons):
                pos = 0

            self.season = self.seasons[pos]

        return True

    def prev(self):
        if not self._prev():
            return
        self.setup()

    @busy.dialog()
    def _prev(self):
        if self.parentList:
            mli = self.parentList.getListItemByDataSource(self.season)
            if not mli:
                return False

            pos = mli.pos() - 1
            if pos < 0:
                pos = self.parentList.size() - 1

            self.season = self.parentList.getListItem(pos).dataSource
        else:
            if not self.getSeasons():
                return False

            if self.season not in self.seasons:
                return False

            pos = self.seasons.index(self.season)
            pos -= 1
            if pos < 0:
                pos = len(self.seasons) - 1

            self.season = self.seasons[pos]

        return True

    def searchButtonClicked(self):
        section_id = self.show_.getLibrarySectionId()
        self.processCommand(search.dialog(self, section_id=section_id or None))

    def playButtonClicked(self, shuffle=False, force_episode=None):
        if shuffle:
            seasonOrShow = self.season or self.show_
            items = seasonOrShow.all()
            pl = playlist.LocalPlaylist(items, seasonOrShow.getServer())

            pl.shuffle(shuffle, first=True)
            videoplayer.play(play_queue=pl)
            return True

        else:
            return self.episodeListClicked(force_episode=force_episode)

    def shuffleButtonClicked(self):
        self.playButtonClicked(shuffle=True)

    def settingsButtonClicked(self):
        mli = self.episodeListControl.getSelectedItem()
        if not mli or mli.getProperty("is.boundary"):
            return

        episode = mli.dataSource

        if not episode.mediaChoice:
            playerObject = plexplayer.PlexPlayer(episode)
            playerObject.build()
        playersettings.showDialog(video=episode, non_playback=True)
        self.setItemAudioAndSubtitleInfo(episode, mli)

    def infoButtonClicked(self):
        mli = self.episodeListControl.getSelectedItem()
        if not mli or mli.getProperty("is.boundary"):
            return

        episode = mli.dataSource

        if episode.index:
            subtitle = u'{0} {1} {2} {3}'.format(T(32303, 'Season'), episode.parentIndex, T(32304, 'Episode'), episode.index)
        else:
            subtitle = episode.originallyAvailableAt.asDatetime('%B %d, %Y')

        opener.handleOpen(
            info.InfoWindow,
            title=episode.title,
            sub_title=subtitle,
            thumb=episode.thumb,
            thumb_fallback='script.plex/thumb_fallbacks/show.png',
            info=episode.summary,
            background=self.getProperty('background'),
            is_16x9=True,
            video=episode
        )

    def episodeListClicked(self, force_episode=None):
        if not force_episode:
            mli = self.episodeListControl.getSelectedItem()
            if not mli or mli.getProperty("is.boundary"):
                return

            episode = mli.dataSource
        else:
            episode = force_episode

        if not episode.available():
            util.messageDialog(T(32312, 'unavailable'), T(32332, 'This item is currently unavailable.'))
            return

        resume = False
        if episode.viewOffset.asInt():
            choice = dropdown.showDropdown(
                options=[
                    {'key': 'resume', 'display': T(32429, 'Resume from {0}').format(util.timeDisplay(episode.viewOffset.asInt()).lstrip('0').lstrip(':'))},
                    {'key': 'play', 'display': T(32317, 'Play from beginning')}
                ],
                pos=(660, 441),
                close_direction='none',
                set_dropdown_prop=False,
                header=T(32314, 'In Progress')
            )

            if not choice:
                return

            if choice['key'] == 'resume':
                resume = True
                if util.advancedSettings.dialogFlickerFix:
                    xbmc.sleep(750)

        self._reloadVideos.append(episode)

        pl = playlist.LocalPlaylist(self.show_.all(), self.show_.getServer())
        try:
            if len(pl):  # Don't use playlist if it's only this video
                pl.setCurrent(episode)
                self.processCommand(videoplayer.play(play_queue=pl, resume=resume))
                return True

            self.processCommand(videoplayer.play(video=episode, resume=resume))
            return True
        except util.NoDataException:
            util.ERROR("No data - disconnected?", notify=True, time_ms=5000)
            self.doClose()

    def optionsButtonClicked(self, from_item=False):
        options = []

        mli = self.episodeListControl.getSelectedItem()

        if mli and not mli.getProperty("is.boundary"):
            inProgress = mli.dataSource.viewOffset.asInt()
            if not mli.dataSource.isWatched or inProgress:
                options.append({'key': 'mark_watched', 'display': T(32319, 'Mark Played')})
            if mli.dataSource.isWatched or inProgress:
                options.append({'key': 'mark_unwatched', 'display': T(32318, 'Mark Unplayed')})

            # if True:
            #     options.append({'key': 'add_to_playlist', 'display': '[COLOR FF808080]Add To Playlist[/COLOR]'})

        if xbmc.getCondVisibility('Player.HasAudio + MusicPlayer.HasNext'):
            options.append({'key': 'play_next', 'display': T(32325, 'Play Next')})

        if self.season:
            if self.season.isWatched:
                options.append({'key': 'mark_season_unwatched', 'display': T(32320, 'Mark Season Unplayed')})
            else:
                options.append({'key': 'mark_season_watched', 'display': T(32321, 'Mark Season Played')})

        if self.show_:
            if options:
                options.append(dropdown.SEPARATOR)

            options.append({'key': 'playback_settings', 'display': T(32925, 'Playback Settings')})
            options.append(dropdown.SEPARATOR)

        if mli.dataSource.server.allowsMediaDeletion:
            options.append({'key': 'delete', 'display': T(32322, 'Delete')})

        # if xbmc.getCondVisibility('Player.HasAudio') and self.section.TYPE == 'artist':
        #     options.append({'key': 'add_to_queue', 'display': 'Add To Queue'})

        if options:
            options.append(dropdown.SEPARATOR)

        options.append({'key': 'to_show', 'display': T(32323, 'Go To Show')})
        options.append({'key': 'to_section', 'display': T(32324, u'Go to {0}').format(
            self.show_.getLibrarySectionTitle())})

        pos = (500, 620)
        bottom = False
        setDropdownProp = False
        if from_item:
            viewPos = self.episodeListControl.getViewPosition()
            if viewPos > 6:
                pos = (1490, 312 + (viewPos * 100))
                bottom = True
            else:
                pos = (1490, 167 + (viewPos * 100))
                bottom = False
            setDropdownProp = True

        choice = dropdown.showDropdown(options, pos, pos_is_bottom=bottom, close_direction='left',
                                       set_dropdown_prop=setDropdownProp)
        if not choice:
            return

        if choice['key'] == 'play_next':
            xbmc.executebuiltin('PlayerControl(Next)')
        elif choice['key'] == 'mark_watched':
            mli.dataSource.markWatched()
            self.updateItems(mli)
            util.MONITOR.watchStatusChanged()
        elif choice['key'] == 'mark_unwatched':
            mli.dataSource.markUnwatched()
            self.updateItems(mli)
            util.MONITOR.watchStatusChanged()
        elif choice['key'] == 'mark_season_watched':
            self.season.markWatched()
            self.updateItems()
            util.MONITOR.watchStatusChanged()
        elif choice['key'] == 'mark_season_unwatched':
            self.season.markUnwatched()
            self.updateItems()
            util.MONITOR.watchStatusChanged()
        elif choice['key'] == 'to_show':
            if util.advancedSettings.dialogFlickerFix:
                xbmc.sleep(750)
            self.processCommand(opener.open(
                self.season.parentRatingKey,
                came_from=self.season.parentRatingKey)
            )
        elif choice['key'] == 'to_section':
            self.goHome(self.show_.getLibrarySectionId())
        elif choice['key'] == 'delete':
            self.delete()
        elif choice['key'] == 'playback_settings':
            self.playbackSettings(self.show_, pos, bottom)

    def mediaButtonClicked(self):
        options = []
        mli = self.episodeListControl.getSelectedItem()
        ds = mli.dataSource
        for media in ds.media:
            ind = ''
            if ds.mediaChoice and media.id == ds.mediaChoice.media.id:
                ind = 'script.plex/home/device/check.png'
            options.append({'key': media, 'display': media.versionString(), 'indicator': ind})
        choice = dropdown.showDropdown(options, header=T(32450, 'Choose Version'), with_indicator=True)
        if not choice:
            return False

        for media in ds.media:
            media.set('selected', '')

        ds.setMediaChoice(choice['key'])
        choice['key'].set('selected', 1)
        self.setPostReloadItemInfo(ds, mli)

    def delete(self):
        button = optionsdialog.show(
            T(32326, 'Really delete?'),
            T(32327, 'Are you sure you really want to delete this media?'),
            T(32328, 'Yes'),
            T(32329, 'No')
        )

        if button != 0:
            return

        if not self._delete():
            util.messageDialog(T(32330, 'Message'), T(32331, 'There was a problem while attempting to delete the media.'))

    @busy.dialog()
    def _delete(self):
        mli = self.episodeListControl.getSelectedItem()
        if not mli or mli.getProperty("is.boundary"):
            return

        video = mli.dataSource
        success = video.delete()
        util.LOG('Media DELETE: {0} - {1}'.format(video, success and 'SUCCESS' or 'FAILED'))
        if success:
            self.episodeListControl.removeItem(mli.pos())
            if not self.episodeListControl.size():
                self.doClose()
            else:
                (self.season or self.show_).reload()
        return success

    def checkForHeaderFocus(self, action):
        # don't continue if we're still waiting for tasks
        if self.tasks or not self.episodesPaginator:
            if self.tasks:
                util.DEBUG_LOG("Episodes: Moving too fast through paginator, throttling.")
            return

        if self.episodesPaginator.boundaryHit:
            items = self.episodesPaginator.paginate()
            self.reloadItems(items)
            return True

        mli = self.episodeListControl.getSelectedItem()
        if not mli or mli.getProperty("is.boundary"):
            return

        lastItem = self.lastItem

        if action in (xbmcgui.ACTION_MOVE_RIGHT, xbmcgui.ACTION_MOVE_LEFT) and lastItem:
            items = self.episodesPaginator.wrap(mli, lastItem, action)
            xbmc.sleep(100)
            mli = self.episodeListControl.getSelectedItem()
            if items:
                self.reloadItems(items)
                return True

        if mli != self.lastItem and not mli.getProperty("is.boundary"):
            self.lastItem = mli
            self.setProgress(mli)

        if action in (xbmcgui.ACTION_MOVE_UP, xbmcgui.ACTION_PAGE_UP):
            if mli.getProperty('is.header'):
                xbmc.executebuiltin('Action(up)')
        if action in (xbmcgui.ACTION_MOVE_DOWN, xbmcgui.ACTION_PAGE_DOWN, xbmcgui.ACTION_MOVE_LEFT, xbmcgui.ACTION_MOVE_RIGHT):
            if mli.getProperty('is.header'):
                xbmc.executebuiltin('Action(down)')

    def updateProperties(self):
        showTitle = self.show_ and self.show_.title or ''

        self.updateBackgroundFrom(self.show_ or self.season.show())
        self.setProperty('season.thumb', (self.season or self.show_).thumb.asTranscodedImageURL(*self.POSTER_DIM))
        self.setProperty('show.title', showTitle)
        self.setProperty('season.title', (self.season or self.show_).title)

        if self.season:
            self.setProperty('episodes.header', u'{0} \u2022 {1} {2}'.format(showTitle, T(32303, 'Season'), self.season.index))
            self.setProperty('extras.header', u'{0} \u2022 {1} {2}'.format(T(32305, 'Extras'), T(32303, 'Season'), self.season.index))
        else:
            self.setProperty('episodes.header', u'Episodes')
            self.setProperty('extras.header', u'Extras')

        self.setProperty('seasons.header',
                         u'{0} \u2022 {1}'.format(showTitle, T(32942, 'Seasons')))
        self.setProperty('related.header', T(32306, 'Related Shows'))
        self.genre = self.show_.genres() and self.show_.genres()[0].tag or ''

    @busy.dialog()
    def updateItems(self, item=None):
        if item:
            item.setProperty('unwatched', not item.dataSource.isWatched and '1' or '')
            self.setProgress(item)
            item.setProperty('progress', util.getProgressImage(item.dataSource))
            (self.season or self.show_).reload()
        else:
            self.fillEpisodes(update=True)

        if self.episode:
            self.episode.reload()

    def setItemInfo(self, video, mli):
        # video.reload(checkFiles=1)
        mli.setProperty('background', util.backgroundFromArt(video.art, width=self.width, height=self.height))
        mli.setProperty('title', video.title)
        mli.setProperty('show.title', video.grandparentTitle or (self.show_.title if self.show_ else ''))
        mli.setProperty('duration', util.durationToText(video.duration.asInt()))
        mli.setProperty('summary', video.summary.strip().replace('\t', ' '))
        mli.setProperty('video.rendering', video.videoCodecRendering)

        if video.index:
            mli.setProperty('season', u'{0} {1}'.format(T(32303, 'Season'), video.parentIndex))
            mli.setProperty('episode', u'{0} {1}'.format(T(32304, 'Episode'), video.index))
        else:
            mli.setProperty('season', '')
            mli.setProperty('episode', '')

        mli.setProperty('date', util.cleanLeadingZeros(video.originallyAvailableAt.asDatetime('%B %d, %Y')))

        # mli.setProperty('related.header', 'Related Shows')
        mli.setProperty('year', video.year)
        mli.setProperty('content.rating', video.contentRating.split('/', 1)[-1])
        mli.setProperty('genre', self.genre)

        if video.get('userRating'):
            stars = str(int(round((video.userRating.asFloat() / 10) * 5)))
            mli.setProperty('rating.stars', stars)
        # elif video.rating:
        #     stars = str(int(round((video.rating.asFloat() / 10) * 5)))
        #     mli.setProperty('rating.stars', stars)

        if video.get('ratingImage'):
            rating = video.rating
            audienceRating = video.audienceRating
            if video.ratingImage.startswith('rottentomatoes:'):
                rating = '{0}%'.format(int(rating.asFloat() * 10))
                if audienceRating:
                    audienceRating = '{0}%'.format(int(audienceRating.asFloat() * 10))

            mli.setProperty('rating', rating)
            mli.setProperty('rating.image', 'script.plex/ratings/{0}.png'.format(video.ratingImage.replace('://', '/')))
            if video.get('audienceRatingImage'):
                mli.setProperty('rating2', audienceRating)
                mli.setProperty('rating2.image', 'script.plex/ratings/{0}.png'.format(video.audienceRatingImage.replace('://', '/')))
        else:
            mli.setProperty('rating', video.rating)

    def setPostReloadItemInfo(self, video, mli):
        self.setItemAudioAndSubtitleInfo(video, mli)
        mli.setProperty('unwatched', not video.isWatched and '1' or '')
        mli.setProperty('video.res', video.resolutionString())
        mli.setProperty('audio.codec', video.audioCodecString())
        mli.setProperty('video.codec', video.videoCodecString())
        mli.setProperty('audio.channels', video.audioChannelsString(metadata.apiTranslate))
        mli.setProperty('video.rendering', video.videoCodecRendering)
        mli.setBoolProperty('unavailable', not video.available())

        defW = 176
        defH = 140
        ids = [301, 302, 303, 304, 305]
        if len(list(filter(lambda x: x.isAccessible(), video.media()))) > 1:
            mli.setBoolProperty('media.multiple', True)
            # adjust button sizes
            ids.append(307)
            for id in ids:
                ctrl = self.getControl(id)
                ctrl.setWidth(161)
                ctrl.setHeight(125)
                del ctrl
        else:
            mli.setBoolProperty('media.multiple', False)
            # reset button sizes
            for id in ids:
                ctrl = self.getControl(id)
                ctrl.setWidth(defW)
                ctrl.setHeight(defH)
                del ctrl

    def setItemAudioAndSubtitleInfo(self, video, mli):
        sas = video.selectedAudioStream()
        mli.setProperty('audio', sas and sas.getTitle(metadata.apiTranslate) or T(32309, 'None'))

        sss = video.selectedSubtitleStream(forced_subtitles_override=
                                           util.getSetting("forced_subtitles_override", False))
        if sss:
            if len(video.subtitleStreams) > 1:
                mli.setProperty(
                    'subtitles', u'{0} \u2022 {1} {2}'.format(sss.getTitle(metadata.apiTranslate), len(video.subtitleStreams) - 1, T(32307, 'More'))
                )
            else:
                mli.setProperty('subtitles', sss.getTitle(metadata.apiTranslate))
        else:
            if video.subtitleStreams:
                mli.setProperty('subtitles', u'{0} \u2022 {1} {2}'.format(T(32309, 'None'), len(video.subtitleStreams), T(32308, 'Available')))
            else:
                mli.setProperty('subtitles', T(32309, 'None'))

    def setProgress(self, mli):
        video = mli.dataSource
        if video.viewOffset.asInt():
            width = video.viewOffset.asInt() and (1 + int((video.viewOffset.asInt() / video.duration.asFloat()) * self.width)) or 1
            self.progressImageControl.setWidth(width)
        else:
            self.progressImageControl.setWidth(1)

        if video.viewOffset.asInt():
            mli.setProperty('remainingTime', T(33615, "{time} left").format(time=video.remainingTimeString))
        else:
            mli.setProperty('remainingTime', '')

    def createListItem(self, episode):
        if episode.index:
            subtitle = u'{0}{1} \u2022 {2}{3}'.format(T(32310, 'S'), episode.parentIndex, T(32311, 'E'), episode.index)
        else:
            subtitle = episode.originallyAvailableAt.asDatetime('%m/%d/%y')

        mli = kodigui.ManagedListItem(
            episode.title,
            subtitle,
            thumbnailImage=episode.thumb.asTranscodedImageURL(*self.THUMB_AR16X9_DIM),
            data_source=episode
        )
        mli.setProperty('episode.number', str(episode.index) or '')
        mli.setProperty('episode.duration', util.durationToText(episode.duration.asInt()))
        mli.setProperty('unwatched', not episode.isWatched and '1' or '')
        # mli.setProperty('progress', util.getProgressImage(obj))
        return mli

    def fillEpisodes(self, update=False):
        items = self.episodesPaginator.paginate()
        self.reloadItems(items)

    def reloadItems(self, items, with_progress=False):
        tasks = []
        for mli in items:
            if not mli.dataSource:
                continue

            task = EpisodeReloadTask().setup(mli.dataSource, self.reloadItemCallback, with_progress=with_progress)
            self.tasks.add(task)
            tasks.append(task)

        backgroundthread.BGThreader.addTasks(tasks)

    def reloadItemCallback(self, task, episode, with_progress=False):
        self.tasks.remove(task)
        del task

        if self.closing:
            return

        selected = self.episodeListControl.getSelectedItem()

        for mli in self.episodeListControl:
            if mli.dataSource == episode:
                if not episode.mediaChoice:
                    episode.setMediaChoice()

                self.setPostReloadItemInfo(episode, mli)
                if with_progress:
                    self.episodesPaginator.prepareListItem(None, mli)
                if mli == selected:
                    self.lastItem = mli
                    self.setProgress(mli)
                return

    def fillExtras(self, has_prev=False):
        items = []
        idx = 0

        seasonOrShow = self.season or self.show_

        if not seasonOrShow.extras:
            self.extraListControl.reset()
            return False

        for extra in seasonOrShow.extras():
            mli = kodigui.ManagedListItem(
                extra.title or '',
                metadata.EXTRA_MAP.get(extra.extraType.asInt(), ''),
                thumbnailImage=extra.thumb.asTranscodedImageURL(*self.EXTRA_DIM),
                data_source=extra
            )

            if mli:
                mli.setProperty('index', str(idx))
                mli.setProperty(
                    'thumb.fallback', 'script.plex/thumb_fallbacks/{0}.png'.format(extra.type in ('show', 'season', 'episode') and 'show' or 'movie')
                )
                items.append(mli)
                idx += 1

        if not items:
            return False

        self.extraListControl.reset()
        self.extraListControl.addItems(items)

        self.setProperty('divider.{0}'.format(self.EXTRA_LIST_ID), has_prev and '1' or '')
        return True

    def fillRelated(self, has_prev=False):
        if not self.relatedPaginator.leafCount:
            self.relatedListControl.reset()
            return has_prev

        items = self.relatedPaginator.paginate()
        if not items:
            return False

        self.setProperty('divider.{0}'.format(self.RELATED_LIST_ID), has_prev and '1' or '')

        return True

    def fillRoles(self, has_prev=False):
        items = []
        idx = 0

        if not self.show_.roles:
            self.rolesListControl.reset()
            return False

        for role in self.show_.roles():
            mli = kodigui.ManagedListItem(role.tag, role.role, thumbnailImage=role.thumb.asTranscodedImageURL(*self.ROLES_DIM), data_source=role)
            mli.setProperty('index', str(idx))
            items.append(mli)
            idx += 1

        if not items:
            return False

        self.setProperty('divider.{0}'.format(self.ROLES_LIST_ID), has_prev and '1' or '')

        self.rolesListControl.reset()
        self.rolesListControl.addItems(items)
        return True
