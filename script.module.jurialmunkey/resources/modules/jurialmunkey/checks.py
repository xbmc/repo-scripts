def has_arg_value(argx, values):
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            if args[argx] not in values:
                return
            return func(self, *args, **kwargs)
        return wrapper
    return decorator
