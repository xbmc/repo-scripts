from lib.script.context import main

try:
    main()
finally:
    import sys
    _database = sys.modules.get('lib.data.database._infrastructure')
    if _database is not None:
        _database.close_connections()
