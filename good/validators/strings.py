import six
from functools import wraps

from ._base import ValidatorBase
from .. import Invalid
from ..schema.util import get_type_name


def stringmethod(func):
    """ Validator factory which call a single method on the string. """
    method_name = func()

    @wraps(func)
    def factory():
        def validator(v):
            if not isinstance(v, six.string_types):
                raise Invalid(_(u'Not a string'), get_type_name(six.text_type), get_type_name(type(v)))
            return getattr(v, method_name)()
        return validator
    return factory


@stringmethod
def Lower():
    """ Casts the provided string to lowercase, fails is the input value is not a string.

    Supports both binary and unicode strings.

    ```python
    from good import Schema, Lower

    schema = Schema(Lower())

    schema(u'ABC')  #-> u'abc'
    schema(123)
    #-> Invalid: Not a string: expected String, provided Integer number
    ```
    """
    return 'lower'


@stringmethod
def Upper():
    """ Casts the input string to UPPERCASE. """
    return 'upper'


@stringmethod
def Capitalize():
    """ Capitalizes the input string. """
    return 'capitalize'


@stringmethod
def Title():
    """ Casts The Input String To Title Case """
    return 'title'


# TODO: Match
# TODO: Replace
# TODO: Url

__all__ = ('Lower', 'Upper', 'Capitalize', 'Title')
