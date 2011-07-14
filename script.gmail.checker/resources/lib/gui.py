import sys
import os
import xbmc
import xbmcgui
import urllib
import feedparser
import socket

_              = sys.modules[ "__main__" ].__language__
__scriptname__ = sys.modules[ "__main__" ].__scriptname__
__version__    = sys.modules[ "__main__" ].__version__
__addon__      = sys.modules[ "__main__" ].__addon__

_URL = "https://mail.google.com/gmail/feed/atom"

STATUS_LABEL   = 100
EMAIL_LIST     = 120
CANCEL_DIALOG  = ( 9, 10, 216, 247, 257, 275, 61467, 61448, )

class GUI( xbmcgui.WindowXMLDialog ):
    
    def __init__( self, *args, **kwargs ):       
      pass

    def onInit( self ):  
      self.setup_all()

    def _get_urlopener(self):
      urlopener = _FancyURLopener(__addon__.getSetting( "user" ), __addon__.getSetting( "pass" ))
      self.getControl( STATUS_LABEL ).setLabel( _(610) + "...")
      urlopener.addheaders = [('User-agent', "urllib/1.0 (urllib)")]
      return urlopener

    def setup_all( self ):
      self.getControl( STATUS_LABEL ).setLabel( _(610) )
      self.getControl( EMAIL_LIST ).reset()
      
      if len(__addon__.getSetting( "user" )) > 3 and len(__addon__.getSetting( "pass" )) > 4:
        try:
          atom_feed = self._get_urlopener().open(_URL)
          atom = feedparser.parse(atom_feed)
          self.atom = atom
          self.entries = []
          self.getControl( STATUS_LABEL ).setLabel( atom.feed.title)
          entries = len(atom.entries)
          if entries > 0:    
            self.getControl( 101 ).setLabel( _(611) % (entries, "" if entries == 1 else "s",))

            for i in xrange(len(atom.entries)):
              title = atom.entries[i].author.split('(', 1)[0]
              listitem = xbmcgui.ListItem( label2=(atom.entries[i].title, 50)[0], label=atom.entries[i].author.split('(', 1)[0]) 
              listitem.setProperty( "summary", atom.entries[i].summary )    
              listitem.setProperty( "updated", _(612) % atom.entries[i].updated.replace("T", " At ").replace("Z","") )
              self.getControl( EMAIL_LIST ).addItem( listitem )
               
            self.setFocus( self.getControl( EMAIL_LIST ) )
            self.getControl( EMAIL_LIST ).selectItem( 0 )
        except:
          self.getControl( STATUS_LABEL ).setLabel( _(613) )

      else:
        self.getControl( STATUS_LABEL ).setLabel( _(614) )    
     
      socket.setdefaulttimeout(None)
    
    def onClick( self, controlId ):
      pass    

    def onFocus( self, controlId ):
      self.controlId = controlId

    def onAction( self, action ):
      if ( action.getId() in CANCEL_DIALOG):
        self.close()
    

class _FancyURLopener(urllib.FancyURLopener):
    def __init__(self, usr, pwd, prx={}):
      urllib.FancyURLopener.__init__(self,prx)
      self.usr = usr
      self.pwd = pwd
        
    def prompt_user_passwd(self, host, realm):
      return (self.usr,self.pwd)

