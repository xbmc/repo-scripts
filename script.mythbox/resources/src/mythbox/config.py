try:
    from mythbox import custom
except ImportError:
    custom = 'empty module'

offline = getattr(custom, 'offline', False)
