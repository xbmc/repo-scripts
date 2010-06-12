import sys
import os
import xbmc
import xbmcgui
import urllib
import feedparser
#import threading

_ = sys.modules[ "__main__" ].__language__
__scriptname__ = sys.modules[ "__main__" ].__scriptname__
__version__ = sys.modules[ "__main__" ].__version__
__settings__ = sys.modules[ "__main__" ].__settings__


_URL = "https://mail.google.com/gmail/feed/atom"

STATUS_LABEL = 100
EMAIL_LIST = 120


class GUI( xbmcgui.WindowXMLDialog ):
	
    def __init__( self, *args, **kwargs ):
    	
	  pass


    def onInit( self ):
    	
		self.setup_all()

    def _get_urlopener(self):
	   tw_usr = __settings__.getSetting( "user" )
	   tw_pwd = __settings__.getSetting( "pass" )

	   urlopener = _FancyURLopener(tw_usr, tw_pwd)
	   self.getControl( STATUS_LABEL ).setLabel( "Connecting to Gmail ......")
	   headers = [('User-agent', "urllib/1.0 (urllib)")]
	   urlopener.addheaders = headers
	   return urlopener	    

    
    def setup_all( self ):
    	self.getControl( STATUS_LABEL ).setLabel( "Connecting to Gmail ...")
    	self.getControl( EMAIL_LIST ).reset()
    	
    	
    	try:
    		
    		if len(__settings__.getSetting( "user" )) > 3 and len(__settings__.getSetting( "pass" )) > 4:
    			atom_feed = self._get_urlopener().open(_URL)
	    		atom = feedparser.parse(atom_feed)
	    		self.atom = atom
	    		self.entries = []
	    		self.getControl( STATUS_LABEL ).setLabel( atom.feed.title)
	    		entries = len(atom.entries)
	    		if entries > 0:	
	    			if entries == 1:self.getControl( 101 ).setLabel("(%s) New e-mail" % entries)
	    			else : self.getControl( 101 ).setLabel("(%s) New e-mails" % entries)

	    			for i in xrange(len(atom.entries)):
	    				title = atom.entries[i].author.split('(', 1)[0]
	
	    				listitem = xbmcgui.ListItem( label2=(atom.entries[i].title, 50)[0], label=atom.entries[i].author.split('(', 1)[0])
		        	
		        		listitem.setProperty( "summary", atom.entries[i].summary )
		        		
		        		listitem.setProperty( "updated", "Received on %s (UTC)" % atom.entries[i].updated.replace("T", " At ").replace("Z","") )
	
	    				self.getControl( EMAIL_LIST ).addItem( listitem )
	    				 
	    			self.setFocus( self.getControl( EMAIL_LIST ) )
	    			self.getControl( EMAIL_LIST ).selectItem( 0 )
    		else:
    		
    			self.getControl( STATUS_LABEL ).setLabel( "Please set Username and Password")		    			
		   
    	except : 
   			error = "Error Connecting to Gmail"
   			self.getControl( STATUS_LABEL ).setLabel( error )

#    	global t
#    	
#    	interval = __settings__.getSetting( "interval" )
#    	
#    	if interval == "0": timer = 60    	
#    	if interval == "1": timer = 300
#    	if interval == "2": timer = 600
#
#    	t = threading.Timer(float(timer), self.setup_all)
#    	t.start()
    
    
    
    def onClick( self, controlId ):
    	pass	

    def onFocus( self, controlId ):

    	self.controlId = controlId

	
def onAction( self, action ):
	if ( action.getButtonCode() in CANCEL_DIALOG ):
		print "Closing"
		self.close()



class _FancyURLopener(urllib.FancyURLopener):

    def __init__(self, usr, pwd, prx={}):

        urllib.FancyURLopener.__init__(self,prx)
        self.usr = usr
        self.pwd = pwd
        
    def prompt_user_passwd(self, host, realm):

        return (self.usr,self.pwd)

