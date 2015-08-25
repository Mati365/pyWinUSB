# Dla fluent API
def chain_method(func):
    def func_wrapper(self, *args, **kwargs):
        func(self, *args, **kwargs)
        return self
    return func_wrapper

# Szybkie emitowanie zdarzeń
def event_method(status):
    def dec(func):
        def func_wrapper(self, *args, **kwargs):
            self.event_handler.on_status(status)
            func(self, *args, **kwargs)
            return self
        return func_wrapper
    return dec

# Metoda instalacyjna
def installer_method(status):
    def dec(func):
        return chain_method(event_method(status)(func))
    return dec