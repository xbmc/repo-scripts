# -*- coding: utf-8 -*-

'''
    Funimation|Now Add-on
    Copyright (C) 2016 Funimation|Now

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



import xbmcaddon;
import logging;
import base64;
import urllib;
import urllib2;
import re;
import json;

from resources.lib.modules import client;
from resources.lib.modules import utils;
from resources.lib.modules.xmltodict import parse;


logger = logging.getLogger('funimationnow');


api = dict({
    'login': 'auth/login/',
    'menu': 'mobile/menu/?territory=%s',
    'help': 'help/?territory=%s',
    'history-config': 'history/config/?territory=%s',
    'myqueue-config': 'myqueue/config/?territory=%s',
    'ratings-config': 'ratings/config/?territory=%s',
    #'history-items': 'history/get-items/?territory=%s',
    #'myqueue-items': 'myqueue/get-items/?territory=%s',
    #'ratings-items': 'ratings/get-items/?territory=%s',
    #'history': 'hitory/get/?territory=%s',
    #'myqueue': 'myqueue/get/?territory=%s',
    #'ratings': 'ratings/get/?territory=%s',
});

#https://github.com/martinblech/xmltodict


def getToken():
    
    token = None;

    try:
        token = utils.getToken('funimationnow')[2];

    except:
        pass;


    return token;


def getAgent():
    import platform;

    try:

        pname = platform.system();
        pversion = platform.version();
        bversion = xbmc.getInfoLabel('System.BuildVersion');
        bversion = bversion.split(' ');
        #kversion = xbmc.getInfoLabel('System.KernelVersion');
        
        agent = 'Kodi/%s (%s %s; XBMC Build/%s)' % (bversion[0], pname, pversion, bversion[1]);

    except:
        agent = 'Kodi/16.1 (Windows NT 10.1; XBMC Build/16.1)';

    return agent;


def getTerritory():
    #http://stackoverflow.com/questions/11787941/get-physical-position-of-device-with-python

    territory = None;

    try:
        territory = utils.setting('fn.territory');

    except:
        pass;

    tOverride = utils.setting('fn.territory_override');

    if tOverride and tOverride in ('true', 'True', True):
        territory = 'US';

    else:

        if territory is None or len(territory) < 1:

            try:

                request = urllib2.urlopen('http://freegeoip.net/json/');
                result = request.read();
                
                request.close();

                territory = str(json.loads(result).get('country_code', 'US'));
                territory = 'GB' if territory == 'UK' else territory;

            except Exception as inst:
                logger.error(inst);

                territory = 'US';


    return territory;


def getLength(data):

    try:
        return str(len(data));

    except:
        return None;


def getHeaders(data=None):

    try:

        hvalues = (getAgent(), getTerritory());

        if None in hvalues:
            headers = None;

        else:

            headers = dict({
                'Accept': '*/*',
                'Accept-Encoding': 'gzip, deflate',
                'clientVersion': utils.getAddonInfo('version'),
                'deviceCategory': 'Console',
                #'deviceType': 'Kodi Box', #Might need to hardcode Win8 due to header check
                'deviceType': 'Win8', #They seem to be intentionally slowing down this Query with the new API url when using Kodi Box
                'territory': hvalues[1],
                'User-Agent': hvalues[0], #They appear to have removed the need for an Agent, but incase they bring it back we are leaving it here
            });


            if data:

                headers.update({
                    'Content-Length': getLength(data),
                    'Content-Type': 'application/x-www-form-urlencoded',
                });


    except:
        headers = None;


    return headers;


def getUrl(sub=None, path=None):

    try:

        path = path if path is not None else api.get(sub);

        #return 'https://api-funimation.dadcdigital.com/xml/%s' % path;  #Old New API, possibly testing grounds
        return 'https://prod-api-funimationnow.dadcdigital.com/xml/%s' % path;

    except: 
        return None;


def encodeData(data):

    try:
        return urllib.urlencode(data);

    except:
        return None;


def setLock(state):

    if state == True:
        utils.lock();

    else:
        utils.unlock();


def login(uid, pwd):

    success = [False, False];

    setLock(True);

    try:

        payload = dict({
            'username': uid, 
            'password': pwd
        });

        url = getUrl('login', None);

        payload = encodeData(payload);
        headers = getHeaders(payload);

        if(payload and headers and url):
            result = client.request(url, post=payload, headers=headers);

        else:
            result = None;

        if result:

            try:

                result = parse(result);

                if 'error' in result['authentication']:

                    error = result['authentication'].get('error', 30300);
                    success = [False, error];

                elif 'token' in result['authentication']:
                    
                    success = utils.setSettings(result);

                    if success:
                        success = utils.setToken('funimationnow', utils.setting('fn.userName'), result['authentication']['token']);

                        userRole = utils.parseValue(result, ['authentication', 'parameters', 'header', 'userRole']);
                        userRole = False if userRole in ('Past Subscriber', 'Basic') else True;

                        success = [success, userRole];

            except Exception as inst:
        
                utils.sendNotification(30300, 3000);

                logger.error(inst);

        else:
            utils.sendNotification(30301, 3000);


    except Exception as inst:

        utils.sendNotification(30301, 3000);

        logger.error(inst);

    setLock(False);


    return success;


def menu():

    success = False;

    try:

        url = getUrl('menu', None);
        
        headers = getHeaders();

        for key in utils.setting('fn.Headers').split(','):
            headers.update({key: utils.setting('fn.%s' % key)});

        token = getToken();

        if(headers and token and url):

            headers.update({'Authorization': token});

            url = (url % headers.get('territory', 'US'));

            result = client.request(url, headers=headers);

        else:
            result = None;

        if result:

            try:

                result = parse(result);

                if 'error' in result['menu']:

                    error = result['menu'].get('error', 30301);
                    
                    utils.sendNotification(error, 5000);

                elif 'pointer' in result['menu']:
                    
                    success = utils.parseValue(result, ['menu', 'pointer'], False);

                else:
                    utils.sendNotification(30301, 3000);

            except Exception as inst:
        
                utils.sendNotification(30301, 3000);

                logger.error(inst);

        else:
            utils.sendNotification(30301, 3000);


    except Exception as inst:

        utils.sendNotification(30301, 3000);

        logger.error(inst);


    return success;


def helpMenu():

    success = False;

    try:

        url = getUrl('help', None);
        
        headers = getHeaders();

        for key in utils.setting('fn.Headers').split(','):
            headers.update({key: utils.setting('fn.%s' % key)});

        token = getToken();

        if(headers and token and url):

            headers.update({'Authorization': token});

            url = (url % headers.get('territory', 'US'));

            result = client.request(url, headers=headers);

        else:
            result = None;

        if result:

            try:

                result = parse(result);

                if 'error' in result['menu']:

                    error = result['menu'].get('error', 30301);
                    
                    utils.sendNotification(error, 5000);

                elif 'pointer' in result['menu']:
                    
                    success = utils.parseValue(result, ['menu', 'pointer'], False);

                else:
                    utils.sendNotification(30301, 3000);

            except Exception as inst:
        
                utils.sendNotification(30301, 3000);

                logger.error(inst);

        else:
            utils.sendNotification(30301, 3000);


    except Exception as inst:

        utils.sendNotification(30301, 3000);

        logger.error(inst);


    return success;


def actionBar(path, params):

    success = False;

    if path and params:

        params = quoteplus(params);

        try:

            url = getUrl(None, path);

            headers = getHeaders();

            for key in utils.setting('fn.Headers').split(','):
                headers.update({key: utils.setting('fn.%s' % key)});

            token = getToken();

            if(headers and token and url):

                headers.update({'Authorization': token});
                headers.update({'Devicetype': 'Win8'}); #New API Uses Headers

                url = '%s?%s' % (url, params);

                result = client.request(url, headers=headers);

            else:
                result = None;

            if result:

                try:

                    result = parse(result);

                    if 'error' in result['content']:

                        error = result['content'].get('error', 30301);
                        
                        utils.sendNotification(error, 5000);

                    elif 'title' in result['content']:
                        
                        success = utils.parseValue(result, ['content'], False);

                    else:
                        utils.sendNotification(30301, 3000);

                except Exception as inst:
            
                    utils.sendNotification(30301, 3000);

                    logger.error(inst);

            else:
                utils.sendNotification(30301, 3000);


        except Exception as inst:

            utils.sendNotification(30301, 3000);

            logger.error(inst);


    return success;


def homescreenmenu(hurl):

    success = False;

    try:

        url = getUrl(None, hurl['path']);
        
        headers = getHeaders();

        for key in utils.setting('fn.Headers').split(','):
            headers.update({key: utils.setting('fn.%s' % key)});

        token = getToken();

        if(headers and token and url):

            headers.update({'Authorization': token});

            url = ('%s?%s' % (url, hurl['params']));

            result = client.request(url, headers=headers);

        else:
            result = None;

        if result:

            try:

                result = parse(result);

                if 'error' in result['list2d']:

                    error = result['list2d'].get('error', 30301);
                    
                    utils.sendNotification(error, 5000);

                elif 'pointer' in result['list2d']:
                    
                    success = utils.parseValue(result, ['list2d', 'pointer'], False);

                else:
                    utils.sendNotification(30301, 3000);

            except Exception as inst:
        
                utils.sendNotification(30301, 3000);

                logger.error(inst);

        else:
            utils.sendNotification(30301, 3000);


    except Exception as inst:

        utils.sendNotification(30301, 3000);

        logger.error(inst);

    setLock(False);


    return success;


def contentCarousel(pointer, idx, myqueue=None):

    success = [None, None, None];

    try:

        features = utils.parseValue(pointer, ['content', 'carousel', 'item'], False);

        if features:

            items = [];

            for item in features:

                try:

                    params = utils.parseValue(item, ['pointer', 'params']);
                    thumbnail = utils.parseValue(item, ['thumbnail', 'alternate'], True, ['parseAlternateImg', '@platforms', 'firetv']);
                    thumbnail = thumbnail if thumbnail is not None else utils.parseValue(item, ['thumbnail', '#text']);
                    thumbnail = formatImgUrl(thumbnail, theme='show');

                    items.append(dict({
                        'title': utils.parseValue(item, ['title']),
                        'description': utils.parseValue(item, ['subtitle']),
                        'thumbnail': thumbnail,
                        'path': utils.parseValue(item, ['pointer', 'path']),
                        'params': params,
                        'titleimg': 'f_%s.png' % params,
                    }));
                    

                except Exception as inst:
                    logger.error(inst);


            menubutton = utils.parseValue(features[0], ['content', 'description'], encoded=False);
            menubutton = utils.parseBtnText(menubutton, '305%02d' % idx);
            menubutton = utils.text2HomeMenu(idx, menubutton);

            navigation = dict({
                'width': menubutton,
                'title': utils.parseValue(features[0], ['content', 'description']),
                'target': utils.parseValue(features[0], ['pointer', 'target']),
                'path': utils.parseValue(features[0], ['pointer', 'path']),
                'params': utils.parseValue(features[0], ['pointer', 'params']),
            });

            features = items;

            success = ['features', features, navigation];


    except Exception as inst:

        success = [None, None, None];

        utils.sendNotification(30301, 3000);

        logger.error(inst);


    return success;


def watchlist(viewtype=None, pkey=None, pointer=None, idx=None):

    success = False;

    try:

        #logger.debug(pointer['longList']['watchlist']['name'])
        viewtype = pointer['longList']['watchlist']['name'] if viewtype is None else viewtype;

        success = globals()[viewtype](pkey, pointer, idx);

        #history
        #myqueue

    except Exception as inst:

        utils.sendNotification(30301, 3000);

        logger.error(inst);


    return success;


def selection(path, params, desc, viewtype, idx=0, loadDisplay=True):

    success = False;

    try:

        success = globals()[path[:-1]](path, params, desc, viewtype, idx, loadDisplay);

    except Exception as inst:

        #utils.sendNotification(30301, 3000);

        logger.error(inst);


    return success;


def history(pkey, pointer, idx):

    success = [None, None, None, None];

    try:

        hconfig = getHistoryConfig();
        hitems = getHistoryItems(hconfig);
        history = getHistory(hconfig);

        if hitems:

            items = [];

            for item in hitems:

                try:

                    historyParams = utils.parseValue(item, ['item', 'history', 'data', 'params']);
                    startPosition = utils.parseValue(history, [historyParams, 'startPosition']);
                    historyDuration = utils.parseValue(history, [historyParams, 'historyDuration']);

                    thumbnail = utils.parseValue(item, ['item', 'thumbnail', 'alternate'], True, ['parseAlternateImg', '@platforms', 'firetv']);
                    thumbnail = thumbnail if thumbnail is not None else utils.parseValue(item, ['item', 'thumbnail', '#text']);
                    thumbnail = formatImgUrl(thumbnail, theme='episode');

                    items.append(dict({
                        'title': utils.parseValue(item, ['item', 'title']),
                        'subtitle': utils.parseValue(item, ['item', 'subtitle']),
                        'thumbnail': thumbnail,
                        'themes': utils.parseValue(item, ['item', 'themes']),
                        'titleimg': 'h_%s.png' % historyParams,
                        'path': utils.parseValue(item, ['item', 'pointer', 'path']),
                        'params': utils.parseValue(item, ['item', 'pointer', 'params']),
                        'ratings': utils.parseValue(item, ['item', 'ratings', 'tv'], True, ['parseRegion', '@region', getTerritory()]),
                        'description': utils.parseValue(item, ['item', 'content', 'description']),
                        'quality': utils.parseValue(item, ['item', 'content', 'metadata', 'format']),
                        'languages': utils.parseValue(item, ['item', 'content', 'metadata', 'languages']),
                        'duration': utils.parseValue(item, ['item', 'content', 'metadata', 'duration']),
                        'episodeNumber': utils.parseValue(item, ['item', 'content', 'metadata', 'episodeNumber']),
                        'contentType': utils.parseValue(item, ['item', 'content', 'metadata', 'contentType']),
                        'releaseYear': utils.parseValue(item, ['item', 'content', 'metadata', 'releaseYear']),
                        'progress': utils.parseProgress(startPosition, historyDuration),
                        'historyPath': utils.parseValue(item, ['item', 'history', 'data', 'path']),
                        'historyParams': historyParams,
                        'startPosition': startPosition,
                        'historyDuration': historyDuration,
                    }));


                except Exception as inst:
                    logger.error(inst);

            
            hitems = items;


            if (hitems is None or len(hitems) < 1) and pointer:

                thumbnail = utils.parseValue(pointer, ['longList', 'watchlist', 'item', 'thumbnail']);
                thumbnail = formatImgUrl(thumbnail, theme='episode');

                hitems = [
                    dict({
                        'title': utils.parseValue(pointer, ['longList', 'watchlist', 'item', 'title']),
                        'subtitle': None,
                        'thumbnail': thumbnail,
                        'themes': None,
                        'titleimg': 'h_filler.png',
                        'path': None,
                        'params': None,
                        'ratings': None,
                        'description': utils.parseValue(pointer, ['longList', 'watchlist', 'item', 'title']),
                        'quality': None,
                        'languages': None,
                        'duration': None,
                        'episodeNumber': None,
                        'contentType': None,
                        'releaseYear': None,
                        'progress': None,
                        'historyPath': None,
                        'historyParams': None,
                        'startPosition': None,
                        'historyDuration': None,
                        'noitem': True,
                    })
                ];

            if idx and pointer:

                menubutton = utils.parseValue(pointer, ['pageButton', 'title'], encoded=False);
                menubutton = utils.parseBtnText(menubutton, '305%02d' % idx);
                menubutton = utils.text2HomeMenu(idx, menubutton);

                navigation = dict({
                    'width': menubutton,
                    'title': utils.parseValue(pointer, ['pageButton', 'title']),
                    'target': utils.parseValue(pointer, ['pageButton', 'pointer', 'target']),
                    'path': utils.parseValue(pointer, ['pageButton', 'pointer', 'path']),
                    'params': utils.parseValue(pointer, ['pageButton', 'pointer', 'params']),
                });

            else:
                navigation = None;

            success = ['history', hitems, history, navigation, hconfig];


    except Exception as inst:

        success = [None, None, None, None];

        utils.sendNotification(30301, 3000);

        logger.error(inst);


    return success;


def getHistoryConfig():

    success = False;

    try:

        url = getUrl('history-config', None);
        
        headers = getHeaders();

        for key in utils.setting('fn.Headers').split(','):
            headers.update({key: utils.setting('fn.%s' % key)});

        token = getToken();

        if(headers and token and url):

            headers.update({'Authorization': token});

            url = (url % headers.get('territory', 'US'));

            result = client.request(url, headers=headers);

        else:
            result = None;

        if result:

            try:

                #logger.debug(parse(result));
                #logger.debug(json.dumps(parse(result)));
                #logger.debug(json.dumps(parse(result, process_namespaces=True)));

                result = parse(result);

                if 'error' in result['history']:

                    error = result['history'].get('error', 30301);
                    
                    utils.sendNotification(error, 5000);

                elif 'getItems' in result['history']:

                    success = dict({
                        'add': utils.parseValue(result, ['history', 'add', 'pointer', 'path'], False),
                        'get': utils.parseValue(result, ['history', 'get', 'pointer', 'path'], False),
                        'getItems': utils.parseValue(result, ['history', 'getItems', 'pointer', 'path'], False),
                        'duration': utils.parseValue(result, ['history', 'duration', 'param'], False),
                        'startPosition': utils.parseValue(result, ['history', 'startPosition', 'param'], False),
                        'msBetweenSaves': utils.parseValue(result, ['history', 'msBetweenSaves'], False),
                    });
                        
                else:
                    utils.sendNotification(30301, 3000);

            except Exception as inst:
        
                utils.sendNotification(30301, 3000);

                logger.error(inst);

        else:
            utils.sendNotification(30301, 3000);


    except Exception as inst:

        utils.sendNotification(30301, 3000);

        logger.error(inst);


    return success;


def getHistoryItems(hconfig):

    success = False;

    if hconfig:

        try:

            url = hconfig.get('getItems', None);
           
            headers = getHeaders();

            for key in utils.setting('fn.Headers').split(','):
                headers.update({key: utils.setting('fn.%s' % key)});

            token = getToken();

            if(headers and token and url):

                headers.update({'Authorization': token});

                url = ('%s?territory=%s' % (url, headers.get('territory', 'US')));

                result = client.request(url, headers=headers);

            else:
                result = None;

            if result:

                try:

                    result = parse(result);

                    if 'error' in result['watchlist']:

                        error = result['watchlist'].get('error', 30301);
                        
                        utils.sendNotification(error, 5000);

                    elif 'items' in result['watchlist']:
                        
                        #success = result['watchlist']['items']['item'];
                        success = utils.parseValue(result, ['watchlist', 'items', 'item'], False);

                        if success and not isinstance(success, list):
                            success = list([success]);

                    else:
                        #utils.sendNotification(30301, 3000);
                        pass;

                except Exception as inst:
            
                    utils.sendNotification(30301, 3000);

                    logger.error(inst);

            else:
                utils.sendNotification(30301, 3000);


        except Exception as inst:

            utils.sendNotification(30301, 3000);

            logger.error(inst);


    return success;


def getHistory(hconfig):

    success = False;

    if hconfig:

        try:

            url = hconfig.get('get', None);
           
            headers = getHeaders();

            for key in utils.setting('fn.Headers').split(','):
                headers.update({key: utils.setting('fn.%s' % key)});

            token = getToken();

            if(headers and token and url):

                headers.update({'Authorization': token});

                url = ('%s?territory=%s' % (url, headers.get('territory', 'US')));

                result = client.request(url, headers=headers);

            else:
                result = None;

            if result:

                try:

                    result = parse(result);

                    if 'error' in result['watchlist']:

                        error = result['watchlist'].get('error', 30301);
                        
                        utils.sendNotification(error, 5000);

                    elif 'items' in result['watchlist']:

                        items = utils.parseValue(result, ['watchlist', 'items'], False);

                        if items and len(items) > 0:

                            historyItems = utils.parseValue(items, ['historyItem'], False);

                            if historyItems:

                                if not isinstance(historyItems, list):
                                
                                    historyItems = list([historyItems]);

                                if len(historyItems) > 0:

                                    success = dict();

                                    for historyItem in historyItems:

                                        success.update({
                                            utils.parseValue(historyItem, ['params']): dict({
                                                'historyPath': utils.parseValue(historyItem, ['path']),
                                                'historyParams': utils.parseValue(historyItem, ['params']),
                                                'startPosition': utils.parseValue(historyItem, ['startPosition']),
                                                'historyDuration': utils.parseValue(historyItem, ['duration'])
                                            })
                                        });

                    else:
                        #utils.sendNotification(30301, 3000);
                        pass;

                except Exception as inst:
            
                    utils.sendNotification(30301, 3000);

                    logger.error(inst);

            else:
                utils.sendNotification(30301, 3000);


        except Exception as inst:

            utils.sendNotification(30301, 3000);

            logger.error(inst);


    return success;


def myqueue(pkey, pointer, idx):

    success = [None, None, None, None, None];

    try:

        mqconfig = getMyQueueConfig();
        mqitems = getMyQueueItems(mqconfig);
        myqueue = getMyQueue(mqconfig);

        items = [];

        if mqitems is not None:

            for item in mqitems:

                try:

                    params = utils.parseValue(item, ['params']);
                    myQueuePath = utils.parseValue(myqueue, [params, 'myQueuePath']);
                    myQueueParams = utils.parseValue(myqueue, [params, 'myQueueParams']);


                    if (pointer or myQueueParams == pkey) or (pointer is None and pkey is None):

                        try:

                            thumbnail = utils.parseValue(item, ['item', 'thumbnail', 'alternate'], True, ['parseAlternateImg', '@platforms', 'firetv']);
                            thumbnail = thumbnail if thumbnail is not None else utils.parseValue(item, ['item', 'thumbnail', '#text']); 

                        except:
                            thumbnail = utils.parseValue(item, ['item', 'thumbnail']);


                        thumbnail = formatImgUrl(thumbnail, theme='show');


                        items.append(dict({
                            'title': utils.parseValue(item, ['item', 'title']),
                            'thumbnail': thumbnail,
                            'starPath': utils.parseValue(item, ['item', 'starRating', 'data', 'path']),
                            'starParams': utils.parseValue(item, ['item', 'starRating', 'data', 'params']),
                            'starRating': utils.parseValue(item, ['item', 'starRating', 'rating']),
                            'ratings': utils.parseValue(item, ['item', 'ratings', 'tv'], True, ['parseRegion', '@region', getTerritory()]),
                            'quality': utils.parseValue(item, ['item', 'content', 'metadata', 'format']),
                            'releaseYear': utils.parseValue(item, ['item', 'content', 'metadata', 'releaseYear']),
                            'detailPath': utils.parseValue(item, ['item', 'pointer', 'path']),
                            'detailParams': utils.parseValue(item, ['item', 'pointer', 'params']),
                            'titleimg': 'mq_%s.png' % utils.parseValue(item, ['item', 'pointer', 'params']),
                            'path': utils.parseValue(item, ['path']),
                            'params': params,
                            'myQueuePath': myQueuePath,
                            'myQueueParams': myQueueParams,
                            'inQueue': (0 if myQueuePath is not None else 1)
                        }));

                        '''
                            success = dict({
                                'add': utils.parseValue(result, ['toggle', 'add', 'pointer', 'path'], False),
                                'remove': utils.parseValue(result, ['toggle', 'remove', 'pointer', 'path'], False),
                                'get': utils.parseValue(result, ['toggle', 'get', 'pointer', 'path'], False),
                                'getItems': utils.parseValue(result, ['toggle', 'getItems', 'pointer', 'path'], False),
                            });
                        '''


                except Exception as inst:
                    logger.error(inst);
        

        mqitems = items;

        if (mqitems is None or len(mqitems) < 1) and pointer:

            try:

                thumbnail = utils.parseValue(pointer, ['longList', 'watchlist', 'item', 'thumbnail', 'alternate'], True, ['parseAlternateImg', '@platforms', 'firetv']);
                thumbnail = thumbnail if thumbnail is not None else utils.parseValue(pointer, ['longList', 'watchlist', 'item', 'thumbnail']);

            except:
                thumbnail = utils.parseValue(pointer, ['longList', 'watchlist', 'item', 'thumbnail']);


            thumbnail = formatImgUrl(thumbnail, theme='show');


            mqitems = [
                dict({
                    'title': utils.parseValue(pointer, ['longList', 'watchlist', 'item', 'title']),
                    'thumbnail': thumbnail,
                    'starPath': None,
                    'starParams': None,
                    'starRating': None,
                    'ratings': None,
                    'quality': None,
                    'releaseYear': None,
                    'detailPath': None,
                    'detailParams': None,
                    'titleimg': 'mq_filler.png',
                    'path': None,
                    'params': None,
                    'myQueuePath': None,
                    'myQueueParams': None,
                    'inQueue': None,
                    'noitem': True,
                })
            ];

        if idx and pointer:

            menubutton = utils.parseValue(pointer, ['pageButton', 'title'], encoded=False);
            menubutton = utils.parseBtnText(menubutton, '305%02d' % idx);
            menubutton = utils.text2HomeMenu(idx, menubutton);

            navigation = dict({
                'width': menubutton,
                'title': utils.parseValue(pointer, ['pageButton', 'title']),
                'target': utils.parseValue(pointer, ['pageButton', 'pointer', 'target']),
                'path': utils.parseValue(pointer, ['pageButton', 'pointer', 'path']),
                'params': utils.parseValue(pointer, ['pageButton', 'pointer', 'params']),
            });

        else:
            navigation = None;

        success = ['myqueue', mqitems, myqueue, navigation, mqconfig];


    except Exception as inst:

        success = [None, None, None, None, None];

        utils.sendNotification(30301, 3000);

        logger.error(inst);


    return success;


def getMyQueueConfig():

    success = False;

    try:

        url = getUrl('myqueue-config', None);
        
        headers = getHeaders();

        for key in utils.setting('fn.Headers').split(','):
            headers.update({key: utils.setting('fn.%s' % key)});

        token = getToken();

        if(headers and token and url):

            headers.update({'Authorization': token});

            url = (url % headers.get('territory', 'US'));

            result = client.request(url, headers=headers);

        else:
            result = None;

        if result:

            try:

                result = parse(result);

                if 'error' in result['toggle']:

                    error = result['toggle'].get('error', 30301);
                    
                    utils.sendNotification(error, 5000);

                elif 'getItems' in result['toggle']:
                    
                    success = dict({
                        'add': utils.parseValue(result, ['toggle', 'add', 'pointer', 'path'], False),
                        'remove': utils.parseValue(result, ['toggle', 'remove', 'pointer', 'path'], False),
                        'get': utils.parseValue(result, ['toggle', 'get', 'pointer', 'path'], False),
                        'getItems': utils.parseValue(result, ['toggle', 'getItems', 'pointer', 'path'], False),
                    });

                else:
                    #utils.sendNotification(30301, 3000);
                    pass;

            except Exception as inst:
        
                utils.sendNotification(30301, 3000);

                logger.error(inst);

        else:
            utils.sendNotification(30301, 3000);
            pass;


    except Exception as inst:

        utils.sendNotification(30301, 3000);

        logger.error(inst);


    return success;


def getMyQueueItems(mqconfig):

    success = False;

    if mqconfig:

        try:

            url = mqconfig.get('getItems', None);
           
            headers = getHeaders();

            for key in utils.setting('fn.Headers').split(','):
                headers.update({key: utils.setting('fn.%s' % key)});

            token = getToken();

            if(headers and token and url):

                headers.update({'Authorization': token});

                url = ('%s?territory=%s' % (url, headers.get('territory', 'US')));

                result = client.request(url, headers=headers);

            else:
                result = None;

            if result:

                try:

                    result = parse(result);

                    if 'error' in result['watchlist']:

                        error = result['watchlist'].get('error', 30301);
                        
                        utils.sendNotification(error, 5000);

                    elif 'items' in result['watchlist']:
                        
                        success = utils.parseValue(result, ['watchlist', 'items', 'item'], False);

                        if success and not isinstance(success, list):
                            success = list([success]);

                    else:
                        #utils.sendNotification(30301, 3000);
                        success = False;
                        pass;

                except Exception as inst:
            
                    utils.sendNotification(30301, 3000);

                    logger.error(inst);

            else:
                utils.sendNotification(30301, 3000);
                pass;


        except Exception as inst:

            utils.sendNotification(30301, 3000);

            logger.error(inst);


    return success;


def getMyQueue(mqconfig):

    success = False;

    if mqconfig:

        try:

            url = mqconfig.get('get', None);
           
            headers = getHeaders();

            for key in utils.setting('fn.Headers').split(','):
                headers.update({key: utils.setting('fn.%s' % key)});

            token = getToken();

            if(headers and token and url):

                headers.update({'Authorization': token});

                url = ('%s?territory=%s' % (url, headers.get('territory', 'US')));

                result = client.request(url, headers=headers);

            else:
                result = None;

            if result:

                try:

                    result = parse(result);

                    if 'error' in result['watchlist']:

                        error = result['watchlist'].get('error', 30301);
                        
                        utils.sendNotification(error, 5000);

                    elif 'items' in result['watchlist']:
                        
                        items = utils.parseValue(result, ['watchlist', 'items'], False);

                        if items and len(items) > 0:

                            myQueueItems = utils.parseValue(items, ['item'], False);

                            if myQueueItems:

                                if not isinstance(myQueueItems, list):
                                    
                                    myQueueItems = list([myQueueItems]);

                                if len(myQueueItems) > 0:

                                    success = dict();

                                    for myQueueItem in myQueueItems:

                                        success.update({
                                            utils.parseValue(myQueueItem, ['params']): dict({
                                                'myQueuePath': utils.parseValue(myQueueItem, ['path']),
                                                'myQueueParams': utils.parseValue(myQueueItem, ['params']),
                                            })
                                        });

                    else:
                        #utils.sendNotification(30301, 3000);
                        pass;

                except Exception as inst:
            
                    #utils.sendNotification(30301, 3000);

                    logger.error(inst);

            else:
                utils.sendNotification(30301, 3000);
                pass;


        except Exception as inst:

            utils.sendNotification(30301, 3000);

            logger.error(inst);


    return success;


def getRatingsConfig():

    success = False;

    try:

        url = getUrl('ratings-config', None);
        
        headers = getHeaders();

        for key in utils.setting('fn.Headers').split(','):
            headers.update({key: utils.setting('fn.%s' % key)});

        token = getToken();

        if(headers and token and url):

            headers.update({'Authorization': token});

            url = (url % headers.get('territory', 'US'));

            result = client.request(url, headers=headers);

        else:
            result = None;

        if result:

            try:

                result = parse(result);

                logger.debug(json.dumps(result));
                
                if 'error' in result['starRating']:

                    error = result['starRating'].get('error', 30301);
                    
                    utils.sendNotification(error, 5000);

                elif 'getItems' in result['starRating']:

                    success = result['starRating'];
                        
                else:
                    utils.sendNotification(30301, 3000);

            except Exception as inst:

                utils.sendNotification(30301, 3000);

                logger.error(inst);

        else:
            utils.sendNotification(30301, 3000);


    except Exception as inst:

        utils.sendNotification(30301, 3000);

        logger.error(inst);


    return success;


def getMyRatings(rconfig):

    success = False;

    if rconfig:

        try:

            url = utils.parseValue(rconfig, ['getItems', 'pointer', 'path']);
           
            headers = getHeaders();

            for key in utils.setting('fn.Headers').split(','):
                headers.update({key: utils.setting('fn.%s' % key)});

            token = getToken();

            if(headers and token and url):

                headers.update({'Authorization': token});

                url = ('%s?territory=%s' % (url, headers.get('territory', 'US')));

                result = client.request(url, headers=headers);

            else:
                result = None;

            if result:

                try:

                    result = parse(result);

                    if 'error' in result['watchlist']:

                        error = result['watchlist'].get('error', 30301);
                        
                        utils.sendNotification(error, 5000);

                    elif 'items' in result['watchlist']:
                        
                        items = utils.parseValue(result, ['watchlist', 'items'], False);

                        if items and len(items) > 0:

                            myStarItems = utils.parseValue(items, ['starItem'], False);

                            if myStarItems:

                                if not isinstance(myStarItems, list):
                                    
                                    myStarItems = list([myStarItems]);

                                if len(myStarItems) > 0:

                                    success = dict();

                                    for myStarItem in myStarItems:

                                        success.update({
                                            utils.parseValue(myStarItem, ['params']): dict({
                                                'myStarPath': utils.parseValue(myStarItem, ['path']),
                                                'myStarParams': utils.parseValue(myStarItem, ['params']),
                                                'myStarRating': utils.parseValue(myStarItem, ['rating']),
                                            })
                                        });

                    else:
                        utils.sendNotification(30301, 3000);

                except Exception as inst:
            
                    utils.sendNotification(30301, 3000);

                    logger.error(inst);

            else:
                utils.sendNotification(30301, 3000);


        except Exception as inst:

            utils.sendNotification(30301, 3000);

            logger.error(inst);


    return success;


def episode(pointer, idx, history):

    success = [None, None, None];

    try:

        episodes = utils.parseValue(pointer, ['longList', 'items', 'item'], False);

        if episodes:

            items = [];

            for item in episodes:

                try:

                    eid = utils.parseValue(item, ['id']);
                    historyParams = utils.parseValue(item, ['history', 'data', 'params']);
                    startPosition = utils.parseValue(history, [historyParams, 'startPosition']);
                    historyDuration = utils.parseValue(history, [historyParams, 'historyDuration']);
                    thumbnail = utils.parseValue(item, ['thumbnail', 'alternate'], True, ['parseAlternateImg', '@platforms', 'firetv']);
                    thumbnail = thumbnail if thumbnail is not None else utils.parseValue(item, ['thumbnail', '#text']);
                    thumbnail = formatImgUrl(thumbnail, theme='episode');

                    items.append(dict({
                        'title': utils.parseValue(item, ['title']),
                        'subtitle': utils.parseValue(item, ['subtitle']),
                        'thumbnail': thumbnail,
                        'themes': utils.parseValue(item, ['themes']),
                        'id': eid,
                        'titleimg': 'e_%s.png' % eid,
                        'ratings': utils.parseValue(item, ['ratings', 'tv'], True, ['parseRegion', '@region', getTerritory()]),
                        'starPath': utils.parseValue(item, ['starRating', 'data', 'path']),
                        'starParams': utils.parseValue(item, ['starRating', 'data', 'params']),
                        'starRating': utils.parseValue(item, ['starRating', 'rating']),
                        'quality': utils.parseValue(item, ['content', 'metadata', 'format']),
                        'languages': utils.parseValue(item, ['content', 'metadata', 'languages']),
                        'path': utils.parseValue(item, ['pointer', 'path']),
                        'params': utils.parseValue(item, ['pointer', 'params']),
                        'infoPath': utils.parseValue(item, ['legend', 'button', 'pointer', 'path']),
                        'infoParams': utils.parseValue(item, ['legend', 'button', 'pointer', 'params']),
                        'progress': utils.parseProgress(startPosition, historyDuration),
                        'historyPath': utils.parseValue(item, ['history', 'data', 'path']),
                        'historyParams': historyParams,
                        'startPosition': startPosition,
                        'historyDuration': historyDuration,
                    }));


                except Exception as inst:
                    logger.error(inst);


            episodes = items;

            menubutton = utils.parseValue(pointer, ['pageButton', 'title'], encoded=False);
            menubutton = utils.parseBtnText(menubutton, '305%02d' % idx);
            menubutton = utils.text2HomeMenu(idx, menubutton);


            navigation = dict({
                'width': menubutton,
                'title': utils.parseValue(pointer, ['pageButton', 'title']),
                'target': utils.parseValue(pointer, ['pageButton', 'pointer', 'target']),
                'path': utils.parseValue(pointer, ['pageButton', 'pointer', 'path']),
                'params': utils.parseValue(pointer, ['pageButton', 'pointer', 'params']),
            });

            success = ['episodes', episodes, navigation];


    except Exception as inst:

        success = [None, None, None];

        utils.sendNotification(30301, 3000);

        logger.error(inst);


    return success;


def show(pointer, idx, myqueue):

    success = [None, None, None];

    try:

        shows = utils.parseValue(pointer, ['longList', 'items', 'item'], False);

        if shows:

            items = [];

            for item in shows:

                try:

                    params = utils.parseValue(item, ['pointer', 'params']);
                    toggleParams = utils.parseValue(item, ['legend', 'button', 'pointer', 'toggle', 'data', 'params']);
                    myQueuePath = utils.parseValue(myqueue, [toggleParams, 'myQueuePath']);

                    thumbnail = utils.parseValue(item, ['thumbnail', 'alternate'], True, ['parseAlternateImg', '@platforms', 'firetv']);
                    thumbnail = thumbnail if thumbnail is not None else utils.parseValue(item, ['thumbnail', '#text']);
                    thumbnail = formatImgUrl(thumbnail, theme='show');

                    items.append(dict({
                        'title': utils.parseValue(item, ['title']),
                        'thumbnail': thumbnail,
                        'path': utils.parseValue(item, ['pointer', 'path']),
                        'params': params,
                        'titleimg': 's_%s.png' % params,
                        'togglePath': utils.parseValue(item, ['legend', 'button', 'pointer', 'toggle', 'data', 'path']),
                        'toggleParams': toggleParams,
                        'myQueuePath': myQueuePath,
                        'myQueueParams': utils.parseValue(myqueue, [toggleParams, 'myQueueParams']),
                        'inQueue': (0 if myQueuePath is not None else 1)
                    }));
                    

                except Exception as inst:
                    logger.error(inst);


            shows = items;

            menubutton = utils.parseValue(pointer, ['pageButton', 'title'], encoded=False);
            menubutton = utils.parseBtnText(menubutton, '305%02d' % idx);
            menubutton = utils.text2HomeMenu(idx, menubutton);

            navigation = dict({
                'width': menubutton,
                'title': utils.parseValue(pointer, ['pageButton', 'title']),
                'target': utils.parseValue(pointer, ['pageButton', 'pointer', 'target']),
                'path': utils.parseValue(pointer, ['pageButton', 'pointer', 'path']),
                'params': utils.parseValue(pointer, ['pageButton', 'pointer', 'params']),
            });

            success = ['shows', shows, navigation];


    except Exception as inst:

        success = [None, None, None];

        utils.sendNotification(30301, 3000);

        logger.error(inst);


    return success;


def detail(path, params, desc, viewtype, idx, loadDisplay=False):

    success = False;

    if path and params:

        params = quoteplus(params);

        try:

            url = getUrl(None, path);
           
            headers = getHeaders();

            for key in utils.setting('fn.Headers').split(','):
                headers.update({key: utils.setting('fn.%s' % key)});

            token = getToken();

            if(headers and token and url):

                headers.update({'Authorization': token});

                url = ('%s?%s&territory=%s' % (url, params, headers.get('territory', 'US')));

                result = client.request(url, headers=headers);

            else:
                result = None;

            if result:

                try:

                    result = parse(result);

                    if 'error' in result['list2d']:

                        error = result['list2d'].get('error', 30302);
                        
                        if loadDisplay:
                            utils.sendNotification(error, 7000);

                    else:
                        success = globals()[desc](result, viewtype, idx);

                except Exception as inst:
            
                    if loadDisplay:
                        utils.sendNotification(30302, 5000);

                    logger.error(inst);

            else:
                
                if loadDisplay:
                    utils.sendNotification(30302, 5000);


        except Exception as inst:

            if loadDisplay:
                utils.sendNotification(30302, 5000);

            logger.error(inst);


    return success;


def player(path, params, desc, viewtype, idx, loadDisplay=False):

    success = False;

    if path and params:

        params = re.sub(r'\{.*\}', 'OFF', params);
        params = quoteplus(params);

        try:

            url = getUrl(None, path);
           
            headers = getHeaders();

            for key in utils.setting('fn.Headers').split(','):
                headers.update({key: utils.setting('fn.%s' % key)});

            token = getToken();

            if(headers and token and url):

                headers.update({'Authorization': token});

                url = ('%s?%s&territory=%s' % (url, params, headers.get('territory', 'US')));

                result = client.request(url, headers=headers);

            else:
                result = None;

            if result:

                try:

                    result = parse(result);

                    if 'error' in result['player']:

                        error = result['player'].get('error', 30302);
                        
                        if loadDisplay:
                            utils.sendNotification(error, 7000);

                    else:
                        success = globals()[desc](result, viewtype, idx);

                except Exception as inst:
            
                    if loadDisplay:
                        utils.sendNotification(30302, 5000);

                    logger.error(inst);

            else:
                
                if loadDisplay:
                    utils.sendNotification(30302, 5000);


        except Exception as inst:

            if loadDisplay:
                utils.sendNotification(30302, 5000);

            logger.error(inst);


    return success;


def getSeries(path, params, loadDisplay=True):

    success = False;

    if path and params:

        params = quoteplus(params);

        try:

            url = getUrl(None, path);
           
            headers = getHeaders();

            for key in utils.setting('fn.Headers').split(','):
                headers.update({key: utils.setting('fn.%s' % key)});

            token = getToken();

            if(headers and token and url):

                headers.update({'Authorization': token});

                url = ('%s?%s&territory=%s' % (url, params, headers.get('territory', 'US')));

                result = client.request(url, headers=headers);

            else:
                result = None;

            if result:

                try:

                    result = parse(result);

                    if 'error' in result['list2d']:

                        error = result['list2d'].get('error', 30302);
                        
                        if loadDisplay:
                            utils.sendNotification(error, 7000);

                    else:
                        success = result; #globals()[desc](result, viewtype, idx);

                except Exception as inst:
            
                    if loadDisplay:
                        utils.sendNotification(30302, 5000);

                    logger.error(inst);

            else:
                
                if loadDisplay:
                    utils.sendNotification(30302, 5000);


        except Exception as inst:

            if loadDisplay:
                utils.sendNotification(30302, 5000);

            logger.error(inst);


    return success;


def getLongList(path, params, loadDisplay=True):

    success = False;

    if path and params:

        params = quoteplus(params);

        try:

            url = getUrl(None, path);
           
            headers = getHeaders();

            for key in utils.setting('fn.Headers').split(','):
                headers.update({key: utils.setting('fn.%s' % key)});

            token = getToken();

            if(headers and token and url):

                headers.update({'Authorization': token});

                url = ('%s?%s&territory=%s' % (url, params, headers.get('territory', 'US')));

                result = client.request(url, headers=headers);

            else:
                result = None;

            if result:

                try:

                    result = parse(result);

                    if 'error' in result['longList']:

                        error = result['longList'].get('error', 30302);
                        
                        if loadDisplay:
                            utils.sendNotification(error, 7000);

                    else:
                        success = result['longList']; #globals()[desc](result, viewtype, idx);

                except Exception as inst:
            
                    if loadDisplay:
                        utils.sendNotification(30302, 5000);

                    logger.error(inst);

            else:
                
                if loadDisplay:
                    utils.sendNotification(30302, 5000);


        except Exception as inst:

            if loadDisplay:
                utils.sendNotification(30302, 5000);

            logger.error(inst);


    return success;

    
def getSeriesDetails(path, params, loadDisplay=True):

    success = False;

    if path and params:

        params = quoteplus(params);

        try:

            url = getUrl(None, path);
           
            headers = getHeaders();

            for key in utils.setting('fn.Headers').split(','):
                headers.update({key: utils.setting('fn.%s' % key)});

            token = getToken();

            if(headers and token and url):

                headers.update({'Authorization': token});

                url = ('%s?%s&territory=%s' % (url, params, headers.get('territory', 'US')));

                result = client.request(url, headers=headers);

            else:
                result = None;

            if result:

                try:

                    #lets keep this solution arround for pure JSON no ordered dict
                    #logger.debug(json.dumps(parse(result)));
                    #logger.debug(json.dumps(parse(result, process_namespaces=True)));

                    result = parse(result);

                    if 'error' in result['items']:

                        error = result['items'].get('error', 30302);
                        
                        if loadDisplay:
                            utils.sendNotification(error, 7000);

                    else:
                        success = result; #globals()[desc](result, viewtype, idx);

                except Exception as inst:
            
                    if loadDisplay:
                        utils.sendNotification(30302, 5000);

                    logger.error(inst);

            else:
                
                if loadDisplay:
                    utils.sendNotification(30302, 5000);


        except Exception as inst:

            if loadDisplay:
                utils.sendNotification(30302, 5000);

            logger.error(inst);


    return success;


def showDesc(result, viewtype, idx, loadDisplay=False):

    success = False;

    if result:

        try:

            if 'hero' in result['list2d']:

                desc = dict();

                analytics = utils.parseValue(result, ['list2d', 'analytics', 'label']);
                hero = utils.parseValue(result, ['list2d', 'hero', 'item'], False);
                pointers = utils.parseValue(result, ['list2d', 'pointer'], False);
                seasons = 0;
                episodes = 0;

                if pointers:

                    if not isinstance(pointers, list):
                        pointers = list([pointers]);

                    for pointer in pointers:

                        if 'title' not in pointer:
                            
                            if 'longList' in pointer:

                                filters = utils.parseValue(pointer, ['longList', 'palette', 'filter'], False);
                                items = utils.parseValue(pointer, ['longList', 'items'], False);

                                if filters:

                                    if not isinstance(filters, list):
                                        filters = list([filters]);

                                    for filt in filters:

                                        if utils.parseValue(filt, ['name']) == 'SEASONS':

                                            filt = utils.parseValue(filt, ['choices', 'button'], False);

                                            if not isinstance(filt, list):
                                                filt = list([filt]);

                                            try:
                                                seasons = len(filt);

                                            except:
                                                seasons = 0;

                                            break;

                                if items:

                                    if not isinstance(items, list):
                                        items = list([items]);

                                    for item in items:

                                        if 'item' in item:

                                            eps = utils.parseValue(item, ['item'], False);

                                            if not isinstance(eps, list):
                                                eps = list([eps]);

                                            try:
                                                episodes = len(eps);

                                            except:
                                                episodes = 0;

                                            break;

                            break;


                desc.update({
                    'genres': analytics.split(':')[0] if analytics is not None else 'NA',
                    'sinfo': utils.parseValue(hero, ['subtitle']),
                    'starPath': utils.parseValue(hero, ['starRating', 'data', 'path']),
                    'starParams': utils.parseValue(hero, ['starRating', 'data', 'params']),
                    'starRating': utils.parseValue(hero, ['starRating', 'rating']),
                    'ratings': utils.parseValue(hero, ['ratings', 'tv'], True, ['parseRegion', '@region', getTerritory()]),
                    'description': utils.parseValue(hero, ['content', 'description']),
                    'quality': utils.parseValue(hero, ['content', 'metadata', 'format']),
                    'releaseYear': utils.parseValue(hero, ['content', 'metadata', 'releaseYear']),
                    'seasons': seasons,
                    'episodes': episodes
                });


                success = desc;
                

        except Exception as inst:

            if loadDisplay:
                utils.sendNotification(30301, 3000);

            logger.error(inst);


    return success;


def episodeDesc(result, viewtype, idx, loadDisplay=False):

    success = False;

    if result:

        try:

            if 'item' in result['player']:

                desc = dict();

                item = utils.parseValue(result, ['player', 'item'], False);
                video = utils.parseValue(item, ['video'], False);
                metadata = utils.parseValue(video, ['content', 'metadata'], False);
                related = utils.parseValue(item, ['related'], False);
                buttons = utils.parseValue(result, ['player', 'customPanel', 'items', 'button'], False);

                description = None;

                #GET /xml/longlist/hero-episodes/?season=Season+1&show=124389&inPlayer=true&version=Simulcast&territory=US HTTP/1.1

                if buttons:

                    if not isinstance(buttons, list):
                        buttons = list([buttons]);

                    for button in buttons:

                        pointer = utils.parseValue(button, ['pointer'], False);

                        if 'share' in pointer:

                            description = utils.parseValue(pointer, ['share', 'description']);

                            break;


                desc.update({
                    'title': utils.parseValue(video, ['title']),
                    'subtitle': utils.parseValue(video, ['subtitle']),
                    'season': utils.parseValue(metadata, ['season']),
                    'episode': utils.parseValue(metadata, ['episode']),
                    'duration': utils.parseValue(metadata, ['duration']),
                    'showId': utils.parseValue(metadata, ['showId']),
                    'seasonId': utils.parseValue(metadata, ['seasonId']),
                    'episodeId': utils.parseValue(metadata, ['episodeId']),
                    'audio': utils.parseValue(metadata, ['audio']),
                    'ratings': utils.parseValue(item, ['ratings', 'tv'], True, ['parseRegion', '@region', getTerritory()]),
                    'path': utils.parseValue(related, ['path']),
                    'params': utils.parseValue(related, ['params']),
                    'videourl': utils.parseValue(item, ['hls', 'url']),
                    'description': description
                });


                success = desc;
                

        except Exception as inst:
    
            if loadDisplay:
                utils.sendNotification(30301, 3000);

            logger.error(inst);


    return success;


def getGenres(path, params, loadDisplay=True):

    success = False;

    if path and params:

        #params = quoteplus(params);

        try:

            url = getUrl(None, path);
           
            headers = getHeaders();

            for key in utils.setting('fn.Headers').split(','):
                headers.update({key: utils.setting('fn.%s' % key)});

            token = getToken();

            if(headers and token and url):

                headers.update({'Authorization': token});

                url = ('%s?%s' % (url, params));

                result = client.request(url, headers=headers);

            else:
                result = None;

            if result:

                try:

                    result = parse(result);

                    if 'error' in result['longList']:

                        error = result['longList'].get('error', 30303);
                        
                        if loadDisplay:
                            utils.sendNotification(error, 4000);

                    else:
                        success = result; #globals()[desc](result, viewtype, idx);

                except Exception as inst:
            
                    if loadDisplay:
                        utils.sendNotification(30303, 3000);

                    logger.error(inst);

            else:
                
                if loadDisplay:
                    utils.sendNotification(30303, 3000);


        except Exception as inst:

            if loadDisplay:
                utils.sendNotification(30303, 3000);

            logger.error(inst);


    return success;


def getPage(path, params, loadDisplay=True):

    success = False;

    if path and params:

        params = quoteplus(params);

        try:

            url = getUrl(None, path);

            headers = getHeaders();

            for key in utils.setting('fn.Headers').split(','):
                headers.update({key: utils.setting('fn.%s' % key)});

            token = getToken();

            if(headers and token and url):

                headers.update({'Authorization': token});

                #url = ('%s?%s' % (url, params));

                url = ('%s?%s&territory=%s' % (url, params, headers.get('territory', 'US')));

                result = client.request(url, headers=headers);

            else:
                result = None;

            if result:

                try:

                    result = parse(result);

                    # need to do None checks before checking for error on all of these.

                    if result['items'] is not None:

                        if 'error' in result['items']:

                            error = result['items'].get('error', 30303);
                            
                            if loadDisplay:
                                utils.sendNotification(error, 4000);

                        else:
                            success = result; #globals()[desc](result, viewtype, idx);

                    else:

                        success = None;

                        if loadDisplay:
                            utils.sendNotification(30304, 3000);

                except Exception as inst:
            
                    if loadDisplay:
                        utils.sendNotification(30303, 3000);

                    logger.error(inst);

            else:
                
                if loadDisplay:
                    utils.sendNotification(30303, 3000);


        except Exception as inst:

            if loadDisplay:
                utils.sendNotification(30303, 3000);

            logger.error(inst);


    return success;


def getWatchListSet(path, params, loadDisplay=True):

    success = False;

    if path and params:

        params = quoteplus(params);

        try:

            url = getUrl(None, path);
           
            headers = getHeaders();

            for key in utils.setting('fn.Headers').split(','):
                headers.update({key: utils.setting('fn.%s' % key)});

            token = getToken();

            if(headers and token and url):

                headers.update({'Authorization': token});

                url = ('%s?%s&territory=%s' % (url, params, headers.get('territory', 'US')));

                result = client.request(url, headers=headers);

            else:
                result = None;

            if result:

                try:

                    result = parse(result);

                    # need to do None checks before checking for error on all of these.

                    if result['longList'] is not None:

                        if 'error' in result['longList']:

                            error = result['longList'].get('error', 30303);
                            
                            if loadDisplay:
                                utils.sendNotification(error, 4000);

                        else:
                            success = result; #globals()[desc](result, viewtype, idx);

                    else:

                        success = None;

                        if loadDisplay:
                            utils.sendNotification(30304, 4000);

                except Exception as inst:
            
                    if loadDisplay:
                        utils.sendNotification(30303, 3000);

                    logger.error(inst);

            else:
                
                if loadDisplay:
                    utils.sendNotification(30303, 3000);


        except Exception as inst:

            if loadDisplay:
                utils.sendNotification(30303, 3000);

            logger.error(inst);


    return success;


def getEpisodeDetailExtras(path, params, loadDisplay=False):

    success = False;

    if path and params:

        params = quoteplus(params);

        try:

            url = getUrl(None, path);
           
            headers = getHeaders();

            for key in utils.setting('fn.Headers').split(','):
                headers.update({key: utils.setting('fn.%s' % key)});

            token = getToken();

            if(headers and token and url):

                headers.update({'Authorization': token});

                url = ('%s?%s&territory=%s' % (url, params, headers.get('territory', 'US')));

                result = client.request(url, headers=headers);

            else:
                result = None;

            if result:

                try:

                    result = parse(result);

                    if 'error' in result['longList']:

                        error = result['longList'].get('error', 30301);
                        
                        utils.sendNotification(error, 5000);

                    else:

                        extras = dict();
                        items = utils.parseValue(result, ['longList', 'items', 'item'], False);

                        if items:

                            if not isinstance(items, list):
                                items = list([items]);

                            for item in items:

                                if 'starRating' in item:

                                    extras.update({
                                        'starRating': utils.parseValue(item, ['starRating', 'rating']),
                                        'quality': utils.parseValue(item, ['content', 'metadata', 'format']),
                                        'contentType': utils.parseValue(item, ['content', 'metadata', 'contentType'])
                                    });

                                    break;


                        if extras and len(extras) > 0:
                            success = extras;


                except Exception as inst:
            
                    if loadDisplay:
                        utils.sendNotification(30301, 3000);

                    logger.error(inst);

            else:

                if loadDisplay:
                    utils.sendNotification(30301, 3000);


        except Exception as inst:

            if loadDisplay:
                utils.sendNotification(30301, 3000);

            logger.error(inst);


    return success;


def updateQueue(path, params, qstate):

    success = False;

    if path and params:

        params = quoteplus(params);

        try:

            postpath = 'remove' if qstate < 1 else 'add';
            path = '%s%s/' % (path, postpath);

            url = getUrl(None, path);

            headers = getHeaders();

            for key in utils.setting('fn.Headers').split(','):
                headers.update({key: utils.setting('fn.%s' % key)});

            token = getToken();

            if(headers and token and url):

                headers.update({'Authorization': token});

                url = ('%s?%s&territory=%s' % (url, params, headers.get('territory', 'US')));

                result = client.request(url, headers=headers, output='response');

            else:
                result = None;

            if result:

                try:

                    response = result[0];
                    result = result[1];

                    if response == '200':

                        if result is None or len(result) < 1:
                            success = True;

                        else:

                            try:

                                # Old API
                                resultxml = parse(result);

                                if 'error' in resultxml['authentication']:

                                    success = False;
                                    
                                    msg = utils.lang(30305).encode('utf-8') % postpath;
                                    error = resultxml['authentication'].get('error', msg);
                                    
                                    utils.sendNotification(error, 3000);

                                else:
                                    success = False;
                                    utils.sendNotification(30303, 3000);
                                
                            except:

                                #Occasional GZIP Errors

                                try:

                                    import gzip;

                                    from StringIO import StringIO;

                                    buf = StringIO(response);
                                    f = gzip.GzipFile(fileobj=buf);

                                    result = str(f.read());

                                    if result is not None:

                                        if len(result) < 1:
                                            success = True;

                                        else:
                                            utils.sendNotification(result, 3000);

                                    else:
                                        success = True;
                                        msg = utils.lang(30305).encode('utf-8') % postpath;
                                        #utils.sendNotification(msg, 7000);

                                except:
                                    success = True;
                                    msg = utils.lang(30305).encode('utf-8') % postpath;
                                    #utils.sendNotification(msg, 7000);


                    else:

                        success = False;
                        msg = utils.lang(30305).encode('utf-8') % postpath;

                        utils.sendNotification(msg, 3000);

                except Exception as inst:
                    utils.sendNotification(30303, 3000);

                    logger.error(inst);

            else:
                utils.sendNotification(30303, 3000);


        except Exception as inst:
            utils.sendNotification(30303, 3000);

            logger.error(inst);


    return success;


def updateProgess(litem, currentTime, totalTime):

    success = False;

    try:

        url = litem.getProperty('pAdd');

        payload = dict({
            litem.getProperty('pStart'): int(currentTime),
            litem.getProperty('pDuration'): int(totalTime),
        });

        payload = encodeData(payload);

        historyParams = litem.getProperty('historyParams');

        url = '%s?%s&%s' % (url, payload, historyParams);

        headers = getHeaders();

        for key in utils.setting('fn.Headers').split(','):
            headers.update({key: utils.setting('fn.%s' % key)});

        token = getToken();

        if(headers and token and url):

            headers.update({'Authorization': token});

            url = ('%s&territory=%s' % (url, headers.get('territory', 'US')));

            result = client.request(url, headers=headers, output='response');

        else:
            result = None;

        if result:

            try:

                response = result[0];
                result = result[1];

                if response == '200':

                    if len(result) < 1:
                        success = True;

                    else:

                        result = parse(result);

                        if 'error' in result['authentication']:

                            success = False;
                            error = result['authentication'].get('error', 30307);
                            
                            logger.error(error);

                        else:
                            success = False;
                            logger.error(30303);

                else:
                    success = False;
                    logger.error(30303);

            except Exception as inst:
                logger.error(inst);

                pass;

        else:
            logger.error(30303);


    except Exception as inst:
        logger.error(inst);


    return success;


def updateRating(sRating, sLookup, sPath, sParams):

    success = False;

    try:

        url = utils.parseValue(sLookup, ['add', 'pointer', 'path']);
        pName = utils.parseValue(sLookup, ['name']);
        sPath = utils.parseValue(sLookup, [pName, 'param']);

        payload = dict({sPath: sRating});
        payload = encodeData(payload);

        url = '%s?%s&%s' % (url, payload, sParams);

        headers = getHeaders();

        for key in utils.setting('fn.Headers').split(','):
            headers.update({key: utils.setting('fn.%s' % key)});

        token = getToken();

        if(headers and token and url):

            headers.update({'Authorization': token});

            url = ('%s&territory=%s' % (url, headers.get('territory', 'US')));

            result = client.request(url, headers=headers, output='response');

        else:
            result = None;

        if result:

            try:

                response = result[0];
                result = result[1];

                if response == '200':

                    if len(result) < 1:
                        success = True;

                    else:
                             
                        try:

                            #Old API

                            resultxml = parse(result);

                            if 'error' in resultxml['authentication']:

                                success = False;
                                error = resultxml['authentication'].get('error', 30306);

                                utils.sendNotification(error, 3000);
                                
                                logger.error(error);

                            else:
                                success = False;
                                logger.error(30303);

                        except:

                            try:

                                import gzip;

                                from StringIO import StringIO;

                                buf = StringIO(response);
                                f = gzip.GzipFile(fileobj=buf);

                                result = str(f.read());

                                logger.debug(result);

                                if result is not None:

                                    if len(result) < 1:
                                        success = True;

                                    else:
                                        utils.sendNotification(result, 3000);

                                else:
                                    success = True;

                            except:
                                success = True;

                else:
                    success = False;
                    logger.error(30303);

            except Exception as inst:
                logger.error(inst);

                pass;

        else:
            logger.error(30303);


    except Exception as inst:
        logger.error(inst);


    return success;


def formatImgUrl(img, theme=None):

    imgQuality = utils.setting('fn.image_quality');

    if imgQuality is None:
        imgQuality = 60;

    elif int(imgQuality) < 10:
        imgQuality = 10;


    if theme == 'episode':
        thumbnail = re.sub(r'h_\d+,w_\d+,q_\d+', 'h_378,w_666,q_%s' % imgQuality, img);

    elif theme == 'show':
        thumbnail = re.sub(r'h_\d+,w_\d+,q_\d+', 'h_570,w_666,q_%s' % imgQuality, img);

    elif theme == 'preview':
        thumbnail = re.sub(r'h_\d+,w_\d+,q_\d+', 'h_504,w_888,q_%s' % imgQuality, img);

    elif theme == 'genre':
        thumbnail = re.sub(r'h_\d+,w_\d+,q_\d+', 'h_570,w_666,q_%s' % imgQuality, img);

    else:
        thumbnail = re.sub(r'upload/.*/oth', 'upload/q_%s/oth' % imgQuality, img);


    return thumbnail;


def formatShowImgUrl(img, theme=None):

    thumbnail = None;

    try:
        thumbnail = re.sub(r'upload/.*/oth', 'upload/oth', img);

    except:
        thumbnail = None;


    return thumbnail;


def quoteplus(params):

    import urlparse;

    try:

        return urllib.urlencode(urlparse.parse_qs(params), doseq=True);

    except:
        return params;


def execute(test):
    
    logger.debug(test);

    pass;