#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#     Copyright (C) 2012 Tristan Fischer (sphere@dersphere.de)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#

import os
import re
import sys
import urllib
import json
import ast   #used for processing out context menu

import xbmc
import xbmcaddon
import xbmcgui
from xbmcgui import ControlButton

from utils import build_script, generator, translation

addon = xbmcaddon.Addon()
addonID    = addon.getAddonInfo('id')  #script.reddit.reader
addon_path = addon.getAddonInfo('path')
addon_name = addon.getAddonInfo('name')

def dump(obj):
    for attr in dir(obj):
        if hasattr( obj, attr ):
            log( "obj.%s = %s" % (attr, getattr(obj, attr)))

class ExitMonitor(xbmc.Monitor):
    def __init__(self, exit_callback):
        self.exit_callback = exit_callback


    def abortRequested(self):
        self.exit_callback()

class contextMenu(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)
        self.listing = kwargs.get("listing")


    def onInit(self):
        self.list_control=self.getControl(996)
        self.list_control.addItems(self.listing)
        pass

    def onAction(self, action):
        if action in [ xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_NAV_BACK ]:
            self.close()

    def onClick(self, controlID):
        selected_item=self.list_control.getSelectedItem()
        di_url=selected_item.getPath()
        xbmc.executebuiltin( di_url  )
        self.close()


class cGUI(xbmcgui.WindowXML):

    include_parent_directory_entry=True
    title_bar_text=""
    gui_listbox_SelectedPosition=0


    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXML.__init__(self, *args, **kwargs)

        self.subreddits_file = kwargs.get("subreddits_file")
        self.listing = kwargs.get("listing")
        self.main_control_id = kwargs.get("id")


    def onInit(self):
        xbmc.executebuiltin( "Dialog.Close(busydialog)" )
        self.gui_listbox = self.getControl(self.main_control_id)

        self.gui_listbox.reset()
        self.exit_monitor = ExitMonitor(self.close_gui)#monitors for abortRequested and calls close on the gui

        if self.title_bar_text:
            self.ctl_title_bar = self.getControl(1)
            self.ctl_title_bar.setLabel(self.title_bar_text)

        if self.include_parent_directory_entry:
            if self.gui_listbox_SelectedPosition==0:
                self.gui_listbox_SelectedPosition=1 #skip the ".." as the first selected item
            back_image='DefaultFolderBackSquare.png'
            listitem = xbmcgui.ListItem(label='..', label2="", iconImage=back_image)

            listitem.setArt({"thumb": back_image, "clearart": "DefaultFolderBackSquare.png"}) #, "poster":back_image, "banner":back_image, "fanart":back_image, "landscape":back_image   })

            listitem.setInfo(type='video', infoLabels={"Studio":".."})

            self.gui_listbox.addItem(listitem)

        self.gui_listbox.addItems(self.listing)
        self.setFocus(self.gui_listbox)

        if self.gui_listbox_SelectedPosition > 0:
            self.gui_listbox.selectItem( self.gui_listbox_SelectedPosition )

    def onClick(self, controlID):

        if controlID == self.main_control_id:
            self.gui_listbox_SelectedPosition = self.gui_listbox.getSelectedPosition()
            item = self.gui_listbox.getSelectedItem()
            if not item: #panel listbox control allows user to pick non-existing item by mouse/touchscreen. bypass it here.
                return

            if self.include_parent_directory_entry and self.gui_listbox_SelectedPosition == 0:
                self.close()  #include_parent_directory_entry means that we've added a ".." as the first item on the list onInit

            self.process_clicked_item(item)
        else:
            clicked_control=self.getControl(controlID)
            log('clicked on controlID='+repr(controlID))
            self.process_clicked_item(clicked_control)

    def process_clicked_item(self, clicked_item):
        if isinstance(clicked_item, xbmcgui.ListItem ):
            di_url=clicked_item.getProperty('onClick_action') #this property is created when assembling the kwargs.get("listing") for this class
            item_type=clicked_item.getProperty('item_type').lower()
        elif isinstance(clicked_item, xbmcgui.ControlButton ):

            pass

        log( "  clicked %s  IsPlayable=%s  url=%s " %( repr(clicked_item),item_type, di_url )   )
        if item_type=='playable':

                pl = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
                pl.clear()
                pl.add(di_url, clicked_item)
                xbmc.Player().play(pl, windowed=False)
        elif item_type=='script':

            if 'mode=listSubReddit' in di_url:
                self.busy_execute_sleep(di_url,500,True )
            else:
                self.busy_execute_sleep(di_url,3000,False )

    def onAction(self, action):
        try:focused_control=self.getFocusId()
        except:focused_control=0


        if action in [ xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_NAV_BACK ]:
            self.close()

        if focused_control==self.main_control_id:  #main_control_id is the listbox
            self.gui_listbox_SelectedPosition = self.gui_listbox.getSelectedPosition()
            item = self.gui_listbox.getSelectedItem()


            if action in [xbmcgui.ACTION_CONTEXT_MENU]:
                self.pop_context_menu(item)

    def load_subreddits_file_into_a_listitem(self):
        from utils import compose_list_item, prettify_reddit_query, xstr, samealphabetic, hassamealphabetic
        from reddit import parse_subreddit_entry, assemble_reddit_filter_string, ret_sub_info, ret_settings_type_default_icon
        entries=[]
        listing=[]

        if os.path.exists(self.subreddits_file):
            with open(self.subreddits_file, 'r') as fh:
                content = fh.read()
                fh.close()
                spl = content.split('\n')

                for i in range(0, len(spl), 1):
                    if spl[i]:
                        subreddit = spl[i].strip()
                        entries.append(subreddit )
        entries.sort()


        addtl_subr_info={}
        for subreddit_entry in entries:
            nsfw=False
            addtl_subr_info=ret_sub_info(subreddit_entry)

            entry_type, subreddit, alias, shortcut_description=parse_subreddit_entry(subreddit_entry)

            icon=default_icon=ret_settings_type_default_icon(entry_type)
            reddit_url= assemble_reddit_filter_string("",subreddit, "yes")

            pretty_label=prettify_reddit_query(alias)
            pretty_label=pretty_label.replace('+',' + ')
            if entry_type=='domain':

                pretty_label=re.findall(r'(?::|\/domain\/)(.+)',subreddit)[0]

            if subreddit.lower() in ["all","popular"]:
                liz = compose_list_item( pretty_label, entry_type, "", "script", build_script("listSubReddit",reddit_url,alias) )
            else:
                if addtl_subr_info: #if we have additional info about this subreddit

                    title=addtl_subr_info.get('title','')+'\n'
                    display_name=xstr(addtl_subr_info.get('display_name',''))
                    if samealphabetic( title, display_name): title=''


                    header_title=xstr(addtl_subr_info.get('header_title',''))
                    public_description=xstr( addtl_subr_info.get('public_description',''))
                    nsfw=addtl_subr_info.get('over18')

                    if samealphabetic( header_title, public_description): public_description=''
                    if samealphabetic(title,public_description): public_description=''


                    shortcut_description='[COLOR cadetblue][B]r/%s[/B][/COLOR]\n%s[I]%s[/I]\n%s' %(display_name,title,header_title,public_description )

                    icon=addtl_subr_info.get('icon_img')
                    banner=addtl_subr_info.get('banner_img')
                    header=addtl_subr_info.get('header_img')  #usually the small icon on upper left side on subreddit screen

                    icon=next((item for item in [icon,banner,header] if item ), '') or default_icon

                    liz = compose_list_item( pretty_label, entry_type, "", "script", build_script("listSubReddit",reddit_url,alias) )

                else:
                    liz = compose_list_item( pretty_label, entry_type, "", "script", build_script("listSubReddit",reddit_url,alias) )

            liz.setArt({ "thumb": icon })
            liz.setProperty('ACTION_manage_subreddits', build_script('manage_subreddits', subreddit_entry,"","" ) )
            if nsfw:
                liz.setProperty('nsfw', 'true' )
            listing.append(liz)

        li_search=compose_list_item( translation(32016), translation(32016), "icon_search_subreddit.png", "script", build_script("search", '', '') )
        listing.append(li_search)

        li_setting=compose_list_item( translation(32018), "Program", "icon_settings.png", "script", "Addon.OpenSettings(%s)"%addonID )
        listing.append(li_setting)

        return listing

    def pop_context_menu(self, selected_item):
        cxm_string=selected_item.getProperty('context_menu')
        if cxm_string:

            li=[]
            for label, action in ast.literal_eval(cxm_string):
                liz=xbmcgui.ListItem(label=label,
                     label2='',
                     path=action)
                li.append(liz)

            if len(li)>0:
                cxm=contextMenu('srr_DialogContextMenu.xml',addon_path,listing=li)
                cxm.doModal()
                del cxm
                del li[:]

    def busy_execute_sleep(self,executebuiltin, sleep=500, close=True):

        xbmc.executebuiltin("ActivateWindow(busydialog)")

        xbmc.executebuiltin( executebuiltin  )

        xbmc.Monitor().waitForAbort( int(sleep/1000)   )


        if close:
            self.close()
        else:
            xbmc.executebuiltin( "Dialog.Close(busydialog)" )
        pass

    def close_gui(self):
        log('  close gui via exit monitor')
        self.close()
        pass

class indexGui(cGUI):


    def onInit(self):
        if self.title_bar_text:
            self.ctl_title_bar = self.getControl(1)
            self.ctl_title_bar.setLabel(self.title_bar_text)

        self.gui_listbox = self.getControl(self.main_control_id)

        self.gui_listbox.reset()

        self.gui_listbox.addItems( self.load_subreddits_file_into_a_listitem() )

        self.setFocus(self.gui_listbox)

        if self.gui_listbox_SelectedPosition > 0:
            self.gui_listbox.selectItem( self.gui_listbox_SelectedPosition )

    def onAction(self, action):

        if action in [ xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_NAV_BACK ]:
            self.close()

        try:focused_control=self.getFocusId()
        except:focused_control=0



        if focused_control==self.main_control_id:  #main_control_id is the listbox

            self.gui_listbox_SelectedPosition  = self.gui_listbox.getSelectedPosition()
            item = self.gui_listbox.getSelectedItem()

            try:
                item_type=item.getProperty('item_type').lower()

                if action in [ xbmcgui.ACTION_CONTEXT_MENU ]:
                    ACTION_manage_subreddits=item.getProperty('ACTION_manage_subreddits')
                    log( "   left pressed  %d IsPlayable=%s  url=%s " %(  self.gui_listbox_SelectedPosition, item_type, ACTION_manage_subreddits )   )

                    xbmc.executebuiltin( ACTION_manage_subreddits  )
                    self.close()

            except:

                pass

class listSubRedditGUI(cGUI):
    reddit_query_of_this_gui=''
    SUBREDDITS_LIST=550
    SIDE_SLIDE_PANEL=9000
    SLIDER_CTL=17
    ALBUM_LIST=5501

    def __init__(self, *args, **kwargs):
        cGUI.__init__(self, *args, **kwargs)

        self.setProperty("subreddit_icon", kwargs.get('icon'))  #$INFO[Window.Property(subreddit_icon)]
        self.setProperty("subreddit_banner", kwargs.get('banner'))  #$INFO[Window.Property(subreddit_banner)]
        self.setProperty("subreddit_header", kwargs.get('header'))  #$INFO[Window.Property(subreddit_header)]

    def onInit(self):
        cGUI.onInit(self)

        self.setProperty("bg_image", "srr_blackbg.jpg")  #this is retrieved in the xml file by $INFO[Window.Property(bg_image)]

        self.album_listbox = self.getControl(self.ALBUM_LIST)


    def load_album_images_if_available(self,selected_item):
        from utils import dictlist_to_listItems
        album_images=selected_item.getProperty('album_images')  #set in main_listing.py addLink()
        self.album_listbox.reset()
        if album_images:
            dictlist=json.loads(album_images)
            listItems=dictlist_to_listItems(dictlist)

            self.album_listbox.addItems(listItems)

    def onAction(self, action):
        try:focused_control=self.getFocusId()
        except:focused_control=0


        if focused_control==self.main_control_id:  #main_control_id is the listbox
            self.gui_listbox_SelectedPosition = self.gui_listbox.getSelectedPosition()
            item = self.gui_listbox.getSelectedItem()
            item_type=item.getProperty('item_type').lower()

            self.load_album_images_if_available(item)


            if action in [ xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_NAV_BACK ]:
                self.close()

            if action in [xbmcgui.ACTION_CONTEXT_MENU]:
                self.pop_context_menu(item)

            elif action == xbmcgui.ACTION_MOVE_LEFT:
                comments_action=item.getProperty('comments_action')
                log( "   RIGHT(comments) pressed  %d IsPlayable=%s  url=%s " %(  self.gui_listbox_SelectedPosition, item_type, comments_action )   )
                if comments_action:

                    self.busy_execute_sleep(comments_action,3000,False )


        elif focused_control==self.SLIDER_CTL:
            if action in [xbmcgui.ACTION_MOVE_LEFT]:
                self.setFocusId(self.main_control_id)


        if focused_control==self.ALBUM_LIST:

            item = self.album_listbox.getSelectedItem()
            item_type=item.getProperty('item_type').lower()

            if action in [ xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_NAV_BACK ]:
                self.close()

            if action in [xbmcgui.ACTION_CONTEXT_MENU]:
                log('  context menu pressed for album image')
                pass


    def onClick(self, controlID):

        if controlID==self.main_control_id:
            self.gui_listbox_SelectedPosition = self.gui_listbox.getSelectedPosition()
            listbox_selected_item=self.gui_listbox.getSelectedItem()

            if self.include_parent_directory_entry and self.gui_listbox_SelectedPosition == 0:
                self.close()  #include_parent_directory_entry means that we've added a ".." as the first item on the list onInit()

            self.process_clicked_item(listbox_selected_item)

        elif controlID==self.ALBUM_LIST:

            selected_item=self.album_listbox.getSelectedItem()
            self.process_clicked_item(selected_item)

    def get_more_link_info(self,selected_item):

        pass
def log(message, level=xbmc.LOGDEBUG):
    xbmc.log("reddit.reader GUI:"+message, level=level)

class progressBG( xbmcgui.DialogProgressBG ):
    progress=0.00
    heading='Loading...'
    tick_increment=1.00
    def __init__(self,heading):
        xbmcgui.DialogProgressBG.__init__(self)
        self.heading=heading
        xbmcgui.DialogProgressBG.create(self, self.heading)

    def update(self, progress, message=None):
        if self.progress>=100:
            self.progress=100
        else:
            self.progress+=progress

        if message:
            super(progressBG, self).update( int(self.progress), self.heading, message )
        else:
            super(progressBG, self).update( int(self.progress), self.heading )

    def set_tick_total(self,tick_total):
        if tick_total==0:
            self.tick_increment=1
        else:
            self.tick_total=tick_total
            remaining=100-self.progress
            self.tick_increment=float(remaining)/tick_total


    def tick(self,how_many, message=None):

        self.update(self.tick_increment*how_many, message)

    def end(self):
        super(progressBG, self).update( 100 )
        super(progressBG, self).close() #it is important to close xbmcgui.DialogProgressBG

    def getProgress(self):
        return self.progress

class comments_GUI2(cGUI):
    links_on_top=False
    links_top_selected_position=0
    listbox_selected_position=0
    child_lists=[]
    items_for_listbox=[]
    flag_grouplist_is_scrolled_top=True
    grouplist_scrollbar_id=17
    grouplist_top_button_id=999   #hidden button at the very top of grouplist. will scroll grouplist to top if focused

    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXML.__init__(self, *args, **kwargs)

        self.subreddits_file = kwargs.get("subreddits_file")
        self.listing = kwargs.get("listing")
        self.main_control_id = kwargs.get("id")


        listing_generator=generator(self.listing)

        tlc_id=0 #create id's for top-level-comments
        self.child_lists[:] = []  #a collection of child comments (non-tlc) tlc_children
        tlc_children=[]

        for listing in listing_generator:
            depth=int(listing.getProperty('comment_depth'))

            if not listing.getProperty('link_url'):
                if depth==0:
                    tlc_id+=1
                    listing.setProperty('tlc_id',str(tlc_id)) #assign an id to this top-level-comment
                    self.items_for_listbox.append(listing)    #this post will be on the listbox

                    self.child_lists.append(tlc_children)

                    tlc_children=[]
                    tlc_children.append( self.get_post_text_tuple(listing) ) #save the post_text of the top level comment
                else:

                    child_comment=listing

                    tlc_children.append( self.get_post_text_tuple(child_comment) )
            else: #link in tlc
                if depth>0:
                    listing.setProperty('tlc_id',str(tlc_id))
                    listing.setProperty('non_tlc_link','true')

                listing.setProperty('tlc_id',str(tlc_id))
                self.items_for_listbox.append(listing)

        self.child_lists.append(tlc_children)

        self.exit_monitor = ExitMonitor(self.close_gui)#monitors for abortRequested and calls close on the gui

        self.x_controls=[x for x in range(1000, 1071)]

    def onInit(self):
        xbmc.executebuiltin( "Dialog.Close(busydialog)" )
        self.gui_listbox = self.getControl(self.main_control_id)

        self.gui_listbox.reset()
        self.exit_monitor = ExitMonitor(self.close_gui)#monitors for abortRequested and calls close on the gui

        if self.title_bar_text:
            self.ctl_title_bar = self.getControl(1)
            self.ctl_title_bar.setText(self.title_bar_text)

        self.gui_listbox.addItems(self.items_for_listbox)
        self.setFocus(self.gui_listbox)

        if self.gui_listbox_SelectedPosition > 0:
            self.gui_listbox.selectItem( self.gui_listbox_SelectedPosition )

        self.show_comment_children()

    def onFocus(self,controlId):
        if controlId==self.grouplist_scrollbar_id:
            self.flag_grouplist_is_scrolled_top=False

        if controlId==self.main_control_id: #55
            if self.flag_grouplist_is_scrolled_top==False:
                self.setFocusId(self.grouplist_top_button_id) #scroll the grouplist to top
                self.flag_grouplist_is_scrolled_top=True
                self.setFocusId(self.main_control_id)

    def onAction(self, action):
        focused_control=self.getFocusId()

        if action in [ xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_NAV_BACK ]:
            self.close_gui()

        if focused_control==self.main_control_id:
            self.gui_listbox_SelectedPosition = self.gui_listbox.getSelectedPosition()
            item = self.gui_listbox.getSelectedItem()
            if item:
                self.show_comment_children()

                if action in [xbmcgui.ACTION_CONTEXT_MENU]:
                    self.pop_context_menu(item)

    def show_comment_children(self):
        item = self.gui_listbox.getSelectedItem()
        if item: #item will be None if there are no comments. AttributeError
            if item.getProperty('link_url'):
                self.clear_x_controls()
            else:
                tlc_id=int(item.getProperty('tlc_id'))

                self.populate_tlc_children(tlc_id)

    def populate_tlc_children(self,tlc_id):

        child_comments_tuple_generator=generator(self.child_lists[tlc_id])

        for control_id in self.x_controls:
            control=self.getControl(control_id)

            try:
                post_text,author,depth=child_comments_tuple_generator.next()
            except StopIteration:
                post_text,author,depth=None,None,0

            if post_text:

                control.setText(post_text)
            else:
                control.setText(None)

            control.setAnimations( [ animation_format(0,100,'slide', 0, (20*depth), 'sine', 'in' ) ] )

        return

    def clear_x_controls(self):

        pass

    def get_post_text_tuple(self,list_item):
        try:
            return (list_item.getProperty('plot'),list_item.getProperty('author'),int(list_item.getProperty('comment_depth')) )
        except AttributeError:
            return (None,None,None)


    def onClick(self, controlID):
        cGUI.onClick(self, controlID)

    def close_gui(self):

        del self.items_for_listbox[:]
        self.close()

class text_to_links_gui(comments_GUI2):
    items_for_grouplist=[]
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXML.__init__(self, *args, **kwargs)
        self.listing = kwargs.get("listing")
        self.title_bar_text=kwargs.get("title")
        self.poster=kwargs.get("poster")

        self.main_control_id = None #not used, left here so that we can use the base class methods without error. onClick()

        self.exit_monitor = ExitMonitor(self.close_gui)#monitors for abortRequested and calls close on the gui

        self.x_controls=[x for x in range(1000, 1021)]

    def onInit(self):
        xbmc.executebuiltin( "Dialog.Close(busydialog)" )


        if self.title_bar_text:
            self.ctl_title_bar = self.getControl(1)
            self.ctl_title_bar.setText(self.title_bar_text)

        if self.poster:

            self.getControl(3).setImage(self.poster)

        listing_generator=generator(self.listing)

        for control_id in self.x_controls:
            tx_control=self.getControl(control_id)
            bn_control=self.getControl(control_id+1000)
            img_control=self.getControl(control_id+2000)

            try:

                li=listing_generator.next()
                link_url=li.getProperty('link_url')
                label=li.getLabel()
                label=label.replace(link_url, "")  #remove the http:... part to avoid it looking duplicated because it is already put as a label in button.
                thumb=li.getArt('thumb')

            except StopIteration:
                li=label=link_url=None

            if label:
                tx_control.setText(label)

                if link_url=='http://blank.padding':  #the regex generating this list is not perfect. a padding was added to make it work. we ignore it here.
                    bn_control.setVisible(False)
                else:
                    bn_control.setLabel(label=link_url)
            else:
                tx_control.setText(None)
                tx_control.setVisible(False)
                bn_control.setVisible(False)

            if thumb:
                img_control.setImage(thumb)
            else:
                img_control.setVisible(False) #hide the unused controls so they don't occupy 'space' in the grouplist


    def onFocus(self,controlId):
        pass

    def onClick(self, controlID):
        clicked_control=self.getControl(controlID)

        value_to_search=clicked_control.getLabel() #we'll just use the Property('link_url') that we used as button label to search
        listitems=self.listing

        li = next(l for l in listitems if l.getProperty('link_url') == value_to_search)

        item_type=li.getProperty('item_type')
        di_url=li.getProperty('onClick_action')

        log( "  clicked %s  IsPlayable=%s  url=%s " %( repr(clicked_control),item_type, di_url )   )
        if item_type=='playable':

                pl = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
                pl.clear()
                pl.add(di_url, value_to_search)
                xbmc.Player().play(pl, windowed=False)
        elif item_type=='script':
            self.busy_execute_sleep(di_url,5000,False)

def animation_format(delay, time, effect, start, end, tween='', easing='', center='', extras=''  ):
    a='condition=true delay={0} time={1} '.format(delay, time)

    a+= 'effect={} '.format(effect)
    if start!=None: a+= 'start={} '.format(start)
    if end!=None:   a+= 'end={} '.format(end)

    if center: a+= 'center={} '.format(center)
    if tween:  a+= 'tween={} '.format(tween)
    if easing: a+= 'easing={} '.format(easing)  #'in' 'out' 'inout'
    if extras: a+= extras

    return ('conditional', a )

if __name__ == '__main__':
    pass

