# -*- coding: utf-8 -*-
# Module: default
# Author: jurialmunkey
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html
import xbmcvfs
import xml.etree.ElementTree as ET


XML_HEADER = '<?xml version=\"1.0\" encoding=\"UTF-8\"?>'


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
