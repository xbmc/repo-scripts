# -*- coding: utf-8 -*-
import ast
import re


def case(identifier, cmd):
    return '"{}"'.format(identifier) in cmd


def parse_cmd(cmd):
    cmd = re.compile(r'(\d+),\[".+?",(.*)\]\]').findall(cmd)
    if cmd:
        code = cmd[0][0]
        cmd = ast.literal_eval(
            "{}".format(
                cmd[0][1]
                .replace('"{', '{')
                .replace('}"', '}')
                .replace('\\"', '"')
                )
            )
        return int(code), cmd
    else:
        raise ValueError('Unable to parse CMD')


def get_video_list(data):
    videos = []
    if "videos" in list(data.keys()):
        videos = data["videos"]
    return videos
