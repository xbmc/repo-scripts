# -*- coding: utf-8 -*-
# Module: default
# Author: jurialmunkey
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html
import xml.etree.ElementTree as ET


"""
Module for converting xml based template config code into json
"""


class Meta():
    def __init__(self, root, meta):
        self.root = root
        self.meta = meta

    def set_listtext(self, tag, key=None):
        """
        XML:
        <datafile>D1</datafile>
        <datafile>D2</datafile>
        <condition>C1</condition>
        <condition>C2</condition>

        JSON:
        {
            "datafile": [
                "D1",
                "D2"
            ],
            "condition": [
                "C1",
                "C2"
            ]
        }
        """
        value = [i.text for i in self.root.findall(tag)]
        if not value:
            return
        self.meta[key or tag] = value
        return value

    def set_dicttext(self, tag, key=None):
        """
        XML:
        <tag name="K1">V1</tag>
        <tag name="K2">V2</tag>

        JSON:
        {
            "key or tag": {
                "K1": "V1",
                "K2": "V2"
            }
        }
        """
        value = {}
        for i in self.root.findall(tag):
            k = i.attrib['name']
            v = i.text
            value[k] = v
        if not value:
            return
        self.meta[key or tag] = value
        return value

    def set_itemtext(self, tag, key=None):
        """
        XML:
        <template>T1</template>

        JSON:
        {
            "template": "T1"
        }
        """
        value = next((i.text for i in self.root.findall(tag) if i.text), None)
        if not value:
            return
        self.meta[key or tag] = value
        return value

    def set_value(self, root):
        """
        XML:
        <value name="N1">
            C1
        </value>

        JSON:
        {
            "N1": {
                C1
            }
        }
        """
        items = []
        name = root.attrib['name'] if 'name' in root.attrib else 'value'
        if not list(root):
            self.meta[name] = root.text
            return items
        items.append(Meta(root, self.meta.setdefault(name, {})))
        return items

    def set_rules(self, root):
        """
        XML:
        <rules name="N1">
            <rule>
                <condition>C1</condition>
                <value>V1</value>
            </rule>
            <rule>
                <condition>C2</condition>
                <value>V2</value>
            </rule>
        </rules>

        JSON:
        {
            "N1": [
                {
                    "condition": "C1",
                    "value": "V1"
                },
                {
                    "condition": "C2",
                    "value": "V2"
                }
            ]
        }
        """
        items = []
        name = root.attrib['name']
        self.meta[name] = []
        for item in root.findall('rule'):
            meta = {}
            self.meta[name].append(meta)
            items.append(Meta(item, meta))
        return items

    def set_items(self, root):
        """
        XML:
        <items node="N1" mode="M1" item="I1">
            <item>
                C1
            </item>
            <item>
                C2
            </item>
        </items>

        JSON:
        {
            "node": "N1",
            "mode": "M1",
            "item": "I1",
            "for_each" [
                {
                    C1
                },
                {
                    C2
                }
            ]
        }
        """
        items = []

        for k, v in root.attrib.items():
            self.meta[k] = v

        self.meta['for_each'] = []
        for item in root.findall('item'):
            meta = {}
            self.meta['for_each'].append(meta)
            items.append(Meta(item, meta))
        return items

    def set_lists(self, root):
        """
        XML:
        <lists>
            <list name="N1">
                <value name="K1">V1</value>
                <value name="K2">V2</value>
            </list>
            <list name="N2">
                <value name="K3">V3</value>
                <value name="K4">V4</value>
            </list>
        </lists>

        JSON:
        {
            "list": [
                ["N1", {"K1": "V1", "K2": "V2"}],
                ["N2", {"K3": "V3", "K4": "V4"}]
            ]
        }
        """
        items = []
        self.meta['list'] = []
        for item in root.findall('list'):
            meta = {}
            pair = [item.attrib['name'], meta]
            self.meta['list'].append(pair)
            items.append(Meta(item, meta))
        if not items:
            del self.meta['list']
            return []
        return items


class XMLtoJSON():

    routes = {
        'value': 'set_value',
        'items': 'set_items',
        'rules': 'set_rules',
        'lists': 'set_lists'
    }

    def __init__(self, filecontent):
        self.root = ET.fromstring(filecontent)
        self.meta = {}

    def get_meta(self):
        self.get_contents(Meta(self.root, self.meta))
        return self.meta

    def get_contents(self, meta):
        meta.set_listtext('condition')
        meta.set_itemtext('template')
        meta.set_listtext('datafile')
        meta.set_dicttext('enumitem')

        for i in meta.root:
            func = self.routes.get(i.tag)
            if not func:
                continue
            func = getattr(meta, func)
            for j in func(i):
                self.get_contents(j)


def xml_to_json(filecontent):
    return XMLtoJSON(filecontent).get_meta()
