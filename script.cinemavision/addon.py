import sys

if __name__ == '__main__':
    arg = None
    if len(sys.argv) > 1:
        args = sys.argv[1:] or False
        arg = args.pop(0)
        print '[- CinemaVision -]: Passed args: {0}'.format(repr(sys.argv))

    if arg == 'trailer.clearWatched':
        from lib import settings
        settings.clearDBWatchedStatus()
    elif arg == 'trailer.clearBroken':
        from lib import settings
        settings.clearDBBrokenStatus()
    elif arg == 'experience':
        from lib import player
        player.begin(args=args)
    elif str(arg).startswith('movieid='):
        from lib import player
        player.begin(movieid=arg[8:], args=args)
    elif str(arg).startswith('episodeid='):
        from lib import player
        player.begin(episodeid=arg[10:], args=args)
    elif arg == 'selection':
        from lib import player
        player.begin(selection=True, args=args)
    elif arg == 'update.database':
        from lib import cvutil
        from lib import kodiutil
        cvutil.loadContent(from_settings=True)
        kodiutil.ADDON.openSettings()
    elif arg == 'feature.setRatingBumperStyle':
        from lib import cvutil
        cvutil.setRatingBumperStyle()
    elif arg == 'pastebin.paste.log':
        from lib import settings
        from lib import kodiutil
        settings.pasteLog()
        kodiutil.ADDON.openSettings()
    elif arg == 'pastebin.delete.key':
        from lib import settings
        settings.deleteUserKey()
    elif arg == 'reset.database':
        from lib import settings
        settings.removeContentDatabase()
    elif arg == 'trailer.scrapers':
        from lib import settings
        settings.setScrapers()
    elif arg == 'test.actions':
        from lib import settings
        settings.testEventActions(args[0])
    elif arg == 'install.contextMenu':
        from lib import settings
        settings.installContextMenu()
    elif str(arg).startswith('sequence.'):
        from lib import settings
        settings.setDefaultSequence(arg)
    else:
        from lib import main
        main.main()
