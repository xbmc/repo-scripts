# -*- coding: utf-8 -*-
import xbmc
import xbmcgui
import json
import threading
import time
from Queue import Queue, Empty
from utils import log


q = Queue()
def autoPlay(url, name, type_):
    from domains import sitesBase, parse_reddit_link, ydtl_get_playable_url
    from utils import unescape, post_is_filtered_out, strip_emoji,xbmc_busy, translation, xbmc_notify
    from reddit import reddit_request, determine_if_video_media_from_reddit_json
    from actions import setting_gif_repeat_count


    gif_repeat_count=setting_gif_repeat_count()
    entries = []
    watchdog_counter=0
    playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
    playlist.clear()

    xbmc_busy()

    content = reddit_request(url)
    if not content: return

    content = json.loads(content)

    log("Autoplay %s - Parsing %d items" %( type_, len(content['data']['children']) )    )

    for j_entry in content['data']['children']:
        try:
            title=unescape(j_entry['data']['title'].encode('utf-8'))
            title=strip_emoji(title)

            try:
                media_url = j_entry['data']['url']
            except (AttributeError,TypeError,ValueError):
                media_url = j_entry['data']['media']['oembed']['url']

            is_a_video = determine_if_video_media_from_reddit_json(j_entry)

            log("  %cTITLE:%s"  %( ("v" if is_a_video else " "), title  ) )

            ld=parse_reddit_link(link_url=media_url, assume_is_video=False, needs_preview=False, get_playable_url=True )

            if ld:
                log('      type:%s %s' %( ld.media_type, ld.link_action)   )
                if ld.media_type in [sitesBase.TYPE_VIDEO, sitesBase.TYPE_GIF, sitesBase.TYPE_VIDS, sitesBase.TYPE_MIXED]:

                    if ld.media_type==sitesBase.TYPE_GIF:
                        entries.append([title,ld.playable_url, sitesBase.DI_ACTION_PLAYABLE])
                        for _ in range( 0, gif_repeat_count ):
                            entries.append([title,ld.playable_url, sitesBase.DI_ACTION_PLAYABLE])
                    else:
                        entries.append([title,ld.playable_url, ld.link_action])
            else:

                playable_video_url=ydtl_get_playable_url(media_url)
                if playable_video_url:
                    for u in playable_video_url:
                        entries.append([title, u, sitesBase.DI_ACTION_PLAYABLE])

        except Exception as e:
            log( '  autoPlay exception:' + str(e) )


    for i,e in enumerate(entries):
        try:
            log('  possible playable items(%.2d) %s...%s (%s)' %(i, e[0].ljust(15)[:15], e[1],e[2]) )
        except:
            continue

    if len(entries)==0:
        xbmc_notify(translation(32025), translation(32026))  #Play All     No playable items
        xbmc_busy(False)
        return

    entries_to_buffer=4

    if len(entries) < entries_to_buffer:
        entries_to_buffer=len(entries)


    log("**********autoPlay*************")

    ev = threading.Event()

    t = Worker(entries, q, ev)
    t.daemon = True
    t.start()


    while True:

        try:

            playable_entry = q.get(True, 10)

            q.task_done()

            playlist.add(playable_entry[1], xbmcgui.ListItem(playable_entry[0]))
            log( '    c-buffered(%d):%s...%s' %(playlist.size(), playable_entry[0].ljust(15)[:15], playable_entry[1])  )

        except:
            watchdog_counter+=1
            if ev.is_set():#p is done producing
                break

            pass
        watchdog_counter+=1

        if playlist.size() >= entries_to_buffer:  #q.qsize()
            log('  c-buffer count met')
            break
        if watchdog_counter > entries_to_buffer:
            break

    log('  c-buffering done')

    xbmc_busy(False)

    xbmc.Player().play(playlist)

    watchdog_counter=0
    while True:

        try:

            playable_entry = q.get(True,10)
            q.task_done()

            playlist.add(playable_entry[1], xbmcgui.ListItem(playable_entry[0]))
            log( '    c-got next item(%d):%s...%s' %(playlist.size(), playable_entry[0].ljust(15)[:15], playable_entry[1])  )
        except:
            watchdog_counter+=1
            if ev.isSet(): #p is done producing
                break

            pass


        if ev.isSet() and q.empty():
            log( ' c- ev is set and q.empty -->  break '  )
            break

        if watchdog_counter > 2:
            break

    log( ' c-all done '  )


class Worker(threading.Thread):
    def __init__(self, entries, queue, ev):
        threading.Thread.__init__(self)
        self.queue = queue
        self.work_list=entries
        self.ev=ev


    def stop(self):
        self.running=False

    def run(self):

        self.running = True

        while self.running:
            try:

                self.do_work()

                self.ev.set()

                log( '  p-all done '  )
                self.stop()
            except Empty:

                time.sleep(0.1)

    def do_work(self):
        from domains import sitesBase, ydtl_get_playable_url


        url_to_check=""

        for entry in self.work_list:

            title=entry[0]
            url_to_check=entry[1]
            action=entry[2]

            if url_to_check.startswith('plugin://'):
                self.queue.put( [title, url_to_check] )
            elif action==sitesBase.DI_ACTION_PLAYABLE:
                self.queue.put( [title, url_to_check] )
            elif action==sitesBase.DI_ACTION_YTDL:
                playable_url = ydtl_get_playable_url( url_to_check )  #<-- will return a playable_url or a list of playable urls

                if playable_url:
                    for u in playable_url:
                        log('    p-(multiple)%d %s... %s' %(self.queue.qsize(), title.ljust(15)[:15], u)  )
                        self.queue.put( [title, u] )
                else:
                    log('      p-(ytdl-failed) %s' %( title )  )



if __name__ == '__main__':
    pass