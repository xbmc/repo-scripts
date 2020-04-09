#!/usr/bin/python3
import re
import os

ADDON_VERSION_RE = re.compile(r'(<addon.+?version=")([^"]+)(")', re.I | re.DOTALL)
XBMC_PYTHON_VERSION_RE = re.compile(r'(addon="xbmc.python".+?version=")([^"]+)(")',
                                    re.I | re.DOTALL)

def modify_addon_xml_for_matrix(addon_xml_path):
    print('Modifying addon.xml for matrix branch')
    with open(addon_xml_path, 'r', encoding='utf-8') as fo:
        addon_xml = fo.read()
    addon_version_match = ADDON_VERSION_RE.search(addon_xml)
    if addon_version_match is None:
        raise Exception('Unable to parse addon version in addon.xml')
    xbmc_python_version_match = XBMC_PYTHON_VERSION_RE.search(addon_xml)
    if xbmc_python_version_match is None:
        raise Exception('Unable to parse xbmc.python version in addon.xml')
    addon_version = addon_version_match.group(2)
    matrix_addon_version = addon_version + '+matrix.1'
    matrix_addon_version_mask = r'\g<1>{}\g<3>'.format(matrix_addon_version)
    addon_xml = ADDON_VERSION_RE.sub(matrix_addon_version_mask, addon_xml)
    addon_xml = XBMC_PYTHON_VERSION_RE.sub(r'\g<1>3.0.0\g<3>', addon_xml)
    with open(addon_xml_path, 'w', encoding='utf-8') as fo:
        fo.write(addon_xml)
    print('Addon.xml modified successfully')

if __name__ == "__main__":
    modify_addon_xml_for_matrix(os.path.join(os.getcwd(), "addon.xml"))
