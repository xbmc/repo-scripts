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

from basic import logerror
from basic import opthandle

if sys.version_info[0] > 2:
	try:
		from PIL import Image
		from PIL import ImageDraw
	except ModuleNotFoundError:
		logerror("please install python3-pil")
else:
	try:
		from PIL import Image
		from PIL import ImageDraw
	except ImportError:
		logerror("please install python-pil")

def createGraph2(fn, spec = None, width = 1700, height = 700):
	with Image.new("RGBA",(width, height),(0,0,0,0)) as im:
		h = height
		w = width
		zero_x = 0
		scale = h / 40
		zero_y = scale * 4

		xscale = w / 2.8

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
