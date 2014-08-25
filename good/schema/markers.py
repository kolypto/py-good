class Marker(object): pass

#region Dictionary keys behavior

class Required(Marker): pass

class Optional(Marker): pass

class Remove(Marker): pass

class Reject(Marker): pass

#endregion

def Anything(v):
    return v

__all__ = ('Required', 'Optional', 'Remove', 'Reject', 'Anything')
