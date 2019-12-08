# -*- coding: utf-8 -*-
import sys

from textwrap import dedent

from bottle import SimpleTemplate


PY3 = sys.version_info.major >= 3


def build_template(template):
    return SimpleTemplate(dedent(template))

def str_to_bytes(string):
    if PY3:
        return bytes(string, 'utf-8')
    return string