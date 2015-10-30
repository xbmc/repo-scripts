import experience
import kodiutil
import cvutil
import kodigui
import xbmc
import xbmcgui

from kodiutil import T

kodiutil.checkAPILevel()

CHANNEL_STRINGS = {
    0: '0.0',
    1: '1.0',
    2: '2.0',
    3: '2.1',
    4: '4.0',
    5: '4.1',
    6: '5.1',
    7: '6.1',
    8: '7.1',
    10: '9.1',
    12: '11.1'
}

CODEC_IMAGES = ('aac', )


def showNoFeaturesDialog():
    import xbmcgui
    xbmcgui.Dialog().ok(
        T(32561, 'No Features'),
        T(32562, 'No movies are in the Queue.'),
        '',
        T(32563, 'Please queue some features and try again.')
    )


def featureComfirmationDialog(features):
    pd = PlaylistDialog.open(features=features)
    if not pd.play:
        return None, None

    return pd.features, pd.sequencePath


def begin(movieid=None, episodeid=None, selection=False):
    e = experience.ExperiencePlayer().create()
    seqPath = None

    if not e.hasFeatures() or selection or movieid or episodeid:
        if not e.addSelectedFeature(selection=selection, movieid=movieid, episodeid=episodeid):
            return showNoFeaturesDialog()

    if not kodiutil.getSetting('hide.queue.dialog', False) or (kodiutil.getSetting('hide.queue.dialog.single', False) and len(e.features) > 1):
        e.features, seqPath = featureComfirmationDialog(e.features)

    if not e.features:
        return

    if seqPath:
        kodiutil.DEBUG_LOG('Loading selected sequence: {0}'.format(repr(seqPath)))
    else:
        seqPath = cvutil.getSequencePath(for_3D=e.has3D)
        kodiutil.DEBUG_LOG('Loading sequence for {0}: {1}'.format(e.has3D and '3D' or '2D', repr(seqPath)))

    e.start(seqPath)


class PlaylistDialog(kodigui.BaseDialog):
    xmlFile = 'script.cinemavision-playlist-dialog.xml'
    path = kodiutil.ADDON_PATH
    theme = 'Main'
    res = '1080i'

    VIDEOS_LIST_ID = 300
    PLAY_BUTTON_ID = 201
    APPLY_BUTTON_ID = 203
    CANCEL_BUTTON_ID = 202
    SEQUENCE_SELECT_ID = 204

    def __init__(self, *args, **kwargs):
        kodigui.BaseDialog.__init__(self, *args, **kwargs)
        kodiutil.setScope()
        self.features = kwargs.get('features', [])
        self.play = False
        self.moving = None
        self.sequencePath = None

    def onFirstInit(self):
        self.videoListControl = kodigui.ManagedControlList(self, self.VIDEOS_LIST_ID, 5)
        self.start()

    def onClick(self, controlID):
        if controlID == self.PLAY_BUTTON_ID:
            self.play = True
            self.doClose()
        elif controlID == self.CANCEL_BUTTON_ID:
            self.doClose()
        elif controlID == self.APPLY_BUTTON_ID:
            self.apply()
        elif controlID == self.VIDEOS_LIST_ID:
            self.moveItem()
        elif controlID == self.SEQUENCE_SELECT_ID:
            self.selectSequence()

    def onAction(self, action):
        try:
            if action == xbmcgui.ACTION_CONTEXT_MENU:
                self.delete()
                return
            elif action in (
                xbmcgui.ACTION_MOVE_UP,
                xbmcgui.ACTION_MOVE_DOWN,
                xbmcgui.ACTION_MOUSE_MOVE,
                xbmcgui.ACTION_MOUSE_WHEEL_UP,
                xbmcgui.ACTION_MOUSE_WHEEL_DOWN
            ):
                if self.getFocusId() == self.VIDEOS_LIST_ID:
                    self.moveItem(True)
                return
            elif action.getButtonCode() in (61575, 61486):
                self.delete()
        except:
            kodigui.BaseDialog.onAction(self, action)
            kodiutil.ERROR()
            return

        kodigui.BaseDialog.onAction(self, action)

    def start(self):
        self.updateSequenceSelection()
        items = []
        for f in self.features:
            mli = kodigui.ManagedListItem(f.title, f.durationMinutesDisplay, thumbnailImage=f.thumb, data_source=f)
            mli.setProperty('rating', str(f.rating or '').replace(':', u' \u2022 '))
            mli.setProperty('year', str(f.year or ''))
            if f.audioFormat:
                mli.setProperty('af', f.audioFormat)
            elif f.codec and f.codec in CODEC_IMAGES:
                mli.setProperty('afcodec', f.codec)
                mli.setProperty('afchannels', str(f.channels or ''))
            mli.setProperty('genres', f.genres and u' \u2022 '.join(f.genres) or '')
            mli.setProperty('codec', str(f.codec or ''))
            mli.setProperty('channels', CHANNEL_STRINGS.get(f.channels, ''))
            items.append(mli)

        self.videoListControl.addItems(items)
        xbmc.sleep(100)
        self.setFocusId(self.PLAY_BUTTON_ID)

    def queueHas3D(self):
        for f in self.features:
            if f.is3D:
                return True
        return False

    def updateSequenceSelection(self):
        if self.sequencePath:
            return

        seqPath, name = cvutil.getSequencePath(for_3D=self.queueHas3D(), with_name=True)
        if not seqPath:
            return

        self.getControl(self.SEQUENCE_SELECT_ID).setLabel(name)

    def delete(self):
        item = self.videoListControl.getSelectedItem()
        if not item:
            return

        # yes = xbmcgui.Dialog().yesno('Remove', '', 'Remove?')
        yes = True
        if yes:
            self.videoListControl.removeItem(item.pos())
            self.updateReturn()
            self.updateSequenceSelection()

    def updateReturn(self):
        self.features = [i.dataSource for i in self.videoListControl]
        if not self.features:
            self.setFocusId(self.CANCEL_BUTTON_ID)

    def moveItem(self, move=False):
        if move:
            if self.moving:
                pos = self.videoListControl.getSelectedPosition()
                self.videoListControl.moveItem(self.moving, pos)
        else:
            if self.moving:
                self.moving.setProperty('moving', '')
                self.moving = None
                self.updateReturn()
            else:
                item = self.videoListControl.getSelectedItem()
                self.moving = item
                item.setProperty('moving', '1')

    def apply(self):
        from kodijsonrpc import rpc

        rpc.Playlist.Clear(playlistid=xbmc.PLAYLIST_VIDEO)

        for i in self.videoListControl:
            f = i.dataSource
            if f.dbType == 'movie':
                item = {'movieid': f.ID}
            elif f.dbType == 'tvshow':
                item = {'episodeid': f.ID}
            else:
                item = {'file': f.path}

            rpc.Playlist.Add(playlistid=xbmc.PLAYLIST_VIDEO, item=item)

    def selectSequence(self):
        selection = cvutil.selectSequence()
        if not selection:
            return

        self.sequencePath = selection['path']
        self.getControl(self.SEQUENCE_SELECT_ID).setLabel(selection['name'])
