# -*- coding: utf-8 -*-
#
# source: https://github.com/mk-fg/python-pulse-control
# License MIT
#

from __future__ import print_function, unicode_literals

import itertools as it, operator as op, functools as ft
import re


lookup_types = {
	'sink': 'sink_list', 'source': 'source_list',
	'sink-input': 'sink_input_list', 'source-output': 'source_output_list' }
lookup_types.update(it.chain.from_iterable(
	((v, lookup_types[k]) for v in v) for k,v in
	{ 'source': ['src'], 'sink-input': ['si', 'playback', 'play'],
		'source-output': ['so', 'record', 'rec', 'mic'] }.items() ))

lookup_key_defaults = dict(
	# No default keys for type = no implicit matches for that type
	sink_input_list=[ # match sink_input_list objects with these keys by default
		'media.name', 'media.icon_name', 'media.role',
		'application.name', 'application.process.binary', 'application.icon_name' ] )


def pulse_obj_lookup(pulse, obj_lookup, prop_default=None):
	'''Return set of pulse object(s) with proplist values matching lookup-string.

		Pattern syntax:
			[ { 'sink' | 'source' | 'sink-input' | 'source-output' } [ / ... ] ':' ]
			[ proplist-key-name (non-empty) [ / ... ] ':' ] [ ':' (for regexp match) ]
			[ proplist-key-value ]

		Examples:
			- sink:alsa.driver_name:snd_hda_intel
				Match sink(s) with alsa.driver_name=snd_hda_intel (exact match!).
			- sink/source:device.bus:pci
				Match all sinks and sources with device.bus=pci.
			- myprop:somevalue
				Match any object (of all 4 supported types) that has myprop=somevalue.
			- mpv
				Match any object with any of the "default lookup props" (!!!) being equal to "mpv".
				"default lookup props" are specified per-type in lookup_key_defaults above.
				For example, sink input will be looked-up by media.name, application.name, etc.
			- sink-input/source-output:mpv
				Same as above, but lookup streams only (not sinks/sources).
				Note that "sink-input/source-output" matches type spec, and parsed as such, not as key.
			- si/so:mpv
				Same as above - see aliases for types in lookup_types.
			- application.binary/application.icon:mpv
				Lookup by multiple keys with "any match" logic, same as with multiple object types.
			- key\/with\/slashes\:and\:colons:somevalue
				Lookup by key that has slashes and colons in it.
				"/" and ":" must only be escaped in the proplist key part, used as-is in values.
				Backslash itself can be escaped as well, i.e. as "\\".
			- module-stream-restore.id:sink-input-by-media-role:music
				Value has ":" in it, but there's no need to escape it in any way.
			- device.description::Analog
				Value lookup starting with : is interpreted as a regexp,
					i.e. any object with device.description *containing* "Analog" in this case.
			- si/so:application.name::^mpv\b
				Return all sink-inputs/source-outputs ("si/so") where
					"application.name" proplist value matches regexp "^mpv\b".
			- :^mpv\b
				Regexp lookup (stuff starting with "mpv" word) without type or key specification.

		For python2, lookup string should be unicode type.
		"prop_default" keyword arg can be used to specify
			default proplist value for when key is not found there.'''

	# \ue000-\uf8ff - private use area, never assigned to symbols
	obj_lookup = obj_lookup.replace('\\\\', '\ue000').replace('\\:', '\ue001')
	obj_types_re = '({0})(/({0}))*'.format('|'.join(lookup_types))
	m = re.search(
		( r'^((?P<t>{}):)?'.format(obj_types_re) +
			r'((?P<k>.+?):)?' r'(?P<v>.*)$' ), obj_lookup, re.IGNORECASE )
	if not m: raise ValueError(obj_lookup)
	lookup_type, lookup_keys, lookup_re = op.itemgetter('t', 'k', 'v')(m.groupdict())
	if lookup_keys:
		lookup_keys = list(
			v.replace('\ue000', '\\\\').replace('\ue001', ':').replace('\ue002', '/')
			for v in lookup_keys.replace('\\/', '\ue002').split('/') )
	lookup_re = lookup_re.replace('\ue000', '\\\\').replace('\ue001', '\\:')
	obj_list_res, lookup_re = list(), re.compile( lookup_re[1:]
		if lookup_re.startswith(':') else '^{}$'.format(re.escape(lookup_re)) )
	for k in set( lookup_types[k] for k in
			(lookup_type.split('/') if lookup_type else lookup_types.keys()) ):
		if not lookup_keys: lookup_keys = lookup_key_defaults.get(k)
		if not lookup_keys: continue
		obj_list = getattr(pulse, k)()
		if not obj_list: continue
		for obj, k in it.product(obj_list, lookup_keys):
			v = obj.proplist.get(k, prop_default)
			if v is None: continue
			if lookup_re.search(v): obj_list_res.append(obj)
	return set(obj_list_res)
