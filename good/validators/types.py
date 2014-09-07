from .base import ValidatorBase
from .. import Invalid
from ..schema.util import get_primitive_name, get_type_name


class Type(ValidatorBase):
    """ Check if the value has the specific type with `isinstance()` check.

    In contrast to [Schema types](#schema) which performs a strict check, this check is relaxed and accepts subtypes
    as well.

    ```python
    from good import Schema, Type

    schema = Schema(Type(int))
    schema(1)  #-> 1
    schema(True)  #-> True
    ```

    :param types: The type to check instances against.

        If multiple types are provided, then any of them is acceptable.

    :type types: list[type]
    """
    def __init__(self, *types):
        self.types = types
        self.name = _(u'|').join(get_type_name(x) for x in self.types)

    def __call__(self, v):
        # Type check
        if not isinstance(v, self.types):
            raise Invalid(_(u'Wrong type'), provided=get_type_name(type(v)))
        # Fine
        return v


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
            raise Invalid(_(u'Invalid value'))

__all__ = ('Type', 'Coerce',)
