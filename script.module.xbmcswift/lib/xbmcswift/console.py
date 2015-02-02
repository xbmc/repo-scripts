from optparse import OptionParser
from shutil import copytree
from os import getcwd
import readline
import string
import os

SKEL = os.path.join(os.path.dirname(__file__), 'skel')

def parse_cli():
    '''Currently only one positional arg, create.'''
    parser = OptionParser()
    return parser.parse_args()

def validator_nonblank(value):
    return value

def validator_pluginid(value):
    valid = string.ascii_letters + string.digits + '.'
    return all(c in valid for c in value)

def validator_isfolder(value):
    return os.path.isdir(value)

def get_valid_value(prompt, validator, default=None):

    ans = _get_value(prompt, default)
    while not validator(ans):
        print '! Invalid value.'
        ans = _get_value(prompt, default)

    return ans
    
def _get_value(prompt, default=None):
    _prompt = '%s : ' % prompt
    if default:
        _prompt = '%s [%s]: ' % (prompt, default)

    ans = raw_input(_prompt)

    # If user hit Enter and there is a default value
    if not ans and default:
        ans = default
    
    return ans

def update_file(fn, items):
    '''Replaces instances of {key} in a file with the provided value from
    items.'''
    with open(fn, 'r') as f:
        text = f.read()

    for k, v in items.items():
        text = text.replace('{%s}' % k, v)
    output = text
    #try:
        #output = text.format(**items)
    #except AttributeError:
        ## Fallback to re if <= python 2.4
        #for k, v in items.items():
            #text = text.replace('{%s}' % k, v)
        #output = text

    # Now write out
    with open(fn, 'w') as f:
        f.write(output)

def create_new_project():
    # tab completion yo!
    readline.parse_and_bind('tab: complete')

    print \
'''
    XBMC Swift - A micro-framework for creating XBMC plugins.
    xbmc@jonathanbeluch.com
    --
'''
    print 'I\'m going to ask you a few questions to get this project' \
        ' started.'

    opts = {}

    # Plugin Name
    opts['plugin_name'] = get_valid_value(
        'What is your plugin name?',
        validator_nonblank
    )

    # Plugin ID
    opts['plugin_id'] = get_valid_value(
        'Enter your plugin id.',
        validator_pluginid,
        'plugin.video.%s' % (opts['plugin_name'].lower().replace(' ', ''))
    )

    # Parent Directory
    opts['parent_dir'] = get_valid_value(
        'Enter parent folder (where to create project)',
        validator_isfolder,
        getcwd()
    )
    opts['plugin_dir'] = os.path.join(opts['parent_dir'], opts['plugin_id'])
    assert not os.path.isdir(opts['plugin_dir']), \
        'A folder named %s already exists in %s.' % (opts['plugin_id'], opts['parent_dir'])

    # Provider
    opts['provider_name'] = get_valid_value(
        'Enter provider name',
        validator_nonblank,
    )

    # Create the project folder by copying over skel
    copytree(SKEL, opts['plugin_dir'])

    # Walk through all the new files and fill in with out options
    for root, dirs, files in os.walk(opts['plugin_dir']):
        for fn in files:
            update_file(os.path.join(root, fn), opts)

    print 'Projects successfully created in %s.' % opts['plugin_dir']
    print 'Done.'
        
    


    

def main():
    modes = {
        'create': create_new_project,
    }

    opts, args = parse_cli() 
    assert args, 'Requires at least one positional argument.'

    mode = args[0]
    assert mode in modes.keys(), (
        'Requires a valid mode as the first positional argument.'
        ' Valid modes are %s.' % \
            ', '.join('"%s"' % m for m in modes.keys())
    )

    # Run the requested mode
    modes[mode]()


