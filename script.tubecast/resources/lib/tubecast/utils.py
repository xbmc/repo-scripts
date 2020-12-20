# -*- coding: utf-8 -*-
import sys

from textwrap import dedent

from bottle import SimpleTemplate


def build_template(template):
    return SimpleTemplate(dedent(template))
