import urllib2, json
import utils

BASE_URL = 'http://api.openweathermap.org/data/2.5/weather?id=1993378&lang=en&APPID=%s&units=metric'

for key in KEYS:
    url = BASE_URL % key
    req = urllib2.urlopen(url)
    response = req.read()
    req.close()
    data = json.loads(response)
    if data['cod'] == 401:
        print 'invalid key: %s' % key
    elif data['cod'] != 200:
        print 'error: %s' % data
