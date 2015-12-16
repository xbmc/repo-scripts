import xbmcgui,xbmc
from traceback import print_exc

class DialogContextMenu( xbmcgui.WindowXMLDialog ):
    def __init__( self, *args, **kwargs ):
        xbmcgui.WindowXMLDialog.__init__( self )
        self.listing = kwargs.get( "listing" )
        self.windowtitle = kwargs.get( "windowtitle" )
        self.result = -1

    def onInit(self):
        try:
            self.fav_list = self.getControl(6)
            self.getControl(3).setVisible(False)
        except:
            print_exc()
            self.fav_list = self.getControl(3)

        self.getControl(5).setVisible(False)
        self.getControl(1).setLabel(self.windowtitle)

        for item in self.listing :
            listitem = xbmcgui.ListItem(label=item.getLabel(), label2=item.getLabel2(), iconImage=item.getProperty( "icon" ), thumbnailImage=item.getProperty( "thumbnail" ))
            listitem.setProperty( "Addon.Summary", item.getLabel2() )
            self.fav_list.addItem( listitem )

        self.setFocus(self.fav_list)

    def onAction(self, action):
        if action.getId() in ( 9, 10, 92, 216, 247, 257, 275, 61467, 61448, ):
            self.result = -1
            self.close()

    def onClick(self, controlID):
        if controlID == 6 or controlID == 3:
            num = self.fav_list.getSelectedPosition()
            self.result = num
        else:
            self.result = -1

        self.close()

    def onFocus(self, controlID):
        pass

class DialogSelectSmall( xbmcgui.WindowXMLDialog ):
    def __init__( self, *args, **kwargs ):
        xbmcgui.WindowXMLDialog.__init__( self )
        self.listing = kwargs.get( "listing" )
        self.windowtitle = kwargs.get( "windowtitle" )
        self.multiselect = kwargs.get( "multiselect" )
        self.totalitems = 0
        self.result = -1
        self.autoFocusId = 0

    def onInit(self):
        self.getControl(6).setVisible(False)
        self.getControl(3).setEnabled(True)
        self.getControl(1).setLabel(self.windowtitle)
        try:
            self.getControl(7).setLabel(xbmc.getLocalizedString(222))
        except: pass
        
        if self.multiselect == False:
            self.getControl(5).setVisible(False)
        
        self.fav_list = self.getControl(3)

        for item in self.listing :
            listitem = xbmcgui.ListItem(label=item.getLabel(), label2=item.getLabel2(), iconImage=item.getProperty( "icon" ), thumbnailImage=item.getProperty( "thumbnail" ))
            listitem.setProperty( "Addon.Summary", item.getLabel2() )
            listitem.select(selected=item.isSelected())
            self.fav_list.addItem( listitem )

        self.setFocus(self.fav_list)
        try: self.fav_list.selectItem(self.autoFocusId)
        except: self.fav_list.selectItem(0)
        self.totalitems = len(self.listing)

    def onAction(self, action):
        if action.getId() in ( 9, 10, 92, 216, 247, 257, 275, 61467, 61448, ):
            if self.multiselect == True:
                itemsList = []
                itemcount = self.totalitems -1
                while (itemcount != -1):
                    li = self.fav_list.getListItem(itemcount)
                    if li.isSelected() == True:
                        itemsList.append(itemcount)
                    itemcount -= 1
                self.result = itemsList
            else:        
                self.result = -1
            self.close()
        
        # select item in list
        if (action.getId() == 7 or action.getId() == 100) and xbmc.getCondVisibility("Control.HasFocus(3)"):
            if self.multiselect == True:
                item =  self.fav_list.getSelectedItem()
                if item.isSelected() == True:
                    item.select(selected=False)
                else:
                    item.select(selected=True)
            else:
                num = self.fav_list.getSelectedPosition()
                self.result = num
                self.close()
        

    def onClick(self, controlID):
        
        # OK button
        if controlID == 5:
            itemsList = []
            itemcount = self.totalitems -1
            while (itemcount != -1):
                li = self.fav_list.getListItem(itemcount)
                if li.isSelected() == True:
                    itemsList.append(itemcount)
                itemcount -= 1
            self.result = itemsList
            self.close()
        
        # Other buttons (including cancel)
        else:
            self.result = -1
            self.close()

    def onFocus(self, controlID):
        pass

class DialogSelectBig( xbmcgui.WindowXMLDialog ):
    def __init__( self, *args, **kwargs ):
        xbmcgui.WindowXMLDialog.__init__( self )
        self.listing = kwargs.get( "listing" )
        self.windowtitle = kwargs.get( "windowtitle" )
        self.result = -1
        self.autoFocusId = 0

    def onInit(self):
        try:
            self.fav_list = self.getControl(6)
            self.getControl(1).setLabel(self.windowtitle)
            self.getControl(3).setVisible(False)
            try:
                self.getControl(7).setLabel(xbmc.getLocalizedString(222))
            except: pass
        except:
            print_exc()
            self.fav_list = self.getControl(3)

        self.getControl(5).setVisible(False)

        for item in self.listing :
            listitem = xbmcgui.ListItem(label=item.getLabel(), label2=item.getLabel2(), iconImage=item.getProperty( "icon" ), thumbnailImage=item.getProperty( "thumbnail" ))
            listitem.setProperty( "Addon.Summary", "" )
            self.fav_list.addItem( listitem )

        self.setFocus(self.fav_list)
        try: self.fav_list.selectItem(self.autoFocusId)
        except: self.fav_list.selectItem(0)

    def onAction(self, action):
        if action.getId() in ( 9, 10, 92, 216, 247, 257, 275, 61467, 61448, ):
            self.result = -1
            self.close()

    def onClick(self, controlID):
        if controlID == 6 or controlID == 3:
            num = self.fav_list.getSelectedPosition()
            self.result = num
        else:
            self.result = -1

        self.close()

    def onFocus(self, controlID):
        pass
        
