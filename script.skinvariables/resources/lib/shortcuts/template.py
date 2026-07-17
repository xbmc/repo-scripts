# -*- coding: utf-8 -*-
# Module: default
# Author: jurialmunkey
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html
import re
import xbmc
import xbmcaddon
from json import loads
from jurialmunkey.logger import TimerFunc
from jurialmunkey.parser import parse_math, boolean, parse_paramstring
from jurialmunkey.futils import load_filecontent, write_skinfile, make_hash
from resources.lib.kodiutils import ProgressDialog, get_localized
from resources.lib.operations import RuleOperations, check_condition
from resources.lib.shortcuts.node import ListGetShortcutsNode, get_menunode_lookup
from resources.lib.shortcuts.xmltojson import xml_to_json
from xml.dom import minidom
from copy import deepcopy


ADDON = xbmcaddon.Addon()

SKIN_BASEDIR = 'special://skin'
SHORTCUTS_FOLDER = 'shortcuts'


def escape_ampersands(myxml):
    regex = re.compile(r"&(?!amp;|lt;|gt;)")
    return regex.sub("&amp;", myxml)


def pretty_xmlcontent(myxml):
    myxml = minidom.parseString(myxml)
    return '\n'.join([line for line in myxml.toprettyxml(indent=' ' * 4).split('\n') if line.strip()])


class FormatDict(dict):
    def __missing__(self, key):
        if key.endswith('_escaped'):
            return self[key[:-8]]
        return ''


class TemplatePart():
    def __init__(self, parent, genxml, **kwargs):
        self.skinid = parent.skinid
        self.genxml = deepcopy(genxml)
        self.params = FormatDict(kwargs)
        self.stored = parent.stored if hasattr(parent, 'stored') else {}

    @property
    def is_condition(self):
        try:
            return self._is_condition
        except AttributeError:
            self._is_condition = self.parse_condition(self.genxml.pop('condition', []))
            return self._is_condition

    def parse_condition(self, conditions):
        conditions = conditions if isinstance(conditions, list) else [conditions]
        return all([check_condition(self.get_formatted(condition)) for condition in conditions])

    def parse_lookup(self, string):
        """ $LOOKUP[lookup_key?menu=sidemenu&filter_guid=xyz] """
        LOOKUP_REGEX = r'\$LOOKUP\[(.*?)\]'
        match = re.search(LOOKUP_REGEX, string)
        if not match:
            return string
        lookup, paramstring = match.group(1).split('?', 1)
        params = parse_paramstring(paramstring)
        output = get_menunode_lookup(lookup, skin=self.skinid, **params)
        string = string.replace(match.group(0), output)
        return self.parse_lookup(string)

    def get_formatted(self, string, params=None):
        string = string.format_map(params or self.params)
        string = parse_math(string)
        string = self.parse_lookup(string)
        return string

    def get_conditional_value(self, items):
        for i in items:
            if isinstance(i, str):
                return self.get_formatted(i)
            if self.parse_condition(i.get('condition', 'true')):
                return self.get_formatted(i['value'] or '')
        return ''

    def update_params(self):
        for k, v in self.genxml.items():
            if isinstance(v, dict):
                self.params[k] = '\n'.join(self.get_contents(v, self.params))
                continue
            if isinstance(v, list):
                self.params[k] = self.get_conditional_value(v)
                continue
            self.params[k] = self.get_formatted(v)
        return self.params

    def get_menunode(self):
        for_each = self.genxml.pop("for_each")
        menu = self.get_formatted(self.genxml.pop("menu", ''))
        item = self.get_formatted(self.genxml.pop("item", ''))
        mode = self.get_formatted(self.genxml.pop("mode", ''))

        contents = []

        node_obj = ListGetShortcutsNode(None, None)
        node_obj.refresh = True  # Refresh mem cache because we want to build from the file
        nodelist = node_obj.get_directory(menu=menu, skin=self.skinid, node=item, mode=mode, func='node') or []

        for item_x, item_i in enumerate(nodelist):
            item_i = {'value': item_i} if isinstance(item_i, str) else item_i  # In case of actions list we only have strings so massage to dictionary
            item_i.pop('submenu', [])
            item_i.pop('widgets', [])
            for action_x, action_i in enumerate(for_each):
                item_d = deepcopy(self.params)  # Inherit parent values
                item_d.update({f'parent_{k}': v for k, v in item_d.items()})  # Update with item values
                item_d.update({f'item_{k}': v for k, v in item_i.items()})  # Update with item values
                item_d['item_x'] = item_x  # Add item index
                item_d['item_action_x'] = action_x  # Add item index
                item_d['item_length_x'] = len(nodelist)  # Add length of nodelist that current item is in
                item_d['item_menu'] = menu  # Add item menu
                item_d['item_node'] = item  # Add item menu
                item_d['item_mode'] = mode  # Add item menu
                contents += self.get_contents(action_i, item_d)
        return contents

    def get_itemlist(self):
        contents = []
        itemlist = self.genxml.pop("list")
        for_each = self.genxml.pop("for_each")
        for item, defs in itemlist:
            item_d = deepcopy(self.params)  # Inherit parent values
            item_d.update(defs)  # Add in any specific values for item
            item_d.update({f'parent_{k}': v for k, v in item_d.items()})  # Update with item values
            item_d['item'] = item  # Add item menu
            for action in for_each:
                contents += self.get_contents(action, item_d)
        return contents

    def get_template(self):  # _make_template
        filelist = self.genxml.pop("template")
        filelist = filelist if isinstance(filelist, list) else [filelist]
        contents = []
        fmt_dict = self.update_params()
        for template in filelist:
            file = load_filecontent(f'{SKIN_BASEDIR}/{SHORTCUTS_FOLDER}/{template}') if template.endswith('.xmltemplate') else template
            item = self.get_formatted(file, fmt_dict)
            contents.append(item)
        return ['\n'.join(contents)]

    def add_datafile(self):
        filelist = self.genxml.pop("datafile")
        filelist = filelist if isinstance(filelist, list) else [filelist]
        contents = {}
        for datafile in filelist:
            file = load_filecontent(f'{SKIN_BASEDIR}/{SHORTCUTS_FOLDER}/{datafile}')
            func = xml_to_json if datafile.endswith('.xml') else loads
            meta = func(file) if file else {}
            contents.update(meta)
        contents.update(self.genxml)
        self.genxml = contents
        return self.genxml

    def get_enumitem(self):
        enumitem = self.genxml.pop("enumitem")
        for k, v in enumitem.items():
            name = self.get_formatted(v)
            enum = self.stored.setdefault(name, 0) + 1
            self.stored[name] = enum
            self.genxml[k] = f'{enum}'
            self.params[k] = f'{enum}'
        return self.genxml

    def get_for_each(self):
        if 'list' in self.genxml:
            return self.get_itemlist()
        return self.get_menunode()

    def get_contents(self, genxml, params):
        params = params or {}
        return TemplatePart(self, genxml, **params).get_content()

    def get_content(self):  # _make_contents
        if 'datafile' in self.genxml:
            self.add_datafile()
        if not self.is_condition:
            return []
        if 'enumitem' in self.genxml:
            self.get_enumitem()
        if 'template' in self.genxml:
            return self.get_template()
        if 'for_each' in self.genxml:
            return self.get_for_each()
        return []


class ShortcutsTemplate(object):
    allow_users = True

    def __init__(self, template: str = None):
        self.template = f'skinvariables-generator-{template}' if template else 'skinvariables-generator'
        self.hashname = f'script-{self.template}{self.skinuser}-hash'
        self.contents = load_filecontent(f'{SKIN_BASEDIR}/{SHORTCUTS_FOLDER}/{self.template}.json')
        self.meta = loads(self.contents) or {}
        self.folder = self.meta.get('folder') or SHORTCUTS_FOLDER
        self.p_dialog = None

    @property
    def skinuser(self):
        try:
            return self._skinuser
        except AttributeError:
            return self.get_skinuser()

    def get_skinuser(self):
        self._skinuser = '' if not self.allow_users else xbmc.getInfoLabel("Skin.String(SkinVariables.SkinUser)") or ''
        return self._skinuser

    @property
    def filepath(self):
        try:
            return self._filepath
        except AttributeError:
            return self.get_filepath()

    def get_filepath(self):
        self._filepath = f'{SKIN_BASEDIR}/{self.folder}/{self.filename}'
        return self._filepath

    @property
    def filename(self):
        try:
            return self._filename
        except AttributeError:
            return self.get_filename()

    def get_filename(self):
        self._filename = self.meta['output'].format(skinuser=self.skinuser)
        return self._filename

    @property
    def skinid(self):
        try:
            return self._skinid
        except AttributeError:
            return self.get_skinid()

    def get_skinid(self):
        self._skinid = self.meta.get('skinid')
        if not self._skinid or not self.skinuser:
            return self._skinid
        self._skinid = f'{self._skinid}-{self.skinuser}'
        return self._skinid

    def create_xml(self):
        self.p_dialog.update(message=f'{get_localized(32046)}...')  # Generating globals

        pre_generated_nfo = {**self.meta['getnfo']}
        pre_generated_nfo.update({
            k: TemplatePart(self, v, **self.meta['getnfo']).get_template()[0]
            for k, v in self.meta.get('global', {}).items()})

        self.p_dialog.update(message=f'{get_localized(32047)}...')  # Generating content

        content = []

        if 'header' in self.meta:
            content += [self.meta['header']]

        content += [j for i in self.meta['genxml'] for j in TemplatePart(self, i, **pre_generated_nfo).get_content()]

        if 'footer' in self.meta:
            content += [self.meta['footer']]

        self.p_dialog.update(message=f'{get_localized(32048)}...')  # Formatting content

        content = '\n'.join(content)
        content = escape_ampersands(content)
        content = pretty_xmlcontent(content)
        return content

    def update_xml(self, force=False, no_reload=False, genxml='', background=True, **kwargs):
        if not self.meta:
            return

        hashinput = '_'.join([
            '_'.join([f'{k}.{v}' for k, v in kwargs.items()]),
            f'{genxml}',
            f'{self.contents}',
            xbmc.getInfoLabel("System.ProfileName")
        ])

        def get_hashvalue():
            return make_hash(f'{hashinput}--{load_filecontent(self.filepath)}')

        hashvalue = get_hashvalue()

        def is_updated():
            if force:
                return
            if not hashvalue:
                return
            last_version = xbmc.getInfoLabel(f'Skin.String({self.hashname})')
            if not last_version:
                return
            if last_version != hashvalue:
                return
            return True

        if is_updated():
            return

        with TimerFunc('script.skinvariables - update_xml: ', log_threshold=0.001, inline=True):
            with ProgressDialog(
                    ADDON.getLocalizedString(32001),
                    f'{get_localized(32049)}...',
                    logging=2, total=4, background=boolean(background)
            ) as self.p_dialog:
                self.meta['genxml'] += [{k: v for j in i.split('|') for k, v in (j.split('='), )} for i in genxml.split('||')] if genxml else []
                self.meta['getnfo'] = {k: xbmc.getInfoLabel(v) for k, v in self.meta['getnfo'].items()} if 'getnfo' in self.meta else {}
                self.meta['getnfo'].update(kwargs)
                self.meta['getnfo'].update(RuleOperations(self.meta['addnfo'], **self.meta['getnfo']).params) if 'addnfo' in self.meta else {}
                write_skinfile(folders=[self.folder], filename=self.filename, content=self.create_xml(), hashvalue=hashvalue, hashname=self.hashname)

        if no_reload:
            return

        xbmc.Monitor().waitForAbort(0.5)
        xbmc.executebuiltin('Skin.SetString({},{})'.format(self.hashname, get_hashvalue()))  # Update hashvalue with new content to avoid loop
        xbmc.executebuiltin('ReloadSkin()')
