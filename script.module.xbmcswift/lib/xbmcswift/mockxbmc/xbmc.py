import tempfile
import os

temp_dir = os.path.join(tempfile.gettempdir(), 'xbmcswift_debug')
def translatePath(path):
    '''Creates folders in the OS's temp directory. Doesn't touch any possible
    XBMC installation on the machine. Attempting to do as little work as
    possible to enable this function to work seamlessly.
    '''
    valid_dirs = ['xbmc', 'home', 'temp', 'masterprofile', 'profile',
        'subtitles', 'userdata', 'database', 'thumbnails', 'recordings',
        'screenshots', 'musicplaylists', 'videoplaylists', 'cdrips', 'skin',
    ]

    assert path.startswith('special://'), 'Not a valid special:// path.'
    parts = path.split('/')[2:]
    assert parts[0] in valid_dirs, '%s is not a valid root dir.' % parts[0]

    root_dir = os.path.join(temp_dir, parts[0])
    if not os.path.isdir(root_dir):
        os.makedirs(root_dir)

    return os.path.join(temp_dir, *parts)
    
