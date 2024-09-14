from __future__ import absolute_import

from kodi_six import xbmc
from kodi_six import xbmcgui
from plexnet import plexplayer, media

from lib import metadata
from lib import util
from lib.util import T
from . import busy
from . import dropdown
from . import info
from . import kodigui
from . import opener
from . import optionsdialog
from . import pagination
from . import playersettings
from . import search
from . import videoplayer
from . import windowutils
from .mixins import RatingsMixin, PlaybackBtnMixin

VIDEO_RELOAD_KW = dict(includeExtras=1, includeExtrasCount=10, includeChapters=1, includeReviews=1)


class RelatedPaginator(pagination.BaseRelatedPaginator):
    def getData(self, offset, amount):
        return self.parentWindow.video.getRelated(offset=offset, limit=amount)


class PrePlayWindow(kodigui.ControlledWindow, windowutils.UtilMixin, RatingsMixin, PlaybackBtnMixin):
    xmlFile = 'script-plex-pre_play.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    THUMB_POSTER_DIM = util.scaleResolution(347, 518)
    RELATED_DIM = util.scaleResolution(268, 397)
    EXTRA_DIM = util.scaleResolution(329, 185)
    ROLES_DIM = util.scaleResolution(334, 334)
    PREVIEW_DIM = util.scaleResolution(343, 193)

    ROLES_LIST_ID = 400
    REVIEWS_LIST_ID = 401
    EXTRA_LIST_ID = 402
    RELATED_LIST_ID = 403

    OPTIONS_GROUP_ID = 200
    PROGRESS_IMAGE_ID = 250

    HOME_BUTTON_ID = 201
    SEARCH_BUTTON_ID = 202

    INFO_BUTTON_ID = 304
    PLAY_BUTTON_ID = 302
    TRAILER_BUTTON_ID = 303
    SETTINGS_BUTTON_ID = 305
    OPTIONS_BUTTON_ID = 306
    MEDIA_BUTTON_ID = 307

    PLAYER_STATUS_BUTTON_ID = 204

    def __init__(self, *args, **kwargs):
        kodigui.ControlledWindow.__init__(self, *args, **kwargs)
        PlaybackBtnMixin.__init__(self)
        self.video = kwargs.get('video')
        self.parentList = kwargs.get('parent_list')
        self.videos = None
        self.exitCommand = None
        self.trailer = None
        self.lastFocusID = None
        self.lastNonOptionsFocusID = None
        self.initialized = False
        self.relatedPaginator = None

    def doClose(self):
        self.relatedPaginator = None
        kodigui.ControlledWindow.doClose(self)

    def onFirstInit(self):
        self.extraListControl = kodigui.ManagedControlList(self, self.EXTRA_LIST_ID, 5)
        self.relatedListControl = kodigui.ManagedControlList(self, self.RELATED_LIST_ID, 5)
        self.rolesListControl = kodigui.ManagedControlList(self, self.ROLES_LIST_ID, 5)
        self.reviewsListControl = kodigui.ManagedControlList(self, self.REVIEWS_LIST_ID, 5)

        self.progressImageControl = self.getControl(self.PROGRESS_IMAGE_ID)
        self.setup()
        self.initialized = True

    def doAutoPlay(self):
        # First reload the video to get all the other info
        self.video.reload(checkFiles=1, **VIDEO_RELOAD_KW)
        return self.playVideo(from_auto_play=True)

    @busy.dialog()
    def onReInit(self):
        PlaybackBtnMixin.onReInit(self)
        self.initialized = False
        if util.getSetting("slow_connection", False):
            self.progressImageControl.setWidth(1)
            self.setProperty('remainingTime', T(32914, "Loading"))
        self.video.reload(checkFiles=1, fromMediaChoice=self.video.mediaChoice is not None, **VIDEO_RELOAD_KW)
        self.refreshInfo(from_reinit=True)
        self.initialized = True

    def refreshInfo(self, from_reinit=False):
        oldFocusId = self.getFocusId()

        util.setGlobalProperty('hide.resume', '' if self.video.viewOffset.asInt() else '1')
        # skip setting background when coming from reinit (other window) if we've focused something other than main
        self.setInfo(skip_bg=from_reinit and not (self.PLAY_BUTTON_ID <= oldFocusId <= self.MEDIA_BUTTON_ID))
        self.fillRelated()
        xbmc.sleep(100)

        if oldFocusId == self.PLAY_BUTTON_ID:
            self.focusPlayButton()

    def onAction(self, action):
        try:
            controlID = self.getFocusId()

            if not controlID and self.lastFocusID and not action == xbmcgui.ACTION_MOUSE_MOVE:
                self.setFocusId(self.lastFocusID)

            if action == xbmcgui.ACTION_CONTEXT_MENU:
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
                        not util.addonSettings.fastBack:
                    if self.getProperty('on.extras'):
                        self.setFocusId(self.OPTIONS_GROUP_ID)
                        return

            elif action == xbmcgui.ACTION_LAST_PAGE and xbmc.getCondVisibility('ControlGroup(300).HasFocus(0)'):
                next(self)
            elif action == xbmcgui.ACTION_NEXT_ITEM:
                self.setFocusId(300)
                next(self)
            elif action == xbmcgui.ACTION_FIRST_PAGE and xbmc.getCondVisibility('ControlGroup(300).HasFocus(0)'):
                self.prev()
            elif action == xbmcgui.ACTION_PREV_ITEM:
                self.setFocusId(300)
                self.prev()

            elif action == xbmcgui.ACTION_MOVE_UP and controlID in (self.REVIEWS_LIST_ID,
                                                                    self.ROLES_LIST_ID,
                                                                    self.EXTRA_LIST_ID):
                self.updateBackgroundFrom(self.video)

            if controlID == self.RELATED_LIST_ID:
                if self.relatedPaginator.boundaryHit:
                    self.relatedPaginator.paginate()
                    return
                elif action in (xbmcgui.ACTION_MOVE_LEFT, xbmcgui.ACTION_MOVE_RIGHT):
                    self.updateBackgroundFrom(self.relatedListControl.getSelectedItem().dataSource)
        except:
            util.ERROR()

        kodigui.ControlledWindow.onAction(self, action)

    def onClick(self, controlID):
        if controlID == self.HOME_BUTTON_ID:
            self.goHome()
        elif controlID == self.EXTRA_LIST_ID:
            self.openItem(self.extraListControl)
        elif controlID == self.RELATED_LIST_ID:
            self.openItem(self.relatedListControl)
        elif controlID == self.ROLES_LIST_ID:
            self.roleClicked()
        elif controlID == self.PLAY_BUTTON_ID:
            self.playVideo()
        elif controlID == self.PLAYER_STATUS_BUTTON_ID:
            self.showAudioPlayer()
        elif controlID == self.INFO_BUTTON_ID:
            self.infoButtonClicked()
        elif controlID == self.SETTINGS_BUTTON_ID:
            self.settingsButtonClicked()
        elif controlID == self.TRAILER_BUTTON_ID:
            self.openItem(item=self.trailer)
        elif controlID == self.OPTIONS_BUTTON_ID:
            self.optionsButtonClicked()
        elif controlID == self.MEDIA_BUTTON_ID:
            self.mediaButtonClicked()
        elif controlID == self.SEARCH_BUTTON_ID:
            self.searchButtonClicked()

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

    def searchButtonClicked(self):
        self.processCommand(search.dialog(self, section_id=self.video.getLibrarySectionId() or None))

    def settingsButtonClicked(self):
        if not self.video.mediaChoice:
            playerObject = plexplayer.PlexPlayer(self.video)
            playerObject.build()
        playersettings.showDialog(video=self.video, non_playback=True)
        self.setAudioAndSubtitleInfo()

    def infoButtonClicked(self):
        opener.handleOpen(
            info.InfoWindow,
            title=self.video.defaultTitle,
            sub_title=self.getProperty('info'),
            thumb=self.video.type == 'episode' and self.video.thumb or self.video.defaultThumb,
            thumb_fallback='script.plex/thumb_fallbacks/{0}.png'.format(self.video.type == 'episode' and 'show' or 'movie'),
            info=self.video.summary,
            background=self.getProperty('background'),
            is_16x9=self.video.type == 'episode',
            video=self.video
        )

    def optionsButtonClicked(self):
        options = []

        inProgress = self.video.viewOffset.asInt()
        if not self.video.isWatched or inProgress:
            options.append({'key': 'mark_watched', 'display': T(32319, 'Mark Played')})
        if self.video.isWatched or inProgress:
            options.append({'key': 'mark_unwatched', 'display': T(32318, 'Mark Unplayed')})

        options.append(dropdown.SEPARATOR)

        if self.video.type == 'episode':
            options.append({'key': 'to_season', 'display': T(32400, 'Go to Season')})
            options.append({'key': 'to_show', 'display': T(32323, 'Go to Show')})

        if self.video.type in ('episode', 'movie'):
            options.append({'key': 'to_section', 'display': T(32324, u'Go to {0}').format(self.video.getLibrarySectionTitle())})

        if self.video.server.allowsMediaDeletion:
            options.append({'key': 'delete', 'display': T(32322, 'Delete')})
        # if xbmc.getCondVisibility('Player.HasAudio') and self.section.TYPE == 'artist':
        #     options.append({'key': 'add_to_queue', 'display': 'Add To Queue'})

        # if False:
        #     options.append({'key': 'add_to_playlist', 'display': 'Add To Playlist'})
        posy = 880
        if not util.getGlobalProperty('hide.resume'):
            posy += 106
        if self.getProperty('trailer.button'):
            posy += 106
        choice = dropdown.showDropdown(options, (posy, 618), close_direction='left')
        if not choice:
            return

        if choice['key'] == 'play_next':
            xbmc.executebuiltin('PlayerControl(Next)')
        elif choice['key'] == 'mark_watched':
            self.video.markWatched(**VIDEO_RELOAD_KW)
            self.refreshInfo()
            util.MONITOR.watchStatusChanged()
        elif choice['key'] == 'mark_unwatched':
            self.video.markUnwatched(**VIDEO_RELOAD_KW)
            self.refreshInfo()
            util.MONITOR.watchStatusChanged()
        elif choice['key'] == 'to_season':
            self.processCommand(opener.open(self.video.parentRatingKey))
        elif choice['key'] == 'to_show':
            self.processCommand(opener.open(self.video.grandparentRatingKey))
        elif choice['key'] == 'to_section':
            self.goHome(self.video.getLibrarySectionId())
        elif choice['key'] == 'delete':
            self.delete()

    def mediaButtonClicked(self):
        options = []
        for media in self.video.media:
            ind = ''
            if self.video.mediaChoice and media.id == self.video.mediaChoice.media.id:
                ind = 'script.plex/home/device/check.png'
            options.append({'key': media, 'display': media.versionString(), 'indicator': ind})
        choice = dropdown.showDropdown(options, header=T(32450, 'Choose Version'), with_indicator=True)
        if not choice:
            return False

        for media in self.video.media:
            media.set('selected', '')

        self.video.setMediaChoice(choice['key'])
        choice['key'].set('selected', 1)
        self.setInfo()

    def delete(self):
        button = optionsdialog.show(
            T(32326, 'Really delete?'),
            T(33035, "Delete {}: {}?").format(type(self.video).__name__, self.video.defaultTitle),
            T(32328, 'Yes'),
            T(32329, 'No')
        )

        if button != 0:
            return

        if self._delete():
            self.doClose()
        else:
            util.messageDialog(T(32330, 'Message'), T(32331, 'There was a problem while attempting to delete the media.'))

    @busy.dialog()
    def _delete(self):
        success = self.video.delete()
        util.LOG('Media DELETE: {0} - {1}', self.video, success and 'SUCCESS' or 'FAILED')
        return success

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

    def getVideos(self):
        if not self.videos:
            if self.video.TYPE == 'episode':
                self.videos = self.video.show().episodes()

        if not self.videos:
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
            mli = self.parentList.getListItemByDataSource(self.video)
            if not mli:
                return False

            pos = mli.pos() + 1
            if not self.parentList.positionIsValid(pos):
                pos = 0

            self.video = self.parentList.getListItem(pos).dataSource
        else:
            if not self.getVideos():
                return False

            if self.video not in self.videos:
                return False

            pos = self.videos.index(self.video)
            pos += 1
            if pos >= len(self.videos):
                pos = 0

            self.video = self.videos[pos]

        return True

    def prev(self):
        if not self._prev():
            return
        self.setup()

    @busy.dialog()
    def _prev(self):
        if self.parentList:
            mli = self.parentList.getListItemByDataSource(self.video)
            if not mli:
                return False

            pos = mli.pos() - 1
            if pos < 0:
                pos = self.parentList.size() - 1

            self.video = self.parentList.getListItem(pos).dataSource
        else:
            if not self.getVideos():
                return False

            if self.video not in self.videos:
                return False

            pos = self.videos.index(self.video)
            pos -= 1
            if pos < 0:
                pos = len(self.videos) - 1

            self.video = self.videos[pos]

        return True

    def getRoleItemDDPosition(self):
        y = 200
        if xbmc.getCondVisibility('Control.IsVisible(500)'):
            y += 360
        if xbmc.getCondVisibility('Control.IsVisible(501)'):
            y += 520
        if xbmc.getCondVisibility('!String.IsEmpty(Window.Property(on.extras))'):
            y -= 300
        if xbmc.getCondVisibility('Integer.IsGreater(Window.Property(hub.focus),0) + Control.IsVisible(500)'):
            y -= 500
        if xbmc.getCondVisibility('Integer.IsGreater(Window.Property(hub.focus),1) + Control.IsVisible(501)'):
            y -= 500
        if xbmc.getCondVisibility('Integer.IsGreater(Window.Property(hub.focus),2) + Control.IsVisible(502)'):
            y -= 500

        tries = 0
        focus = xbmc.getInfoLabel('Container(400).Position')
        while tries < 2 and focus == '':
            focus = xbmc.getInfoLabel('Container(400).Position')
            xbmc.sleep(250)
            tries += 1

        focus = int(focus)

        x = ((focus + 1) * 304) - 100
        return x, y

    def playVideo(self, from_auto_play=False):
        if self.playBtnClicked:
            return

        if not self.video.available():
            util.messageDialog(T(32312, 'Unavailable'), T(32313, 'This item is currently unavailable.'))
            return

        resume = False
        if self.video.viewOffset.asInt():
            choice = dropdown.showDropdown(
                options=[
                    {'key': 'resume', 'display': T(32429, 'Resume from {0}').format(util.timeDisplay(self.video.viewOffset.asInt()).lstrip('0').lstrip(':'))},
                    {'key': 'play', 'display': T(32317, 'Play from beginning')}
                ],
                pos=(660, 441),
                close_direction='none',
                set_dropdown_prop=False,
                header=T(32314, 'In Progress'),
                dialog_props=from_auto_play and self.dialogProps or None
            )

            if not choice:
                return

            if choice['key'] == 'resume':
                resume = True

        if not from_auto_play:
            self.playBtnClicked = True

        self.processCommand(videoplayer.play(video=self.video, resume=resume))
        return True

    def openItem(self, control=None, item=None):
        if not item:
            mli = control.getSelectedItem()
            if not mli:
                return
            item = mli.dataSource

        self.processCommand(opener.open(item))

    def focusPlayButton(self):
        try:
            if not self.getFocusId() == self.PLAY_BUTTON_ID:
                self.setFocusId(self.PLAY_BUTTON_ID)
        except (SystemError, RuntimeError):
            self.setFocusId(self.PLAY_BUTTON_ID)

    @busy.dialog()
    def setup(self):
        self.focusPlayButton()

        util.DEBUG_LOG('PrePlay: Showing video info: {0}', self.video)
        if self.video.type == 'episode':
            self.setProperty('preview.yes', '1')
        elif self.video.type == 'movie':
            self.setProperty('preview.no', '1')

        self.video.reload(checkFiles=1, **VIDEO_RELOAD_KW)
        try:
            self.relatedPaginator = RelatedPaginator(self.relatedListControl, leaf_count=int(self.video.relatedCount),
                                                     parent_window=self)
        except ValueError:
            raise util.NoDataException

        self.setInfo()
        self.setBoolProperty("initialized", True)
        hasRoles = self.fillRoles()
        hasReviews = self.fillReviews()
        hasExtras = self.fillExtras()
        self.fillRelated(hasRoles and not hasExtras and not hasReviews)

    def setInfo(self, skip_bg=False):
        if not skip_bg:
            self.updateBackgroundFrom(self.video)
        self.setProperty('title', self.video.title)
        self.setProperty('duration', util.durationToText(self.video.duration.asInt()))
        self.setProperty('summary', self.video.summary.strip().replace('\t', ' '))
        self.setProperty('unwatched', not self.video.isWatched and '1' or '')
        self.setBoolProperty('watched', self.video.isFullyWatched)

        directors = u' / '.join([d.tag for d in self.video.directors()][:3])
        directorsLabel = len(self.video.directors) > 1 and T(32401, u'DIRECTORS').upper() or T(32383, u'DIRECTOR').upper()
        self.setProperty('directors', directors and u'{0}    {1}'.format(directorsLabel, directors) or '')
        writers = u' / '.join([r.tag for r in self.video.writers()][:3])
        writersLabel = len(self.video.writers) > 1 and T(32403, u'WRITERS').upper() or T(32402, u'WRITER').upper()
        self.setProperty('writers',
                         writers and u'{0}{1}    {2}'.format(directors and '    ' or '', writersLabel, writers) or '')

        # fixme: can this ever happen?
        if self.video.type == 'episode':
            self.setProperty('content.rating', '')
            self.setProperty('thumb', self.video.defaultThumb.asTranscodedImageURL(*self.THUMB_POSTER_DIM))
            self.setProperty('preview', self.video.thumb.asTranscodedImageURL(*self.PREVIEW_DIM))
            self.setProperty('info', u'{0} {1}'.format(T(32303, 'Season').format(self.video.parentIndex), T(32304, 'Episode').format(self.video.index)))
            self.setProperty('date', util.cleanLeadingZeros(self.video.originallyAvailableAt.asDatetime('%B %d, %Y')))
            self.setProperty('related.header', T(32306, 'Related Shows'))
        elif self.video.type == 'movie':
            self.setProperty('title', self.video.defaultTitle)
            self.setProperty('preview', '')
            self.setProperty('thumb', self.video.thumb.asTranscodedImageURL(*self.THUMB_POSTER_DIM))
            genres = u' / '.join([g.tag for g in self.video.genres()][:3])
            self.setProperty('info', genres)
            self.setProperty('date', self.video.year)
            self.setProperty('content.rating', self.video.contentRating.split('/', 1)[-1])

            cast = u' / '.join([r.tag for r in self.video.roles()][:5])
            castLabel = 'CAST'
            self.setProperty('cast', cast and u'{0}    {1}'.format(castLabel, cast) or '')
            self.setProperty('related.header', T(32404, 'Related Movies'))

        self.setProperty('video.res', self.video.resolutionString())
        self.setProperty('audio.codec', self.video.audioCodecString())
        self.setProperty('video.codec', self.video.videoCodecString())
        self.setProperty('video.rendering', self.video.videoCodecRendering)
        self.setProperty('audio.channels', self.video.audioChannelsString(metadata.apiTranslate))
        self.setBoolProperty('media.multiple', len(list(filter(lambda x: x.isAccessible(), self.video.media()))) > 1)

        self.populateRatings(self.video, self)

        self.setAudioAndSubtitleInfo()

        self.setProperty('unavailable', all(not v.isAccessible() for v in self.video.media()) and '1' or '')

        if self.video.viewOffset.asInt():
            width = self.video.viewOffset.asInt() and (1 + int((self.video.viewOffset.asInt() / self.video.duration.asFloat()) * self.width)) or 1
            self.progressImageControl.setWidth(width)
        else:
            self.progressImageControl.setWidth(1)

        if self.video.viewOffset.asInt():
            self.setProperty('remainingTime', T(33615, "{time} left").format(time=self.video.remainingTimeString))
        else:
            self.setProperty('remainingTime', '')

    def setAudioAndSubtitleInfo(self):
        sas = self.video.selectedAudioStream()

        if sas:
            if len(self.video.audioStreams) > 1:
                self.setProperty(
                    'audio', sas and u'{0} \u2022 {1} {2}'.format(sas.getTitle(metadata.apiTranslate),
                                                                  len(self.video.audioStreams) - 1, T(32307, 'More'))
                    or T(32309, 'None')
                )
            else:
                self.setProperty('audio', sas and sas.getTitle(metadata.apiTranslate) or T(32309, 'None'))

        sss = self.video.selectedSubtitleStream(
            forced_subtitles_override=util.getSetting("forced_subtitles_override", False))
        if sss:
            if len(self.video.subtitleStreams) > 1:
                self.setProperty(
                    'subtitles', u'{0} \u2022 {1} {2}'.format(sss.getTitle(metadata.apiTranslate), len(self.video.subtitleStreams) - 1, T(32307, 'More'))
                )
            else:
                self.setProperty('subtitles', sss.getTitle(metadata.apiTranslate))
        else:
            if self.video.subtitleStreams:
                self.setProperty('subtitles', u'{0} \u2022 {1} {2}'.format(T(32309, 'None'), len(self.video.subtitleStreams), T(32308, 'Available')))
            else:
                self.setProperty('subtitles', T(32309, u'None'))

    def createListItem(self, obj):
        mli = kodigui.ManagedListItem(obj.title or '', thumbnailImage=obj.thumb.asTranscodedImageURL(*self.EXTRA_DIM), data_source=obj)
        return mli

    def fillExtras(self, has_prev=False):
        items = []
        idx = 0

        if not self.video.extras:
            self.extraListControl.reset()
            return False

        for extra in self.video.extras():
            if not self.trailer and extra.extraType.asInt() == media.METADATA_RELATED_TRAILER:
                self.trailer = extra
                self.setProperty('trailer.button', '1')
                continue

            mli = self.createListItem(extra)
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
            return False

        items = self.relatedPaginator.paginate()

        if not items:
            return False

        self.setProperty('divider.{0}'.format(self.RELATED_LIST_ID), has_prev and '1' or '')

        return True

    def fillRoles(self, has_prev=False):
        items = []
        idx = 0

        if not self.video.roles:
            self.rolesListControl.reset()
            return False

        for role in self.video.roles():
            mli = kodigui.ManagedListItem(role.tag, role.role, thumbnailImage=role.thumb.asTranscodedImageURL(*self.ROLES_DIM), data_source=role)
            mli.setProperty('index', str(idx))
            items.append(mli)
            idx += 1

        if not items:
            return False

        self.rolesListControl.reset()
        self.rolesListControl.addItems(items)
        return True

    def fillReviews(self, has_prev=False):
        items = []
        idx = 0

        if not self.video.reviews:
            self.reviewsListControl.reset()
            return False

        for review in self.video.reviews():
            mli = kodigui.ManagedListItem(review.source, review.tag, thumbnailImage=review.ratingImage())
            mli.setProperty('index', str(idx))
            mli.setProperty('text', review.text)
            items.append(mli)
            idx += 1

        if not items:
            return False

        self.reviewsListControl.reset()
        self.reviewsListControl.addItems(items)
        return True
