# KarmaMole Skin Helper (script.karmamole.helper)
# Copyright (C) 2026 Omar Kamel
# SPDX-License-Identifier: GPL-2.0-or-later
"""RunScript(script.karmamole.helper,action=...) entry point. Every action returns quickly; nothing here blocks the GUI.

  action=queue_move,from=N,to=M        move the Up next card at offset N to offset M (1 = next song)
  action=queue_remove,offset=N         remove the song at offset N
  action=play_shuffled,path=P          every song under a music folder in a random order built here (first song random too; Kodi's shuffle untouched)
  action=play_slice,ring=R,value=V     shuffled mix of a wheel slice (prefer RunPlugin with ListItem.Property(Groove.PlayPath))
  action=colours,image=URL,prefix=P    colours + soft art of any image into Window(Home).Property(Groove.P.*)
  action=spines_rebuild                re-render every spine (asks the service)
Each action needs its feature to be on for the running skin (features.py); otherwise it is logged and ignored.
"""
import xbmc

from .common import ADDON_ID, log, parse_args, rpc
from .features import active, allowed

NEEDS = {'queue_move': 'queue', 'queue_remove': 'queue', 'play_shuffled': 'shuffle', 'play_slice': 'wheel',
         'colours': 'colours', 'spines_rebuild': 'spines'}


def main(argv):
    args = parse_args(argv)
    action = args.get('action', '')
    if action in NEEDS and not allowed(NEEDS[action]):
        return
    if action == 'queue_move':
        from . import queue
        queue.move(args.get('from'), args.get('to'))
    elif action == 'queue_remove':
        from . import queue
        queue.remove(args.get('offset'))
    elif action == 'play_shuffled':
        from . import wheel
        wheel.play_shuffled(args.get('path', ''))
    elif action == 'play_slice':
        from . import wheel
        wheel.play(args.get('ring', ''), args.get('value', ''))
    elif action == 'colours':
        from .glow import Publisher, Renderer
        prefix = ''.join(c for c in args.get('prefix', 'Custom') if c.isalnum()) or 'Custom'
        url = args.get('image', '')
        renderer = Renderer(soft='softart' in active())
        Publisher('Groove.' + prefix, threaded=False).publish(url, renderer.render(url) if url else None)
    elif action == 'spines_rebuild':
        rpc('JSONRPC.NotifyAll', {'sender': ADDON_ID, 'message': 'spines_rebuild'})
    else:
        log('unknown action %r (args %s)' % (action, argv), xbmc.LOGWARNING)

