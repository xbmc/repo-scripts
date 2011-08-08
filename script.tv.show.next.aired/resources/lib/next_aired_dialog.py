# -*- coding: utf-8 -*-

from traceback import print_exc
import xbmc
import xbmcgui
import xbmcaddon

__addon__ = xbmcaddon.Addon()
__cwd__ = __addon__.getAddonInfo('path')


class MainGui( xbmcgui.WindowXMLDialog ):
    # control id's
    CONTROL_MAIN_LIST_START  = 50
    CONTROL_MAIN_LIST_END    = 59

    def __init__( self, *args, **kwargs ):
        xbmcgui.WindowXMLDialog.__init__( self )
        xbmc.executebuiltin( "Skin.Reset(AnimeWindowXMLDialogClose)" )
        xbmc.executebuiltin( "Skin.SetBool(AnimeWindowXMLDialogClose)" )
        self.next_ep = kwargs.get( "listing" )

    def onInit(self):
        try:
            self.set_container()
            id = 50 + int( __addon__.getSetting( "view_mode" ) )
            xbmc.executebuiltin( "Container.SetViewMode(%i)" % id )
        except:
            print_exc()

    def set_container(self):
        try:
            # reset all container
            self.clearList()
            for episode in self.next_ep:
                #On crée un element de liste, avec son label
                listitem = xbmcgui.ListItem( "%s" % episode["Show Name"] )
                for keys in episode:
                    if keys == "Next Episode":
                        listitem.setProperty("next_ep_se", "Season %s Episode %s" % (episode[keys].split("^")[0].split("x")[0] , episode[keys].split("^")[0].split("x")[1]))
                        listitem.setProperty("next_ep_season", episode[keys].split("^")[0].split("x")[0])
                        listitem.setProperty("next_ep_num", episode[keys].split("^")[0].split("x")[1])
                        listitem.setProperty("next_ep_name", episode[keys].split("^")[1])
                        next_ep_date = episode[keys].split("^")[2].split("/")
                        if len(next_ep_date) == 3: listitem.setProperty("next_ep_date", "%s %s %s" % ( next_ep_date[1] , next_ep_date[0] , next_ep_date[2] ) )
                        elif len(next_ep_date) == 2: listitem.setProperty("next_ep_date", "%s %s" % ( next_ep_date[0] , next_ep_date[1] ) )
                        else: listitem.setProperty("next_ep_date", next_ep_date[0] )
                    #else:
                    listitem.setProperty(keys.replace( "+", "" ), episode[keys].replace( "^", ". " ).replace( "|", "/" ))

                    #print "-"*100
                    #print keys
                    #print repr( episode[keys] )
                    #print "-"*100
                #infos availables:
                #Status
                #ep_img
                #RFC3339
                #GMT+0 NODST
                #Network
                #Classification
                #Started
                #Show Name
                #Show path
                #Show URL
                #Genres
                #Premiered
                #Airtime
                #Ended
                #Show ID
                #Country
                #Next Episode
                #Runtime
                #dbname
                #Latest Episode

                #On injecte l'élément liste à la liste xml
                self.addItem( listitem )
        except:
            print_exc()

    def onClick(self, controlID):
        """
            Notice: onClick not onControl
            Notice: it gives the ID of the control not the control object
        """
        try:
            if controlID == 6:
                kb = xbmc.Keyboard( "", "Enter your TV Show" )
                kb.doModal()
                if kb.isConfirmed() and kb.getText():
                    user_request = kb.getText()
                    from scraper import getDetails
                    self.next_ep = getDetails( user_request )
                    del getDetails
                    self.set_container()
            elif controlID == 8:
                __addon__.openSettings()
        except:
            print_exc()


    def onFocus(self, controlID):
        pass

    # Cette def permet de gérer les actions en fonctions de la touche du clavier pressée
    def onAction( self, action ):
        #( ACTION_PARENT_DIR, ACTION_PREVIOUS_MENU, ACTION_CONTEXT_MENU, )
        if action in ( 9, 10, 92, 216, 247, 257, 275, 61467, 61448, ): self._close_dialog()

    def _close_dialog( self ):
        for id in range( self.CONTROL_MAIN_LIST_START, self.CONTROL_MAIN_LIST_END + 1 ):
            try:
                if xbmc.getCondVisibility( "Control.IsVisible(%i)" % id ):
                    __addon__.setSetting( "view_mode", str( id - 50 ) )
                    break
            except:
                pass
        import time
        xbmc.executebuiltin( "Skin.Reset(AnimeWindowXMLDialogClose)" )
        time.sleep( .4 )
        self.close()

def MyDialog(tv_list):
    #"MyDialog.xml", __cwd__, current_skin, force_fallback sert a ouvrir le xml du script
    w = MainGui( "DialogNextAired.xml", __cwd__, "DefaultSkin" , listing=tv_list )
    w.doModal()
    del w

def test():
    tv_list = [{'Status': 'Returning Series', 'ep_img': 'C:\\Program Files\\XBMC\\userdata\\Thumbnails\\Video\\3\\3ae2ce22.tbn', 'RFC3339': '2010-08-16T22:00:00-4:00', 'GMT+0 NODST': '1282003200', 'Network': 'Showtime', 'Classification': 'Scripted', 'Started': 'Aug/07/2005', 'Show Name': 'Weeds', 'Show URL': 'http://www.tvrage.com/Weeds', 'Genres': 'Comedy | Crime | Drama', 'Premiered': '2005', 'Airtime': 'Monday at 10:00 pm', 'Ended': '', 'Show ID': '6554', 'Country': 'USA', 'Next Episode': '06x01^Season 6 Premiere^Aug/16/2010', 'Runtime': '30', 'dbname': 'Weeds', 'Latest Episode': '05x13^All About My Mom^Aug/31/2009'}, {'Status': 'Returning Series', 'ep_img': 'C:\\Program Files\\XBMC\\userdata\\Thumbnails\\Video\\a\\af34f363.tbn', 'RFC3339': '2010-06-19T18:50:00+01:00', 'GMT+0 NODST': '1276962600', 'Network': 'BBC One (United Kingdom)', 'Classification': 'Scripted', 'Started': 'Mar/26/2005', 'Show Name': 'Doctor Who (2005)', 'Show URL': 'http://www.tvrage.com/DoctorWho_2005', 'Genres': 'Action | Adventure | Sci-Fi', 'Premiered': '2005', 'Airtime': 'Saturday at 07:00 pm', 'Ended': '', 'Country': 'United Kingdom', 'Show ID': '3332', 'Special Airtime': '06:50 pm', 'Next Episode': '05x12^The Pandorica Opens (1)^Jun/19/2010', 'Runtime': '50', 'dbname': 'Doctor Who (2005)', 'Latest Episode': '05x11^The Lodger^Jun/12/2010'}, {'Status': 'New Series', 'ep_img': 'C:\\Program Files\\XBMC\\userdata\\Thumbnails\\Video\\d\\d2463954.tbn', 'Genres': 'Action | Drama', 'GMT+0 NODST': '', 'Network': 'Starz', 'Classification': 'Scripted', 'Started': 'Jan/22/2010', 'Show Name': 'Spartacus: Blood and Sand', 'Show URL': 'http://www.tvrage.com/Spartacus-Blood_and_Sand', 'Premiered': '2010', 'Airtime': 'Friday at 10:00 pm', 'Ended': '', 'Show ID': '21885', 'Country': 'USA', 'Next Episode': '02x01^Season 2, Episode 1^Jan/2011', 'Runtime': '60', 'dbname': 'Spartacus Blood and Sand', 'Latest Episode': '01x13^Kill Them All^Apr/16/2010'}, {'Status': 'Returning Series', 'ep_img': 'C:\\Program Files\\XBMC\\userdata\\Thumbnails\\Video\\8\\877c6a59.tbn', 'RFC3339': '2010-09-26T21:00:00-4:00', 'GMT+0 NODST': '1285542000', 'Network': 'Showtime', 'Classification': 'Scripted', 'Started': 'Oct/01/2006', 'Show Name': 'Dexter', 'Show URL': 'http://www.tvrage.com/Dexter', 'Genres': 'Crime | Drama', 'Premiered': '2006', 'Airtime': 'Sunday at 09:00 pm', 'Ended': '', 'Show ID': '7926', 'Country': 'USA', 'Next Episode': '05x01^Season 5, Episode 1^Sep/26/2010', 'Runtime': '60', 'dbname': 'Dexter', 'Latest Episode': '04x12^The Getaway^Dec/13/2009'}, {'Status': 'Returning Series', 'ep_img': 'C:\\Program Files\\XBMC\\userdata\\Thumbnails\\Video\\1\\1b5ead11.tbn', 'Genres': 'Action | Adventure | Crime | Drama', 'GMT+0 NODST': '', 'Network': 'CBS', 'Classification': 'Scripted', 'Started': 'Sep/22/2005', 'Show Name': 'Criminal Minds', 'Show URL': 'http://www.tvrage.com/Criminal_Minds', 'Premiered': '2005', 'Airtime': 'Wednesday at 09:00 pm', 'Ended': '', 'Show ID': '3171', 'Country': 'USA', 'Next Episode': '06x01^Season 6, Episode 1^Sep/2010', 'Runtime': '60', 'dbname': 'Esprits Criminels', 'Latest Episode': '05x23^Our Darkest Hour^May/26/2010'}, {'Status': 'Returning Series', 'ep_img': 'C:\\Program Files\\XBMC\\userdata\\Thumbnails\\Video\\1\\160b5358.tbn', 'RFC3339': '2010-09-11T22:00:00-4:00', 'GMT+0 NODST': '1284249600', 'Network': 'Showtime', 'Classification': 'Scripted', 'Started': 'Aug/13/2007', 'Show Name': 'Californication', 'Show URL': 'http://www.tvrage.com/Californication', 'Genres': 'Comedy | Drama', 'Premiered': '2007', 'Airtime': 'Sunday at 10:00 pm', 'Ended': '', 'Show ID': '15319', 'Country': 'USA', 'Next Episode': '04x01^Season 4, Episode 1^Sep/11/2010', 'Runtime': '30', 'dbname': 'Californication', 'Latest Episode': '03x12^Mia Culpa^Dec/13/2009'}, {'Status': 'New Series', 'ep_img': 'C:\\Program Files\\XBMC\\userdata\\Thumbnails\\Video\\f\\fb6829f7.tbn', 'RFC3339': '2010-06-14T12:00:00+09:00', 'GMT+0 NODST': '1276477200', 'Network': 'TV Tokyo (Japan)', 'Classification': 'Animation', 'Started': 'Oct/12/2009', 'Show Name': 'Fairy Tail', 'Show URL': 'http://www.tvrage.com/shows/id-24288', 'Genres': 'Anime | Action | Adventure | Drama | Fantasy', 'Premiered': '2009', 'Airtime': 'Monday', 'Ended': '', 'Show ID': '24288', 'Country': 'Japan', 'Next Episode': '01x34^Gerard^Jun/14/2010', 'Runtime': '30', 'dbname': 'Fairy Tail', 'Latest Episode': '01x33^Tower of Paradise^Jun/07/2010'}, {'Status': 'Returning Series', 'ep_img': 'C:\\Program Files\\XBMC\\userdata\\Thumbnails\\Video\\2\\2377d88e.tbn', 'RFC3339': '2010-06-17T19:30:00+09:00', 'GMT+0 NODST': '1276763400', 'Network': 'TV Tokyo (Japan)', 'Classification': 'Animation', 'Started': 'Feb/15/2007', 'Show Name': 'Naruto: Shippuuden', 'Show URL': 'http://www.tvrage.com/Naruto_Shippuuden', 'Genres': 'Anime | Action | Adventure | Comedy | Drama | Fantasy | Mystery', 'Premiered': '2007', 'Airtime': 'Thursday at 07:30 pm', 'Ended': '', 'Show ID': '14748', 'Country': 'Japan', 'Next Episode': '07x22^Nine-Tails Capture Complete^Jun/17/2010', 'Runtime': '30', 'dbname': 'Naruto', 'Latest Episode': '07x21^Crisis! Sage Mode Disappears^Jun/10/2010'}, {'Status': 'Returning Series', 'ep_img': 'C:\\Program Files\\XBMC\\userdata\\Thumbnails\\Video\\1\\1b84f8e2.tbn', 'RFC3339': '2010-06-15T19:30:00+09:00', 'GMT+0 NODST': '1276590600', 'Network': 'TV Tokyo (Japan)', 'Classification': 'Animation', 'Started': 'Oct/05/2004', 'Show Name': 'Bleach (JP)', 'Show URL': 'http://www.tvrage.com/Bleach_JP', 'Genres': 'Anime | Action | Adventure | Fantasy', 'Premiered': '2004', 'Airtime': 'Wednesday at 07:30 pm', 'Ended': '', 'Show ID': '2825', 'Country': 'Japan', 'Next Episode': '14x20^The Approaching Breath of Death, the King Who Rules Over Death!^Jun/15/2010', 'Runtime': '30', 'dbname': 'Bleach', 'Latest Episode': '14x19^Hitsugaya, the Suicidal Frozen Heavens Hundred Flowers Funeral!^Jun/08/2010'}, {'Status': 'Returning Series', 'ep_img': 'C:\\Program Files\\XBMC\\userdata\\Thumbnails\\Video\\1\\15b02f06.tbn', 'RFC3339': '2010-06-17T19:30:00+09:00', 'GMT+0 NODST': '1276763400', 'Network': 'TV Tokyo (Japan)', 'Classification': 'Animation', 'Started': 'Feb/15/2007', 'Show Name': 'Naruto: Shippuuden', 'Show URL': 'http://www.tvrage.com/Naruto_Shippuuden', 'Genres': 'Anime | Action | Adventure | Comedy | Drama | Fantasy | Mystery', 'Premiered': '2007', 'Airtime': 'Thursday at 07:30 pm', 'Ended': '', 'Show ID': '14748', 'Country': 'Japan', 'Next Episode': '07x22^Nine-Tails Capture Complete^Jun/17/2010', 'Runtime': '30', 'dbname': 'Naruto Shippuuden', 'Latest Episode': '07x21^Crisis! Sage Mode Disappears^Jun/10/2010'}]
    MyDialog(tv_list)
