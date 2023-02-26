# -*- coding: utf-8 -*-
"""
    Copyright (C) 2020 Tubed API (script.module.tubed.api)

    This file is part of script.module.tubed.api

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only.txt for more information.
"""


class Quality:
    MAP = {
        0: 240,
        1: 360,
        2: 480,
        3: 720,
        4: 1080,
        5: 1440,
        6: 2160,
        7: 4320,
        8: 'mp4',
        9: 'webm'
    }

    def __init__(self, height, limit_30fps=True, hdr=False, av1=False):

        self._index = self._index_of_height(height)
        self._limit_30fps = limit_30fps
        self._hdr = hdr
        if hdr:
            self._limit_30fps = False

        self._av1 = av1

    @property
    def map(self):
        return self.MAP

    @property
    def quality(self):
        return self.map.get(self._index, 'mp4')

    @property
    def qualities(self):
        if not isinstance(self.quality, int):
            return self.quality

        qualities = sorted([quality for quality in self.map.values()
                            if isinstance(quality, int) and quality <= self.quality],
                           reverse=True)

        return qualities

    @property
    def limit_30fps(self):
        if self.hdr:
            return False
        return self._limit_30fps

    @property
    def hdr(self):
        return self._hdr

    @property
    def av1(self):
        return self._av1

    def _index_of_height(self, height):
        for index, quality in self.MAP.items():
            if height == quality:
                return index

        return 8
