# -*- coding: utf-8 -*-
''' This is the actual InputStream Helper API script entry point '''

from __future__ import absolute_import, division, unicode_literals
import os
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lib'))  # noqa: E402
from inputstreamhelper.api import run

run(sys.argv)
