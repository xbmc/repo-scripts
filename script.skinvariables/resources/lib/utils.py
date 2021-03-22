import sys
import xbmc
import xbmcvfs
import xbmcgui
import json
import hashlib
import xml.etree.ElementTree as ET
from contextlib import contextmanager


XML_HEADER = '<?xml version=\"1.0\" encoding=\"UTF-8\"?>'


@contextmanager
def isactive_winprop(name, value='True', windowid=10000):
    xbmcgui.Window(windowid).setProperty(name, value)
    try:
        yield
    finally:
        xbmcgui.Window(windowid).clearProperty(name)


@contextmanager
def busy_dialog():
    xbmc.executebuiltin('ActivateWindow(busydialognocancel)')
    try:
        yield
    finally:
        xbmc.executebuiltin('Dialog.Close(busydialognocancel)')


def get_localized(text):
    if text.startswith('$LOCALIZE'):
        text = text.strip('$LOCALIZE[]')
    if try_parse_int(text):
        text = xbmc.getLocalizedString(try_parse_int(text))
    return text


def get_jsonrpc(method=None, params=None):
    if not method or not params:
        return {}
    query = {
        "jsonrpc": "2.0",
        "params": params,
        "method": method,
        "id": 1}
    try:
        jrpc = xbmc.executeJSONRPC(json.dumps(query))
        response = json.loads(try_decode_string(jrpc, errors='ignore'))
    except Exception as exc:
        kodi_log(u'SkinVariables - JSONRPC Error:\n{}'.format(exc), 1)
        response = {}
    return response


def make_xml_itertxt(xmltree, indent=1, indent_spaces=4, p_dialog=None):
    """
    xmltree = [{'tag': '', 'attrib': {'attrib-name': 'attrib-value'}, 'content': '' or []}]
    <{tag} {attrib-name}="{attrib-value}">{content}</{name}>
    """
    txt = []
    indent_str = ' ' * indent_spaces * indent

    p_total = len(xmltree) if p_dialog else 0
    p_dialog_txt = ''
    for p_count, i in enumerate(xmltree):
        if not i.get('tag', ''):
            continue  # No tag name so ignore

        txt += ['\n', indent_str, '<{}'.format(i.get('tag'))]  # Start our tag

        for k, v in i.get('attrib', {}).items():
            if not k:
                continue
            txt.append(' {}=\"{}\"'.format(k, v))  # Add tag attributes
            p_dialog_txt = v

        if not i.get('content'):
            txt.append('/>')
            continue  # No content so close tag and move onto next line

        txt.append('>')

        if p_dialog:
            p_dialog.update((p_count * 100) // p_total, message=u'{}'.format(p_dialog_txt))

        if isinstance(i.get('content'), list):
            txt.append(make_xml_itertxt(i.get('content'), indent=indent + 1))
            txt += ['\n', indent_str]  # Need to indent before closing tag
        else:
            txt.append(i.get('content'))
        txt.append('</{}>'.format(i.get('tag')))  # Finish
    return ''.join(txt)


def make_xml_includes(lines=[], p_dialog=None):
    txt = [XML_HEADER]
    txt.append('<includes>')
    txt.append(make_xml_itertxt(lines, p_dialog=p_dialog))
    txt.append('</includes>')
    return '\n'.join(txt)


def merge_dicts(org, upd, skipempty=False):
    source = org.copy()
    for k, v in upd.items():
        if not k:
            continue
        if skipempty and not v:
            continue
        if isinstance(v, dict):
            if not isinstance(source.get(k), dict):
                source[k] = {}
            source[k] = merge_dicts(source.get(k), v, skipempty=skipempty)
            continue
        source[k] = v
    return source


def del_empty_keys(d, values=[]):
    my_dict = d.copy()
    for k, v in d.items():
        if not v or v in values:
            del my_dict[k]
    return my_dict


def get_skinfolders():
    """
    Get the various xml folders for skin as defined in addon.xml
    e.g. 21x9 1080i xml etc
    """
    folders = []
    try:
        addonfile = xbmcvfs.File('special://skin/addon.xml')
        addoncontent = addonfile.read()
    finally:
        addonfile.close()
    xmltree = ET.ElementTree(ET.fromstring(addoncontent))
    for child in xmltree.getroot():
        if child.attrib.get('point') == 'xbmc.gui.skin':
            for grandchild in child:
                if grandchild.tag == 'res' and grandchild.attrib.get('folder'):
                    folders.append(grandchild.attrib.get('folder'))
    return folders


def make_hash(content):
    return hashlib.md5(content.encode('utf-8')).hexdigest()


def check_hash(hashname, hashvalue=None):
    last_version = xbmc.getInfoLabel('Skin.String({})'.format(hashname))
    if not last_version:
        return hashvalue
    if hashvalue != last_version:
        return hashvalue


def write_file(filepath=None, content=None):
    if not filepath:
        return
    f = xbmcvfs.File(filepath, 'w')
    f.write(try_encode_string(content))
    f.close()


def write_skinfile(filename=None, folders=None, content=None, hashvalue=None, hashname=None, reloadskin=True, checksum=None):
    if not filename or not folders or not content:
        return

    for folder in folders:
        write_file(filepath='special://skin/{}/{}'.format(folder, filename), content=content)

    if hashvalue and hashname:
        xbmc.executebuiltin('Skin.SetString({},{})'.format(hashname, hashvalue))

    if checksum:
        xbmc.executebuiltin('Skin.SetString({},{})'.format(checksum, make_hash(content)))

    if reloadskin:
        xbmc.executebuiltin('ReloadSkin()')


def join_conditions(org='', new='', operator=' | '):
    return '{}{}{}'.format(org, operator, new) if org else new


def kodi_log(value, level=0):
    try:
        if isinstance(value, bytes):
            value = value.decode('utf-8')
        logvalue = u'{0}{1}'.format('[script.skinvariables]\n', value)
        if sys.version_info < (3, 0):
            logvalue = logvalue.encode('utf-8', 'ignore')
        if level == 1:
            xbmc.log(logvalue, level=xbmc.LOGNOTICE)
        else:
            xbmc.log(logvalue, level=xbmc.LOGDEBUG)
    except Exception as exc:
        xbmc.log(u'Logging Error: {}'.format(exc), level=xbmc.LOGNOTICE)


def load_filecontent(filename=None):
    try:
        vfs_file = xbmcvfs.File(filename)
        content = vfs_file.read()
    finally:
        vfs_file.close()
    return content


def try_parse_int(string):
    '''helper to parse int from string without erroring on empty or misformed string'''
    try:
        return int(string)
    except Exception:
        return 0


def try_decode_string(string, encoding='utf-8', errors=None):
    """helper to decode strings for PY 2 """
    if sys.version_info.major == 3:
        return string
    try:
        return string.decode(encoding, errors) if errors else string.decode(encoding)
    except Exception:
        return string


def try_encode_string(string, encoding='utf-8'):
    """helper to encode strings for PY 2 """
    if sys.version_info.major == 3:
        return string
    try:
        return string.encode(encoding)
    except Exception:
        return string
