class Marker(object):
    def __init__(self, schema):
        self.schema = schema

    def __repr__(self):
        return '{cls}({0.schema!r})'.format(self, cls=type(self).__name__)

#region Dictionary keys behavior

class Required(Marker): pass

class Optional(Marker): pass

class Remove(Marker): pass

class Reject(Marker): pass

#endregion

def Anything(v):
    return v

__all__ = ('Required', 'Optional', 'Remove', 'Reject', 'Anything')
