#    urlresolver XBMC Addon
#    Copyright (C) 2011 t0mm0
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

import urlresolver
from urlresolver import common
from plugnplay.interfaces import UrlResolver
from plugnplay.interfaces import SiteAuth

class HostedMediaFile:
    '''
    This class represents a piece of media (file or stream) that is hosted 
    somewhere on the internet. It may be instantiated with EITHER the url to the
    web page associated with the media file, OR the host name and a unique 
    ``media_id`` used by the host to point to the media.
    
    For example::
    
        HostedMediaFile(url='http://youtube.com/watch?v=ABC123XYZ')
        
    represents the same piece of media as::
    
        HostedMediaFile(host='youtube.com', media_id='ABC123XYZ')
        
    ``title`` is a free text field useful for display purposes such as in
    :func:`choose_source`.
    
    .. note::
    
        If there is no resolver plugin to handle the arguments passed, 
        the resulting object will evaluate to ``False``. Otherwise it will 
        evaluate to ``True``. This is a handy way of checking whether
        a resolver exists::
            
            hmf = HostedMediaFile('http://youtube.com/watch?v=ABC123XYZ')
            if hmf:
                print 'yay! we can resolve this one'
            else:
                print 'sorry :( no resolvers available to handle this one.')
    
    .. warning::
        
        If you pass ``url`` you must not pass ``host`` or ``media_id``. You 
        must pass either ``url`` or ``host`` AND ``media_id``.
    '''
    def __init__(self, url='', host='', media_id='', title=''):
        '''
        Args:
            url (str): a URL to a web page that represents a piece of media.
            
            host (str): the host of the media to be represented.
            
            media_id (str): the unique ID given to the media by the host.
        '''
        if not url and not (host and media_id) or (url and (host or media_id)):
            raise ValueError('Set either url, or host AND media_id. ' +
                             'No other combinations are valid.')
        self._url = url
        self._host = host
        self._media_id = media_id
        
        self._resolvers = self._find_resolvers()
        if url and self._resolvers and self._resolvers[0].get_host_and_id(url):
            self._host, self._media_id = self._resolvers[0].get_host_and_id(url)
        elif self._resolvers:
            if self._resolvers[0].isUniversal():
                if len(self._resolvers) > 1:
                    self._url = self._resolvers[1].get_url(host, media_id)
                    result = self._resolvers[0].get_host_and_id(self._url)
                    if result:
                        self._host, self._media_id = result
                    else:
                        self._resolvers = []
                else:
                    self._resolvers = []
            else:    
                self._url = self._resolvers[0].get_url(host, media_id)
        
        if title:
            self.title = title
        else:
            self.title = self._host
            

    def get_url(self):
        '''
        Returns the URL of this :class:`HostedMediaFile`.
        '''
        return self._url    
    
    def get_host(self):
        '''
        Returns the host of this :class:`HostedMediaFile`.
        '''
        return self._host
        
    def get_media_id(self):
        '''
        Returns the media_id of this :class:`HostedMediaFile`.
        '''
        return self._media_id
          
    def resolve(self):
        '''
        Resolves this :class:`HostedMediaFile` to a media URL. 
        
        Example::
            
            stream_url = HostedMediaFile(host='youtube.com', media_id='ABC123XYZ').resolve()
        
        .. note::
        
            This method currently uses just the highest priority resolver to 
            attempt to resolve to a media URL and if that fails it will return 
            False. In future perhaps we should be more clever and check to make 
            sure that there are no more resolvers capable of attempting to 
            resolve the URL first. 
        
        Returns:
            A direct URL to the media file that is playable by XBMC, or False
            if this was not possible. 
        '''
        if self._resolvers:
            resolver = self._resolvers[0]
            common.addon.log_debug('resolving using %s plugin' % resolver.name)
            if SiteAuth in resolver.implements:
                common.addon.log_debug('logging in')
                resolver.login()
            return resolver.get_media_url(self._host, self._media_id)
        else:
            return False
        
    def valid_url(self):
        '''
        Returns True if the ``HostedMediaFile`` can be resolved.
        
        .. note::
            
            The following are exactly equivalent::
                
                if HostedMediaFile('http://youtube.com/watch?v=ABC123XYZ').valid_url():
                    print 'resolvable!'

                if HostedMediaFile('http://youtube.com/watch?v=ABC123XYZ'):
                    print 'resolvable!'
            
        '''
        if self._resolvers:
            return True
        return False
        
    def _find_resolvers(self):
        imps = []
        for imp in UrlResolver.implementors():
            if imp.valid_url(self.get_url(), self.get_host()):
                imps.append(imp)
        return imps

        
    def __nonzero__(self):
        return self.valid_url() 
        
    def __str__(self):
        return '{\'url\': \'%s\', \'host\': \'%s\', \'media_id\': \'%s\'}' % (
                    self._url, self._host, self._media_id)

    def __repr__(self):
        return self.__str__()
