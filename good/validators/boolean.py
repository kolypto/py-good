import six

from .base import ValidatorBase
from .. import Invalid
from ..schema.util import get_callable_name, get_primitive_name, get_type_name


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
            raise Invalid(u'Empty value', provided=get_primitive_name(v))
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
            raise Invalid(u'Non-empty value', provided=get_primitive_name(v))
        return v


class Boolean(ValidatorBase):
    """ Convert human-readable boolean values to a `bool`.

    The following values are supported:

    * `None`: `False`
    * `bool`: direct
    * `int`: `0` = `False`, everything else is `True`
    * `str`: Textual boolean values, compatible with [YAML 1.1 boolean literals](http://yaml.org/type/bool.html), namely:

            y|Y|yes|Yes|YES|n|N|no|No|NO|
            true|True|TRUE|false|False|FALSE|
            on|On|ON|off|Off|OFF

        [`Invalid`](#invalid) is thrown if an unknown string literal is provided.

    Example:

    ```python
    from good import Schema, Boolean

    schema = Schema(Boolean())

    schema(None)  #-> False
    schema(0)  #-> False
    schema(1)  #-> True
    schema(True)  #-> True
    schema(u'yes')  #-> True
    ```
    """
    #: Case-insensitive constants for boolean strings
    _true_values_ci  = (u'y', u'Y', u'yes', u'Yes', u'YES', u'true',  u'True',  u'TRUE',  u'on',  u'On',  u'ON' )
    _false_values_ci = (u'n', u'N', u'no',  u'No',  u'NO',  u'false', u'False', u'FALSE', u'off', u'Off', u'OFF')

    def __init__(self):
        self.name = _(u'Boolean')

    def __call__(self, v):
        # None
        if v is None:
            return False
        # Bool, Int
        elif isinstance(v, six.integer_types):
            return v != 0
        # Str
        elif isinstance(v, six.string_types):
            v = six.text_type(v)
            # Match
            if v in self._true_values_ci:
                return True
            elif v in self._false_values_ci:
                return False
            else:
                raise Invalid(_(u'Wrong boolean value'))
        # Other types
        else:
            raise Invalid(_(u'Wrong boolean value type'), provided=get_type_name(type(v)))



__all__ = ('Check', 'Truthy', 'Falsy', 'Boolean')
