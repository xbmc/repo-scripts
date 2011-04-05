class TestData:
    abortRequested = False
    
    def getSetting(self,name):
        if name == 'debug':
            return 'true'
        elif name == 'testmode':
            return 'false'
        else:
            raise RuntimeError    

addon = None

try:
    import xbmcaddon
    addon = xbmcaddon.Addon(id='script.mymediadb')
except:
    addon = TestData()
    
try:
    import xbmc
except:
    xbmc = TestData()  
    

def debug(txt):
    if(addon.getSetting('debug') == 'true'):
        try:
            print txt
        except:
            pass
        
def sleeper(millis):
    while (not xbmc.abortRequested and millis > 0):
        xbmc.sleep(1000)
        millis -= 1000

