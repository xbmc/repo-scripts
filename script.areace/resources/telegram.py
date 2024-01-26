import requests
import re
import datetime as dtm

host="https://api.telegram.org/"

def handleMessage(post, results):
    if(not 'text' in post): return
    text = post['text']
    timestamp = post['date']
    date = dtm.datetime.fromtimestamp(timestamp)
    obj={'text':' '.join(text.split()),'date':date}
    match = re.findall(r'[0-9a-f]{40}', text)
    for id in match:
        o = obj.copy()
        o['acestream_id'] = id
        results.append(o)

def handleTelegramResponse(json):
    if(not json['ok']): return []
    results=[]
    for update in json['result']:
        if('channel_post' in update): handleMessage(update['channel_post'], results)
        if('message' in update): handleMessage(update['message'], results)
    return results

def fetch(config):
    params = dict(offset=config['offset'])
    url=host+'bot'+config['token']+'/getUpdates'
    res = requests.get(url, params)
    return handleTelegramResponse(res.json())