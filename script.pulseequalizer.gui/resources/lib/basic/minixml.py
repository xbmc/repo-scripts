#!/usr/bin/python3

#	This file is part of PulseEqualizerGui for Kodi.
#
#	Copyright (C) 2021 wastis    https://github.com/wastis/PulseEqualizerGui
#
#	PulseEqualizerGui is free software; you can redistribute it and/or modify
#	it under the terms of the GNU Lesser General Public License as published
#	by the Free Software Foundation; either version 3 of the License,
#	or (at your option) any later version.
#

def parse_attr(val):
	cols = val.split(' ')
	tag=cols[0]
	attr={}

	ncols=[]
	for col in cols[1:]:
		if col=='': continue
		ncols = ncols + col.split("=")

	it = iter(ncols)
	try:
		while True:
			col = next(it)
			attr[col]= next(it)
	except StopIteration: pass
	return tag,attr

def parse_tag(val,it):
	if val.startswith("!--"): return None,{}

	tag_det, tag_val = val.strip().split(">")

	if tag_det[-1]=='/':
		tag , attr = parse_attr(tag_det[:-1])
		if attr:
			return tag,{"attr":attr}
		else:
			return tag,{}

	else:
		tag , attr = parse_attr(tag_det)
		result = {}

		if attr:
			result = {"attr":attr}

		if tag_val:
			result["val"]=tag_val

		while True:
			val = next(it)
			if val[0]=='/':
				return tag,result

			subtag,subdict = parse_tag(val,it)
			if subtag in result:
				result[subtag].append(subdict)
			else:
				result[subtag] = [subdict]

def str_attr(attr):
	result = ""
	for key,val in list(attr.items()):
		result = result + " {}={}".format(key,val)
	return result

def str_tag(tag, data, ident=''):
	string = ""
	for d in data:
		attr=""
		val=""
		sub=""
		nl=""
		inl=""

		for key, items in list(d.items()):
			if key == "attr": attr = str_attr(items)
			elif key == "val": val = items
			else: sub = sub + str_tag(key,items,ident + "\t")

		if sub:
			nl = "\n"
			inl = ident

		if not sub and not val:
			string = string + "{ident}<{tag}{attr}/>\n"\
			.format(tag=tag, attr=attr, ident=ident)

		else:
			string = string + "{ident}<{tag}{attr}>{nl}{sub}{val}{inl}</{tag}>\n"\
			.format(tag=tag, attr=attr, sub=sub, val=val, nl=nl,ident=ident,inl=inl)

	return string

def parse_xml(text):
	content = text.replace("\n","").strip().split("<")

	it = iter(content)
	val = next(it)
	while val == "" or val.startswith('?xml'):
		val = next(it)

	tag , val = parse_tag(val,it)

	return {tag:[val]}

def get_xml(content):
	result = ""
	for key, items in list(content.items()):
		result = result + str_tag(key,items)

	return result

def arr_to_dic(attr_id, arr):
	result = {}
	for item in arr:
		if "attr" not in item:
			continue
		if attr_id not in item["attr"]:
			continue

		result[item["attr"][attr_id].replace('"','')] = item

	return result
