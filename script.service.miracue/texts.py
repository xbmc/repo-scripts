import xbmcaddon

addon = xbmcaddon.Addon()
localize = addon.getLocalizedString
_ = localize

DEFAULT_DIALOG_TITLE = _(32020)

SELECT_PAIRING_METHOD = _(32021)
VOICE_PAIR_TEXT = _(32022)
TEXT_PAIR_TEXT = _(32023)
TEXT_NOT_CONNECTED = {
    'line1': _(32024),
    'line2': _(32025)
}

VOICE_ENABLE_MIRACLE_SKILL = {
    'line1': _(32026),
    'line2': _(32027),
    'line3': _(32028)
}

ASK_USER_IF_REPAIR = {
    'line1': _(32029),
    'line2': _(32030)
}

TEXT_ENABLE_MIRACLE_SKILL = VOICE_ENABLE_MIRACLE_SKILL.copy()
TEXT_ENABLE_MIRACLE_SKILL['line1'] = _(32031)
TEXT_ENABLE_MIRACLE_SKILL['line2'] = _(32032)

PAIRED = _(32037)
UNPAIRED_FROM_ALEXA = _(32038)
NOT_PAIRED = _(32039)


def get_voice_pair_text(pair_code):
    return dict(
        line1=_(32033),
        line2=_(32034) % (pair_code[:4], pair_code[4:])
    )


def get_text_pair_text(pair_code):
    return dict(
        line1=_(32036) % ("\n[COLOR red]%s %s[/COLOR]" % (pair_code[:4], pair_code[4:]))
    )
