#v.0.2.1

import socket
import requests as _requests
    

class URL():

    def __init__( self, returntype='text', headers='', timeout=10 ):
        self.timeout = timeout
        self.headers = headers
        self.returntype = returntype

    
    def Get( self, url, **kwargs ):
        params, data = self._unpack_args( kwargs )
        return self._urlcall( url, params, '', 'get' )
    
    
    def Post( self, url, **kwargs ):
        params, data = self._unpack_args( kwargs )
        return self._urlcall( url, params, data, 'post' ) 
    
    
    def Delete( self, url, **kwargs ):
        params, data = self._unpack_args( kwargs )
        return self._urlcall( url, params, data, 'delete' )
    
    
    def _urlcall( self, url, params, data, urltype ):
        loglines = []        
        urldata = ''
        try:
            if urltype == "get":
                urldata = _requests.get( url, params=params, timeout=self.timeout, verify=False )
            elif urltype == "post":
                urldata = _requests.post( url, params=params, data=data, headers=self.headers, timeout=self.timeout, verify=False )
            elif urltype == "delete":
                urldata = _requests.delete( url, params=params, data=data, headers=self.headers, timeout=self.timeout, verify=False )
            loglines.append( "the url is: " + urldata.url )
            loglines.append( 'the params are: ')
            loglines.append( params )
            loglines.append( 'the data are: ')
            loglines.append( data )
        except _requests.exceptions.ConnectionError, e:
            loglines.append( 'site unreachable at ' + url )
            loglines.append( e )
        except _requests.exceptions.Timeout, e:
            loglines.append( 'timeout error while downloading from ' + url )
            loglines.append( e )
        except socket.timeout, e:
            loglines.append( 'timeout error while downloading from ' + url )
            loglines.append( e )
        except _requests.exceptions.HTTPError, e:
            loglines.append( 'HTTP Error while downloading from ' + url )
            loglines.append( e )
        except _requests.exceptions.RequestException, e:
            loglines.append( 'unknown error while downloading from ' + url )
            loglines.append( e )
        if urldata:
            success = True
            loglines.append( 'returning URL as ' + self.returntype )
            try:
                if self.returntype == 'text':
                    data = urldata.text
                elif self.returntype == 'binary':
                    data = urldata.content
                elif self.returntype == 'json':
                    data = urldata.json()
            except:
                success = False
                data = ''
                loglines.append( 'unable to convert returned object to acceptable type' )
                loglines.append( urldata )
        else:
            success = False
            data = ''
        loglines.append( '-----URL OBJECT RETURNED-----' )
        loglines.append( data )
        return success, loglines, data
    
    
    def _unpack_args( self, kwargs ):
        params = kwargs.get( 'params', {} )
        if self.returntype == 'json':
            data = kwargs.get( 'data', [] )
        else:
            data = kwargs.get( 'data', '' )
    	return params, data