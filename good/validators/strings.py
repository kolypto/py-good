import six
from functools import wraps
import re

from .base import ValidatorBase
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
    :param message: Error message override
    :type message: unicode
    :param expected: Textual representation of what's expected from the user
    :type expected: unicode
    """

    def __init__(self, pattern, message=None, expected=None):
        self.rex = re.compile(pattern)  # accepts compiled patterns as well
        self.name = expected or _(u'(special format)')
        self.message = message or _(u'Wrong format')

    def __call__(self, v):
        try:
            # Try to match
            match = self.rex.match(v)
        except TypeError:
            # Wrong type
            raise Invalid(_(u'Wrong value type'), u'String', get_type_name(type(v)))

        # Matched?
        if not match:
            raise Invalid(self.message)
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
    :param message: Error message override
    :type message: unicode|None
    :param expected: Textual representation of what's expected from the user
    :type expected: unicode
    """

    def __init__(self, pattern, repl, message=None, expected=None):
        super(Replace, self).__init__(pattern, message, expected)
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
            raise Invalid(self.message)
        else:
            return v


class Url(ValidatorBase):
    """ Validate a URL, make sure it's in the absolute format, including the protocol.

    ```python
    from good import Schema, Url

    schema = Schema(Url('https'))

    schema('example.com')  #-> 'https://example.com'
    schema('http://example.com')  #-> 'http://example.com'
    ```

    :param protocols: List of allowed protocols.

        If no protocol is provided by the user -- the first protocol is used by default.

    :type protocols: str|list[str]
    """

    _url_rex = r'^' \
               r'(?:' r'(?P<scheme>[^:]+)' r'://?)?' \
               r'(?:' r'(?P<auth>[^@/]+(?::[^@/]*)?)' r'@)?' \
               r'(?P<host>[^/@:]+)' \
               r'(?:' r':(?P<port>\d+)' r')?' \
               r'(?:' r'(?P<path>/.*)' r')?' \
               r'$'

    name = u'URL'

    def __init__(self, protocols=('http', 'https')):
        self.protocols = tuple(x.lower()
                               for x in ((protocols,)
                                         if isinstance(protocols, six.string_types) else
                                         tuple(protocols)))

        self.rex = re.compile(self._url_rex)

    def __call__(self, v):
        # Match
        try:
            match = self.rex.match(v)
        except TypeError:
            raise Invalid(_(u'Wrong URL value type'), u'String', get_type_name(type(v)))

        # Matched?
        if not match:
            raise Invalid(_(u'Wrong URL format'))

        try:
            # Prepare
            parts = match.groupdict()
            if not parts['scheme']:
                parts['scheme'] = self.protocols[0]

            # Validate
            if parts['scheme'].lower() not in self.protocols:
                raise Invalid(u'Protocol not allowed', _(u',').join(self.protocols), six.text_type(parts['scheme']))
            if '.' not in parts['host']:
                raise Invalid(u'Incorrect domain name')

            # Combine back again
            return six.moves.urllib.parse.urlunsplit((
                parts['scheme'],
                  ('{auth}@'.format(**parts) if parts['auth'] else '')
                + parts['host']
                + (':{port}'.format(**parts) if parts['port'] else ''),
                parts['path'] or '/',
                None,
                None
            ))
        except Exception as e:
            if isinstance(e, Invalid):
                raise
            else:
                # Other error types are not expected, so reraise them
                raise RuntimeError('{}: {}'.format(type(e).__name__, e))


class Email(Match):
    """ Validate that a value is an e-mail address.

    This simply tests for the presence of the '@' sign, surrounded by some characters.

    ```python
    from good import Email

    schema = Schema(Email())

    schema('user@example.com')  #-> 'user@example.com'
    schema('user@localhost')  #-> 'user@localhost'
    schema('user')
    #-> Invalid: Invalid e-mail: expected E-Mail, got user
    ```
    """

    _rex = re.compile(r'.+@.+')

    def __init__(self):
        super(Email, self).__init__(self._rex, u'Invalid E-Mail', u'E-Mail')


__all__ = ('Lower', 'Upper', 'Capitalize', 'Title', 'Match', 'Replace', 'Url', 'Email')
