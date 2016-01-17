# -*- coding: utf-8 -*-
from re import DOTALL, search, compile

import xbmc


def dirEntries(dir_name, media_type="files", recursive="FALSE", contains=""):
    '''Returns a list of valid XBMC files from a given directory(folder)
       
       Method to call:
       dirEntries( dir_name, media_type, recursive )
            dir_name   - the name of the directory to be searched
            media_type - valid types: video, music, pictures, files, programs
            recursive  - Setting to "TRUE" searches Parent and subdirectories, Setting to "FALSE" only search Parent Directory
    '''
    fileList = []
    json_query = '{"jsonrpc": "2.0", "method": "Files.GetDirectory", "params": {"directory": "%s", "media": "%s", "recursive": "%s"}, "id": 1}' % (
    escapeDirJSON(dir_name), media_type, recursive)
    json_folder_detail = xbmc.executeJSONRPC(json_query)
    file_detail = compile("{(.*?)}", DOTALL).findall(json_folder_detail)
    for f in file_detail:
        match = search('"file" : "(.*?)",', f)
        if not match:
            match = search('"file":"(.*?)",', f)
        if match:
            if (match.group(1).endswith("/") or match.group(1).endswith("\\")):
                if (recursive == "TRUE"):
                    fileList.extend(dirEntries(match.group(1), media_type, recursive, contains))
            elif not contains or (contains and (contains in match.group(1))):
                fileList.append(match.group(1))
        else:
            continue
    return fileList


def escapeDirJSON(dir_name):
    ''' escapes characters in a directory path for use in JSON RPC calls
        
        Method to call:
        escapeDirJSON( dir_name )
            dir_name    - the name of the directory
    '''
    if (dir_name.find(":")):
        dir_name = dir_name.replace("\\", "\\\\")
    return dir_name
