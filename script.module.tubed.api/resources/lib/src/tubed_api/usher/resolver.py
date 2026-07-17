# -*- coding: utf-8 -*-
"""
    Copyright (C) 2020 Tubed API (script.module.tubed.api)

    This file is part of script.module.tubed.api

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only.txt for more information.
"""

from .lib.quality import Quality
from .lib.video_info import VideoInfo


def resolve(video_id, quality=None, language='en-US', region='US'):
    if not quality:
        quality = Quality('mp4')
    elif isinstance(quality, (int, str)):
        quality = Quality(quality)

    video_info = VideoInfo(language, region)
    video = video_info.get_video(video_id, quality)

    return video
