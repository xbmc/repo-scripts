# -*- coding: utf-8 -*-
# 2008-07, Erik Svensson <erik.public@gmail.com>

import logging

logger = logging.getLogger('transmissionrpc')
logger.setLevel(logging.ERROR)

def mirror_dict(d):
    d.update(dict((v, k) for k, v in d.iteritems()))
    return d

DEFAULT_PORT = 9091

TR_STATUS_CHECK_WAIT   = (1<<0)
TR_STATUS_CHECK        = (1<<1)
TR_STATUS_DOWNLOAD     = (1<<2)
TR_STATUS_SEED         = (1<<3)
TR_STATUS_STOPPED      = (1<<4)

STATUS = mirror_dict({
    'check pending' : TR_STATUS_CHECK_WAIT,
    'checking'      : TR_STATUS_CHECK,
    'downloading'   : TR_STATUS_DOWNLOAD,
    'seeding'       : TR_STATUS_SEED,
    'stopped'       : TR_STATUS_STOPPED,
})

TR_PRI_LOW    = -1
TR_PRI_NORMAL =  0
TR_PRI_HIGH   =  1

PRIORITY = mirror_dict({
    'low'    : TR_PRI_LOW,
    'normal' : TR_PRI_NORMAL,
    'high'   : TR_PRI_HIGH
})

TR_RATIOLIMIT_GLOBAL    = 0 # follow the global settings
TR_RATIOLIMIT_SINGLE    = 1 # override the global settings, seeding until a certain ratio
TR_RATIOLIMIT_UNLIMITED = 2 # override the global settings, seeding regardless of ratio

RATIO_LIMIT = mirror_dict({
    'global'    : TR_RATIOLIMIT_GLOBAL,
    'single'    : TR_RATIOLIMIT_SINGLE,
    'unlimeted' : TR_RATIOLIMIT_UNLIMITED
})

# A note on argument maps
# These maps are used to verify *-set methods. The information is structured in
# a tree.
# set +- <argument1> - [<type>, <added version>, <removed version>, <previous argument name>, <next argument name>]
#  |  +- <argument2> - [<type>, <added version>, <removed version>, <previous argument name>, <next argument name>]
#  |
# get +- <argument1> - [<type>, <added version>, <removed version>, <previous argument name>, <next argument name>]
#     +- <argument2> - [<type>, <added version>, <removed version>, <previous argument name>, <next argument name>]

# Arguments for torrent methods
TORRENT_ARGS = {
    'get' : {
        'activityDate':             ('number', 1, None, None, None),
        'addedDate':                ('number', 1, None, None, None),
        'announceResponse':         ('string', 1, None, None, None),
        'announceURL':              ('string', 1, None, None, None),
        'bandwidthPriority':        ('number', 5, None, None, None),
        'comment':                  ('string', 1, None, None, None),
        'corruptEver':              ('number', 1, None, None, None),
        'creator':                  ('string', 1, None, None, None),
        'dateCreated':              ('number', 1, None, None, None),
        'desiredAvailable':         ('number', 1, None, None, None),
        'doneDate':                 ('number', 1, None, None, None),
        'downloadDir':              ('string', 4, None, None, None),
        'downloadedEver':           ('number', 1, None, None, None),
        'downloaders':              ('number', 4, None, None, None),
        'downloadLimit':            ('number', 1, None, None, None),
        'downloadLimited':          ('boolean', 5, None, None, None),
        'downloadLimitMode':        ('number', 1, 5, None, None),
        'error':                    ('number', 1, None, None, None),
        'errorString':              ('number', 1, None, None, None),
        'eta':                      ('number', 1, None, None, None),
        'files':                    ('array', 1, None, None, None),
        'fileStats':                ('array', 5, None, None, None),
        'hashString':               ('string', 1, None, None, None),
        'haveUnchecked':            ('number', 1, None, None, None),
        'haveValid':                ('number', 1, None, None, None),
        'honorsSessionLimits':      ('boolean', 5, None, None, None),
        'id':                       ('number', 1, None, None, None),
        'isPrivate':                ('boolean', 1, None, None, None),
        'lastAnnounceTime':         ('number', 1, None, None, None),
        'lastScrapeTime':           ('number', 1, None, None, None),
        'leechers':                 ('number', 1, None, None, None),
        'leftUntilDone':            ('number', 1, None, None, None),
        'manualAnnounceTime':       ('number', 1, None, None, None),
        'maxConnectedPeers':        ('number', 1, None, None, None),
        'name':                     ('string', 1, None, None, None),
        'nextAnnounceTime':         ('number', 1, None, None, None),
        'nextScrapeTime':           ('number', 1, None, None, None),
        'peer-limit':               ('number', 5, None, None, None),
        'peers':                    ('array', 2, None, None, None),
        'peersConnected':           ('number', 1, None, None, None),
        'peersFrom':                ('object', 1, None, None, None),
        'peersGettingFromUs':       ('number', 1, None, None, None),
        'peersKnown':               ('number', 1, None, None, None),
        'peersSendingToUs':         ('number', 1, None, None, None),
        'percentDone':              ('double', 5, None, None, None),
        'pieces':                   ('string', 5, None, None, None),
        'pieceCount':               ('number', 1, None, None, None),
        'pieceSize':                ('number', 1, None, None, None),
        'priorities':               ('array', 1, None, None, None),
        'rateDownload':             ('number', 1, None, None, None),
        'rateUpload':               ('number', 1, None, None, None),
        'recheckProgress':          ('double', 1, None, None, None),
        'scrapeResponse':           ('string', 1, None, None, None),
        'scrapeURL':                ('string', 1, None, None, None),
        'seeders':                  ('number', 1, None, None, None),
        'seedRatioLimit':           ('double', 5, None, None, None),
        'seedRatioMode':            ('number', 5, None, None, None),
        'sizeWhenDone':             ('number', 1, None, None, None),
        'startDate':                ('number', 1, None, None, None),
        'status':                   ('number', 1, None, None, None),
        'swarmSpeed':               ('number', 1, None, None, None),
        'timesCompleted':           ('number', 1, None, None, None),
        'trackers':                 ('array', 1, None, None, None),
        'totalSize':                ('number', 1, None, None, None),
        'torrentFile':              ('string', 5, None, None, None),
        'uploadedEver':             ('number', 1, None, None, None),
        'uploadLimit':              ('number', 1, None, None, None),
        'uploadLimitMode':          ('number', 1, 5, None, None),
        'uploadLimited':            ('boolean', 5, None, None, None),
        'uploadRatio':              ('double', 1, None, None, None),
        'wanted':                   ('array', 1, None, None, None),
        'webseeds':                 ('array', 1, None, None, None),
        'webseedsSendingToUs':      ('number', 1, None, None, None),
    },
    'set': {
        'bandwidthPriority':        ('number', 5, None, None, None),
        'downloadLimit':            ('number', 5, None, 'speed-limit-down', None),
        'downloadLimited':          ('boolean', 5, None, 'speed-limit-down-enabled', None),
        'files-wanted':             ('array', 1, None, None, None),
        'files-unwanted':           ('array', 1, None, None, None),
        'honorsSessionLimits':      ('boolean', 5, None, None, None),
        'ids':                      ('array', 1, None, None, None),
        'peer-limit':               ('number', 1, None, None, None),
        'priority-high':            ('array', 1, None, None, None),
        'priority-low':             ('array', 1, None, None, None),
        'priority-normal':          ('array', 1, None, None, None),
        'seedRatioLimit':           ('double', 5, None, None, None),
        'seedRatioMode':            ('number', 5, None, None, None),
        'speed-limit-down':         ('number', 1, 5, None, 'downloadLimit'),
        'speed-limit-down-enabled': ('boolean', 1, 5, None, 'downloadLimited'),
        'speed-limit-up':           ('number', 1, 5, None, 'uploadLimit'),
        'speed-limit-up-enabled':   ('boolean', 1, 5, None, 'uploadLimited'),
        'uploadLimit':              ('number', 5, None, 'speed-limit-up', None),
        'uploadLimited':            ('boolean', 5, None, 'speed-limit-up-enabled', None),
    },
    'add': {
        'download-dir':             ('string', 1, None, None, None),
        'filename':                 ('string', 1, None, None, None),
        'files-wanted':             ('array', 1, None, None, None),
        'files-unwanted':           ('array', 1, None, None, None),
        'metainfo':                 ('string', 1, None, None, None),
        'paused':                   ('boolean', 1, None, None, None),
        'peer-limit':               ('number', 1, None, None, None),
        'priority-high':            ('array', 1, None, None, None),
        'priority-low':             ('array', 1, None, None, None),
        'priority-normal':          ('array', 1, None, None, None),
    }
}

# Arguments for session methods
SESSION_ARGS = {
    'get': {
        "alt-speed-down":            ('number', 5, None, None, None),
        "alt-speed-enabled":         ('boolean', 5, None, None, None),
        "alt-speed-time-begin":      ('number', 5, None, None, None),
        "alt-speed-time-enabled":    ('boolean', 5, None, None, None),
        "alt-speed-time-end":        ('number', 5, None, None, None),
        "alt-speed-time-day":        ('number', 5, None, None, None),
        "alt-speed-up":              ('number', 5, None, None, None),
        "blocklist-enabled":         ('boolean', 5, None, None, None),
        "blocklist-size":            ('number', 5, None, None, None),
        "encryption":                ('string', 1, None, None, None),
        "download-dir":              ('string', 1, None, None, None),
        "peer-limit":                ('number', 1, 5, None, None),
        "peer-limit-global":         ('number', 5, None, None, None),
        "peer-limit-per-torrent":    ('number', 5, None, None, None),
        "pex-allowed":               ('boolean', 1, 5, None, None),
        "pex-enabled":               ('boolean', 5, None, None, None),
        "port":                      ('number', 1, 5, None, None),
        "peer-port":                 ('number', 5, None, None, None),
        "peer-port-random-on-start": ('boolean', 5, None, None, None),
        "port-forwarding-enabled":   ('boolean', 1, None, None, None),
        "rpc-version":               ('number', 4, None, None, None),
        "rpc-version-minimum":       ('number', 4, None, None, None),
        "seedRatioLimit":            ('double', 5, None, None, None),
        "seedRatioLimited":          ('boolean', 5, None, None, None),
        "speed-limit-down":          ('number', 1, None, None, None),
        "speed-limit-down-enabled":  ('boolean', 1, None, None, None),
        "speed-limit-up":            ('number', 1, None, None, None),
        "speed-limit-up-enabled":    ('boolean', 1, None, None, None),
        "version":                   ('string', 3, None, None, None),
    },
    'set': {
        "alt-speed-down":            ('number', 5, None, None, None),
        "alt-speed-enabled":         ('boolean', 5, None, None, None),
        "alt-speed-time-begin":      ('number', 5, None, None, None),
        "alt-speed-time-enabled":    ('boolean', 5, None, None, None),
        "alt-speed-time-end":        ('number', 5, None, None, None),
        "alt-speed-time-day":        ('number', 5, None, None, None),
        "alt-speed-up":              ('number', 5, None, None, None),
        "blocklist-enabled":         ('boolean', 5, None, None, None),
        "encryption":                ('string', 1, None, None, None),
        "download-dir":              ('string', 1, None, None, None),
        "peer-limit":                ('number', 1, 5, None, 'peer-limit-global'),
        "peer-limit-global":         ('number', 5, None, 'peer-limit', None),
        "peer-limit-per-torrent":    ('number', 5, None, None, None),
        "pex-allowed":               ('boolean', 1, 5, None, 'pex-enabled'),
        "pex-enabled":               ('boolean', 5, None, 'pex-allowed', None),
        "port":                      ('number', 1, 5, None, 'peer-port'),
        "peer-port":                 ('number', 5, None, 'port', None),
        "peer-port-random-on-start": ('boolean', 5, None, None, None),
        "port-forwarding-enabled":   ('boolean', 1, None, None, None),
        "seedRatioLimit":            ('double', 5, None, None, None),
        "seedRatioLimited":          ('boolean', 5, None, None, None),
        "speed-limit-down":          ('number', 1, None, None, None),
        "speed-limit-down-enabled":  ('boolean', 1, None, None, None),
        "speed-limit-up":            ('number', 1, None, None, None),
        "speed-limit-up-enabled":    ('boolean', 1, None, None, None),
    },
}
