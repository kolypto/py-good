from .base import ValidatorBase
from .. import Invalid
from ..schema.util import get_literal_name, get_type_name


class Range(ValidatorBase):
    """ Validate that the value is within the defined range, inclusive.
    Raise [`Invalid`](#invalid) error if not.

    ```python
    from good import Schema, Range

    schema = Schema(Range(1, 10))

    schema(1)  #-> 1
    schema(10)  #-> 10
    schema(15)
    #-> Invalid: Value must be at most 10: expected Range(1..10), got 15
    ```

    If the value cannot be compared to a number -- raises [`Invalid`](#invalid).
    Note that in Python2 almost everything can be compared to a number, including strings, dicts and lists!

    :param min: Minimal allowed value, or `None` to impose no limits.
    :type min: int|float|None
    :param max: Maximal allowed value, or `None` to impose no limits.
    :type max: int|float|None
    """

    def __init__(self, min=None, max=None):
        # `min` validator
        self.min_error = lambda: Invalid(_(u'Value must be at least {min}').format(min=min), get_literal_name(min))
        self.min = min

        # `max` validator
        self.max_error = lambda: Invalid(_(u'Value must be at most {max}').format(max=max),  get_literal_name(max))
        self.max = max

        # Name
        self.name = _(u'Range({min}..{max})').format(
            min=_(u'') if min is None else min,
            max=_(u'') if max is None else max
        )

    def __call__(self, v):
        # Validate
        try:
            if self.min is not None and v < self.min:
                raise self.min_error()
            if self.max is not None and v > self.max:
                raise self.max_error()
        except TypeError:  # cannot compare
            raise Invalid(_(u'Value should be a number'), _(u'Number'), get_type_name(type(v)))

        # Ok
        return v


class Clamp(ValidatorBase):
    """ Clamp a value to the defined range, inclusive.

    ```python
    from good import Schema, Clamp

    schema = Schema(Clamp(1, 10))

    schema(-1)  #-> 1
    schema(1)  #-> 1
    schema(10)  #-> 10
    schema(15)  #-> 10
    ```

    If the value cannot be compared to a number -- raises [`Invalid`](#invalid).
    Note that in Python2 almost everything can be compared to a number, including strings, dicts and lists!

    :param min: Minimal allowed value, or `None` to impose no limits.
    :type min: int|float|None
    :param max: Maximal allowed value, or `None` to impose no limits.
    :type max: int|float|None
    """

    def __init__(self, min=None, max=None):
        self.min = min
        self.max = max

        # Name
        self.name = _(u'Clamp({min}..{max})').format(
            min=_(u'') if min is None else min,
            max=_(u'') if max is None else max
        )

    def __call__(self, v):
        # Clamp
        try:
            if self.min is not None and v < self.min:
                return self.min
            if self.max is not None and v > self.max:
                return self.max
        except TypeError:  # cannot compare
            raise Invalid(_(u'Value should be a number'), _(u'Number'), get_type_name(type(v)))

        # Ok
        return v


__all__ = ('Range', 'Clamp', )
