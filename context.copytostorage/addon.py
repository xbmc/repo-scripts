import xbmc
import xbmcgui
import xbmcaddon
import sys
import os
import errno
import shutil
import json

reload(sys)
sys.setdefaultencoding('utf8')


__addon__ = xbmcaddon.Addon()
__addonname__ = __addon__.getAddonInfo('name')


files_to_send=[]
def make_file_name_safe(filename):
    return "".join([c for c in filename if c.isalpha() or c.isdigit() or c==' ']).rstrip()


def parse_item_from_uri(uri):
    # keep this for reference 
    # videodb://movies/some/thing/some/12321
    scheme_nonscheme = uri.split("://")

    scheme = scheme_nonscheme[0]

    nonscheme_splits = scheme_nonscheme[1].split("/")

    db_type =  nonscheme_splits[0]

    db_filter = "/".join(nonscheme_splits[1:-1]) if len(nonscheme_splits)>=3 else ""
    db_id =  nonscheme_splits[-1]

    return scheme, db_type, db_filter, db_id


def execute_jsonrpc(request):
    response = xbmc.executeJSONRPC(json.dumps(request))

    j = json.loads(response)

    result = j.get('result')

    return result



def get_directory_info(directory_path):
    request = {'jsonrpc': '2.0',
               'method': 'Files.GetDirectory',
               'params': {'properties': ['title', 'genre', 'year', 'rating', 'runtime', 'plot', 'file', 'art', 'sorttitle', 'originaltitle','artist','albumartist','album','duration','trailer','country','season','episode','thumbnail','tag','albumlabel','dateadded','size'],
                          'directory': directory_path,
                          'media': 'files'},
                'id': 1
               }
    return execute_jsonrpc(request)



def get_single_file_info(file_path):
    request = {'jsonrpc': '2.0',
               'method': 'Files.GetFileDetails',
               'params': {'properties': ['title', 'genre', 'year', 'rating', 'runtime', 'plot', 'file', 'art', 'sorttitle', 'originaltitle','artist','albumartist','album','duration','trailer','country','season','episode','thumbnail','tag','albumlabel','dateadded','size'],
                          'file': file_path,
                          'media': 'files'},
                'id': 2
               }

    ret_val = execute_jsonrpc(request)


    return ret_val


def sanitize_path(url):
    return url.split('?')[0]


def copy_file_or_folder(src, dest):

    file_name = os.path.basename(src)



    try:
        shutil.copytree(src, dest)
    except OSError as e:
        
        if e.errno == errno.ENOTDIR:

            shutil.copy(src, dest)
        else:
            LOCALIZED_ERROR_COPYING = __addon__.getLocalizedString(32006)
            LOCALIZED_FILE_NOT_COPIED = __addon__.getLocalizedString(32012)


            xbmcgui.Dialog().ok(LOCALIZED_ERROR_COPYING, LOCALIZED_FILE_NOT_COPIED,file_name , str(e))
            return str(e)



def copy_files(file_items):
    file_name = ""
    error_list= []
    try:

        dialog = xbmcgui.Dialog()

        LOCALIZED_COPY_FILE = __addon__.getLocalizedString(32010)
        LOCALIZED_FILES = __addon__.getLocalizedString(32011)

        dest_path_only = dialog.browseSingle(3, LOCALIZED_COPY_FILE, LOCALIZED_FILES, '', True, False, '')


        if dest_path_only == "":
            # xbmcgui.Dialog().ok("Destination empty","Copying cancled")

            return

        for i,fi in enumerate(file_items):
            src_path = fi.get('file_src')
            if src_path[-1] == '/': src_path = src_path[:-1]
            file_name = os.path.basename(src_path)
            



            if src_path != "":
                dest_file_path = dest_path_only + file_name
                LOCALIZED_COPYING = __addon__.getLocalizedString(32008)


                xbmcgui.Dialog().notification(LOCALIZED_COPYING%(i+1,len(file_items)) ,file_name,xbmcgui.NOTIFICATION_INFO,10000000)

                copy_ret = copy_file_or_folder(src_path, dest_file_path)

                if copy_ret != None:
                    error_list.append(copy_ret)




    except Exception as e:
        error_list.append(str(e))
        LOCALIZED_ERROR_COPYING = __addon__.getLocalizedString(32006)
        LOCALIZED_FAILED_TO_COPY = __addon__.getLocalizedString(32007)

        xbmcgui.Dialog().ok(LOCALIZED_ERROR_COPYING, file_name, LOCALIZED_FAILED_TO_COPY, str(e))

    LOCALIZED_COPYING_FINISHED = __addon__.getLocalizedString(32003)
    xbmcgui.Dialog().notification(LOCALIZED_COPYING_FINISHED,file_name ,xbmcgui.NOTIFICATION_INFO,1000)


    LOCALIZED_DONE = __addon__.getLocalizedString(32004)
    LOCALIZED_DONE_COPYING_WITH_ERROR = __addon__.getLocalizedString(32005)

    xbmcgui.Dialog().ok(LOCALIZED_DONE, LOCALIZED_DONE_COPYING_WITH_ERROR%(str(len(file_items)),str(len(error_list))),"\n".join(error_list) )     
    
    if len(error_list) == 0:
        # clear_cart() FOR DEBUG: DISABLE LATER
        pass


def main():
    li_path = sys.listitem.getPath()

    is_item_path_directory = False



    sanitized_path = sanitize_path(li_path)

    path_info = get_single_file_info(sanitized_path)

    if path_info == None:
        path_info = get_directory_info(sanitized_path)

        if path_info != None:
            is_item_path_directory = True
        


    if path_info == None:
        LOCALIZED_ERROR = __addon__.getLocalizedString(32001)
        LOCALIZED_ERROR_RESOLVING = __addon__.getLocalizedString(32002)

        xbmcgui.Dialog().notification(LOCALIZED_ERROR,LOCALIZED_ERROR_RESOLVING +" "+sanitized_path,xbmcgui.NOTIFICATION_ERROR,10000)
        return



    if is_item_path_directory:
        if path_info.get("files"):
            for file in path_info.get("files"):
                

                file_data = {"file_src":file.get('file'),"kodi_path":li_path}
                files_to_send.append( file_data )
                
                # FOR DEBUG
                # for key in file.keys():
                #     xbmc.log("%s %s"%(key,file.get(key)))
                    

    else:
        if path_info.get("filedetails"):
            file_data = {"file_src":path_info.get("filedetails").get('file'),"kodi_path":li_path }
            files_to_send.append( file_data )
            # FOR DEBUG
            # for key in path_info.get("filedetails").keys():
            #     xbmc.log("%s %s"%(key,path_info.get("filedetails").get(key)))


    item_scheme, item_db_type, item_db_filter, item_db_id = parse_item_from_uri(li_path)


    if files_to_send != []:
        copy_files(files_to_send)
    
            




if __name__ == '__main__':
    main()
