import six
from functools import wraps
import re

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


class Match(ValidatorBase):
    """ Validate the input string against a regular expression.

    ```python
    from good import Schema, Match

    schema = Schema(All(
        unicode,
        Match(r'^0x[A-F0-9]+$', 'hex number')
    ))

    schema('0xDEADBEEF')  #-> '0xDEADBEEF'
    schema('0x')
    #-> Invalid: Wrong format: expected hex number, got 0xDEADBEEF
    ```

    :param pattern: RegExp pattern to match with: a string, or a compiled pattern
    :type pattern: str|_SRE_Pattern
    :param expected: Textual representation of what's expected from the user
    :type expected: unicode
    """

    def __init__(self, pattern, expected=None):
        self.rex = re.compile(pattern)  # accepts compiled patterns as well
        self.name = expected or _(u'(special format)')

    def __call__(self, v):
        try:
            # Try to match
            match = self.rex.match(v)
        except TypeError:
            # Wrong type
            raise Invalid(_(u'Wrong value type'), u'String', get_type_name(type(v)))

        # Matched?
        if not match:
            raise Invalid(_(u'Wrong format'), self.name)
        else:
            return v


class Replace(Match):
    """ RegExp substitution.

    ```python
    from good import Schema, Replace

    schema = Schema(Replace(
        # Grab domain name
        r'^https?://([^/]+)/.*'
        # Replace
        r'\1',
        # Tell the user that we're expecting a URL
        u'URL'
    ))

    schema('http://example.com/a/b/c')  #-> 'example.com'
    schema('user@example.com')
    #-> Invalid: Wrong format: expected URL, got user@example.com
    ```

    :param pattern: RegExp pattern to match with: a string, or a compiled pattern
    :type pattern: str|_SRE_Pattern
    :param repl: Replacement pattern.

        Backreferences are supported, just like in the [`re`](https://docs.python.org/2/library/re.html) module.

    :type repl: unicode
    :param expected: Textual representation of what's expected from the user
    :type expected: unicode
    """

    def __init__(self, pattern, repl, expected=None):
        super(Replace, self).__init__(pattern, expected)
        self.repl = repl

    def __call__(self, v):
        try:
            # Try to match
            v, n_subs = self.rex.subn(self.repl, v)
        except TypeError:
            # Wrong type
            raise Invalid(_(u'Wrong value type'), u'String', get_type_name(type(v)))

        # Matched?
        if not n_subs:
            raise Invalid(_(u'Wrong format'), self.name)
        else:
            return v


# TODO: Url
# TODO: EMail

__all__ = ('Lower', 'Upper', 'Capitalize', 'Title', 'Match', 'Replace')
