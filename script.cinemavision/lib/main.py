import os

import xbmcgui
import xbmcvfs

import kodiutil
import kodigui

from kodiutil import T

kodiutil.LOG('Version: {0}'.format(kodiutil.ADDON.getAddonInfo('version')))

import cvutil

from lib import cinemavision


class ItemSettingsWindow(kodigui.BaseDialog):
    xmlFile = 'script.cinemavision-sequence-item-settings.xml'
    path = kodiutil.ADDON_PATH
    theme = 'Main'
    res = '1080i'

    SETTINGS_LIST_ID = 300
    SLIDER_ID = 401

    def __init__(self, *args, **kwargs):
        kodigui.BaseDialog.__init__(self, *args, **kwargs)
        self.main = kwargs['main']
        self.item = kwargs['item']
        self.pos = self.item.pos()
        seqSize = self.main.sequenceControl.size() - 1
        self.leftOffset = int((self.pos + 1) / 2) - 1
        self.rightOffset = int((seqSize - (self.pos + 1)) / 2)
        self.modified = False

    def onFirstInit(self):
        self.settingsList = kodigui.ManagedControlList(self, self.SETTINGS_LIST_ID, 10)
        self.sliderControl = self.getControl(self.SLIDER_ID)
        self.fillSettingsList()
        self.updateItem()

    def fillSettingsList(self, update=False):
        sItem = self.item.dataSource

        items = []
        for i, e in enumerate(sItem._elements):
            if not sItem.elementVisible(e):
                continue
            attr = e['attr']
            mli = kodigui.ManagedListItem(
                e['name'], e['limits'] != cinemavision.sequence.LIMIT_ACTION and unicode(sItem.getSettingDisplay(attr)) or '', data_source=attr
            )
            if sItem.getType(attr) == int:
                mli.setProperty('type', 'integer')
            items.append(mli)

        if update:
            self.settingsList.replaceItems(items)
        else:
            self.settingsList.reset()
            self.settingsList.addItems(items)

        self.setFocusId(self.SETTINGS_LIST_ID)

    def onAction(self, action):
        try:
            # print action.getId()
            if action == xbmcgui.ACTION_MOVE_LEFT:
                self.moveLeft()
            elif action == xbmcgui.ACTION_MOVE_RIGHT:
                self.moveRight()
            elif action == xbmcgui.ACTION_MOUSE_DRAG:
                self.dragSlider()
            else:
                self.updateItem()

        except:
            kodiutil.ERROR()
            kodigui.BaseDialog.onAction(self, action)
            return

        kodigui.BaseDialog.onAction(self, action)

    def onClick(self, controlID):
        if not controlID == self.SETTINGS_LIST_ID:
            return

        self.editItemSetting()

    def dragSlider(self):
        item = self.settingsList.getSelectedItem()
        if not item or not item.getProperty('type') == 'integer':
            return

        pct = self.sliderControl.getPercent()

        sItem = self.item.dataSource
        attr = item.dataSource
        limits = self.getLimits(sItem, attr)
        total = limits[1] - limits[0]
        val = int(round(((pct/100.0) * total) + limits[0]))
        val = val - (val % limits[2])
        sItem.setSetting(attr, val)

        item.setLabel2(sItem.getSettingDisplay(attr))

        self.modified = True

        self.main.updateSpecials()
        self.main.updateItemSettings(self.item)

    def updateItem(self):
        item = self.settingsList.getSelectedItem()
        if not item or not item.getProperty('type') == 'integer':
            return

        sItem = self.item.dataSource
        attr = item.dataSource
        if item.getProperty('type') == 'integer':
            val = sItem.getSetting(attr)
            self.updateSlider(val, *self.getLimits(sItem, attr))

        self.main.updateItemSettings(self.item)

    def moveLeft(self):
        self.moveLR(-1)

    def moveRight(self):
        self.moveLR(1)

    def moveLR(self, offset):
        item = self.settingsList.getSelectedItem()
        if not item or not item.getProperty('type') == 'integer':
            return

        sItem = self.item.dataSource
        attr = item.dataSource
        val = sItem.getSetting(attr)
        limits = self.getLimits(sItem, attr)

        val += offset * limits[2]

        if not limits[0] <= val <= limits[1]:
            return

        sItem.setSetting(attr, val)
        self.updateSlider(val, *limits)
        item.setLabel2(sItem.getSettingDisplay(attr))

        self.modified = True

        self.main.updateSpecials()
        self.main.updateItemSettings(self.item)

    def updateSlider(self, val, min_val, max_val, step):
        total = max_val - min_val
        val = val - min_val
        pct = (val/float(total)) * 100
        self.sliderControl.setPercent(pct)

    def getLimits(self, sItem, attr):
        limits = sItem.getLimits(attr)
        if sItem._type == 'command':
            if sItem.command == 'back':
                return (limits[0], min(limits[1], self.leftOffset), limits[2])
            elif sItem.command == 'skip':
                return (limits[0], min(limits[1], self.rightOffset), limits[2])

        return limits

    def editItemSetting(self):
        self._editItemSetting()
        self.fillSettingsList(update=True)

    def _editItemSetting(self):
        item = self.settingsList.getSelectedItem()
        if not item or item.getProperty('type') == 'integer':
            return

        sItem = self.item.dataSource

        attr = item.dataSource

        options = sItem.getSettingOptions(attr)

        if options in (cinemavision.sequence.LIMIT_FILE, cinemavision.sequence.LIMIT_FILE_DEFAULT):
            select = True
            if sItem.getSetting(attr):
                yes = xbmcgui.Dialog().yesno(
                    T(32517, 'Change Path'),
                    '',
                    T(32518, 'Would choose a new path, or clear the current path?'),
                    '',
                    T(32519, 'Choose'),
                    T(32520, 'Clear')
                )
                if yes:
                    if options == cinemavision.sequence.LIMIT_FILE:
                        value = ''
                    else:
                        value = None
                    select = False

            if select:
                value = xbmcgui.Dialog().browse(1, T(32521, 'Select File'), 'files', None, False, False, sItem.getSetting(attr))
                if not value:
                    return
                value = value.decode('utf-8')
        elif options == cinemavision.sequence.LIMIT_DB_CHOICE:
            options = sItem.DBChoices(attr)
            if not options:
                xbmcgui.Dialog().ok(T(32508, 'No Content'), '', T(32522, 'No matching content found.'))
                return False
            options.insert(0, (None, T(32322, 'Default')))
            idx = xbmcgui.Dialog().select(T(32523, 'Options'), [x[1] for x in options])
            if idx < 0:
                return False
            value = options[idx][0]
        elif options == cinemavision.sequence.LIMIT_DIR:
            select = True
            if sItem.getSetting(attr):
                yes = xbmcgui.Dialog().yesno(
                    T(32517, 'Change Path'),
                    '',
                    T(32518, 'Choose a new path or clear the current path?'),
                    '',
                    T(32520, 'Clear'),
                    T(32519, 'Choose')
                )
                if yes:
                    value = None
                    select = False

            if select:
                value = xbmcgui.Dialog().browse(0, T(32524, 'Select Directory'), 'files')
                if not value:
                    return
                value = value.decode('utf-8')
        elif options == cinemavision.sequence.LIMIT_MULTI_SELECT:
            options = sItem.Select(attr)
            if not options:
                xbmcgui.Dialog().ok(T(32525, 'No Options'), '', T(32526, 'No options found.'))
                return False
            result = cvutil.multiSelect(options)
            if result is False:
                return False
            value = result
        elif options == cinemavision.sequence.LIMIT_BOOL_DEFAULT:
            curr = sItem.getSetting(attr)
            if curr is None:
                value = True
            elif curr is True:
                value = False
            else:
                value = None
        elif options == cinemavision.sequence.LIMIT_BOOL:
            value = not sItem.getSetting(attr)
        elif options == cinemavision.sequence.LIMIT_ACTION:
            if self.item.dataSource._type == 'action':
                cvutil.evalActionFile(self.item.dataSource.file)
            return False
        elif isinstance(options, list):
            idx = xbmcgui.Dialog().select(T(32523, 'Options'), [x[1] for x in options])
            if idx < 0:
                return False
            value = options[idx][0]
        else:
            return False

        sItem.setSetting(attr, value)
        item.setLabel2(unicode(sItem.getSettingDisplay(attr)))

        self.modified = True

        self.main.updateItemSettings(self.item)

        if sItem._type == 'command' and attr == 'command':
            self.main.updateSpecials()


class SequenceEditorWindow(kodigui.BaseWindow):
    xmlFile = 'script.cinemavision-sequence-editor.xml'
    path = kodiutil.ADDON_PATH
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    SEQUENCE_LIST_ID = 201
    ADD_ITEM_LIST_ID = 202
    ITEM_OPTIONS_LIST_ID = 203

    def __init__(self, *args, **kwargs):
        kodigui.BaseWindow.__init__(self, *args, **kwargs)
        self.move = None
        self.modified = False
        self.setName('')
        self.path = ''

    def onFirstInit(self):
        self.sequenceControl = kodigui.ManagedControlList(self, self.SEQUENCE_LIST_ID, 22)
        self.addItemControl = kodigui.ManagedControlList(self, self.ADD_ITEM_LIST_ID, 22)
        self.itemOptionsControl = kodigui.ManagedControlList(self, self.ITEM_OPTIONS_LIST_ID, 22)
        self.start()

    def onClick(self, controlID):
        if self.focusedOnItem():
            self.itemOptions()
        else:
            self.addItem()
            self.updateFocus(pre=True)

    def onAction(self, action):
        try:
            if action == xbmcgui.ACTION_PREVIOUS_MENU or action == xbmcgui.ACTION_NAV_BACK:
                if self.handleClose():
                    return

            if self.move:
                if action == xbmcgui.ACTION_MOVE_LEFT:
                    pos2 = self.sequenceControl.getSelectedPosition()
                    pos1 = pos2 - 2
                    if self.sequenceControl.swapItems(pos1, pos2):
                        self.sequenceControl.selectItem(pos1)
                    self.updateSpecials()
                    return
                elif action == xbmcgui.ACTION_MOVE_RIGHT:
                    pos1 = self.sequenceControl.getSelectedPosition()
                    pos2 = pos1 + 2
                    if self.sequenceControl.swapItems(pos1, pos2):
                        self.sequenceControl.selectItem(pos2)
                    self.updateSpecials()
                    return
            else:
                if action == xbmcgui.ACTION_MOVE_LEFT or (action == xbmcgui.ACTION_MOUSE_WHEEL_UP and self.mouseYTrans(action.getAmount2()) < 505):
                    if self.sequenceControl.size() < 2:
                        return
                    pos = self.sequenceControl.getSelectedPosition()
                    pos -= 1
                    if not self.sequenceControl.positionIsValid(pos):
                        pos = self.sequenceControl.size() - 1
                        self.sequenceControl.selectItem(pos)
                    else:
                        self.sequenceControl.selectItem(pos)
                        self.updateFocus(pre=True)
                elif action == xbmcgui.ACTION_MOVE_RIGHT or (action == xbmcgui.ACTION_MOUSE_WHEEL_DOWN and self.mouseYTrans(action.getAmount2()) < 505):
                    if self.sequenceControl.size() < 2:
                        return
                    pos = self.sequenceControl.getSelectedPosition()
                    pos += 1
                    if not self.sequenceControl.positionIsValid(pos):
                        pos = 0
                        self.sequenceControl.selectItem(pos)
                    else:
                        self.sequenceControl.selectItem(pos)
                        self.updateFocus(pre=True)
                elif action == xbmcgui.ACTION_CONTEXT_MENU:
                        self.doMenu()

        except:
            kodiutil.ERROR()

        kodigui.BaseWindow.onAction(self, action)

    def handleClose(self):
        yes = True
        if self.modified:
            yes = xbmcgui.Dialog().yesno(
                T(32527, 'Confirm'),
                T(32528, 'Sequence was modified.'),
                '',
                T(32529, 'Do you really want to exit without saving changes?')
            )

        if yes:
            return False

        self.save(as_new=True)

        return True

    def updateFocus(self, pre=False):
        if (pre and not self.focusedOnItem()) or (not pre and self.focusedOnItem()):
            self.setFocusId(self.ITEM_OPTIONS_LIST_ID)
        else:
            self.setFocusId(self.ADD_ITEM_LIST_ID)

    def start(self):
        self.loadContent()
        self.fillOptions()
        self.fillSequence()
        self.loadDefault()

    def loadContent(self):
        if self.checkForContentDB() and not kodiutil.getSetting('database.autoUpdate', False):
            return

        cvutil.loadContent()

    def checkForContentDB(self):
        if kodiutil.getSetting('content.path'):
            kodiutil.setGlobalProperty('DEMO_MODE', '')
            return kodiutil.getSetting('content.initialized', False)
        else:
            kodiutil.setGlobalProperty('DEMO_MODE', '1')
            return True

    def fillOptions(self):
        for i in cinemavision.sequence.ITEM_TYPES:
            item = kodigui.ManagedListItem(
                '{0}: {1}'.format(T(32530, 'Add'), i[1]),
                thumbnailImage='small/script.cinemavision-{0}.png'.format(i[2]),
                data_source=i[0]
            )
            item.setProperty('thumb.focus', 'small/script.cinemavision-{0}_selected.png'.format(i[2]))
            self.addItemControl.addItem(item)

        item = kodigui.ManagedListItem(T(32531, 'Edit'), T(32531, 'Edit'), thumbnailImage='small/script.cinemavision-edit.png', data_source='edit')
        item.setProperty('alt.thumb', 'small/script.cinemavision-edit.png')
        item.setProperty('thumb.focus', 'small/script.cinemavision-A_selected.png')
        self.itemOptionsControl.addItem(item)

        item = kodigui.ManagedListItem(T(32532, 'Rename'), T(32532, 'Rename'), thumbnailImage='small/script.cinemavision-rename.png', data_source='rename')
        item.setProperty('alt.thumb', 'small/script.cinemavision-rename.png')
        item.setProperty('thumb.focus', 'small/script.cinemavision-A_selected.png')
        self.itemOptionsControl.addItem(item)

        item = kodigui.ManagedListItem(T(32533, 'Copy'), T(32533, 'Copy'), thumbnailImage='small/script.cinemavision-copy.png', data_source='copy')
        item.setProperty('alt.thumb', 'small/script.cinemavision-copy.png')
        item.setProperty('thumb.focus', 'small/script.cinemavision-A_selected.png')
        self.itemOptionsControl.addItem(item)

        item = kodigui.ManagedListItem(T(32534, 'Move'), T(32534, 'Move'), thumbnailImage='small/script.cinemavision-move.png', data_source='move')
        item.setProperty('alt.thumb', 'small/script.cinemavision-move.png')
        item.setProperty('thumb.focus', 'small/script.cinemavision-A_selected.png')
        self.itemOptionsControl.addItem(item)

        item = kodigui.ManagedListItem(T(32535, 'Disable'), T(32535, 'Disable'), thumbnailImage='small/script.cinemavision-disable.png', data_source='enable')
        item.setProperty('alt.thumb', 'small/script.cinemavision-enable.png')
        item.setProperty('thumb.focus', 'small/script.cinemavision-A_selected.png')
        self.itemOptionsControl.addItem(item)

        item = kodigui.ManagedListItem(T(32536, 'Remove'), T(32536, 'Remove'), thumbnailImage='small/script.cinemavision-minus.png', data_source='remove')
        item.setProperty('alt.thumb', 'small/script.cinemavision-minus.png')
        item.setProperty('thumb.focus', 'small/script.cinemavision-A_selected.png')
        self.itemOptionsControl.addItem(item)

    def fillSequence(self):
        mli = kodigui.ManagedListItem()

        self.sequenceControl.addItem(mli)
        # self.setFocusId(self.SEQUENCE_LIST_ID)

    def addItem(self):
        item = self.addItemControl.getSelectedItem()
        if not item:
            return

        pos = self.sequenceControl.getSelectedPosition()

        sItem = cinemavision.sequence.getItem(item.dataSource)()

        self.insertItem(sItem, pos)

    def insertItem(self, sItem, pos):
        mli = kodigui.ManagedListItem(sItem.display(), data_source=sItem)
        mli.setProperty('type', sItem.fileChar)
        mli.setProperty('type.name', sItem.displayName)
        mli.setProperty('enabled', sItem.enabled and '1' or '')

        self.updateItemSettings(mli)

        self.sequenceControl.insertItem(pos, mli)
        self.sequenceControl.insertItem(pos, kodigui.ManagedListItem())

        self.updateFirstLast()

        self.modified = True
        self.updateSpecials()

    def addItems(self, items):
        final = []
        for sItem in items:
            mli = kodigui.ManagedListItem(sItem.display(), data_source=sItem)
            mli.setProperty('type', sItem.fileChar)
            mli.setProperty('type.name', sItem.displayName)
            mli.setProperty('enabled', sItem.enabled and '1' or '')

            self.updateItemSettings(mli)

            final.append(mli)
            final.append(kodigui.ManagedListItem())

        self.sequenceControl.addItems(final)

        # Helix has navigation issue if this is not done
        dummy = kodigui.ManagedListItem()
        self.sequenceControl.addItem(dummy)
        self.sequenceControl.removeItem(dummy.pos())

        self.updateFirstLast()

        self.modified = True
        self.updateSpecials()

    def updateFirstLast(self):
        for i in self.sequenceControl:
            i.setProperty('first', '')
            i.setProperty('last', '')
            i.setProperty('second', '')
            i.setProperty('almost.last', '')
        self.sequenceControl[0].setProperty('first', '1')
        self.sequenceControl[self.sequenceControl.size() - 1].setProperty('last', '1')
        if self.sequenceControl.size() > 1:
            self.sequenceControl[1].setProperty('second', '1')
            self.sequenceControl[self.sequenceControl.size() - 2].setProperty('almost.last', '1')

    def updateSpecials(self):
        skip = 0
        for i in self.sequenceControl:
            sItem = i.dataSource

            i.setProperty('connect.start', '')
            i.setProperty('connect.join', '')
            i.setProperty('connect.end', '')
            i.setProperty('connect.skip.start', '')
            i.setProperty('connect.skip.join', '')
            i.setProperty('connect.skip.end', '')

            if not sItem:
                continue

            i.setLabel(sItem.display())

            if sItem.enabled and sItem._type == 'command':
                if sItem.command == 'back':
                    pos = i.pos()
                    all = range(1, (sItem.arg * 2) + 1)
                    last = pos - all[-1]

                    i.setProperty('connect.end', '1')
                    prev = None

                    for x in all:
                        modPos = pos - x
                        if modPos < 0:
                            break
                        item = self.sequenceControl[modPos]
                        if not item.dataSource:
                            continue

                        if item.dataSource._type == 'command' and item.dataSource.command == 'back':
                            if prev:
                                prev.setProperty('connect.start', '1')
                                prev.setProperty('connect.join', '')
                            break

                        if modPos == 1 or modPos == last:
                            item.setProperty('connect.start', '1')
                        else:
                            item.setProperty('connect.join', '1')

                        prev = item
                elif sItem.command == 'skip':
                    skip = sItem.arg
                    i.setProperty('connect.skip.start', '1')

            if skip:
                if not i.getProperty('connect.skip.start'):
                    skip -= 1
                    if skip == 0:
                        i.setProperty('connect.skip.end', '1')
                    else:
                        i.setProperty('connect.skip.join', '1')

    def itemOptions(self):
        if self.move:
            return self.moveItem()
        item = self.itemOptionsControl.getSelectedItem()
        if not item:
            return

        if item.dataSource == 'enable':
            self.toggleItemEnabled()
        elif item.dataSource == 'remove':
            self.removeItem()
            self.updateFocus()
        elif item.dataSource == 'copy':
            self.copyItem()
            self.updateFocus()
        elif item.dataSource == 'move':
            self.moveItem()
        elif item.dataSource == 'edit':
            self.editItem()
            self.updateFocus()
        elif item.dataSource == 'rename':
            self.renameItem()

        self.updateSpecials()

    def toggleItemEnabled(self):
        item = self.sequenceControl.getSelectedItem()
        if not item:
            return

        sItem = item.dataSource
        sItem.enabled = not sItem.enabled
        item.setProperty('enabled', sItem.enabled and '1' or '')
        self.updateItemSettings(item)

        self.modified = True

    def removeItem(self):
        if not xbmcgui.Dialog().yesno(T(32527, 'Confirm'), '', T(32537, 'Do you really want to remove this module?')):
            return

        pos = self.sequenceControl.getSelectedPosition()
        if pos < 0:
            return
        self.sequenceControl.removeItem(pos)
        self.sequenceControl.removeItem(pos)

        self.updateFirstLast()

        self.modified = True

    def copyItem(self):
        item = self.sequenceControl.getSelectedItem()
        if not item:
            return

        sItem = item.dataSource.copy()

        self.insertItem(sItem, item.pos() + 1)

    def moveItem(self):
        item = self.sequenceControl.getSelectedItem()
        if not item:
            return
        if self.move:
            kodiutil.DEBUG_LOG('Move item: Finished')
            self.move.setProperty('moving', '')
            self.move = None
            self.modified = True
        else:
            kodiutil.DEBUG_LOG('Move item: Started')
            self.move = item
            self.move.setProperty('moving', '1')

    def editItem(self):
        item = self.sequenceControl.getSelectedItem()
        if not item:
            return
        isw = ItemSettingsWindow.open(main=self, item=item)

        self.updateItemSettings(item)

        if not self.modified:
            self.modified = isw.modified

    def updateItemSettings(self, item):
        sItem = item.dataSource

        ct = 0
        item.setProperty('setting{0}'.format(ct), sItem.enabled and T(32320, 'Yes') or T(32321, 'No'))
        item.setProperty('setting{0}_name'.format(ct), T(32538, 'Enabled'))
        ct += 1
        for e in sItem._elements:
            if not sItem.elementVisible(e):
                continue

            if e['limits'] == cinemavision.sequence.LIMIT_ACTION:
                continue

            disp = sItem.getSettingDisplay(e['attr'])
            item.setProperty('setting{0}'.format(ct), disp)
            item.setProperty('setting{0}_name'.format(ct), e['name'])
            ct += 1
        for i in range(ct, 8):
            item.setProperty('setting{0}'.format(i), '')
            item.setProperty('setting{0}_name'.format(i), '')

    def renameItem(self):
        item = self.sequenceControl.getSelectedItem()
        if not item:
            return

        sItem = item.dataSource

        name = xbmcgui.Dialog().input(T(32539, 'Enter a name for this item'), sItem.name)

        if name == sItem.name:
            return

        sItem.name = name or ''

        self.modified = True

    def focusedOnItem(self):
        item = self.sequenceControl.getSelectedItem()
        return bool(item.dataSource)

    def doMenu(self):
        options = []
        options.append(('settings', T(32540, 'Add-on settings')))
        options.append(('new', T(32541, 'New')))
        options.append(('save', T(32542, 'Save')))
        options.append(('saveas', T(32543, 'Save as...')))
        options.append(('load', T(32544, 'Load')))
        options.append(('import', T(32545, 'Import')))
        options.append(('export', T(32546, 'Export')))
        options.append(('test', T(32547, 'Play')))
        idx = xbmcgui.Dialog().select(T(32548, 'Sequence Options'), [o[1] for o in options])
        if idx < 0:
            return
        option = options[idx][0]

        if option == 'settings':
            self.settings()
        elif option == 'new':
            self.new()
        elif option == 'save':
            self.save()
        elif option == 'saveas':
            self.save(as_new=True)
        elif option == 'load':
            self.load()
        elif option == 'import':
            self.load(import_=True)
        elif option == 'export':
            self.save(export=True)
        elif option == 'test':
            self.test()

    def settings(self):
        kodiutil.ADDON.openSettings()

        kodiutil.setScope()
        cinemavision.init(kodiutil.DEBUG())

        for item in self.sequenceControl:
            if item.dataSource:
                self.updateItemSettings(item)

        if not self.checkForContentDB():
            cvutil.loadContent()

    def test(self):
        import experience

        savePath = os.path.join(kodiutil.PROFILE_PATH, 'temp.cvseq')
        self._save(savePath, temp=True)

        e = experience.ExperiencePlayer().create(from_editor=True)
        e.start(savePath)

    def abortOnModified(self):
        if self.modified:
            if not xbmcgui.Dialog().yesno(
                T(32527, 'Confirm'),
                T(32549, 'Sequence is modified.'),
                T(32550, 'This will delete all changes.'),
                T(32551, 'Do you really want to do this?')
            ):
                return True
        return False

    def new(self):
        if self.abortOnModified():
            return

        self.setName('')
        self.sequenceControl.reset()
        self.fillSequence()
        self.setFocusId(self.ADD_ITEM_LIST_ID)

    def savePath(self, path=None, name=None):
        name = name or self.name
        if not path:
            contentPath = kodiutil.getSetting('content.path')
            if not contentPath:
                return

            path = cinemavision.util.pathJoin(contentPath, 'Sequences')

        if not name or not path:
            return None
        if name.endswith('.cvseq'):
            name = name[:-6]
        return cinemavision.util.pathJoin(path, name) + '.cvseq'

    def setName(self, name):
        self.name = name
        kodiutil.setGlobalProperty('EDITING', name)

    def defaultSavePath(self):
        return cvutil.defaultSavePath()

    def save(self, as_new=False, export=False):
        if export:
            path = xbmcgui.Dialog().browse(3, T(32552, 'Select Save Directory'), 'files', None, False, False)
            if not path:
                return
        else:
            contentPath = kodiutil.getSetting('content.path')
            if not contentPath:
                xbmcgui.Dialog().ok(T(32503, 'No Content Path'), ' ', T(32553, 'Please set the content path in addon settings.'))
                return

            path = cinemavision.util.pathJoin(contentPath, 'Sequences')

        name = self.name

        if not name or as_new or export:
            name = xbmcgui.Dialog().input(T(32554, 'Enter name for file'), name)
            if not name:
                return

            if not export:
                self.setName(name)

        fullPath = self.savePath(path, name)

        self._save(fullPath, temp=export)

    def _save(self, full_path, temp=False):
        items = [li.dataSource for li in self.sequenceControl if li.dataSource]
        xmlString = cinemavision.sequence.getSaveString(items)

        kodiutil.DEBUG_LOG('Saving to: {0}'.format(full_path))

        f = xbmcvfs.File(full_path, 'w')
        f.write(xmlString)
        f.close()

        if not temp:
            self.modified = False
            self.saveDefault()

            sequence2D = kodiutil.getSetting('sequence.2D')
            sequence3D = kodiutil.getSetting('sequence.3D')
            if not sequence2D or (self.name != sequence2D and self.name != sequence3D):
                yes = xbmcgui.Dialog().yesno(T(32555, 'Set Default'), T(32556, 'Would you like to set this as the default for playback?'))
                if yes:
                    as3D = xbmcgui.Dialog().yesno('2D/3D', T(32557, 'For 2D or 3D?'), nolabel='2D', yeslabel='3D')
                    if as3D:
                        kodiutil.setSetting('sequence.3D', self.name)
                    else:
                        kodiutil.setSetting('sequence.2D', self.name)

    def load(self, import_=False):
        if self.abortOnModified():
            return

        if import_:
            path = xbmcgui.Dialog().browse(1, T(32521, 'Select File'), 'files', '*.cvseq', False, False)
            if not path:
                return
        else:
            selection = cvutil.selectSequence()

            if not selection:
                return

            path = selection['path']

        self._load(path)

        sep = cinemavision.util.getSep(path)

        self.path, name = path.rsplit(sep, 1)
        self.path += sep
        self.setName(name.rsplit('.', 1)[0])

        self.saveDefault()

    def _load(self, path):
        f = xbmcvfs.File(path, 'r')
        xmlString = f.read().decode('utf-8')
        f.close()
        sItems = cinemavision.sequence.getItemsFromString(xmlString)
        self.sequenceControl.reset()
        self.fillSequence()

        self.addItems(sItems)

        if self.sequenceControl.positionIsValid(1):
            self.sequenceControl.selectItem(1)
            self.setFocusId(self.ITEM_OPTIONS_LIST_ID)
        else:
            self.setFocusId(self.ADD_ITEM_LIST_ID)

        self.modified = False

    def saveDefault(self, force=True):
        if (not self.name or not self.path) and not force:
            return
        kodiutil.setSetting('save.name', self.name)
        kodiutil.setSetting('save.path', self.path)

    def loadDefault(self):
        self.setName(kodiutil.getSetting('save.name', ''))

        if not self.name:
            savePath = self.defaultSavePath()
        else:
            savePath = self.savePath()
            if not xbmcvfs.exists(savePath):
                self.setName('')
                self.saveDefault(force=True)
                new = xbmcgui.Dialog().yesno(
                    T(32558, 'Missing'),
                    T(32559, 'Previous save not found.'),
                    '',
                    T(32560, 'Load the default or start a new sequence?'),
                    T(32322, 'Default'),
                    T(32541, 'New')
                )
                if new:
                    self.setName('')
                    self.setFocusId(self.ADD_ITEM_LIST_ID)
                    return
                else:
                    savePath = self.defaultSavePath()

        kodiutil.DEBUG_LOG('Loading previous save: {0}'.format(savePath))

        self._load(savePath)

        kodiutil.DEBUG_LOG('Previous save loaded')


def main():
    kodiutil.checkAPILevel()
    kodiutil.setScope()
    kodiutil.setGlobalProperty('VERSION', kodiutil.ADDON.getAddonInfo('version'))
    kodiutil.LOG('Sequence editor: OPENING')
    SequenceEditorWindow.open()
    kodiutil.LOG('Sequence editor: CLOSED')
