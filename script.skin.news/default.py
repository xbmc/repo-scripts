import xbmc, xbmcgui, urllib, sys

try: 
    news = urllib.urlopen(sys.argv[ 1 ])
    newstext = news.read()
except: 
    newstext = False
    print "no url passed"

if (not newstext.startswith('[NEWS]')):
    newstext = 'Unable to fetch data from server. Please check your connection and try again later.'
else:
    newstext = newstext.replace('[NEWS]', '')
    
xbmcgui.Window(10000).setProperty("News",newstext)