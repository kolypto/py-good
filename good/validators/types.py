from ._base import ValidatorBase
from .. import Invalid
from ..schema.util import get_literal_name, get_primitive_name


class Coerce(ValidatorBase):
    """ Coerce a value to a type with the provided callable.

    `Coerce` applies the *constructor* to the input value and returns a value cast to the provided type.

    If *constructor* fails with `TypeError` or `ValueError`, the value is considered invalid and `Coerce` complains
    on that with a custom message.

    However, if *constructor* raises [`Invalid`](#invalid) -- the error object is used as it.

    ```python
    from good import Schema, Coerce

    schema = Schema(Coerce(int))
    schema(u'1')  #-> 1
    schema(u'a')
    #-> Invalid: Invalid value: expected *Integer number, got a
    ```

    :param constructor: Callable that typecasts the input value
    :type constructor: callable|type
    """

    def __init__(self, constructor):
        self.constructor = constructor
        self.name = _(u'*{type}').format(type=get_primitive_name(constructor))

    def __call__(self, v):
        try:
            return self.constructor(v)
        except (TypeError, ValueError):
            raise Invalid(_(u'Invalid value'), self.name, get_literal_name(v))

__all__ = ('Coerce',)
