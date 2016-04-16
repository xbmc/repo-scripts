import os, sys
import xbmc, xbmcgui
from xmlParser import XMLParser

#enable localization
getLS   = sys.modules[ "__main__" ].LANGUAGE
CWD = sys.modules[ "__main__" ].CWD

class GUI(xbmcgui.WindowXMLDialog):

    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)
        self.setNum = kwargs['setNum']
        self.parser = XMLParser()
        if self.parser.feedsTree:
            self.doModal()


    def onInit(self):
        self.defineControls()
        if not self.parser.feedsList:
            xbmcgui.Dialog().ok(getLS(40)+'RssFeeds.xml', 'RssFeeds.xml '+getLS(32041), getLS(32042), getLS(32043))
            self.closeDialog()
        self.showDialog()

    def defineControls(self):
        #actions
        self.action_cancel_dialog = ( 9, 10, 92, 216, 247, 257, 275, 61467, 61448 )
        #control ids
        self.control_heading_label_id       = 2
        self.control_list_label_id          = 4
        self.control_list_id                = 10
        self.control_modifySet_button_id    = 11
        self.control_add_button_id          = 13
        self.control_remove_button_id       = 14
        self.control_ok_button_id           = 18
        self.control_cancel_button_id       = 19
        #controls
        self.heading_label      = self.getControl(self.control_heading_label_id)
        self.list_label         = self.getControl(self.control_list_label_id)
        self.list               = self.getControl(self.control_list_id)
        self.add_button         = self.getControl(self.control_add_button_id)
        self.remove_button      = self.getControl(self.control_remove_button_id)
        self.modifySet_button   = self.getControl(self.control_modifySet_button_id)
        self.ok_button          = self.getControl(self.control_ok_button_id)
        self.cancel_button      = self.getControl(self.control_cancel_button_id)
        #defaults
        self.dFeedsList = [{'url':'http://feeds.feedburner.com/xbmc', 'updateinterval':'30'},
                           {'url':'http://feeds.feedburner.com/latest_xbmc_addons', 'updateinterval':'30'},
                           {'url':'http://feeds.feedburner.com/updated_xbmc_addons', 'updateinterval':'30'}]

    def showDialog(self):
        self.heading_label.setLabel(getLS(32030))
        self.list_label.setLabel(getLS(32024))
        self.modifySet_button.setLabel(getLS(32006))
        self.updateSetsList()
        self.setFocus(self.list)

    def closeDialog(self):
        """Close the Set Editor Dialog and open RSS Editor Dialog"""
        import rssEditor
        rssEditorUI = rssEditor.GUI("script-RSS_Editor.xml", CWD, "default", setNum = self.setNum)
        self.close()
        del rssEditorUI

    def onClick(self, controlId):
        #select existing set
        if controlId == self.control_list_id:
            setItem = self.list.getSelectedItem()
            self.setNum = setItem.getLabel()
            self.parser.writeXmlToFile()
            self.closeDialog()
        #add new set
        elif controlId == self.control_add_button_id:
            self.getNewSet()
            self.updateSetsList()
        #remove existing set
        elif controlId == self.control_remove_button_id:
            self.removeSet()
            self.updateSetsList()
        #modify existing set
        elif controlId == self.control_modifySet_button_id:
            self.editSet()
            self.updateSetsList()
        #write sets to file/dialog to modify feeds within set.
        elif controlId == self.control_ok_button_id:
            self.parser.writeXmlToFile()
            self.closeDialog()
        #cancel dialog
        elif controlId == self.control_cancel_button_id:
            self.closeDialog()

    def onAction(self, action):
        if action in self.action_cancel_dialog:
            self.closeDialog()

    def onFocus(self, controlId):
        pass

    def editSet(self):
        """Edit the attributes of an existing set"""
        setItem = self.list.getSelectedItem()
        oldSetLabel = setItem.getLabel()
        #ask user for set number
        newSetNum = self.getSetNum(oldSetLabel[3:])
        if newSetNum:
            newSetLabel = 'set'+newSetNum
            #ask user if set contains right to left text
            rtl = self.containsRTLText()
            #copy settings from old label
            self.parser.feedsList[newSetLabel] = self.parser.feedsList[oldSetLabel]
            #apply new attributes
            self.parser.feedsList[newSetLabel]['attrs'] = {'rtl':rtl, 'id':newSetNum}
            #if the set# changes, remove the old one.
            if newSetLabel != oldSetLabel:
                self.removeSet(oldSetLabel)

    def getNewSet(self):
        """Add a new set with some default values"""
        #default setNumber = find highest numbered set, then add 1
        defaultSetNum = max([int(setNum[3:]) for setNum in self.parser.feedsList.keys()])+1
        #ask user for set number
        newSetNum = self.getSetNum(defaultSetNum)
        #check if set number already exists
        if newSetNum:
            newSetLabel = 'set'+newSetNum
            #ask user if set contains right to left text
            rtl = self.containsRTLText()
            #add default information
            self.parser.feedsList[newSetLabel] = {'feedslist':self.dFeedsList, 'attrs':{'rtl':rtl, 'id':newSetNum}}

    def getSetNum(self, defaultSetNum, title = getLS(32025)):
        newSetNum = str(xbmcgui.Dialog().numeric(0, title, str(defaultSetNum)))
        if self.setNumExists(newSetNum) and newSetNum != defaultSetNum:
            self.getSetNum(defaultSetNum, getLS(32050) % newSetNum)
        else:
            return newSetNum

    def setNumExists(self, setNum):
        if 'set'+setNum in self.parser.feedsList.keys():
            return True

    def containsRTLText(self):
        """Returns xml style lowercase 'true' or 'false'"""
        return str(bool(xbmcgui.Dialog().yesno(getLS(32027), getLS(32027)))).lower()

    def removeSet(self, setNum = None):
        """Removes a set or if set is required resets it to default"""
        if setNum is None:
            setNum = self.list.getSelectedItem().getLabel()
        if setNum == 'set1':
            #Ask if user wants to set everything to default.
            if xbmcgui.Dialog().yesno(getLS(32045), getLS(32046), getLS(32047)):
                self.parser.feedsList[setNum] = {'feedslist':self.dFeedsList, 'attrs':{'rtl':'false','id':'1'}}
        else:
            del self.parser.feedsList[setNum]

    def updateSetsList(self):
        self.list.reset()
        for setNum in sorted(self.parser.feedsList.keys()):
            self.list.addItem(setNum)
            self.list_label.setLabel(getLS(32024))
