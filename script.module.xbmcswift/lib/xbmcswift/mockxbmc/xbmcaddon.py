import os
from xml.dom.minidom import parse

class Addon(object):
    def __init__(self, id):
        self._id = id

    def getAddonInfo(self, id):
        properties = ['author', 'changelog', 'description', 'disclaimer',
            'fanart', 'icon', 'id', 'name', 'path', 'profile', 'stars', 'summary',
            'type', 'version']
        assert id in properties, '%s is not a valid property.' % id
        return True

    def getLocalizedString(self, id):
        key = str(id)
        assert key in self._strings, 'ID not found in English/strings.xml.'
        return self._strings[key]

    def getSetting(self, id):
        raise NotImplementedError, 'Not ready yet!'

    def setSetting(self, id, value):
        raise NotImplementedError, 'Not ready yet!'

    def openSettings(self):
        pass

    def _setup(self, path):
        '''This is not an official XBMC method, it is here to faciliate
        mocking up the other methods when running outside of XBMC.'''
        def get_strings(fn):
            xml = parse(fn)
            strings = {}
            for tag in xml.getElementsByTagName('string'):
                strings[tag.getAttribute('id')] = tag.firstChild.data
            return strings

        self._path = path
        self._settings_xml_fn = os.path.join(self._path, 'resources', 'settings.xml')
        #self._settings_xml = parse(self._settings_fn)
        self._strings_xml_fn = os.path.join(self._path, 'resources', 'language', 'English', 'strings.xml')
        self._strings = get_strings(self._strings_xml_fn)

        
