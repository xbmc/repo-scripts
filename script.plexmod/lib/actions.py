# coding=utf-8
from kodi_six import xbmcgui

KEY_VKEY = 0xF000
KEY_UNICODE = 0xF200

ACTIONS = {}

for action in dir(xbmcgui):
    if action.startswith("ACTION_") or action.startswith("REMOTE_"):
        ACTIONS[action] = getattr(xbmcgui, action)

ACTIONS_REVERSED = {b: a for a, b in ACTIONS.items()}


# ref: https://github.com/kcsaff/getkey/blob/master/getkey/keynames.py
ASCII_NAMES = {
    '\t': 'tab',

    ' ': 'space',          # 0x20
    '!': 'exclamation',    # 0x21
    '"': 'double quote',   # 0x22
    '#': 'hash',           # 0x23
    '$': 'dollar',         # 0x24
    '%': 'percent',        # 0x25
    '&': 'ampersand',      # 0x26
    '\'': 'single quote',  # 0x27
    '(': 'open paren',     # 0x28
    ')': 'close paren',    # 0x29
    '*': 'asterisk',       # 0x2a
    '+': 'plus',           # 0x2b
    ',': 'comma',          # 0x2c
    '-': 'minus',          # 0x2d
    '.': 'period',         # 0x2e
    '/': 'slash',          # 0x2f

    ':': 'colon',          # 0x3a
    ';': 'semicolon',      # 0x3b
    '<': 'less than',      # 0x3c
    '=': 'equals',         # 0x3d
    '>': 'greater than',   # 0x3e
    '?': 'question',       # 0x3f
    '@': 'at',             # 0x40

    '[': 'left bracket',   # 0x5b
    '\\': 'backslash',     # 0x5c
    ']': 'right bracket',  # 0x5d
    '^': 'caret',          # 0x5e
    '_': 'underscore',     # 0x5f
    '`': 'backtick',       # 0x60

    '{': 'left brace',     # 0x7b
    '|': 'pipe',           # 0x7c
    '}': 'right brace',    # 0x7d
    '~': 'tilde',          # 0x7e
}


# https://github.com/xbmc/xbmc/blob/master/xbmc/input/keyboard/Key.h#L64
MODIFIERS = dict(
    MODIFIER_CTRL=(0x00010000, "ctrl"),
    MODIFIER_SHIFT=(0x00020000, "shift"),
    MODIFIER_ALT=(0x00040000, "alt"),
    MODIFIER_RALT=(0x00080000, "ralt"),
    MODIFIER_SUPER=(0x00100000, "super"),
    MODIFIER_META=(0X00200000, "meta"),
    MODIFIER_LONG=(0X01000000, "long"),
    MODIFIER_NUMLOCK=(0X02000000, "numlock"),
    MODIFIER_CAPSLOCK=(0X04000000, "capslock"),
    MODIFIER_SCROLLLOCK=(0X08000000, "scrolllock")
)

MODIFIERS_REVERSED = {v[0]: k for k, v in MODIFIERS.items()}

MODIFIER_MIN = MODIFIERS["MODIFIER_CTRL"][0]
MODIFIER_MAX = MODIFIERS["MODIFIER_SCROLLLOCK"][0]


class ActionKey(object):
    key = None
    code = None

    def __init__(self, code):
        self.code = code
        self.key = translate_key(code)
        self.key_found = self.key != code

    @property
    def name(self):
        code = self.code
        if KEY_VKEY < code < KEY_UNICODE:
            return "Keyboard"
        elif code in ACTIONS_REVERSED:
            return ACTIONS_REVERSED[code]
        return self.__class__.__name__

    def __str__(self):
        return "{0}: {1}".format(self.name, self.key)

    def __unicode__(self):
        return str(self)


def translate_key(code):
    if KEY_VKEY < code < KEY_UNICODE:
        tcode = code - KEY_VKEY
        c = chr(tcode)
        return ASCII_NAMES.get(c, code) if tcode < 33 or tcode > 126 else c
    return ACTIONS_REVERSED.get(code, code)
