import six
from .util import get_type_name
from .errors import Invalid, MultipleInvalid


class Marker(object):
    def __new__(cls, value):
        # See: http://stackoverflow.com/questions/25510668/thin-proxy-class
        value_type = type(value)
        Type = type(
            '{}({!r})'.format(cls.__name__, value),
            (cls, value_type),
            {
                # Compiled schema here
            })
        Type.__new__ = value_type.__new__  # Prevent recursion
        return Type(value)

    def __repr__(self):
        return type(self).__name__

    @classmethod
    def validate_marked_values(cls, marked, value):
        raise NotImplementedError('{} does not implement validation'.format(type(cls).__name__))

#region Dictionary keys behavior

class Required(Marker):
    @classmethod
    def validate_marked_values(cls, marked, value):  # CHECKME: Experimental!
        # `value` must contain ALL `marked` values
        missing_keys = marked - set(value)  # Missing keys, marked as Required()
        if missing_keys:
            errors = [Invalid(_(u'Required key not provided'), six.text_type(key), u'', [key], validator=key)
                      for key in missing_keys]
            raise MultipleInvalid.if_multiple(errors)
        return value


class Optional(Marker): pass

class Remove(Marker): pass

class Reject(Marker): pass

#endregion

def Anything(v):
    return v

__all__ = ('Required', 'Optional', 'Remove', 'Reject', 'Anything')
