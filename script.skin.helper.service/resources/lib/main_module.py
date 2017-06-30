#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
    script.skin.helper.service
    Helper service and scripts for Kodi skins
    mainmodule.py
    All script methods provided by the addon
'''

import xbmc
import xbmcvfs
import xbmcgui
import xbmcaddon
from skinsettings import SkinSettings
from simplecache import SimpleCache
from utils import log_msg, KODI_VERSION
from utils import log_exception, get_current_content_type, ADDON_ID, recursive_delete_dir
from dialogselect import DialogSelect
from xml.dom.minidom import parse
from metadatautils import KodiDb, process_method_on_list
import urlparse
import sys


class MainModule:
    '''mainmodule provides the script methods for the skinhelper addon'''

    def __init__(self):
        '''Initialization and main code run'''
        self.win = xbmcgui.Window(10000)
        self.addon = xbmcaddon.Addon(ADDON_ID)
        self.kodidb = KodiDb()
        self.cache = SimpleCache()

        self.params = self.get_params()
        log_msg("MainModule called with parameters: %s" % self.params)
        action = self.params.get("action", "")
        # launch module for action provided by this script
        try:
            getattr(self, action)()
        except AttributeError:
            log_exception(__name__, "No such action: %s" % action)
        except Exception as exc:
            log_exception(__name__, exc)
        finally:
            xbmc.executebuiltin("dialog.Close(busydialog)")

        # do cleanup
        self.close()

    def close(self):
        '''Cleanup Kodi Cpython instances on exit'''
        self.cache.close()
        del self.win
        del self.addon
        del self.kodidb
        log_msg("MainModule exited")

    @classmethod
    def get_params(self):
        '''extract the params from the called script path'''
        params = {}
        for arg in sys.argv[1:]:
            paramname = arg.split('=')[0]
            paramvalue = arg.replace(paramname + "=", "")
            paramname = paramname.lower()
            if paramname == "action":
                paramvalue = paramvalue.lower()
            params[paramname] = paramvalue
        return params

    def deprecated_method(self, newaddon):
        '''
            used when one of the deprecated methods is called
            print warning in log and call the external script with the same parameters
        '''
        action = self.params.get("action")
        log_msg("Deprecated method: %s. Please call %s directly" % (action, newaddon), xbmc.LOGWARNING)
        paramstring = ""
        for key, value in self.params.iteritems():
            paramstring += ",%s=%s" % (key, value)
        if xbmc.getCondVisibility("System.HasAddon(%s)" % newaddon):
            xbmc.executebuiltin("RunAddon(%s%s)" % (newaddon, paramstring))
        else:
            # trigger install of the addon
            if KODI_VERSION > 16:
                xbmc.executebuiltin("InstallAddon(%s)" % newaddon)
            else:
                xbmc.executebuiltin("RunPlugin(plugin://%s)" % newaddon)

    @staticmethod
    def musicsearch():
        '''helper to go directly to music search dialog'''
        xbmc.executebuiltin("ActivateWindow(Music)")
        xbmc.executebuiltin("SendClick(8)")

    def setview(self):
        '''sets the selected viewmode for the container'''
        xbmc.executebuiltin("ActivateWindow(busydialog)")
        content_type = get_current_content_type()
        if not content_type:
            content_type = "files"
        current_view = xbmc.getInfoLabel("Container.Viewmode").decode("utf-8")
        view_id, view_label = self.selectview(content_type, current_view)
        current_forced_view = xbmc.getInfoLabel("Skin.String(SkinHelper.ForcedViews.%s)" % content_type)

        if view_id is not None:
            # also store forced view
            if (content_type and current_forced_view and current_forced_view != "None" and
                    xbmc.getCondVisibility("Skin.HasSetting(SkinHelper.ForcedViews.Enabled)")):
                xbmc.executebuiltin("Skin.SetString(SkinHelper.ForcedViews.%s,%s)" % (content_type, view_id))
                xbmc.executebuiltin("Skin.SetString(SkinHelper.ForcedViews.%s.label,%s)" % (content_type, view_label))
                self.win.setProperty("SkinHelper.ForcedView", view_id)
                if not xbmc.getCondVisibility("Control.HasFocus(%s)" % current_forced_view):
                    xbmc.sleep(100)
                    xbmc.executebuiltin("Container.SetViewMode(%s)" % view_id)
                    xbmc.executebuiltin("SetFocus(%s)" % view_id)
            else:
                self.win.clearProperty("SkinHelper.ForcedView")
            # set view
            xbmc.executebuiltin("Container.SetViewMode(%s)" % view_id)

    def selectview(self, content_type="other", current_view=None, display_none=False):
        '''reads skinfile with all views to present a dialog to choose from'''
        cur_view_select_id = None
        label = ""
        all_views = []
        if display_none:
            listitem = xbmcgui.ListItem(label="None")
            listitem.setProperty("id", "None")
            all_views.append(listitem)
        # read the special skin views file
        views_file = xbmc.translatePath('special://skin/extras/views.xml').decode("utf-8")
        if xbmcvfs.exists(views_file):
            doc = parse(views_file)
            listing = doc.documentElement.getElementsByTagName('view')
            itemcount = 0
            for view in listing:
                label = xbmc.getLocalizedString(int(view.attributes['languageid'].nodeValue))
                viewid = view.attributes['value'].nodeValue
                mediatypes = view.attributes['type'].nodeValue.lower().split(",")
                if label.lower() == current_view.lower() or viewid == current_view:
                    cur_view_select_id = itemcount
                    if display_none:
                        cur_view_select_id += 1
                if (("all" in mediatypes or content_type.lower() in mediatypes) and
                    (not "!" + content_type.lower() in mediatypes) and not
                        xbmc.getCondVisibility("Skin.HasSetting(SkinHelper.view.Disabled.%s)" % viewid)):
                    image = "special://skin/extras/viewthumbs/%s.jpg" % viewid
                    listitem = xbmcgui.ListItem(label=label, iconImage=image)
                    listitem.setProperty("viewid", viewid)
                    listitem.setProperty("icon", image)
                    all_views.append(listitem)
                    itemcount += 1
        dialog = DialogSelect("DialogSelect.xml", "", listing=all_views,
                              windowtitle=self.addon.getLocalizedString(32012), richlayout=True)
        dialog.autofocus_id = cur_view_select_id
        dialog.doModal()
        result = dialog.result
        del dialog
        if result:
            viewid = result.getProperty("viewid")
            label = result.getLabel().decode("utf-8")
            return (viewid, label)
        else:
            return (None, None)

    # pylint: disable-msg=too-many-local-variables
    def enableviews(self):
        '''show select dialog to enable/disable views'''
        all_views = []
        views_file = xbmc.translatePath('special://skin/extras/views.xml').decode("utf-8")
        richlayout = self.params.get("richlayout", "") == "true"
        if xbmcvfs.exists(views_file):
            doc = parse(views_file)
            listing = doc.documentElement.getElementsByTagName('view')
            for view in listing:
                view_id = view.attributes['value'].nodeValue
                label = xbmc.getLocalizedString(int(view.attributes['languageid'].nodeValue))
                desc = label + " (" + str(view_id) + ")"
                image = "special://skin/extras/viewthumbs/%s.jpg" % view_id
                listitem = xbmcgui.ListItem(label=label, label2=desc, iconImage=image)
                listitem.setProperty("viewid", view_id)
                if not xbmc.getCondVisibility("Skin.HasSetting(SkinHelper.view.Disabled.%s)" % view_id):
                    listitem.select(selected=True)
                excludefromdisable = False
                try:
                    excludefromdisable = view.attributes['excludefromdisable'].nodeValue == "true"
                except Exception:
                    pass
                if not excludefromdisable:
                    all_views.append(listitem)

        dialog = DialogSelect(
            "DialogSelect.xml",
            "",
            listing=all_views,
            windowtitle=self.addon.getLocalizedString(32013),
            multiselect=True, richlayout=richlayout)
        dialog.doModal()
        result = dialog.result
        del dialog
        if result:
            for item in result:
                view_id = item.getProperty("viewid")
                if item.isSelected():
                    # view is enabled
                    xbmc.executebuiltin("Skin.Reset(SkinHelper.view.Disabled.%s)" % view_id)
                else:
                    # view is disabled
                    xbmc.executebuiltin("Skin.SetBool(SkinHelper.view.Disabled.%s)" % view_id)
    # pylint: enable-msg=too-many-local-variables

    def setforcedview(self):
        '''helper that sets a forced view for a specific content type'''
        content_type = self.params.get("contenttype")
        if content_type:
            current_view = xbmc.getInfoLabel("Skin.String(SkinHelper.ForcedViews.%s)" % content_type)
            if not current_view:
                current_view = "0"
            view_id, view_label = self.selectview(content_type, current_view, True)
            if view_id or view_label:
                xbmc.executebuiltin("Skin.SetString(SkinHelper.ForcedViews.%s,%s)" % (content_type, view_id))
                xbmc.executebuiltin("Skin.SetString(SkinHelper.ForcedViews.%s.label,%s)" % (content_type, view_label))

    @staticmethod
    def get_youtube_listing(searchquery):
        '''get items from youtube plugin by query'''
        lib_path = u"plugin://plugin.video.youtube/kodion/search/query/?q=%s" % searchquery
        return KodiDb().files(lib_path)

    def searchyoutube(self):
        '''helper to search youtube for the given title'''
        xbmc.executebuiltin("ActivateWindow(busydialog)")
        title = self.params.get("title", "")
        window_header = self.params.get("header", "")
        results = []
        for media in self.get_youtube_listing(title):
            if not media["filetype"] == "directory":
                label = media["label"]
                label2 = media["plot"]
                image = ""
                if media.get('art'):
                    if media['art'].get('thumb'):
                        image = (media['art']['thumb'])
                listitem = xbmcgui.ListItem(label=label, label2=label2, iconImage=image)
                listitem.setProperty("path", media["file"])
                results.append(listitem)

        # finished lookup - display listing with results
        xbmc.executebuiltin("dialog.Close(busydialog)")
        dialog = DialogSelect("DialogSelect.xml", "", listing=results, windowtitle=window_header,
                              multiselect=False, richlayout=True)
        dialog.doModal()
        result = dialog.result
        del dialog
        if result:
            if xbmc.getCondVisibility(
                    "Window.IsActive(script-skin_helper_service-CustomInfo.xml) | "
                    "Window.IsActive(movieinformation)"):
                xbmc.executebuiltin("Dialog.Close(movieinformation)")
                xbmc.executebuiltin("Dialog.Close(script-skin_helper_service-CustomInfo.xml)")
                xbmc.sleep(1000)
            xbmc.executebuiltin('PlayMedia("%s")' % result.getProperty("path"))
            del result

    def getcastmedia(self):
        '''helper to show a dialog with all media for a specific actor'''
        xbmc.executebuiltin("ActivateWindow(busydialog)")
        name = self.params.get("name", "")
        window_header = self.params.get("name", "")
        results = []
        items = self.kodidb.castmedia(name)
        items = process_method_on_list(self.kodidb.prepare_listitem, items)
        for item in items:
            if item["file"].startswith("videodb://"):
                item["file"] = "ActivateWindow(Videos,%s,return)" % item["file"]
            else:
                item["file"] = 'PlayMedia("%s")' % item["file"]
            results.append(self.kodidb.create_listitem(item, False))
        # finished lookup - display listing with results
        xbmc.executebuiltin("dialog.Close(busydialog)")
        dialog = DialogSelect("DialogSelect.xml", "", listing=results, windowtitle=window_header, richlayout=True)
        dialog.doModal()
        result = dialog.result
        del dialog
        if result:
            while xbmc.getCondVisibility("System.HasModalDialog"):
                xbmc.executebuiltin("Action(Back)")
                xbmc.sleep(300)
            xbmc.executebuiltin(result.getfilename())
            del result

    def setfocus(self):
        '''helper to set focus on a list or control'''
        control = self.params.get("control")
        fallback = self.params.get("fallback")
        position = self.params.get("position", "0")
        relativeposition = self.params.get("relativeposition")
        if relativeposition:
            position = int(relativeposition) - 1
        count = 0
        if control:
            while not xbmc.getCondVisibility("Control.HasFocus(%s)" % control):
                if xbmc.getCondVisibility("Window.IsActive(busydialog)"):
                    xbmc.sleep(150)
                    continue
                elif count == 20 or (xbmc.getCondVisibility(
                        "!Control.IsVisible(%s) | "
                        "!IntegerGreaterThan(Container(%s).NumItems,0)" % (control, control))):
                    if fallback:
                        xbmc.executebuiltin("Control.SetFocus(%s)" % fallback)
                    break
                else:
                    xbmc.executebuiltin("Control.SetFocus(%s,%s)" % (control, position))
                    xbmc.sleep(50)
                    count += 1

    def setwidgetcontainer(self):
        '''helper that reports the current selected widget container/control'''
        controls = self.params.get("controls", "").split("-")
        if controls:
            xbmc.sleep(50)
            for i in range(10):
                for control in controls:
                    if xbmc.getCondVisibility("Control.IsVisible(%s) + IntegerGreaterThan(Container(%s).NumItems,0)"
                                              % (control, control)):
                        self.win.setProperty("SkinHelper.WidgetContainer", control)
                        return
                xbmc.sleep(50)
        self.win.clearProperty("SkinHelper.WidgetContainer")

    def saveskinimage(self):
        '''let the user select an image and save it to addon_data for easy backup'''
        skinstring = self.params.get("skinstring", "")
        allow_multi = self.params.get("multi", "") == "true"
        header = self.params.get("header", "")
        value = SkinSettings().save_skin_image(skinstring, allow_multi, header)
        if value:
            xbmc.executebuiltin("Skin.SetString(%s,%s)" % (skinstring.encode("utf-8"), value.encode("utf-8")))

    @staticmethod
    def checkskinsettings():
        '''performs check of all default skin settings and labels'''
        SkinSettings().correct_skin_settings()

    def setskinsetting(self):
        '''allows the user to set a skin setting with a select dialog'''
        setting = self.params.get("setting", "")
        org_id = self.params.get("id", "")
        if "$" in org_id:
            org_id = xbmc.getInfoLabel(org_id).decode("utf-8")
        header = self.params.get("header", "")
        SkinSettings().set_skin_setting(setting=setting, window_header=header, original_id=org_id)

    def setskinconstant(self):
        '''allows the user to set a skin constant with a select dialog'''
        setting = self.params.get("setting", "")
        value = self.params.get("value", "")
        header = self.params.get("header", "")
        SkinSettings().set_skin_constant(setting, header, value)

    def setskinconstants(self):
        '''allows the skinner to set multiple skin constants'''
        settings = self.params.get("settings", "").split("|")
        values = self.params.get("values", "").split("|")
        SkinSettings().set_skin_constants(settings, values)

    def setskinshortcutsproperty(self):
        '''allows the user to make a setting for skinshortcuts using the special skinsettings dialogs'''
        setting = self.params.get("setting", "")
        prop = self.params.get("property", "")
        header = self.params.get("header", "")
        SkinSettings().set_skinshortcuts_property(setting, header, prop)

    def togglekodisetting(self):
        '''toggle kodi setting'''
        settingname = self.params.get("setting", "")
        cur_value = xbmc.getCondVisibility("system.getbool(%s)" % settingname)
        if cur_value:
            new_value = "false"
        else:
            new_value = "true"
        xbmc.executeJSONRPC(
            '{"jsonrpc":"2.0", "id":1, "method":"Settings.SetSettingValue","params":{"setting":"%s","value":%s}}' %
            (settingname, new_value))

    def setkodisetting(self):
        '''set kodi setting'''
        settingname = self.params.get("setting", "")
        value = self.params.get("value", "")
        is_int = False
        try:
            valueint = int(value)
            is_int = True
            del valueint
        except Exception:
            pass
        if value.lower() == "true":
            value = 'true'
        elif value.lower() == "false":
            value = 'false'
        elif is_int:
            value = '"%s"' % value
        xbmc.executeJSONRPC('{"jsonrpc":"2.0", "id":1, "method":"Settings.SetSettingValue",\
            "params":{"setting":"%s","value":%s}}' % (settingname, value))

    def playtrailer(self):
        '''auto play windowed trailer inside video listing'''
        if not xbmc.getCondVisibility("Player.HasMedia | Container.Scrolling | Container.OnNext | "
                                      "Container.OnPrevious | !IsEmpty(Window(Home).Property(traileractionbusy))"):
            self.win.setProperty("traileractionbusy", "traileractionbusy")
            widget_container = self.params.get("widgetcontainer", "")
            trailer_mode = self.params.get("mode", "").replace("auto_", "")
            allow_youtube = self.params.get("youtube", "") == "true"
            if not trailer_mode:
                trailer_mode = "windowed"
            if widget_container:
                widget_container_prefix = "Container(%s)." % widget_container
            else:
                widget_container_prefix = ""

            li_title = xbmc.getInfoLabel("%sListItem.Title" % widget_container_prefix).decode('utf-8')
            li_trailer = xbmc.getInfoLabel("%sListItem.Trailer" % widget_container_prefix).decode('utf-8')
            if not li_trailer and allow_youtube:
                youtube_result = self.get_youtube_listing("%s Trailer" % li_title)
                if youtube_result:
                    li_trailer = youtube_result[0].get("file")
            # always wait a bit to prevent trailer start playing when we're scrolling the list
            xbmc.Monitor().waitForAbort(3)
            if li_trailer and (li_title == xbmc.getInfoLabel("%sListItem.Title"
                                                             % widget_container_prefix).decode('utf-8')):
                if trailer_mode == "fullscreen" and li_trailer:
                    xbmc.executebuiltin('PlayMedia("%s")' % li_trailer)
                else:
                    xbmc.executebuiltin('PlayMedia("%s",1)' % li_trailer)
                self.win.setProperty("TrailerPlaying", trailer_mode)
            self.win.clearProperty("traileractionbusy")

    def colorpicker(self):
        '''legacy'''
        self.deprecated_method("script.skin.helper.colorpicker")

    def backup(self):
        '''legacy'''
        self.deprecated_method("script.skin.helper.skinbackup")

    def restore(self):
        '''legacy'''
        self.deprecated_method("script.skin.helper.skinbackup")

    def reset(self):
        '''legacy'''
        self.deprecated_method("script.skin.helper.skinbackup")

    def colorthemes(self):
        '''legacy'''
        self.deprecated_method("script.skin.helper.skinbackup")

    def createcolortheme(self):
        '''legacy'''
        self.deprecated_method("script.skin.helper.skinbackup")

    def restorecolortheme(self):
        '''legacy'''
        self.deprecated_method("script.skin.helper.skinbackup")

    def conditionalbackgrounds(self):
        '''legacy'''
        self.deprecated_method("script.skin.helper.backgrounds")

    def splashscreen(self):
        '''helper to show a user defined splashscreen in the skin'''
        import time
        splashfile = self.params.get("file", "")
        duration = int(self.params.get("duration", 5))
        if (splashfile.lower().endswith("jpg") or splashfile.lower().endswith("gif") or
                splashfile.lower().endswith("png") or splashfile.lower().endswith("tiff")):
            # this is an image file
            self.win.setProperty("SkinHelper.SplashScreen", splashfile)
            # for images we just wait for X seconds to close the splash again
            start_time = time.time()
            while (time.time() - start_time) <= duration:
                xbmc.sleep(500)
        else:
            # for video or audio we have to wait for the player to finish...
            xbmc.Player().play(splashfile, windowed=True)
            xbmc.sleep(500)
            while xbmc.getCondVisibility("Player.HasMedia"):
                xbmc.sleep(150)
        # replace startup window with home
        startupwindow = xbmc.getInfoLabel("System.StartupWindow")
        xbmc.executebuiltin("ReplaceWindow(%s)" % startupwindow)
        autostart_playlist = xbmc.getInfoLabel("$ESCINFO[Skin.String(autostart_playlist)]")
        if autostart_playlist:
            xbmc.executebuiltin("PlayMedia(%s)" % autostart_playlist)

    def videosearch(self):
        '''show the special search dialog'''
        xbmc.executebuiltin("ActivateWindow(busydialog)")
        from resources.lib.searchdialog import SearchDialog
        search_dialog = SearchDialog("script-skin_helper_service-CustomSearch.xml",
                                     self.addon.getAddonInfo('path').decode("utf-8"), "Default", "1080i")
        search_dialog.doModal()
        del search_dialog

    def showinfo(self):
        '''shows our special videoinfo dialog'''
        dbid = self.params.get("dbid", "")
        dbtype = self.params.get("dbtype", "")
        from infodialog import show_infodialog
        show_infodialog(dbid, dbtype)

    def deletedir(self):
        '''helper to delete a directory, input can be normal filesystem path or vfs'''
        del_path = self.params.get("path")
        if del_path:
            ret = xbmcgui.Dialog().yesno(heading=xbmc.getLocalizedString(122),
                                         line1=u"%s[CR]%s" % (xbmc.getLocalizedString(125), del_path))
            if ret:
                success = recursive_delete_dir(del_path)
                if success:
                    xbmcgui.Dialog().ok(heading=xbmc.getLocalizedString(19179),
                                        line1=self.addon.getLocalizedString(32014))
                else:
                    xbmcgui.Dialog().ok(heading=xbmc.getLocalizedString(16205),
                                        line1=xbmc.getLocalizedString(32015))

    def overlaytexture(self):
        '''legacy: helper to let the user choose a background overlay from a skin defined folder'''
        skinstring = self.params.get("skinstring", "BackgroundOverlayTexture")
        self.params["skinstring"] = skinstring
        self.params["resourceaddon"] = "resource.images.backgroundoverlays"
        self.params["customfolder"] = "special://skin/extras/bgoverlays/"
        self.params["allowmulti"] = "false"
        self.params["header"] = self.addon.getLocalizedString(32002)
        self.selectimage()

    def busytexture(self):
        '''legacy: helper which lets the user select a busy spinner from predefined spinners in the skin'''
        skinstring = self.params.get("skinstring", "SkinHelper.SpinnerTexture")
        self.params["skinstring"] = skinstring
        self.params["resourceaddon"] = "resource.images.busyspinners"
        self.params["customfolder"] = "special://skin/extras/busy_spinners/"
        self.params["allowmulti"] = "true"
        self.params["header"] = self.addon.getLocalizedString(32006)
        self.selectimage()

    def selectimage(self):
        '''helper which lets the user select an image or imagepath from resourceaddons or custom path'''
        skinsettings = SkinSettings()
        skinstring = self.params.get("skinstring", "")
        skinshortcutsprop = self.params.get("skinshortcutsproperty", "")
        current_value = self.params.get("currentvalue", "")
        resource_addon = self.params.get("resourceaddon", "")
        allow_multi = self.params.get("allowmulti", "false") == "true"
        windowheader = self.params.get("header", "")
        skinhelper_backgrounds = self.params.get("skinhelperbackgrounds", "false") == "true"
        label, value = skinsettings.select_image(
            skinstring, allow_multi=allow_multi, windowheader=windowheader, resource_addon=resource_addon,
            skinhelper_backgrounds=skinhelper_backgrounds, current_value=current_value)
        if label:
            if skinshortcutsprop:
                # write value to skinshortcuts prop
                from skinshortcuts import set_skinshortcuts_property
                set_skinshortcuts_property(skinshortcutsprop, value, label)
            else:
                # write the values to skin strings
                if value.startswith("$INFO"):
                    # we got an dynamic image from window property
                    skinsettings.set_skin_variable(skinstring, value)
                    value = "$VAR[%s]" % skinstring
                skinstring = skinstring.encode("utf-8")
                label = label.encode("utf-8")
                xbmc.executebuiltin("Skin.SetString(%s.label,%s)" % (skinstring, label))
                xbmc.executebuiltin("Skin.SetString(%s.name,%s)" % (skinstring, label))
                xbmc.executebuiltin("Skin.SetString(%s,%s)" % (skinstring, value))
                xbmc.executebuiltin("Skin.SetString(%s.path,%s)" % (skinstring, value))
        del skinsettings

    def dialogok(self):
        '''helper to show an OK dialog with a message'''
        headertxt = self.params.get("header")
        bodytxt = self.params.get("message")
        if bodytxt.startswith(" "):
            bodytxt = bodytxt[1:]
        if headertxt.startswith(" "):
            headertxt = headertxt[1:]
        dialog = xbmcgui.Dialog()
        dialog.ok(heading=headertxt, line1=bodytxt)
        del dialog

    def dialogyesno(self):
        '''helper to show a YES/NO dialog with a message'''
        headertxt = self.params.get("header")
        bodytxt = self.params.get("message")
        yesactions = self.params.get("yesaction", "").split("|")
        noactions = self.params.get("noaction", "").split("|")
        if bodytxt.startswith(" "):
            bodytxt = bodytxt[1:]
        if headertxt.startswith(" "):
            headertxt = headertxt[1:]
        if xbmcgui.Dialog().yesno(heading=headertxt, line1=bodytxt):
            for action in yesactions:
                xbmc.executebuiltin(action.encode("utf-8"))
        else:
            for action in noactions:
                xbmc.executebuiltin(action.encode("utf-8"))

    def textviewer(self):
        '''helper to show a textviewer dialog with a message'''
        headertxt = self.params.get("header", "")
        bodytxt = self.params.get("message", "")
        if bodytxt.startswith(" "):
            bodytxt = bodytxt[1:]
        if headertxt.startswith(" "):
            headertxt = headertxt[1:]
        xbmcgui.Dialog().textviewer(headertxt, bodytxt)

    def fileexists(self):
        '''helper to let the skinner check if a file exists
        and write the outcome to a window prop or skinstring'''
        filename = self.params.get("file")
        skinstring = self.params.get("skinstring")
        windowprop = self.params.get("winprop")
        if xbmcvfs.exists(filename):
            if windowprop:
                self.win.setProperty(windowprop, "exists")
            if skinstring:
                xbmc.executebuiltin("Skin.SetString(%s,exists)" % skinstring)
        else:
            if windowprop:
                self.win.clearProperty(windowprop)
            if skinstring:
                xbmc.executebuiltin("Skin.Reset(%s)" % skinstring)

    def stripstring(self):
        '''helper to allow the skinner to strip a string and write results to a skin string'''
        splitchar = self.params.get("splitchar")
        if splitchar.upper() == "[SPACE]":
            splitchar = " "
        skinstring = self.params.get("string")
        if not skinstring:
            skinstring = self.params.get("skinstring")
        output = self.params.get("output")
        index = self.params.get("index", 0)
        skinstring = skinstring.split(splitchar)[int(index)]
        self.win.setProperty(output, skinstring)

    def getfilename(self, filename=""):
        '''helper to display a sanitized filename in the vidoeinfo dialog'''
        output = self.params.get("output")
        if not filename:
            filename = xbmc.getInfoLabel("ListItem.FileNameAndPath")
        if not filename:
            filename = xbmc.getInfoLabel("ListItem.FileName")
        if "filename=" in filename:
            url_params = dict(urlparse.parse_qsl(filename))
            filename = url_params.get("filename")
        self.win.setProperty(output, filename)

    def getplayerfilename(self):
        '''helper to parse the filename from a plugin (e.g. emby) filename'''
        filename = xbmc.getInfoLabel("Player.FileNameAndPath")
        if not filename:
            filename = xbmc.getInfoLabel("Player.FileName")
        self.getfilename(filename)

    def getpercentage(self):
        '''helper to calculate the percentage of 2 numbers and write results to a skinstring'''
        total = int(params.get("total"))
        count = int(params.get("count"))
        roundsteps = self.params.get("roundsteps")
        skinstring = self.params.get("skinstring")
        percentage = int(round((1.0 * count / total) * 100))
        if roundsteps:
            roundsteps = int(roundsteps)
            percentage = percentage + (roundsteps - percentage) % roundsteps
        xbmc.executebuiltin("Skin.SetString(%s,%s)" % (skinstring, percentage))

    def setresourceaddon(self):
        '''helper to let the user choose a resource addon and set that as skin string'''
        from resourceaddons import setresourceaddon
        addontype = self.params.get("addontype", "")
        skinstring = self.params.get("skinstring", "")
        setresourceaddon(addontype, skinstring)

    def checkresourceaddons(self):
        '''allow the skinner to perform a basic check if some required resource addons are available'''
        from resourceaddons import checkresourceaddons
        addonslist = self.params.get("addonslist", [])
        if addonslist:
            addonslist = addonslist.split("|")
        checkresourceaddons(addonslist)
