#	This file is part of PulseEqualizerGui for Kodi.
#
#	Copyright (C) 2021 wastis    https://github.com/wastis/PulseEqualizerGui
#
#	PulseEqualizerGui is free software; you can redistribute it and/or modify
#	it under the terms of the GNU Lesser General Public License as published
#	by the Free Software Foundation; either version 3 of the License,
#	or (at your option) any later version.
#
#

import sys
import math

from helper import logerror, opthandle

if sys.version_info[0] > 2:
	try:
		from PIL import Image, ImageDraw
	except ModuleNotFoundError:
		logerror("please install python3-pil")
else:
	try:
		from PIL import Image, ImageDraw
	except ImportError:
		logerror("please install python-pil")

def createGraph(fn, spec = None, width = 1700, height = 700):
	with Image.new("RGBA",(width, height),(0,0,0,0)) as im:
		h = height
		w = width
		zero_y = int(h / 2)
		zero_x = 0
		scale = h / 40
		xscale = w / 2.5

		draw = ImageDraw.Draw(im)

		if spec:
			coords = []
			for f,v in spec.freq_db:
				if f < 100: continue
				if f > 25000: break

				try:
					xl = (math.log10(f) - 2) * xscale + zero_x
					yl = math.log10(1 / v) * 20
					if yl > 20: yl = 20
					yl = zero_y - yl * scale

					coords.append((xl, yl))
				except Exception as e: opthandle(e)
			if coords:
				x1, y1 = coords[0]
				for x2,y2 in coords[1:]:
					draw.line((x1, y1, x2, y2),fill=(255,255,255,255), width = 4)
					x1 = x2
					y1 = y2

		im.save(fn, "PNG")

def createGraphdB(fn, spec = None, width = 1700, height = 700):
	with Image.new("RGBA",(width, height),(0,0,0,0)) as im:
		h = height
		w = width
		zero_y = int(h / 2)
		zero_x = 0
		scale = h / 40
		xscale = w / 2.5

		draw = ImageDraw.Draw(im)

		if spec:
			coords = []
			for f,v in spec.freq_db:
				if f < 100: continue
				if f > 25000: break

				try:
					xl = (math.log10(f) - 2) * xscale + zero_x
					yl = v
					if yl > 20: yl = 20
					yl = zero_y - yl * scale

					coords.append((xl, yl))
				except Exception as e: opthandle(e)
			if coords:
				x1, y1 = coords[0]
				for x2,y2 in coords[1:]:
					draw.line((x1, y1, x2, y2),fill=(255,255,255,255), width = 4)
					x1 = x2
					y1 = y2

		im.save(fn, "PNG")

def createGraph2(fn, spec = None, width = 1700, height = 700):
	with Image.new("RGBA",(width, height),(0,0,0,0)) as im:
		h = height
		w = width
		zero_x = 0
		scale = h / 40
		zero_y = scale * 4

		xscale = w / 2.8

		col= (255,255,255,255)
		draw = ImageDraw.Draw(im)

		if spec:
			coords = []
			for f,v in spec.freq_db:
				if f < 40: continue
				if f > 25000: break

				try:
					xl = (math.log10(f) - 1.6) * xscale + zero_x
					yl = v
					if yl > 4: yl = 4
					yl = zero_y - yl * scale

					coords.append((xl, yl))
				except Exception as e: opthandle(e)
			if coords:
				x1, y1 = coords[0]
				for x2,y2 in coords[1:]:
					draw.line((x1, y1, x2, y2),fill=(255,255,255,255), width = 4)
					x1 = x2
					y1 = y2

		im.save(fn, "PNG")

def createGrid(fn, spec = None, width = 1700, height = 700):
	with Image.new("RGBA",(width, height),(0,0,0,0)) as im:
		h = height
		w = width
		zero_y = int(h / 2)
		zero_x = 0
		scale = h / 40
		xscale = w / 2.5

		col= (255,255,255,255)
		col2 = (192,192,192,255)
		draw = ImageDraw.Draw(im)

		for i in [4,8,12,16]:
			ch = i * scale
			draw.line((zero_x, zero_y + ch , zero_x + w, zero_y + ch ), fill=col2, width = 2)
			draw.line((zero_x, zero_y - ch , zero_x + w, zero_y - ch ), fill=col2, width = 2)

		for i in [200,300,400,600,700,800,900,2000,3000,4000,5000,6000,7000,8000,9000,20000,30000]:
			x = (math.log10(i) - 2) * xscale + zero_x
			draw.line((x, 0, x, h), fill=col2, width = 2)

		for i in [100,500,1000,5000,10000]:
			x = (math.log10(i) - 2) * xscale + zero_x
			draw.line((x, 0, x, h), fill=col, width = 2)

		# 0 line
		draw.line((zero_x, zero_y, zero_x + w, zero_y), fill=col, width = 5)
		#horizontal
		draw.line((zero_x, 2, zero_x + w, 2), fill=col, width = 5)
		draw.line((zero_x, h-3, zero_x + w, h-3), fill=col, width = 5)
		#vertical
		draw.line((zero_x+3, 0, zero_x+3, h), fill=col, width = 5)
		draw.line((zero_x + w-3, 0, zero_x + w-3, h), fill=col, width = 5)

		im.save(fn, "PNG")

def createGrid2(fn, spec = None, width = 1700, height = 700):
	with Image.new("RGBA",(width, height),(0,0,0,0)) as im:
		h = height
		w = width
		zero_x = 0
		scale = h / 40
		zero_y = scale * 4

		xscale = w / 2.8

		col= (255,255,255,255)
		col2 = (192,192,192,255)
		draw = ImageDraw.Draw(im)

		for i in [4, 8,12,16,20,24,28,32]:
			ch = i * scale
			draw.line((zero_x, zero_y + ch , zero_x + w, zero_y + ch ), fill=col2, width = 2)

		for i in [40,50,60,70,80,90, 200,300,400,600,700,800,900,2000,3000,4000,5000,6000,7000,8000,9000,20000,30000]:
			x = (math.log10(i) - 1.6) * xscale + zero_x
			draw.line((x, 0, x, h), fill=col2, width = 2)

		for i in [100,500,1000,5000,10000]:
			x = (math.log10(i) - 1.6) * xscale + zero_x
			draw.line((x, 0, x, h), fill=col, width = 2)

		# 0 line
		draw.line((zero_x, zero_y, zero_x + w, zero_y), fill=col, width = 5)
		#horizontal
		draw.line((zero_x, 2, zero_x + w, 2), fill=col, width = 5)
		draw.line((zero_x, h-3, zero_x + w, h-3), fill=col, width = 5)
		#vertical
		draw.line((zero_x+2, 0, zero_x+2, h), fill=col, width = 5)
		draw.line((zero_x + w-3, 0, zero_x + w-3, h), fill=col, width = 5)

		im.save(fn, "PNG")
