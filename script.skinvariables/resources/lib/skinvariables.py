# -*- coding: utf-8 -*-
# Module: default
# Author: jurialmunkey
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html
import xbmc
import xbmcgui
import xbmcaddon
from json import loads, dumps
import xml.etree.ElementTree as ET
from jurialmunkey.parser import try_int, del_empty_keys
from resources.lib.xmlhelper import make_xml_includes, get_skinfolders
from jurialmunkey.futils import load_filecontent, write_skinfile, make_hash

ADDON = xbmcaddon.Addon()


class SkinVariables(object):
    def __init__(self, template: str = None, skinfolder: str = None):
        self.template = f"skinvariables-{template}" if template else 'skinvariables'
        self.filename = f'script-{self.template}-includes.xml'
        self.hashname = f'script-{self.template}-hash'
        self.folders = [skinfolder] if skinfolder else get_skinfolders()
        self.content = self.build_json(f'special://skin/shortcuts/{self.template}.xml')
        self.content = self.content or load_filecontent(f'special://skin/shortcuts/{self.template}.json')
        self.meta = loads(self.content) or []

    def build_json(self, file):
        xmlstring = load_filecontent(file)
        if not xmlstring:
            return

        json = []
        for variable in ET.fromstring(xmlstring):
            if not variable.attrib.get('name'):
                continue  # No name specified so skip
            if variable.tag not in ['expression', 'variable']:
                continue  # Not an expression or variable so skip

            item = {}

            if variable.tag == 'expression' and variable.text:
                item['expression'] = variable.text
            elif variable.tag == 'variable':
                item['values'] = [{i.attrib.get('condition') or 'True': i.text} for i in variable]

            if not item.get('expression') and not item.get('values'):
                continue  # No values or expression so skip

            item['name'] = variable.attrib.get('name')
            item['containers'] = [
                j for i in variable.attrib.get('containers', '').split(',') for j
                in (range(*(int(y) + x for x, y, in enumerate(i.split('...')))) if '...' in i else (int(i),))]
            item['listitems'] = {}
            item['listitems']['start'] = try_int(variable.attrib.get('start'))
            item['listitems']['end'] = try_int(variable.attrib.get('end'))
            item['types'] = variable.attrib['types'].split(',') if variable.attrib.get('types') else ['listitem']
            item['parent'] = variable.attrib.get('parent')
            item['null_id'] = variable.attrib.get('null_id')

            json.append(del_empty_keys(item))

        return dumps(json)

    def build_containers(self, variable={}):
        containers = variable.get('containers', [])
        containers.append('')
        return containers

    def build_listitems(self, variable={}):
        li_a = variable.get('listitems', {}).get('start', 0)
        li_z = variable.get('listitems', {}).get('end')
        listitems = [i for i in range(li_a, int(li_z) + 1)] if li_z else []
        listitems.append('')
        return listitems

    def get_contentvalues(self, values, f_dict):
        content = []
        for value in values:
            build_var = {}
            build_var['tag'] = 'value'
            build_var['attrib'] = {}
            for k, v in value.items():
                if not k:
                    continue
                build_var['attrib']['condition'] = k.format(**f_dict)
                build_var['content'] = v.format(**f_dict) if v else ''
            content.append(build_var)
        return content

    def get_skinvariable(self, variable, expression=False):
        if not variable:
            return

        var_name = variable.get('name')

        if not var_name:
            return

        containers = self.build_containers(variable)
        listitems = self.build_listitems(variable)
        values = variable.get('values', [])
        listitem_types = variable.get('types') or ['listitem']
        skin_vars = []

        listitem_type_tags = {
            'listitem': '',
            'listitemabsolute': '_LIA',
            'listitemnowrap': '_LIN',
            'listitemposition': '_LIP',
        }

        def _build_var(container=None, listitem=None, listitem_type='listitem'):
            build_var = {
                'tag': 'expression' if expression else 'variable',
                'attrib': {},
                'content': []
            }

            li_name = 'ListItem'
            tag_name = var_name
            _lid = ''
            _cid = ''

            tag_name += listitem_type_tags[listitem_type]

            if container == -1:  # Special value for building container without ID
                tag_name += '_Container'
                li_name = 'Container.ListItem'
                container = ''  # Blank out container ID

            if container:
                tag_name += '_C{}'.format(container)
                li_name = 'Container({}).ListItem'.format(container)
                _cid = '_C{}'.format(container)

            if listitem or listitem == 0:
                tag_name += '_{}'.format(listitem)
                li_name += '({})'.format(listitem)
                _lid = '_{}'.format(listitem)

            build_var['attrib']['name'] = tag_name

            f_dict = {
                'id': container or '',
                'cid': _cid,
                'lid': _lid,
                'pos': listitem or 0,
                'listitem': li_name,
                'listitemabsolute': li_name.replace('ListItem(', 'ListItemAbsolute('),
                'listitemnowrap': li_name.replace('ListItem(', 'ListItemNoWrap('),
                'listitemposition': li_name.replace('ListItem(', 'ListItemPosition(')
            }

            f_dict['listitem'] = f_dict[listitem_type]

            if expression:
                build_var['content'] = variable.get('expression', '').format(**f_dict)
                return build_var

            build_var['content'] = self.get_contentvalues(values, f_dict)
            return build_var

        for lit in listitem_types:
            for container in containers:
                # Build Variables for each ListItem Position in Container
                for listitem in listitems:
                    skin_vars.append(_build_var(container, listitem, lit))

            if variable.get('null_id', '').lower() == 'true':
                # Build a Container.ListItem variable without an id
                for listitem in listitems:
                    skin_vars.append(_build_var(-1, listitem, lit))

        def _build_parent_var(listitem_type='listitem'):

            parent_var_name = var_name + listitem_type_tags[listitem_type]

            build_var = {
                'tag': 'variable',
                'attrib': {'name': parent_var_name + '_Parent'},
                'content': []
            }

            content = []

            for container in containers:
                cond = 'True'
                valu = parent_var_name
                if container:
                    valu += '_C{}'.format(container)
                    cond = variable['parent'].format(**{'id': container or ''})
                valu = '$VAR[{}]'.format(valu)
                content.append({'tag': 'value', 'attrib': {'condition': cond}, 'content': valu})

            build_var['content'] = content
            return build_var

        # Build variable for parent containers
        for lit in listitem_types:
            if variable.get('parent'):
                skin_vars.append(_build_parent_var(lit))

        return skin_vars

    def update_xml(self, force=False, no_reload=False, **kwargs):
        if not self.meta:
            return

        hashvalue = make_hash(self.content)

        if not force:  # Allow overriding over built check
            last_version = xbmc.getInfoLabel(f'Skin.String({self.hashname})')
            if hashvalue and last_version and hashvalue == last_version:
                return  # Already updated

        p_dialog = xbmcgui.DialogProgressBG()
        p_dialog.create(ADDON.getLocalizedString(32001), ADDON.getLocalizedString(32000))

        xmltree = []
        for i in self.meta:
            item = None
            if i.get('values'):
                item = self.get_skinvariable(i)
            elif i.get('expression'):
                item = self.get_skinvariable(i, expression=True)
            xmltree = xmltree + item if item else xmltree

        # Save to folder
        if self.folders:
            write_skinfile(
                folders=self.folders, filename=self.filename,
                content=make_xml_includes(xmltree, p_dialog=p_dialog),
                hashvalue=hashvalue, hashname=self.hashname)

        p_dialog.close()
        xbmc.executebuiltin('ReloadSkin()') if not no_reload else None
