# -*- coding: utf-8 -*-
from textwrap import dedent

from bottle import SimpleTemplate


def build_template(template):
    return SimpleTemplate(dedent(template))
