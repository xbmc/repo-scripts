#! /usr/bin/python

import os
import xml.etree.ElementTree as ET
import argparse
import codecs

from jinja2 import Template
import Image

REPO_ID = 'repository.russellharrower'

tree = ET.parse("addons.xml").getroot()

template = Template(open('index_template.html').read())

def get_addons():
    for addon in sorted(tree, key=lambda element: element.attrib['name']):
        a = {}

        module = addon.find("extension[@point='xbmc.python.module']")
        if module is not None:
            continue

        repo = addon.find("extension[@point='xbmc.addon.repository']")
        if repo is not None:
            a['types'] = ['repository']

        plugin = addon.find("extension[@point='xbmc.python.pluginsource']")
        if plugin is not None:
            a['types'] = plugin.find('provides').text.split()

        script = addon.find("extension[@point='xbmc.python.script']")
        if script is not None:
            a['types'] = ['program']

        skin = addon.find("extension[@point='xbmc.gui.skin']")
        if skin is not None:
            a['types'] = ['skin']

        for attrib in ('id', 'name', 'version', 'provider-name'):
            a[attrib] = addon.get(attrib)

        a['icon'] = os.path.join(a['id'], 'icon.png')

        metadata = addon.find("extension[@point='xbmc.addon.metadata']")


        data = metadata.find("summary[@lang='en']")
        if data is None:
            data = metadata.find("summary")

        if data is not None:
            a['summary'] = data.text


        data = metadata.find("description[@lang='en']")
        if data is None:
            data = metadata.find("description")

        if data is not None:
            a['description'] = [line for line in data.text.splitlines() if line]


        for key in ('website', 'forum', 'source'):
            data = metadata.find(key)
            if data is not None:
                a[key] = data.text

        yield a

addons = {}
repo = None
for addon in get_addons():
    if addon['id'] == REPO_ID:
        repo = addon
    else:
        addon_type = addon['types'][0] # group by first type if multiple types
        addons.setdefault(addon_type, []).append(addon)
	print addon['name']

text = template.render(repo=repo,
                       categories=('program', 'video', 'audio', 'image', 'skin'), # define order of categories
                       addons=addons)



codecs.open('index.html', 'w', 'utf-8').write(text)

im = Image.open(repo['icon'])
im.thumbnail((32, 32), Image.ANTIALIAS)
im.save('favicon.png', 'png')
