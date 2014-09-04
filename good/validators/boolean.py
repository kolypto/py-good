import six

from ._base import ValidatorBase
from .. import Invalid
from ..schema.util import get_callable_name, get_primitive_name


class Check(ValidatorBase):
    """ Use the provided boolean function as a validator and raise errors when it's `False`.

    ```python
    import os.path
    from good import Schema, Check

    schema = Schema(
        Check(os.path.isdir, u'Must be an existing directory'))
    schema('/')  #-> '/'
    schema('/404')
    #-> Invalid: Must be an existing directory: expected isDir(), got /404
    ```

    :param bvalidator: Boolean validator function
    :type bvalidator: callable
    :param message: Error message to report when `False`
    :type message: unicode
    :param expected: Expected value string representation, or `None` to get it from the wrapped callable
    :type expected: None|str|unicode
    """

    def __init__(self, bvalidator, message, expected):
        assert isinstance(message, six.text_type), 'Check() message must be a unicode string'
        assert isinstance(expected, six.text_type) or expected is None, 'Check() expected must be a unicode string'

        self.bvalidator = bvalidator
        self.name = get_callable_name(bvalidator)
        self.message = message
        self.expected = expected

    def __call__(self, v):
        #  Test with the boolean function
        if self.bvalidator(v):
            # Return value as is
            return v
        else:
            # If the boolean function reported False -- raise Invalid
            raise Invalid(self.message, self.expected)


class Truthy(ValidatorBase):
    """ Assert that the value is truthy, in the Python sense.

    This fails on all "falsy" values: `False`, `0`, empty collections, etc.

    ```python
    from good import Schema, Truthy

    schema = Schema(Truthy())

    schema(1)  #-> 1
    schema([1,2,3])  #-> [1,2,3]
    schema(None)
    #-> Invalid: Empty value: expected truthy(), got None
    ```
    """

    @classmethod
    def truthy(cls, v):
        return bool(v)

    def __init__(self):
        self.name = _(u'Truthy')

    def __call__(self, v):
        if not self.truthy(v):
            raise Invalid(u'Empty value', self.name, get_primitive_name(v))
        return v


class Falsy(ValidatorBase):
    """ Assert that the value is falsy, in the Python sense.

    Supplementary to [`Truthy`](#truthy).
    """

    @classmethod
    def falsy(cls, v):
        return not bool(v)

    def __init__(self):
        self.name = _(u'Falsy')

    def __call__(self, v):
        if not self.falsy(v):
            raise Invalid(u'Non-empty value', self.name, get_primitive_name(v))
        return v


# TODO: Boolean

__all__ = ('Check', 'Truthy', 'Falsy')
