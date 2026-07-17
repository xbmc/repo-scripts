import xbmc, xbmcgui
from resources.data_loader import load_data

def main_dialog():
    dialog = xbmcgui.Dialog()
    items = load_data()
    selected=dialog.select("Streams", list([x['text'] for x in items]))
    if selected>=0:
      item = items[selected]
      cmd = 'StartAndroidActivity("","org.acestream.action.start_content","","acestream:?content_id=%s")' % item['acestream_id']
      xbmc.executebuiltin(cmd)