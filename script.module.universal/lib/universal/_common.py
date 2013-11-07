'''
    universal XBMC module
    Copyright (C) 2013 the-one @ XUNITYTALK.COM

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import os    
from t0mm0.common.addon import Addon
import xbmc
import xbmcvfs
import xbmcgui

addon = Addon('script.module.universal')
addon_path = addon.get_path()

default_path = 'special://profile/addon_data/script.module.universal/'

db_path = addon.get_setting('local_save_location')
use_remote_db = addon.get_setting('use_remote_db')
db_address = addon.get_setting('db_address')
db_port = addon.get_setting('db_port')
if db_port: db_address = '%s:%s' %(db_address,db_port)
db_user = addon.get_setting('db_user')
db_pass = addon.get_setting('db_pass')
db_name = addon.get_setting('db_name')

def make_dir(mypath, dirname):
    ''' Creates sub-directories if they are not found. '''
    subpath = os.path.join(mypath, dirname)
    if not xbmcvfs.exists(subpath): 
        try:
            xbmcvfs.mkdirs(subpath)
        except:
            xbmcvfs.mkdir(subpath)
    return subpath
    
def bool2str(myinput):    
    if myinput is False: return 'false'
    elif myinput is True: return 'true'
    
def str2bool(myinput):    
    if myinput == 'false': return False
    elif myinput == 'true': return True
    
def str_conv(data):
    if isinstance(data, str):
        # Must be encoded in UTF-8
        data = data.decode('utf8')
	
    import unicodedata
    data = unicodedata.normalize('NFKD', data).encode('ascii','ignore')
	
    data = data.decode('string-escape')
        
    return data
        
def encode_dict(dict):
    out_dict = {}
    for k, v in dict.iteritems():
        v = str_conv(v)
        if v.find(',') >= 0:
            v = v.replace(',', '<comma>')
        if v.find("'") >= 0:
            v = v.replace("'", '<squot>')
        if v.find('"') >= 0:
            v = v.replace('"', '<dquot>')
        if v.find('{') >= 0:
            v = v.replace('{', '<ltbrc>')
        if v.find('}') >= 0:
            v = v.replace('}', '<rtbrc>')
        if v.find(':') >= 0:
            v = v.replace(':', '<colon>')
        out_dict[k] = v
    return out_dict
    
def decode_dict(dict):
    out_dict = {}
    for k, v in dict.iteritems():
        v = str_conv(v)
        if v.find('<comma>') >= 0:
            v = v.replace('<comma>', ',')
        if v.find("<squot>") >= 0:
            v = v.replace("<squot>", "'")
        if v.find('<dquot>') >= 0:
            v = v.replace("<dquot>", '"')
        if v.find('<ltbrc>') >= 0:
            v = v.replace('<ltbrc>', '{')
        if v.find('<rtbrc>') >= 0:
            v = v.replace('<rtbrc>', '}')
        if v.find('<colon>') >= 0:
            v = v.replace('<colon>', ':')        
        out_dict[k] = v
    return out_dict    

def dict_to_paramstr(dict):
    out_dict = {}
    for k, v in dict.iteritems():
        if isinstance(v, unicode):
            v = v.encode('utf8')
        elif isinstance(v, str):
            # Must be encoded in UTF-8
            v.decode('utf8')
        out_dict[k] = v
    
    import urllib    
    return urllib.urlencode(out_dict)
    
def notify(addon_id, typeq, title, message, times, line2='', line3=''):
    addon_tmp = Addon(addon_id)
    if title == '' :
        title='[B]' + addon_tmp.get_name() + '[/B]'
    if typeq == 'small':
        if times == '':
           times='5000'
        smallicon= addon_tmp.get_icon()
        xbmc.executebuiltin("XBMC.Notification("+title+","+message+","+times+","+smallicon+")")
    elif typeq == 'big':
        dialog = xbmcgui.Dialog()
        dialog.ok(' '+title+' ', ' '+message+' ', line2, line3)
    else:
        dialog = xbmcgui.Dialog()
        dialog.ok(' '+title+' ', ' '+message+' ')    
        
def TextBoxes(heading,anounce):
        class TextBox():
            """Thanks to BSTRDMKR for this code:)"""
                # constants
            WINDOW = 10147
            CONTROL_LABEL = 1
            CONTROL_TEXTBOX = 5

            def __init__( self, *args, **kwargs):
                # activate the text viewer window
                xbmc.executebuiltin( "ActivateWindow(%d)" % ( self.WINDOW, ) )
                # get window
                self.win = xbmcgui.Window( self.WINDOW )                
                # give window time to initialize
                xbmc.sleep( 500 )
                self.setControls()
                xbmc.sleep( 500 )

            def setControls( self ):
                # set heading
                self.win.getControl( self.CONTROL_LABEL ).setLabel(heading)
                try:
                        f = open(anounce)
                        text = f.read()
                except:
                        text=anounce
                self.win.getControl( self.CONTROL_TEXTBOX ).setText(text)
                return
        TextBox()        
