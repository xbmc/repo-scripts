import requests
import re
import datetime as dtm

host="https://api.telegram.org/"

def fetch(config):
    results=[]
    params = dict(offset=config['offset'])
    url=host+'bot'+config['token']+'/getUpdates'
    res = requests.get(url, params)
    json=res.json()
    for update in json['result']:
        if(not 'channel_post' in update): continue
        if(not 'text' in update['channel_post']): continue
        text = update['channel_post']['text']
        timestamp = update['channel_post']['date']
        date = dtm.datetime.fromtimestamp(timestamp)
        obj={'text':text,'date':date}
        match = re.search(r'[0-9a-f]{40}', text)
        if match:
            id = match.group()
            if (id): 
                obj['acestream_id'] = id
                results.append(obj)
    return results