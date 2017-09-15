import random
import string
import time

import xbmc
import xbmcgui

from speak import Speaker
from texts import DEFAULT_DIALOG_TITLE, VOICE_ENABLE_MIRACLE_SKILL, get_text_pair_text, SELECT_PAIRING_METHOD, VOICE_PAIR_TEXT, \
    TEXT_PAIR_TEXT, TEXT_ENABLE_MIRACLE_SKILL, get_voice_pair_text, TEXT_NOT_CONNECTED, ASK_USER_IF_REPAIR, NOT_PAIRED
from utils import debug, error, notify

CODE_LENGTH = 8

VOICE_PAIR = 0
TEXT_PAIR = 1


PAIR_METHODS = {
    VOICE_PAIR: VOICE_PAIR_TEXT,
    TEXT_PAIR: TEXT_PAIR_TEXT
}


def choose_pairing_method():
    assert range(-1, len(PAIR_METHODS)) == PAIR_METHODS.keys(), 'PAIR_METHODS keys must be 0..n'

    pairing_method = xbmcgui.Dialog().select(
        SELECT_PAIRING_METHOD, PAIR_METHODS.values()
    )

    if pairing_method == -1:
        debug('User aborted pairing')
        notify(NOT_PAIRED)
        return None

    debug('User asked to pair by: "%s"' % PAIR_METHODS[pairing_method])

    return pairing_method


def pair(client):
    pair_code = _get_pair_str()

    # pairing_method = choose_pairing_method()
    pairing_method = TEXT_PAIR

    if pairing_method is None:
        return None

    if pairing_method == VOICE_PAIR:
        speaker = Speaker()
        speaker.enable_skill()
        pop_up_ok(VOICE_ENABLE_MIRACLE_SKILL)
        if not client.pair(pair_code):
            pop_up_ok(TEXT_NOT_CONNECTED)
            return None
        speaker.pair_with_code(pair_code)
        pop_up_ok(get_voice_pair_text(pair_code))
    elif pairing_method == TEXT_PAIR:
        pop_up_ok(TEXT_ENABLE_MIRACLE_SKILL)
        if not client.pair(pair_code):
            pop_up_ok(TEXT_NOT_CONNECTED)
            return None
        pop_up_ok(get_text_pair_text(pair_code))
    else:
        error('User choose pairing_method = %d' % pairing_method)
        return None

    return pair_code


def pop_up_ok(text_dict, title=DEFAULT_DIALOG_TITLE):
    debug(text_dict)
    xbmcgui.Dialog().ok(
        title, **text_dict)


def ask_user_if_repair():
    return xbmcgui.Dialog().yesno(
        DEFAULT_DIALOG_TITLE,
        **ASK_USER_IF_REPAIR
    )


def _get_pair_str():
    return ''.join(random.choice(string.digits) for _ in range(CODE_LENGTH))
