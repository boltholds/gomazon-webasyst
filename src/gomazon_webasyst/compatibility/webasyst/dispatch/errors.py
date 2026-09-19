class DispatchTargetNotFound(LookupError):
    pass


class ApplicationUnavailable(LookupError):
    pass


class PluginUnavailable(LookupError):
    pass
